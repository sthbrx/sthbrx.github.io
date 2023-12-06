Title: Lifecycle of a kernel task
Date: 2023-12-01 08:00:00
Authors: Benjamin Gray
Category: Development
Tags: linux

## Introduction

CPU cores are very limited in number. Right now my computer tells me it's running around 500 processes, and I definitely do not have that many CPU cores. The ability for the operating system to virtualise the concept of an 'execution unit' and swap them in and out of running on the limited pool CPU cores is one of the foundations of modern computing.

The Linux kernel calls these virtual execution units _tasks_. Each task encapsulates all the information the kernel needs to swap it in and out of running on a CPU core, including register state, memory mappings, file descriptor table, and any other resource that needs to be tied to a particular task. Nearly every workload in the kernel, including kernel background jobs and userspace threads, is handled by this unified task concept. The kernel uses a scheduler to determine when and where to run tasks according to some parameters, such as maximising throughput, minimising latency, or whatever other characteristics the user desires.

In this article, we'll dive into the lifecycle of a task in the kernel.


## Booting

The kernel starts up with no concept of tasks, just running from whatever location the bootloader decided to start it at. The first idea of a task takes root in `early_setup()` (`arch/powerpc/kernel/setup_64.c`), where we initialise the processor address communications area (PACA). We use the PACA to (among other things) hold a reference to the active task, and the task we start with is the special `init_task`. This task is a statically defined instance of a `task_struct` that is the root of all future tasks. Its resources are various `init_*` versions of things, themselves each statically defined somewhere. We aren't really taking advantage of tasks at this point, it's more about making it look like we're a task for any initialisation code that cares.

From here we continue on with the boot process. At some point we allocate a PACA for each CPU; these all get the `init_task` task as well (all referencing the same structure, not copies of it).

The next point of interest is `fork_init()`. This is one of the initialisation functions in `start_kernel()`, the generic entry point of the kernel once any arch specific setup is done. Here we create a `task_struct` allocator to serve any task creation requests. We also limit the number of tasks here, dynamically picking the limit based on the available memory, page size, and a fixed upper bound.

Towards the end of the init sequence we reach `rest_init()`. In here we finally dynamically create our first two tasks: the init task (not to be confused with `init_task`), and the kthreadd task (with the double 'd'). The init task is (eventually) the userspace init process. We create it first to get the PID value 1, which is relied on by a number of things in the kernel and in userspace[^5]. The kthreadd task provides an asynchronous creation mechanism for kthreads: callers append their thread parameters to a dedicated list, and the kthreadd task spawns any entries on the list whenever it gets scheduled. Creating the tasks automatically put them on the scheduler run queue, and they might even have started automatically with preemption.

[^5]: One example of the init task being special is that the kernel will not allow its process to be killed. It must always have at least one thread.

```c
// init/main.c

noinline void __ref __noreturn rest_init(void)
{
	struct task_struct *tsk;
	int pid;

	rcu_scheduler_starting();
	/*
	 * We need to spawn init first so that it obtains pid 1, however
	 * the init task will end up wanting to create kthreads, which, if
	 * we schedule it before we create kthreadd, will OOPS.
	 */
	pid = user_mode_thread(kernel_init, NULL, CLONE_FS);
	/*
	 * Pin init on the boot CPU. Task migration is not properly working
	 * until sched_init_smp() has been run. It will set the allowed
	 * CPUs for init to the non isolated CPUs.
	 */
	rcu_read_lock();
	tsk = find_task_by_pid_ns(pid, &init_pid_ns);
	tsk->flags |= PF_NO_SETAFFINITY;
	set_cpus_allowed_ptr(tsk, cpumask_of(smp_processor_id()));
	rcu_read_unlock();

	numa_default_policy();
	pid = kernel_thread(kthreadd, NULL, NULL, CLONE_FS | CLONE_FILES);
	rcu_read_lock();
	kthreadd_task = find_task_by_pid_ns(pid, &init_pid_ns);
	rcu_read_unlock();

	/*
	 * Enable might_sleep() and smp_processor_id() checks.
	 * They cannot be enabled earlier because with CONFIG_PREEMPTION=y
	 * kernel_thread() would trigger might_sleep() splats. With
	 * CONFIG_PREEMPT_VOLUNTARY=y the init task might have scheduled
	 * already, but it's stuck on the kthreadd_done completion.
	 */
	system_state = SYSTEM_SCHEDULING;

	complete(&kthreadd_done);

	/*
	 * The boot idle thread must execute schedule()
	 * at least once to get things moving:
	 */
	schedule_preempt_disabled();
	/* Call into cpu_idle with preempt disabled */
	cpu_startup_entry(CPUHP_ONLINE);
}

```

