Title: Tracking SPRs during a context switch
Date: 2023-11-28 08:00:00
Authors: Benjamin Gray
Category: Development
Tags: linux

## Introduction

I've recently been adding kernel support for a hardware feature that interfaces with the OS through a Special Purpose Register (SPR). An SPR is a register-like interface to some state of the CPU, allowing reading and/or writing various configuration details depending on the SPR in question. Similar to General Purpose Registers (GPRs), most (not all!) SPRs are per-CPU, so a given CPU manages it's own value independently of the other CPUs. SPRs tend to be supervisor or hypervisor privileged, requiring userspace interact with them through a kernel provided interface, if at all.

For example, the CTR (Count Register) is an SPR that enables several branch variations. It can be set to an arbitrary value and used as an indirect branch location, or certain conditional branch instructions can automatically decrement this value and only perform the branch once it reaches zero.

Unlike the 32 general purpose registers (GPRs) though, we can only read and write to these SPRs through the dedicated `mfspr` and `mtspr` instructions (read "move from SPR" and "move to SPR"). And this is _slow_. Well, not so slow that you will notice the occasional access, but there's one case in the kernel that occurs extremely often and needs to change a lot of these SPRs: context switches.


## What's a context anyway?

The context we are concerned about in this article is the thread context. That's all the state that makes up a 'thread' in the eyes of the kernel. There are the obvious components, like the current register values, thread ID, memory mappings, etc., but there are also a few SPRs that get tracked on a per thread basis. By tracking SPR values for each thread context, the kernel can emulate per-thread support for these SPRs, despite the hardware being per-CPU. The kernel simply has to save the values when switching out a thread, and set up the values stored for the thread being switched in.

Some of this switching occurs early in the interrupt handler boilerplate, for values that are highly volatile (like GPRs) and need to be preserved before the kernel clobbers them with its own usage. Some, however, are fine to leave as-is until the current user thread is actually being swapped to a different one.


## Processes, threads, and tasks

What's the difference? Who knows


## Anatomy of a context switch

We start our investigation in the aptly named `context_switch()` function in `kernel/sched/core.c`.

```c
// kernel/sched/core.c

/*
 * context_switch - switch to the new MM and the new thread's register state.
 */
static __always_inline struct rq *
context_switch(struct rq *rq, struct task_struct *prev,
               struct task_struct *next, struct rq_flags *rf)
```

Along with some scheduling metadata, we see it takes a previous task and a next task. The `struct task_struct` type is what we've been calling the thread context (though later we'll look at a `struct thread_struct`, so the terminology is a little imprecise here).

This function starts off with some generic preparation and memory context changes, before getting to the meat of the function with `switch_to(prev, next, prev)`. This `switch_to()` call is actually a macro, which unwraps to a call to `__switch_to()`. It's also at this point that we've entered architecture specific implementation.

> Aside: Changing the active memory mapping has no immediate effect on the running code due to address space quadrants. In the hardware, the top two bits of a 64 bit effective address determine what memory mapping is applied to resolve it to a real address. If it is a userspace address (top two bits are 0) then the configured mapping is used. But if it is a kernel address (top two bits are 1) then the PID 0 mapping is always used. So our change to the memory mapping only applies once we return to userspace, or try to access memory through a userspace address (through `get_user()` and `put_user()`). The other two values (0b01 and 0b10) are used by the hypervisor to control whether it wants the supervisor or problem state mappings.

```c
// arch/powerpc/include/asm/switch_to.h  (switch_to)
// arch/powerpc/kernel/process.c         (__switch_to)

struct task_struct *__switch_to(struct task_struct *prev,
                                struct task_struct *new)
```

Here we've only got our previous and next tasks to work with, focusing on just doing the switch.
