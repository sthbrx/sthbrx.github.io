Title: Getting logs out of things
Authors: Andrew Donnellan
Date: 2016-03-22 18:00
Category: OpenPOWER
Tags: debugging, skiboot, OPAL, FSP, kernel, development

Here at OzLabs, we have an unfortunate habit of making our shiny Power computers very sad, which is a common problem in systems programming and kernel hacking. When this happens, we like having logs. In particular, we like to have the kernel log and the OPAL firmware log, which are, very surprisingly, rather helpful when debugging kernel and firmware issues.

Here's how to get them.

## From userspace

You're lucky enough that your machine is still up, yay! As every Linux sysadmin knows, you can just grab the kernel log using `dmesg`.

As for the OPAL log: we can simply ask OPAL to tell us where its log is located in memory, copy it from there, and hand it over to userspace. In Linux, as per standard Unix conventions, we do this by exposing the log as a file, which can be found in `/sys/firmware/opal/msglog`.

Annoyingly, the `msglog` file reports itself as size 0 (I'm not sure exactly why, but I *think* it's due to limitations in sysfs), so if you try to copy the file with `cp`, you end up with just a blank file. However, you can read it with `cat` or `less`.

## From `xmon`

`xmon` is a really handy in-kernel debugger for PowerPC that allows you to do basic debugging over the console without hooking up a second machine to use with `kgdb`. On our development systems, we often configure `xmon` to automatically begin debugging whenever we hit an oops or panic (using `xmon=on` on the kernel command line, or the `XMON_DEFAULT` Kconfig option). It can also be manually triggered:

	root@p86:~# echo x > /proc/sysrq-trigger
	sysrq: SysRq : Entering xmon
	cpu 0x7: Vector: 0  at [c000000fcd717a80]
    pc: c000000000085ad8: sysrq_handle_xmon+0x68/0x80
    lr: c000000000085ad8: sysrq_handle_xmon+0x68/0x80
    sp: c000000fcd717be0
	msr: 9000000000009033
	current = 0xc000000fcd689200
	paca    = 0xc00000000fe01c00   softe: 0        irq_happened: 0x01
    pid   = 7127, comm = bash
	Linux version 4.5.0-ajd-11118-g968f3e3 (ajd@ka1) (gcc version 5.2.1 20150930 (GCC) ) #1 SMP Tue Mar 22 17:01:58 AEDT 2016
	enter ? for help
	7:mon>

From `xmon`, simply type `dl` to dump out the kernel log. If you'd like to page through the log rather than dump the entire thing at once, use `#<n>` to split it into groups of `n` lines.

Until recently, it wasn't as easy to extract the OPAL log without knowing magic offsets. A couple of months ago, I was debugging a nasty CAPI issue and got rather frustrated by this, so one day when I had a couple of hours free I [refactored](http://patchwork.ozlabs.org/patch/581775/) the existing sysfs interface and [added](http://patchwork.ozlabs.org/patch/581774/) the `do` command to `xmon`. These patches will be included from kernel 4.6-rc1 onwards.

When you're done, `x` will attempt to recover the machine and continue, `zr` will reboot, and `zh` will halt.

## From the FSP

Sometimes, not even `xmon` will help you. In production environments, you're not generally going to start a debugger every time you have an incident. Additionally, a serious hardware error can cause a 'checkstop', which completely halts the system. (Thankfully, end users don't see this very often, but kernel developers, on the other hand...)

This is where the Flexible Service Processor, or FSP, comes in. The FSP is an IBM-developed baseboard management controller used on most IBM-branded Power Systems machines, and is responsible for a whole range of things, including monitoring system health. Among its many capabilities, the FSP can automatically take "system dumps" when fatal errors occur, capturing designated regions of memory for later debugging. System dumps can be configured and triggered via the FSP's web interface, which is beyond the scope of this post but is [documented](https://www.ibm.com/support/knowledgecenter/POWER8/p8ha5/mainstoragedump.htm?cp=POWER8%2F1-3-14-2) in IBM Power Systems user manuals.