After this, it basically just enters the scheduler. We're now almost fully task driven, and our journey picks back up inside of the init task.

> Hint: you can see where the `init_task` vs the init task is used in the console. The `init_task` has PID 0, so appears as `T0` in the log line metadata. The init task has PID 1, so appears as `T1`.


## The init task

When we created the init task, we set the entry point to be the `kernel_init()` function. Execution simply begins from here once we get scheduled. The very first thing we do is wait for the kthreadd task to be up and running: bad things would happen if we tried to use kernel services that rely on kthreads otherwise.

The wait mechanism itself also interacts with the scheduler a lot: starting with a common `struct completion` object, the waiting task registers itself as awaiting the object to complete. Specifically, it adds its task handle to a queue on the completion object. It then loops calling `schedule()`, which yields itself to the scheduler, until the completion object is flagged as done. Somewhere else, such as another task, the completion object will eventually be marked as completed. As part of this the task marking the completion tries to wake up a task that might have registered itself as waiting earlier.

In the kthreadd case, the init task waits on a completion object that `kernel_init()` marks completed after creating kthreadd. We could technically avoid this synchronization altogether just by creating kthreadd first, but then the init task wouldn't have PID 1.

The rest of the init task wraps up the initialisation stage as a whole. Mostly it moves the system into the 'running' state after freeing any memory marked as for initialisation only (set by `__init` annotations).

Once fully initialised and running, the init tasks attempts to execute the userspace init program.

```c
	if (execute_command) {
		ret = run_init_process(execute_command);
		if (!ret)
			return 0;
		panic("Requested init %s failed (error %d).",
		      execute_command, ret);
	}

	if (CONFIG_DEFAULT_INIT[0] != '\0') {
		ret = run_init_process(CONFIG_DEFAULT_INIT);
		if (ret)
			pr_err("Default init %s failed (error %d)\n",
			       CONFIG_DEFAULT_INIT, ret);
		else
			return 0;
	}

	if (!try_to_run_init_process("/sbin/init") ||
	    !try_to_run_init_process("/etc/init") ||
	    !try_to_run_init_process("/bin/init") ||
	    !try_to_run_init_process("/bin/sh"))
		return 0;

	panic("No working init found.  Try passing init= option to kernel. "
	      "See Linux Documentation/admin-guide/init.rst for guidance.");
```

There are several locations it will attempt, in order:

1. Ramdisk file set by `rdinit=` boot command line parameter, with default path `/init`.
2. File set by `init=` boot command line parameter.
3. `/sbin/init`
4. `/etc/init`
5. `/bin/init`
6. `/bin/sh`

Should none of these work, the kernel just panics. Which seems fair.


## Aside: secondary processors

Until now we've focused on the boot CPU. While the utility of a task still applies to a uniprocessor system (perhaps even more so than one with hardware parallelism), a nice benefit of encapsulating all the execution state into a data structure is being able to load the task onto any other compatible processor on the system. But before we can start scheduling on other CPU cores, we need to bring them online and initialise them to a state ready for the scheduler.

On a pSeries platform, the secondary CPUs are held by the firmware until explicitly released by the guest. During boot the boot CPU will, as part of `prom_init()`, call `prom_hold_cpus()`. This iterates the list of held secondary processors and releases them one by one to the `__secondary_hold` function in `arch/powerpc/kernel/head_64.S`. As each starts executing `__secondary_hold`, it writes a value to the `__secondary_hold_acknowledge` variable that the boot CPU is watching. The secondary processor then immediately starts spinning on `__secondary_hold_spinloop`, waiting for it to become non-zero, while the boot CPU moves on to the the next processor.

Once every coprocessor is confirmed to be spinning on `__secondary_hold_spinloop`, the boot CPU continues on with its boot sequence. Eventually it reaches `smp_release_cpus()` early in `start_kernel()` through `setup_arch()`, which writes the desired entry point address to `__secondary_hold_spinloop`. All the spinning coprocessors now see this value, and jump to it. This function, `generic_secondary_smp_init()`, will set up the coprocessor's PACA value, perform some machine specific initialisation if `cur_cpu_spec->cpu_restore` is set[^4], atomically decrement a `spinning_secondaries` variable, and start spinning once again until further notice. This time it is waiting on the PACA field `cpu_start`, so we can start coprocessors individually.

