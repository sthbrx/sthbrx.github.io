Title: Context switching tasks on PowerPC
Date: 2023-11-28 08:00:00
Authors: Benjamin Gray
Category: Development
Tags: linux

## Introduction

This article is a dive (well, more of a wander) through some of the PowerPC
specific aspects of context switching, especially on the Special Purpose
Register (SPR) handling. It was motivated by my recent work on adding kernel
support for a hardware feature that interfaces with software through an SPR.


## Special Purpose Registers

An SPR is a register-like interface, allowing reading and/or writing various
configuration details of the CPU depending on the SPR in question. Similar to
General Purpose Registers (GPRs), many SPRs are per-CPU, so a given CPU manages
it's own value independently of the other CPUs. SPRs also tend to be supervisor
or hypervisor privileged, requiring userspace interact with them through a
kernel provided interface, if at all.

For example, the Count Register (CTR) is an SPR that enables several variations
of the branch instruction. It can be set to an address and used as an indirect
branch target, or certain conditional branch instructions can automatically
decrement this value and only perform the branch once it reaches zero.

Unlike the 32 general purpose registers (GPRs) though, we can only read and
write to SPRs through the dedicated `mfspr` and `mtspr` instructions (read "move
from SPR" and "move to SPR"). And writing to them is _slow_. Well, not so slow
that you will notice the occasional access, but there's one case in the kernel
that occurs extremely often and needs to change a lot of these SPRs: context
switches.


## What's a context anyway?

The context we are concerned about in this article is the task context. That's
all the state that makes up a 'task' in the eyes of the kernel. There are the
obvious components, like the current register values, thread ID, memory
mappings, etc., but there are also a few SPRs that get tracked on a per task
basis. By tracking SPR values for each task context, the kernel can emulate
per-task support for these SPRs, despite the hardware being per-CPU. The kernel
simply has to save the values when switching out a task, and set up the values
stored for the task being switched in.


## Processes, threads, and tasks

To understand the difference between these three concepts, we'll start with how
the kernel sees everything: tasks. Tasks are the kernel's view of an executable
unit, represented by a `struct task_struct`. This is an enormous struct (around
10K bytes) of all the pieces of data people have wanted to associate with a
particular unit of execution over the decades. The architecture specific state
of the task is stored in a one-to-one mapped `struct thread_struct`, available
through the `thread` member in the `task_struct`. The name 'thread' when
referring to this structure on a task should not be confused with the concept of
a thread we'll visit shortly.

A kernel task is highly flexible in terms of resource sharing. Many resources,
such as the memory mappings and file descriptor tables, are held through
reference counted handles to a backing data structure. This makes it easy to
mix-and-match sharing of different components between other tasks.

Crossing over to userspace, here we think of execution in terms of processes and
threads. Typically, a process is viewed as an execution context that is isolated
from other processes. For example, when created with the `fork()` syscall, the
child process gains a independent copy of the parent process's state. It will
share memory and open files at the time of the fork, but further changes to
these resources in either process are not reflected in the other. Internally,
the kernel simply duplicates the parent's task, and replaces relevant resources
with copies of the parent's values.

> Aside: for memory mappings the kernel uses copy-on-write (COW) to avoid
> duplicating all of the memory of the parent process. But from the point of
> view of the processes, it is no longer shared.

It is often useful to have multiple units of execution share things like memory
and open files though: this is what threads provide. A process can be 'split'
into multiple threads, each backed by its own kernel task. These threads can
share resources that are normally isolated between processes. In the lense of
multithreading, a 'process' as above is really a 'process group' containing one
or more threads.

The thread creation mechanism is very similar to process creation. The `clone()`
family of syscalls allow creating a new thread that shares resources with the
thread that cloned itself. Exactly what resources get shared between threads is
highly configurable, thanks to the kernel's task representation. See the
[`clone(2)` manpage](https://man7.org/linux/man-pages/man2/clone.2.html) for all
the options. Creating a process can be thought of as creating a thread where
nothing is shared. In fact, that's how `fork()` is implemented under the hood:
the `fork()` syscall is implemented as a thin wrapper around `clone()`'s
implementation where nothing is shared, including the process group ID.

```c
// kernel/fork.c  (approximately)

SYSCALL_DEFINE0(fork)
{
	struct kernel_clone_args args = {
		.exit_signal = SIGCHLD,
	};

	return kernel_clone(&args);
}

SYSCALL_DEFINE2(clone3, struct clone_args __user *, uargs, size_t, size)
{
	int err;

	struct kernel_clone_args kargs;
	pid_t set_tid[MAX_PID_NS_LEVEL];

	kargs.set_tid = set_tid;

	err = copy_clone_args_from_user(&kargs, uargs, size);
	if (err)
		return err;

	if (!clone3_args_valid(&kargs))
		return -EINVAL;

	return kernel_clone(&kargs);
}

pid_t kernel_clone(struct kernel_clone_args *args) {
	// do the clone
}
```

That's about it for the differences in processes, threads, and tasks from the
point of view of the kernel. A key takeaway here is that, while you will often
see processes and threads discussed with regards to userspace programs, there is
very little difference under the hood. To the kernel, it's all just tasks with
various degrees of shared resources.


## Anatomy of a context switch

Here we'll explore the actual function behind performing a context switch. We're
interested in the SPR handling especially, because that's going to inform how we
start tracking a new SPR on a per-task basis, so we'll be skimming over a lot of
unrelated aspects.

We start our investigation in the aptly named `context_switch()` function in
`kernel/sched/core.c`.

```c
// kernel/sched/core.c

/*
 * context_switch - switch to the new MM and the new thread's register state.
 */
static __always_inline struct rq *
context_switch(struct rq *rq, struct task_struct *prev,
               struct task_struct *next, struct rq_flags *rf)
```

Along with some scheduling metadata, we see it takes a previous task and a next
task. As we discussed above, the `struct task_struct` type describes an
execution context that defines (among other things) how to set up the state of
the CPU.

This function starts off with some generic preparation and memory context
changes, before getting to the meat of the function with `switch_to(prev, next,
prev)`. This `switch_to()` call is actually a macro, which unwraps to a call to
`__switch_to()`. It's also at this point that we enter the architecture specific
implementation.

> Aside: Changing the active memory mapping has no immediate effect on the
> running code due to address space quadrants. In the hardware, the top two bits
> of a 64 bit effective address determine what memory mapping is applied to
> resolve it to a real address. If it is a userspace address (top two bits are
> 0) then the configured mapping is used. But if it is a kernel address (top two
> bits are 1) then the PID 0 mapping is always used. So our change to the memory
> mapping only applies once we return to userspace, or try to access memory
> through a userspace address (through `get_user()` and `put_user()`). The other
> two values (0b01 and 0b10) are used by the hypervisor to control whether it
> wants to use the hypervisor or supervisor state mappings.

```c
// arch/powerpc/include/asm/switch_to.h  (switch_to)
// arch/powerpc/kernel/process.c         (__switch_to)

struct task_struct *__switch_to(struct task_struct *prev,
                                struct task_struct *new)
```

Here we've only got our previous and next tasks to work with, focusing on just
doing the switch.

Once again, we'll skip through most of the implementation. You'll see a few odds
and ends being handled: asserting we won't be taking any interrupts, handling
some TLB flushing, a copy-paste edge case, and some breakpoint handling on
certain platforms. Then we reach what we were looking for: `save_sprs()`. The
whole section looks something like as follows

```c
	/*
	 * We need to save SPRs before treclaim/trecheckpoint as these will
	 * change a number of them.
	 */
	save_sprs(&prev->thread);

	/* Save FPU, Altivec, VSX and SPE state */
	giveup_all(prev);

	__switch_to_tm(prev, new);

	if (!radix_enabled()) {
		/*
		 * We can't take a PMU exception inside _switch() since there
		 * is a window where the kernel stack SLB and the kernel stack
		 * are out of sync. Hard disable here.
		 */
		hard_irq_disable();
	}

	/*
	 * Call restore_sprs() and set_return_regs_changed() before calling
	 * _switch(). If we move it after _switch() then we miss out on calling
	 * it for new tasks. The reason for this is we manually create a stack
	 * frame for new tasks that directly returns through ret_from_fork() or
	 * ret_from_kernel_thread(). See copy_thread() for details.
	 */
	restore_sprs(old_thread, new_thread);
```


The `save_sprs()` function itself does the following to its `prev->thread`
argument.

```c
// arch/powerpc/kernel/process.c

static inline void save_sprs(struct thread_struct *t)
{
#ifdef CONFIG_ALTIVEC
	if (cpu_has_feature(CPU_FTR_ALTIVEC))
		t->vrsave = mfspr(SPRN_VRSAVE);
#endif
#ifdef CONFIG_SPE
	if (cpu_has_feature(CPU_FTR_SPE))
		t->spefscr = mfspr(SPRN_SPEFSCR);
#endif
#ifdef CONFIG_PPC_BOOK3S_64
	if (cpu_has_feature(CPU_FTR_DSCR))
		t->dscr = mfspr(SPRN_DSCR);

	if (cpu_has_feature(CPU_FTR_ARCH_207S)) {
		t->bescr = mfspr(SPRN_BESCR);
		t->ebbhr = mfspr(SPRN_EBBHR);
		t->ebbrr = mfspr(SPRN_EBBRR);

		t->fscr = mfspr(SPRN_FSCR);

		/*
		 * Note that the TAR is not available for use in the kernel.
		 * (To provide this, the TAR should be backed up/restored on
		 * exception entry/exit instead, and be in pt_regs.  FIXME,
		 * this should be in pt_regs anyway (for debug).)
		 */
		t->tar = mfspr(SPRN_TAR);
	}

	if (cpu_has_feature(CPU_FTR_DEXCR_NPHIE))
		t->hashkeyr = mfspr(SPRN_HASHKEYR);
#endif
}
```

Later, we set up the SPRs of the new task with `restore_sprs()`:

```c
// arch/powerpc/kernel/process.c

static inline void restore_sprs(struct thread_struct *old_thread,
				struct thread_struct *new_thread)
{
#ifdef CONFIG_ALTIVEC
	if (cpu_has_feature(CPU_FTR_ALTIVEC) &&
	    old_thread->vrsave != new_thread->vrsave)
		mtspr(SPRN_VRSAVE, new_thread->vrsave);
#endif
#ifdef CONFIG_SPE
	if (cpu_has_feature(CPU_FTR_SPE) &&
	    old_thread->spefscr != new_thread->spefscr)
		mtspr(SPRN_SPEFSCR, new_thread->spefscr);
#endif
#ifdef CONFIG_PPC_BOOK3S_64
	if (cpu_has_feature(CPU_FTR_DSCR)) {
		u64 dscr = get_paca()->dscr_default;
		if (new_thread->dscr_inherit)
			dscr = new_thread->dscr;

		if (old_thread->dscr != dscr)
			mtspr(SPRN_DSCR, dscr);
	}

	if (cpu_has_feature(CPU_FTR_ARCH_207S)) {
		if (old_thread->bescr != new_thread->bescr)
			mtspr(SPRN_BESCR, new_thread->bescr);
		if (old_thread->ebbhr != new_thread->ebbhr)
			mtspr(SPRN_EBBHR, new_thread->ebbhr);
		if (old_thread->ebbrr != new_thread->ebbrr)
			mtspr(SPRN_EBBRR, new_thread->ebbrr);

		if (old_thread->fscr != new_thread->fscr)
			mtspr(SPRN_FSCR, new_thread->fscr);

		if (old_thread->tar != new_thread->tar)
			mtspr(SPRN_TAR, new_thread->tar);
	}

	if (cpu_has_feature(CPU_FTR_P9_TIDR) &&
	    old_thread->tidr != new_thread->tidr)
		mtspr(SPRN_TIDR, new_thread->tidr);

	if (cpu_has_feature(CPU_FTR_DEXCR_NPHIE) &&
	    old_thread->hashkeyr != new_thread->hashkeyr)
		mtspr(SPRN_HASHKEYR, new_thread->hashkeyr);
#endif

}
```

The gist is we first perform a series of `mfspr` operations, serialising the SPR
values of the currently running task into its associated `task_struct`. Then we
do a series of `mtspr` operations to deserialize the desired values of the new
task back into the CPU.

This procedure has two interesting optimisations, as explained by [the
commit](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?h=v6.7-rc3&id=152d523e6307)
that introduces `save_sprs()` and `restore_sprs()`:

> powerpc: Create context switch helpers save_sprs() and restore_sprs()
>
> Move all our context switch SPR save and restore code into two helpers. We do
> a few optimisations:
>
> - Group all mfsprs and all mtsprs. In many cases an mtspr sets a scoreboarding
> bit that an mfspr waits on, so the current practise of mfspr A; mtspr A; mfpsr
> B; mtspr B is the worst scheduling we can do.
>
> - SPR writes are slow, so check that the value is changing before writing it.

And that's basically it, as far as the implementation goes at least. When first
investigating this one question that kept nagging me was: why do we read these
values here, instead of tracking them as they are set? The answer is that we
either don't know what they were set to, or they could change themselves
according to some event. As they are not general purpose read/write registers,
and instead reflect some kind of CPU state, some SPRs will automatically update
in response to events or changes in CPU state. For example, condition flags on
arithmetic operations are reflected in the Condition Register (CR). Other times
they might be directly accessible to userspace, which can set them arbitrarily
without kernel knowledge. Some of these SPRs are also 'uninteresting' to the
kernel, so it does not preserve them with the rest of the registers on


## Did you catch the issue with `restore_sprs()`?

If you paid close attention, you might have noticed that the previous task being
passed to `restore_sprs()` is not the same as the one being passed to
`save_sprs()`. We have the following instead

```c
struct task_struct *__switch_to(struct task_struct *prev,
	struct task_struct *new)
{
	// ...
	new_thread = &new->thread;
	old_thread = &current->thread;
	// ...
	save_sprs(&prev->thread);             // using prev->thread
	// ...
	restore_sprs(old_thread, new_thread); // using old_thread (current->thread)
	// ...
	last = _switch(old_thread, new_thread);
	// ...
	return last;
}
```

What gives? As far as I can determine, we require that the `prev` argument to
`__switch_to` is always the currently running task. And on PowerPC, we can
access the currently running task's thread struct through the `current` macro.
So, in theory, `current->thread` is an alias for `prev->thread`. Anything else
wouldn't make any sense here, as we are storing the SPR values into
`prev->thread`, but making decisions about their values in `restore_sprs()`
based on the `current->thread` serialised values.

As for why we use both, it appears to be historical. We originally ran
`restore_sprs()` after `_switch()`, which finishes swapping state from the
original thread to the one being loaded in. This means our stack and registers
are swapped out, so our `prev` variable we stored our current SPRs in is lost to
us: it is now the `prev` of the task we just woke up. In fact, we've completely
lost any handle to the task that just swapped itself out. Well, almost: that's
where the `last` return value of `_switch()` comes in. This is a handle to the
task that just went to sleep, and we were originally reloading `old_thread`
based on this `last` value. However a future patch moved `restore_sprs()` to
above the `_switch()` call thanks to an edge case with newly created tasks, but
the use of `old_thread` apparently remained.


## Conclusion

Congratulations, you are now an expert on several of the finer details of
context switching on PowerPC. Well, hopefully you learned something new and/or
interesting at least. I definitely didn't appreciate a lot of the finer details
until I went down the rabbit hole of differentiating threads, processes, and
tasks, and the whole situation with `prev` vs `old_thread`.


## Bonus tidbit

The kernel's implementation of doubly-linked lists does not follow the classic
implementation, where a list node contains a next, previous, and data pointer.
No, if you look at the actual struct definition you will find

```c
struct hlist_node {
	struct hlist_node *next, **pprev;
};
```

which decidedly does _not_ contain any data component.

It turns out that the kernel expects you to embed the node as a field on the
data struct, and the data-getter applies a mixture of macro and compiler builtin
magic to do some pointer arithmetic to convert a node pointer into a pointer to
the structure it belongs to. Naturally this is incredibly type-unsafe, but it's
elegant in its own way.
