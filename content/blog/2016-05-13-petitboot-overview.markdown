Title: Tell Me About Petitboot
Date: 2016-05-13 15:23
Authors: Samuel Mendoza-Jonas
Category: Petitboot
Tags: petitboot, power, p8, openpower, goodposts, realcontent

A Google search for 'Petitboot' brings up results from a number of places, some describing its use on [POWER servers](https://www.ibm.com/support/knowledgecenter/linuxonibm/liabp/liabppetitboot.htm), others talking about how to use it on the [PS3](http://jk.ozlabs.org/projects/petitboot/), in varying levels of detail. I tend to get a lot of general questions about Petitboot and its behaviour, and have had a few requests for a broad "Welcome to Petitboot" blog, suggesting that existing docs deal with more specific topics.. or that people just aren't reading them :)

So today we're going to take a bit of a crash course in the what, why, and possibly how of Petitboot. I won't delve too much into technical details, and this will be focussed on Petitboot in POWER land since that's where I spend most of my time.
Here we go!

What
-----------
Aside from a whole lot of firmware and kernel logs flying past, the first thing you'll see when booting a POWER server<sup>In OPAL mode at least...</sup> is Petitboot's main menu:

![Main Menu][00]

Petitboot is the first interact-able component a user will see. The word 'BIOS' gets thrown around a lot when discussing this area, but that is wrong, and the people using that word are wrong.

When the OPAL firmware layer [Skiboot](https://github.com/open-power/skiboot) has finished its own set up, it loads a certain binary (stored on the BMC) into memory and jumps into it. This could hypothetically be anything, but for any POWER server right now it is 'Skiroot'. Skiroot is a full Linux kernel and userspace, which runs Petitboot. People often say Petitboot when they mean Skiroot - technically Petitboot is the server and UI processes that happen to run within Skiroot, and Skiroot is the full kernel and rootfs package. This is more obvious when you look at the [op-build](https://github.com/open-power/op-build) project - Petitboot is a package built as part of the kernel and rootfs created by Buildroot.

Petitboot is made of two major parts - the UI processes (one for each available console), and the 'discover' server. The discover server updates the UI processes, manages and scans available disks and network devices, and performs the actual booting of host operating systems. The UI, running in ncurses, displays these options, allows the user to edit boot options and system configuration, and tells the server which boot option to kexec.

Why
-----------

The 'why' delves into some of the major architectural differences between a POWER machine and your average x86 machine which, as always, could spread over several blog posts and/or a textbook.

POWER processors don't boot themselves, instead the attached Baseboard Management Controller (BMC) does a lot of low-level poking that gets the primary processor into a state where it is ready to execute instructions. PowerVM systems would then jump directly into the PHYP hypervisor - any subsequent OS, be it AIX or Linux, would then run as a 'partition' under this hypervisor.

What we all really want though is to run Linux directly on the hardware, which meant a new boot process would have to be thought up while still maintaining compatibility with PowerVM so systems could be booted in either mode. Thus became OPAL, and its implementation [Skiboot](https://github.com/open-power/skiboot). Skipping over *so much* detail, the system ends up booting into Skiboot which acts as our firmware layer. Skiboot isn't interactive and doesn't really care about things like disks, so it loads another binary into memory and executes it - Skiroot!

Skiroot exists as an alternative to writing a whole new bootloader just for POWER in OPAL mode, or going through the effort to port an existing bootloader to understand the specifics of POWER. Why do all that when Linux already exists and already knows how to handle disks, network interfaces, and a thousand other things? Not to mention that when Linux gains support for fancy new devices so do we, and adding new features of our own is as simple as writing your average Linux program.

Skiroot itself (not including Skiboot) is roughly comparable to UEFI, or at least much more so than legacy BIOS implementations. But whereas UEFI tends to be a monolithic blob of fairly platform-specific code (in practice), Skiroot is simply a small Linux environment that anyone could put together with Buildroot.

A much better insight into the development and motivation behind Skiroot and Petitboot is available in Jeremy's [LCA2013 talk](https://www.youtube.com/watch?v=oxmMJMibZQ8)

Back to Petitboot
------------------

Petitboot is the part of the 'bootloader' that *did* need to be written, because users probably wouldn't be too thrilled if they had to manually mount disks and kexec their kernels every time they booted the machine. The Petitboot server process mounts any available disk devices and scans them for available operating systems. That's not to say that it scans the entire disk, because otherwise you could be waiting for quite some time, but rather it looks in a list of common locations for bootloader configuration files. This is handy because it means the operating system doesn't need to have any knowledge of Petitboot - it just uses its usual install scripts and Petitboot reads them to know what is available.
At the same time Petitboot makes PXE requests on configured network interfaces so we can netboot, and allows these various sources to be given relative priorities for auto-boot, plus a number of other ways to specially configure booting behaviour.

A particularly neat feature of existing in a Linux environment is the ability to easily recover from boot problems; whereas on another system you might need to use a Live CD to fix a misconfiguration or recover a broken filesystem, in Skiroot you can just drop to the shell and fix the issue right there.

In summary, Petitboot/Skiroot is a small but capable Linux environment that every OPAL POWER machine boots into, gathering up all the various local and remote boot possibilities, and presenting them to you in a state-of-the-art ncurses interface. Petitboot updates all the time, and if you come across a feature that you think Petitboot is missing, patches are very welcome at [petitboot@lists.ozlabs.org](mailto:petitboot@lists.ozlabs.org) (or hassle me on IRC)!

[00]: /images/sammj/mainmenu.png