[^4]: The `cur_cpu_spec->cpu_restore` machine specific initialisation is based on the machine that got selected in `arch/powerpc/kernel/cpu_specs_book3s_64.h`. This is where the `__restore_cpu_*` family of functions might be called, which mostly initialise certain SPRs to sane values.

We leave the coprocessors here for another while, until we eventually get back to them via a hotplug codepath. This boot set of CPUs are brought online by the init task as one of the actions it performs in `kernel_init_freeable() -> smp_init()`. Once told to stop spinning there's a bit more initialisation in Assembly, but they reach `start_secondary()` without much hassle. After yet more initialisation, we finally reach `cpu_startup_entry()` and enter the idle loop. We're now under control of (or, in a better sense, acting as) the scheduler at last.


## Transitioning the init task to userspace

The last remaining job of the kernel side of the init task is to actually load in and execute the userspace program. It's not like we can just call the userspace entry point though: we need to get a little creative here.

The first step has already been done for us. When we created the init task, we declared it to have a kernel entry point, but that it was not a kthread. The `clone_thread()` implementation doesn't set the given entry point directly: it instead sets a small shim that is actually used when the new task eventually gets woken up. The shim expects the requested entry point to be passed via a specific non-volatile register and, in the case of a kthread, basically just calls this after some minor bookkeeping. A kthread should never return directly, so we trap if this happens.

```asm
_GLOBAL(start_kernel_thread)
	bl	CFUNC(schedule_tail)
	mtctr	r14
	mr	r3,r15
#ifdef CONFIG_PPC64_ELF_ABI_V2
	mr	r12,r14
#endif
	bctrl
	/*
	 * This must not return. We actually want to BUG here, not WARN,
	 * because BUG will exit the process which is what the kernel thread
	 * should have done, which may give some hope of continuing.
	 */
100:	trap
	EMIT_BUG_ENTRY 100b,__FILE__,__LINE__,0
```

But the init task isn't a kthread. We passed a kernel entrypoint to `copy_thread()` but did not set the kthread flag, so `copy_thread()` inferred that this means the task will eventually turn into a userspace task. This makes it use `ret_from_kernel_user_thread()` for the entry point shim.

```asm
_GLOBAL(ret_from_kernel_user_thread)
	bl	CFUNC(schedule_tail)
	mtctr	r14
	mr	r3,r15
#ifdef CONFIG_PPC64_ELF_ABI_V2
	mr	r12,r14
#endif
	bctrl
	li	r3,0
	/*
	 * It does not matter whether this returns via the scv or sc path
	 * because it returns as execve() and therefore has no calling ABI
	 * (i.e., it sets registers according to the exec()ed entry point).
	 */
	b	.Lsyscall_exit
```

We start off identically to a kthread, except here we expect the task to return. This is the key: when the init task wants to transition to userspace, it sets up the stack frame as if we were serving a syscall. It then returns, which runs the syscall exit procedure that culminates in an `rfid` to userspace.

The actual setting up of the syscall frame is handled by the `(try_)run_init_process()` function. The interesting call path goes like

```c
run_init_process()
  kernel_execve()
    bprm_execve()
      exec_binprm()
        search_binary_handler()
          list_for_each_entry(fmt, &formats, lh)
            retval = fmt->load_binary(bprm);
```

The outer few calls mainly handle checking prerequisites and bookkeeping. The `exec_binrpm()` call also handles shebang redirection, allowing up to 5 levels of interpretor. At each level it invokes `search_binary_handler()`, which attempts to find a handler for the program file's format. Contrary to the name, the searcher will also immediately try to load the file if it finds an appropriate handler. It's this call to `load_binary` (dispatched to whatever handler was found) that sets up our userspace execution context, including the syscall return state.

All that's left to do here is return 0 all the way up the chain, which you'll see results in the init task returning to the shim that performs the syscall return sequence to userspace. The init task is now fully userspace.


## Creating other tasks

It feels like we've spent a lot of time discussing the init task. What about all the other tasks?

It turns out that the creation of the init task lifecycle is very similar to any other task. All tasks are clones of the task that created them (except the statically defined `init_task` we set early in boot). Note clone is being used in a loose sense here: it's not a one-to-one image of the parent. There's obviously a different task ID to distinguish it from the parent, but theres's also a configuration parameter that determines which components are shared, and which are made into independent copies. The implementation may also just decide to change some things that don't make sense to duplicate.

As we saw earlier, kthreads are created indirectly through a global list and kthreadd daemon task that does the actual cloning. This appears to have two benefits: allowing asynchronous task creation from atomic contexts, and ensuring all kthreads inherit a 'clean' task context, instead of whatever was active at the time.

