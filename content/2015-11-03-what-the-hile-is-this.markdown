Title: "What the HILE is this?"
Date: 2015-11-03 15:02
Authors: Samuel Mendoza-Jonas
Category: Petitboot
Tags: petitboot, power, p8, openpower, goodposts, autoboot, realcontent, kexec, kernel

One of the cool features of POWER8 processors is the ability to run in either big- or little-endian mode. Several distros are already available in little-endian, but up until recently Petitboot has remained big-endian. While it has no effect on the OS, building Petitboot little-endian has its advantages, such as making support for vendor tools easier.
So it should just be a matter of compiling Petitboot LE right? Well...

### Switching Endianess ###

Endianess, and several other things besides, are controlled by the Machine State Register (MSR). Each processor in a machine has an MSR, and each bit of the MSR controls some aspect of the processor such as 64-bit mode or enabling interrupts. To switch endianess we set the LE bit (63) to 1.

When a processor first starts up it defaults to big-endian (bit 63 = 0). However the processor doesn't actually know the endianess of the kernel code it is about to execute - either it is big-endian and everything is fine, or it isn't and the processor will very quickly try to execute an illegal instruction.

The solution to this is an amazing little snippet of code in [arch/powerpc/boot/ppc_asm.h](https://github.com/torvalds/linux/blob/master/arch/powerpc/boot/ppc_asm.h#L65) (follow the link to see some helpful commenting):

```C
#define FIXUP_ENDIAN
	tdi   0, 0, 0x48;
	b     $+36;
	.long 0x05009f42;
	.long 0xa602487d;
	.long 0x1c004a39;
	.long 0xa600607d;
	.long 0x01006b69;
	.long 0xa6035a7d;
	.long 0xa6037b7d;
	.long 0x2400004c
```

By some amazing coincidence if you take the opcode for ``tdi 0, 0, 0x48`` and flip the order of the bytes it forms the opcode for ``b . + 8``. So if the kernel is big-endian, the processor will jump to the next instruction after this snippet. However if the kernel is little-endian we execute the next 8 instructions. These are written in reverse so that if the processor isn't in the right endian it interprets them backwards, executing the instructions shown in the linked comments above, resulting in MSR<sub>LE</sub> being set to 1.

When booting a little-endian kernel all of the above works fine - but there is a problem for Petitboot that will become apparent a little further down...

### Petitboot's Secret Sauce ###

The main feature of Petitboot is that it is a full (but small!) Linux kernel and userspace which scans all available devices and presents possible boot options. To boot an available operating system Petitboot needs to start executing the OS's kernel, which it accomplishes via [kexec](https://en.wikipedia.org/wiki/Kexec). Simply speaking kexec loads the target kernel into memory, shuts the current system down most of the way, and at the last moment sets the instruction pointer to the start of the target kernel. From there it's like booting any other kernel, including the FIXUP_ENDIAN section above.

### We've Booted! Wait... ###

So our LE Petitboot kernel boots fine thanks to FIXUP_ENDIAN, we kexec into some other kernel.. and everything falls to pieces.  
The problem is we've unwittingly changed one of the assumptions of booting a kernel; namely that MSR<sub>LE</sub> defaults to zero. When kexec-ing from an LE kernel we start executing the next kernel in LE mode. This itself is ok, the FIXUP_ENDIAN macro will handle the switch if needed. The problem is that the FIXUP_ENDIAN macro is relatively recent, first entering the kernel in early 2014. So if we're booting, say, an old Fedora 19 install with a v3.9 kernel - things go very bad, very quickly.

### Fix #1 ###

The solution seems pretty straightforward: find where we jump into the next kernel, and just before that make sure we reset the LE bit in the MSR. That's exactly what [this patch](https://github.com/antonblanchard/kexec-lite/commit/150b14e76a4b51f865b929ad9a9bf4133e2d3af7) to kexec-lite does.  
That worked up until I tested on a machine with more than one CPU. Remembering that the MSR is processor-specific, we also have to [reset the endianess of each secondary CPU](https://github.com/torvalds/linux/commit/ffebf5f391dfa9da3e086abad3eef7d3e5300249)  
Now things are looking good! All the CPUs are reset to big-endian, the target kernel boots fine, and then... 'recursive interrupts?!'

### HILE ###

Skipping the debugging process that led to this (hint: [mambo](https://www.flamingspork.com/blog/2014/12/03/running-skiboot-opal-on-the-power8-simulator/) is actually a pretty cool tool), these were the sequence of steps leading up to the problem:

* Little-endian Petitboot kexecs into a big-endian kernel
* All CPUs are reset to big-endian
* The big-endian kernel begins to boot successfully
* Somewhere in the device-tree parsing code we take an exception
* Execution jumps to the exception handler at [0x300](https://github.com/torvalds/linux/blob/master/arch/powerpc/kernel/exceptions-64s.S#L199)
* I notice that MSR<sub>LE</sub> is set to 1
* WHAT WHY IS THE LE BIT IN THE MSR SET TO 1
* We fail to read the first instruction at 0x300 because it's written in big-endian, so we jump to the exception handler at 0x300... oh no.

And then we very busily execute nothing until the machine is killed. I spend some time staring incredulously at my screen, then appeal to a [higher authority](https://github.com/torvalds/linux/blob/master/MAINTAINERS) who replies with "What is the HILE set to?"  
  
..the WHAT?  
Cracking open the [PowerISA](https://www.power.org/documentation/power-isa-v-2-07b/) reveals this tidbit:
> The Hypervisor Interrupt Little-Endian (HILE) bit is a bit
> in an implementation-dependent register or similar
> mechanism. The contents of the HILE bit are copied
> into MSR<sub>LE</sub> by interrupts that set MSR<sub>HV</sub> to 1 (see Section
> 6.5), to establish the Endian mode for the interrupt
> handler. The HILE bit is set, by an implementation-dependent
> method, during system initialization,
> and cannot be modified after system initialization.

To be fair, there are use cases for taking exceptions in a different endianess. The problem is that while HILE gets switched on when setting MSR<sub>LE</sub> to 1, it *doesn't* get turned off when MSR<sub>LE</sub> is set to zero. In particular the line "...cannot be modified after system initialization." led to a fair amount of hand wringing from myself and whoever would listen; if we can't reset the HILE bit, we simply can't use little-endian kernels for Petitboot.  
  
Luckily while on some other systems the machinations of the firmware might be a complete black box, Petitboot runs on OPAL systems - which means the firmware source is [right here](https://github.com/open-power/skiboot). In particular we can see here the OPAL call to [opal_reinit_cpus](https://github.com/open-power/skiboot/blob/master/core/cpu.c#L702) which among other things resets the HILE bit.  
This is actually what turns on the HILE bit in the first place, and is meant to be called early on in boot since it also clobbers a large amount of state. Luckily for us we don't need to hold onto any state since we're about to jump into a new kernel. We just need to choose an appropriate place where we can be sure we won't take an exception before we get into the next kernel: thus the [final patch to support PowerNV machines.](https://github.com/torvalds/linux/commit/e72bb8a5a884d022231149d407653923a1d79e53)
