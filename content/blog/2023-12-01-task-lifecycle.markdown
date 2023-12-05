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

Towards the end of the init sequence we reach `rest_init()`. In here we finally dynamically create our first two tasks: the init task (not to be confused with `init_task`), and the kthreadd task (with the double 'd'). The init task is (eventually) the userspace init process. We create it first to get the PID value 1, which is relied on by a number of things in the kernel and in userspace. The kthreadd task provides an asynchronous creation mechanism for kthreads: callers append their thread parameters to a dedicated list, and the kthreadd task spawns any entries on the list whenever it gets scheduled. Creating the tasks automatically put them on the scheduler run queue, and they might even have started automatically with preemption.

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


## Transitioning the init task to userspace

The last remaining job of the kernel side of the init task is to actually load in and execute the userspace program. It's not like we can just call the userspace entry point though: we need to get a little creative here.

The first step has already been done for us. When we created the init task, we declared it to have a kernel entry point, but that is was not a kthread. The `clone_thread()` implmenetation doesn't set the given entry point directly: it instead sets a small handler that is actually used when the new task eventually gets woken up. The shim expects the requested entry point to be passed via a specific non-volatile register and, in the case of a kthread, basically just calls this after some minor bookkeeping. A kthread should never return directly, so we trap if this happens.

```c
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

```c
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

The actual setting up of the syscall frame is handled by the `[try_]run_init_process()` function. The interesting call path goes like

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


## Secondary processors

Until now we've focused on the boot CPU. While the utility of a task still applies to a uniprocessor system (perhaps even more so than one with hardware parallelism), a nice benefit is being able to distribute the tasks onto any other compatible processors on the system. But before we can start scheduling on other CPU cores, we need to bring them online and initialise them to a state ready for the scheduler.

On a pSeries platform, the secondary CPUs are held by the firmware until explicitly released by the guest. During boot the boot CPU will, as part of `prom_init()`, call `prom_hold_cpus()`. This iterates the list of held secondary processors and releases them one by one to the `__secondary_hold` function in `arch/powerpc/kernel/head_64.S`. As each starts executing `__secondary_hold`, it writes a value to the `__secondary_hold_acknowledge` variable that the boot CPU is watching. The secondary processor then immediately starts spinning on `__secondary_hold_spinloop`, waiting for it to become non-zero, while the boot CPU moves on to the the next processor.

Once every coprocessor is confirmed to be spinning on `__secondary_hold_spinloop`, the boot CPU continues on with its boot sequence. Eventually it reaches `smp_release_cpus()` early in `start_kernel()` through `setup_arch()`, which writes the desired entry point address to `__secondary_hold_spinloop`. All the spinning coprocessors now see this value, and jump to it. This function, `generic_secondary_smp_init()`, will set up the coprocessor's PACA value, perform some machine specific initialisation if `cur_cpu_spec->cpu_restore` is set, atomically decrement a `spinning_secondaries` variable, and start spinning once again until further notice. This time it is waiting on the PACA field `cpu_start`, so we can start coprocessors individually.

> The `cur_cpu_spec->cpu_restore` machine specific initialisation is based on the machine that got selected in `arch/powerpc/kernel/cpu_specs_book3s_64.h`. This is where the `__restore_cpu_*` family of functions might be called. These mostly initialise certain SPRs to sane values.

We leave the coprocessors here for another while, until we eventually get back to them via the hotplug codepath (TODO: How). There's a bit more initialisation in Assembly, but they reach `start_secondary()` without much hassle. After yet more initialisation, we finally reach `cpu_startup_entry()` and enter the idle loop. We're now under control of the scheduler at last.