Userspace task creation, beyond the init task, is driven by the userspace process invoking the `fork()` and `clone()` family of syscalls. Both of these are light wrappers over the `kernel_clone()` function, which we used earlier for the creation of the init task and kthreadd.

When a task runs a syscall in the `exec()` family, it doesn't create a new task. It instead hits the same code path as when we tried to run the userspace init program, where it loads in the context as defined by the program file and returns from the syscall (legitimately this time).


## Context switching

The last piece of the puzzle (as far as this article will look at!) is how tasks are switched in and out, and some of the rules around when it can and can't happen. Once the init and kthreadd tasks are created, we call `cpu_startup_entry(CPUHP_ONLINE)`. Any coprocessors have also been released to call this by now too. These are considered 'idle tasks', which serve to run when no other tasks are available to run. They will spin on a reschedule check, entering an idle state each loop until they see pending tasks to run. They then call `__schedule()` in a loop (also conditional on pending tasks existing), and then loop back to the idle loop once everything is handled.

The `__schedule()` function is the main guts of the scheduler, which until now has been some nebulous controller that's governing our tasks. It starts by deciding which pending task should run (a whole can of worms right there), and then executing `context_switch()` if it changes from the current task. `context_switch()` is the point where the `current` task starts to change. Specifically, you can trace the changing of `current` (i.e., the PACA being updated with a new task pointer) to the following path

```c
context_switch()
  switch_to()
    __switch_to()
      _switch()
        do_switch_64
          std	r6,PACACURRENT(r13)
```

One interesting consequence of tasks calling `context_switch()` is that the previous task is 'suspended'[^2] right where it saves its registers and puts in the new tasks's values. When it is woken up again at some point in the future it resumes right where it left off. So when you are reading the `__switch_to()` implementation, you are actually looking at two different tasks in the same function.

[^2]: Don't forget that the entire concept of tasks is made up by the kernel: from the hardware's point of view we haven't done anything interesting, just changed some registers.

But it gets even weirder: while tasks that put themselves to sleep here wake up inside of `_switch()`, new tasks being woken up for the first time start at a completely different location! So not only is the task changing, the `_switch()` call might not even return back to `__switch_to()`!


## Conclusion

And there you have it, everything<sup>_[citation needed]_</sup> you could ever need to know when getting started with tasks. Will you need to know this specifically? Hard to say. But hopefully it at least provides some useful pointers for understanding the execution model of the kernel.


## Questions

The following are some questions you might have (read: I had).

### Do userspace tasks run in the kernel?

Yes, 'userspace' tasks run in the kernel. We don't have dedicated tasks to swap out to. Thanks to address space quadrants we don't even need to change the active memory mapping: upon entry to the kernel we automatically start using the PID 0 mapping.


### Where does a task get allocated a PID?

Referring to the hardware PID, used for virtual memory translations, this is actually a property of the memory mapping struct (`mm_struct`). You can find a PID being allocated when a new `mm_struct` is created, which may or may not occur depending on the task clone parameters.


### How can the fork and exec syscalls be hooked into for arch specific handling?

Fork (and clone) will always invoke `copy_thread()`. The exec call will invoke `start_thread()` when loading a binary file. Any other kind of file (script, binfmt-misc) will eventually require some form of binary file to load/bootstrap it, so `start_thread()` should work for your purposes.

The task context of the calls is fairly predictable: `current` in `copy_thread()` refers to the parent because we are still in the middle of copying it. For `start_thread()` we have that `current` refers to the task that is going to be the new program because it is just configuring itself.


### Where do exceptions/interrupts fit in?

When a hardware interrupt triggers it just stops whatever it was doing and dumps us at the corresponding exception handler. Our `current()` value still points to whatever task is active (restoring the PACA is done very early). If we were in userspace (MSR<sub>PR</sub> is 0) we consider ourselves to be in 'process state'. This is, in some sense, the default state in the kernel. We are able to sleep (i.e., invoke the scheduler and swap ourselves out), take locks, and generally do anything you might like to do in kernel mode.

However we are a bit more restricted if we arrived at an interrupt from supervisor mode. For example, we don't know if we interrupted an atomic context, so we can't safely do anything that might cause sleep. This is why in some interrupt handlers like `do_program_check()` we have to check `user_mode(regs)` before we can read a userspace instruction[^1].

[^1]: The issue with reading a userspace instruction is that the page access may require the page be faulted in, which can sleep. There is a mechanism to disable the page fault handler specifically, but then we might not be able to read the instruction.