How does the FSP know what to capture? As it turns out, skiboot (the firmware which implements OPAL) maintains a [Memory Dump Source Table](https://github.com/open-power/skiboot/blob/master/hw/fsp/fsp-mdst-table.c) which tells the FSP which memory regions to dump. MDST updates are recorded in the OPAL log:

    [2690088026,5] MDST: Max entries in MDST table : 256
    [2690090666,5] MDST: Addr = 0x31000000 [size : 0x100000 bytes] added to MDST table.
    [2690093767,5] MDST: Addr = 0x31100000 [size : 0x100000 bytes] added to MDST table.
    [2750378890,5] MDST: Table updated.
    [11199672771,5] MDST: Addr = 0x1fff772780 [size : 0x200000 bytes] added to MDST table.
    [11215193760,5] MDST: Table updated.
	[28031311971,5] MDST: Table updated.
	[28411709421,5] MDST: Addr = 0x1fff830000 [size : 0x100000 bytes] added to MDST table.
	[28417251110,5] MDST: Table updated.

In the above log, we see four entries: the skiboot/OPAL log, the [hostboot](https://github.com/open-power/hostboot) runtime log, the petitboot Linux kernel log (which doesn't make it into the final dump) and the real Linux kernel log. skiboot obviously adds the OPAL and hostboot logs to the MDST early in boot, but it also exposes the [`OPAL_REGISTER_DUMP_REGION`](https://github.com/open-power/skiboot/blob/master/doc/opal-api/opal-register-dump-region-101.txt) call which can be used by the operating system to register additional regions. Linux uses this to [register the kernel log buffer](https://github.com/torvalds/linux/blob/master/arch/powerpc/platforms/powernv/opal.c#L608). If you're a kernel developer, you could potentially use the OPAL call to register your own interesting bits of memory.

So, the MDST is all set up, we go about doing our business, and suddenly we checkstop. The FSP does its sysdump magic and a few minutes later it reboots the system. What now?

* After we come back up, the FSP notifies OPAL that a new dump is available. Linux exposes the dump to userspace under `/sys/firmware/opal/dump/`.

* [ppc64-diag](https://sourceforge.net/projects/linux-diag/files/ppc64-diag/) is a suite of utilities that assist in manipulating FSP dumps, including the `opal_errd` daemon. `opal_errd` monitors new dumps and saves them in `/var/log/dump/` for later analysis.

* `opal-dump-parse` (also in the `ppc64-diag` suite) can be used to extract the sections we care about from the dump:

		root@p86:/var/log/dump# opal-dump-parse -l SYSDUMP.842EA8A.00000001.20160322063051 
		|---------------------------------------------------------|
		|ID              SECTION                              SIZE|
		|---------------------------------------------------------|
		|1              Opal-log                           1048576|
		|2              HostBoot-Runtime-log               1048576|
		|128            printk                             1048576|
		|---------------------------------------------------------|
		List completed
		root@p86:/var/log/dump# opal-dump-parse -s 1 SYSDUMP.842EA8A.00000001.20160322063051 
		Captured log to file Opal-log.842EA8A.00000001.20160322063051
		root@p86:/var/log/dump# opal-dump-parse -s 2 SYSDUMP.842EA8A.00000001.20160322063051 
		Captured log to file HostBoot-Runtime-log.842EA8A.00000001.20160322063051
		root@p86:/var/log/dump# opal-dump-parse -s 128 SYSDUMP.842EA8A.00000001.20160322063051 
		Captured log to file printk.842EA8A.00000001.20160322063051

There's various other types of dumps and logs that I won't get into here. I'm probably obliged to say that if you're having problems out in the wild, you should probably contact your friendly local IBM Service Representative...

## Acknowledgements

Thanks to [Stewart Smith](https://flamingspork.com) for pointing me in the right direction regarding FSP sysdumps and related tools.
