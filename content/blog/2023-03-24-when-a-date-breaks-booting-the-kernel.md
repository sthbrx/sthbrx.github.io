Title: Dumb bugs: When a date breaks booting the kernel
Date: 2023-03-24 00:00:00
Authors: Benjamin Gray
Category: Development
Tags: linux

## The setup

I've recently been working on internal CI infrastructure for testing kernels before sending them to the mailing list. As part of this effort, I became interested in [reproducible builds](https://reproducible-builds.org/). Minimising the changing parts outside of the source tree itself could improve consistency and ccache hits, which is great for trying to make the CI faster and more reproducible across different machines. This means removing 'external' factors like timestamps from the build process, because the time changes every build and means the results between builds of the same tree are no longer identical binaries. This also prevents using previously cached results, potentially slowing down builds (though it turns out the kernel does a good job of limiting the scope of where timestamps appear in the build).

As part of this effort, I came across the `KBUILD_BUILD_TIMESTAMP` environment variable. This variable is used to set the kernel timestamp, which is primarily for any users who want to know when their kernel was built. That's mostly irrelevant for our work, so an easy `KBUILD_BUILD_TIMESTAMP=0` later and... it still uses the current date.

Ok, checking [the documentation](https://docs.kernel.org/kbuild/kbuild.html#kbuild-build-timestamp) it says

> Setting this to a date string overrides the timestamp used in the UTS_VERSION definition (uname -v in the running kernel). The value has to be a string that can be passed to date -d. The default value is the output of the date command at one point during build.

So it looks like the timestamp variable is actually expected to be a date format. To make it obvious that it's not a 'real' date, let's set `KBUILD_BUILD_TIMESTAMP=0000-01-01`. A bunch of zeroes (and the ones to make it a valid month and day) should tip off anyone to the fact it's invalid.

As an aside, this is a different date to what I tried to set it to earlier; a 'timestamp' typically refers to the number of seconds since the UNIX epoch (1970), so my first attempt would have corresponded to 1970-01-01. But given we're passing a date, not a timestamp, there should be no problem setting it back to the year 0. And I like the aesthetics of 0000 over 1970.

Building and booting the kernel, we see `#1 SMP 0000-01-01` printed as the build timestamp. Success! After confirming everything works, I set the environment variable in the CI jobs and call it a day.


## An unexpected error

A few days later I need to run the CI to test my patches, and something strange happens. It builds fine, but the boot tests that load a root disk image fail inexplicably: there is a kernel panic saying "VFS: Unable to mount root fs on unknown-block(253,2)".
```text
[    0.909648][    T1] Kernel panic - not syncing: VFS: Unable to mount root fs on unknown-block(253,2)
[    0.909797][    T1] CPU: 0 PID: 1 Comm: swapper/0 Not tainted 6.3.0-rc2-g065ffaee7389 #8
[    0.909880][    T1] Hardware name: IBM pSeries (emulated by qemu) POWER8 (raw) 0x4d0200 0xf000004 of:SLOF,HEAD pSeries
[    0.910044][    T1] Call Trace:
[    0.910107][    T1] [c000000003643b00] [c000000000fb6f9c] dump_stack_lvl+0x70/0xa0 (unreliable)
[    0.910378][    T1] [c000000003643b30] [c000000000144e34] panic+0x178/0x424
[    0.910423][    T1] [c000000003643bd0] [c000000002005144] mount_block_root+0x1d0/0x2bc
[    0.910457][    T1] [c000000003643ca0] [c000000002005720] prepare_namespace+0x1d4/0x22c
[    0.910487][    T1] [c000000003643d20] [c000000002004b04] kernel_init_freeable+0x36c/0x3bc
[    0.910517][    T1] [c000000003643df0] [c000000000013830] kernel_init+0x30/0x1a0
[    0.910549][    T1] [c000000003643e50] [c00000000000df94] ret_from_kernel_thread+0x5c/0x64
[    0.910587][    T1] --- interrupt: 0 at 0x0
[    0.910794][    T1] NIP:  0000000000000000 LR: 0000000000000000 CTR: 0000000000000000
[    0.910828][    T1] REGS: c000000003643e80 TRAP: 0000   Not tainted  (6.3.0-rc2-g065ffaee7389)
[    0.910883][    T1] MSR:  0000000000000000 <>  CR: 00000000  XER: 00000000
[    0.910990][    T1] CFAR: 0000000000000000 IRQMASK: 0
[    0.910990][    T1] GPR00: 0000000000000000 c000000003644000 0000000000000000 0000000000000000
[    0.910990][    T1] GPR04: 0000000000000000 0000000000000000 0000000000000000 0000000000000000
[    0.910990][    T1] GPR08: 0000000000000000 0000000000000000 0000000000000000 0000000000000000
[    0.910990][    T1] GPR12: 0000000000000000 0000000000000000 c000000000013808 0000000000000000
[    0.910990][    T1] GPR16: 0000000000000000 0000000000000000 0000000000000000 0000000000000000
[    0.910990][    T1] GPR20: 0000000000000000 0000000000000000 0000000000000000 0000000000000000
[    0.910990][    T1] GPR24: 0000000000000000 0000000000000000 0000000000000000 0000000000000000
[    0.910990][    T1] GPR28: 0000000000000000 0000000000000000 0000000000000000 0000000000000000
[    0.911371][    T1] NIP [0000000000000000] 0x0
[    0.911397][    T1] LR [0000000000000000] 0x0
[    0.911427][    T1] --- interrupt: 0
qemu-system-ppc64: OS terminated: OS panic: VFS: Unable to mount root fs on unknown-block(253,2)
```

Above the panic was some more context, saying
```text
[    0.906194][    T1] Warning: unable to open an initial console.
...
[    0.908321][    T1] VFS: Cannot open root device "vda2" or unknown-block(253,2): error -2
[    0.908356][    T1] Please append a correct "root=" boot option; here are the available partitions:
[    0.908528][    T1] 0100           65536 ram0
[    0.908657][    T1]  (driver?)
[    0.908735][    T1] 0101           65536 ram1
[    0.908744][    T1]  (driver?)
...
[    0.909216][    T1] 010f           65536 ram15
[    0.909226][    T1]  (driver?)
[    0.909265][    T1] fd00         5242880 vda
[    0.909282][    T1]  driver: virtio_blk
[    0.909335][    T1]   fd01            4096 vda1 d1f35394-01
[    0.909364][    T1]
[    0.909401][    T1]   fd02         5237760 vda2 d1f35394-02
[    0.909408][    T1]
[    0.909441][    T1] fd10             366 vdb
[    0.909446][    T1]  driver: virtio_blk
[    0.909479][    T1] 0b00         1048575 sr0
[    0.909486][    T1]  driver: sr
```

This is even more baffling: if it's unable to open a console, then what am I reading these messages on? And error `-2`, or ENOENT, on opening 'vda2' implies that no such file or directory exists. But it then lists vda2 as a present drive with a known driver? So is vda2 missing or not?


## Living in denial

As you've read the title of this article, you can probably guess as to what changed to cause this error. But at the time I had no idea what could have been the cause. I'd already confirmed that a kernel with a set timestamp can boot to userspace, and there was another (seemingly) far more likely candidate for the failure: as part of the CI design, patches are extracted from the submitted branch and rebased onto the maintainer's tree. This is great from a convenience perspective, because you don't need to worry about forgetting to rebase your patches before testing and submission. But if the maintainer has synced their branch with Linus' tree it means there could be a lot of things changed in the source tree between runs, even if they were only a few days apart.

So, when you're faced with a working test on one commit and a broken test on another commit, it's time to break out the `git bisect`. Downloading the kernel images from the relevant CI jobs, I confirmed that indeed one was working while the other was broken. So I bisected the relevant commits, and... everything kept working. Each step I would build and boot the kernel, and each step would reach userspace just fine. I was getting suspicious at this point, so skipped ahead to the known bad commit and built and tested it locally. It _also worked_.

This was highly confusing, because it meant there was something fishy going on. Some kind of state outside of the kernel tree. Could it be... surely not...

Comparing the boot logs of the two CI kernels, I see that the working one indeed uses an actual timestamp, and the broken one uses the 0000-01-01 fixed date. Oh no. Setting the timestamp with a local build, I can now reproduce the boot panic with a kernel I built myself.


## But... why?

OK, so it's obvious at this point that the timestamp is affecting loading a root disk somehow. But why? The obvious answer is that it's before the UNIX epoch. Something in the build process is turning the date into an actual timestamp, and going wrong when that timestamp gets used for something.

But it's not like there was a build error complaining about it. As best I could tell, the kernel doesn't try to parse the date anywhere, besides passing it to `date` during the build. And if `date` had an issue with it, it would have broken the _build_. Not _booting_ the kernel. There's no `date` utility being invoked during kernel boot!

Regardless, I set about tracing the usage of `KBUILD_BUILD_TIMESTAMP` inside the kernel. The stacktrace in the panic gave the end point of the search; the function `mount_block_root()` wasn't happy. So all I had to do was work out at which point `mount_block_root()` tried to access the `KBUILD_BUILD_TIMESTAMP` value.

In short, that went nowhere.

`mount_block_root()` effectively just tries to open a file in the filesystem. There's massive amounts of code handling this, and any part could have had the undocumented dependency on `KBUILD_BUILD_TIMESTAMP`. Approaching from the other direction, `KBUILD_BUILD_TIMESTAMP` is turned into `build-timestamp` inside a Makefile, which is in turn related to a file `include/generated/utsversion.h`. This file `#define`s `UTS_VERSION` equal to the `KBUILD_BUILD_TIMESTAMP` value. Searching the kernel for `UTS_VERSION`, we hit `init/version-timestamp.c` which stores it in a struct with other build information:
```C
struct uts_namespace init_uts_ns = {
	.ns.count = REFCOUNT_INIT(2),
	.name = {
		.sysname	= UTS_SYSNAME,
		.nodename	= UTS_NODENAME,
		.release	= UTS_RELEASE,
		.version	= UTS_VERSION,
		.machine	= UTS_MACHINE,
		.domainname	= UTS_DOMAINNAME,
	},
	.user_ns = &init_user_ns,
	.ns.inum = PROC_UTS_INIT_INO,
#ifdef CONFIG_UTS_NS
	.ns.ops = &utsns_operations,
#endif
};
```

This is where the trail goes cold: I don't know if you've ever tried this, but searching for `.version` in the kernel's codebase is not a very fruitful endeavor when you're interested in a specific kind of version.

```text
$ rg "(\.|\->)version\b" | wc -l
5718
```

I tried tracing the usage of `init_uts_ns`, but didn't get very far.

By now I'd already posted this in chat and another developer, [Joel Stanley](https://shenki.github.io/), was also investigating this bizarre bug. They had been testing different timestamp values and made the horrifying discovery that the bug sticks around after a rebuild. So you could start with a broken build, set the timestamp back to the correct value, rebuild, and the resulting kernel would _still be broken_. The boot log would report the correct time, but the root disk mounter panicked all the same.


## Getting sidetracked

I wasn't prepared to investigate the boot panic directly until the persistence bug was fixed. Having to run `make clean` and rebuild everything would take an annoyingly long time, even with ccache. Fortunately, I had a plan. All I had to do was work out which generated files are different between a broken and working build, and binary search by deleting half of them until deleting only one made the difference between the bug persisting or not. We can use `diff` for this. Running the initial diff we get

```text
$ diff -q --exclude System.map --exclude .tmp_vmlinux* --exclude tools broken/ working/
Common subdirectories: broken/arch and working/arch
Common subdirectories: broken/block and working/block
Files broken/built-in.a and working/built-in.a differ
Common subdirectories: broken/certs and working/certs
Common subdirectories: broken/crypto and working/crypto
Common subdirectories: broken/drivers and working/drivers
Common subdirectories: broken/fs and working/fs
Common subdirectories: broken/include and working/include
Common subdirectories: broken/init and working/init
Common subdirectories: broken/io_uring and working/io_uring
Common subdirectories: broken/ipc and working/ipc
Common subdirectories: broken/kernel and working/kernel
Common subdirectories: broken/lib and working/lib
Common subdirectories: broken/mm and working/mm
Common subdirectories: broken/net and working/net
Common subdirectories: broken/scripts and working/scripts
Common subdirectories: broken/security and working/security
Common subdirectories: broken/sound and working/sound
Common subdirectories: broken/usr and working/usr
Files broken/.version and working/.version differ
Common subdirectories: broken/virt and working/virt
Files broken/vmlinux and working/vmlinux differ
Files broken/vmlinux.a and working/vmlinux.a differ
Files broken/vmlinux.o and working/vmlinux.o differ
Files broken/vmlinux.strip.gz and working/vmlinux.strip.gz differ
```

Hmm, OK so only some top level files are different. Deleting all the different files doesn't fix the persistence bug though, and I know that a proper `make clean` does fix it, so what could possibly be the difference when all the remaining files are identical?

Oh wait. `man diff` reports that `diff` only compares the top level folder entries by default. So it was literally just telling me "yes, both the broken and working builds have a folder named X". How GNU of it. Re-running the diff command with actually useful options, we get a more promising story

```text
$ diff -qr --exclude System.map --exclude .tmp_vmlinux* --exclude tools build/broken/ build/working/
Files build/broken/arch/powerpc/boot/zImage and build/working/arch/powerpc/boot/zImage differ
Files build/broken/arch/powerpc/boot/zImage.epapr and build/working/arch/powerpc/boot/zImage.epapr differ
Files build/broken/arch/powerpc/boot/zImage.pseries and build/working/arch/powerpc/boot/zImage.pseries differ
Files build/broken/built-in.a and build/working/built-in.a differ
Files build/broken/include/generated/utsversion.h and build/working/include/generated/utsversion.h differ
Files build/broken/init/built-in.a and build/working/init/built-in.a differ
Files build/broken/init/utsversion-tmp.h and build/working/init/utsversion-tmp.h differ
Files build/broken/init/version.o and build/working/init/version.o differ
Files build/broken/init/version-timestamp.o and build/working/init/version-timestamp.o differ
Files build/broken/usr/built-in.a and build/working/usr/built-in.a differ
Files build/broken/usr/initramfs_data.cpio and build/working/usr/initramfs_data.cpio differ
Files build/broken/usr/initramfs_data.o and build/working/usr/initramfs_data.o differ
Files build/broken/usr/initramfs_inc_data and build/working/usr/initramfs_inc_data differ
Files build/broken/.version and build/working/.version differ
Files build/broken/vmlinux and build/working/vmlinux differ
Files build/broken/vmlinux.a and build/working/vmlinux.a differ
Files build/broken/vmlinux.o and build/working/vmlinux.o differ
Files build/broken/vmlinux.strip.gz and build/working/vmlinux.strip.gz differ
```

There are some new entries here: notably `init/version*` and `usr/initramfs*`. Binary searching these files results in a single culprit: `usr/initramfs_data.cpio`. This is quite fitting, as the `.cpio` file is an archive defining a filesystem layout, [much like `.tar` files](https://docs.kernel.org/filesystems/ramfs-rootfs-initramfs.html?highlight=initramfs#why-cpio-rather-than-tar). This file is actually embedded into the kernel image, and loaded as a bare-bones shim filesystem when the user doesn't provide their own initramfs[^1].

[^1]: initramfs, or initrd for the older format, are specific kinds of CPIO archives. The initramfs is intended to be loaded as the initial filesystem of a booted kernel, typically in preparation for loading your normal root filesystem. It might contain modules necessary to mount the disk for example.

So it would make sense that if the CPIO archive wasn't being rebuilt, then the initial filesystem wouldn't change. And it would make sense for the initial filesystem to be causing mount issues of the proper root disk filesystem.

This just leaves the question of how `KBUILD_BUILD_TIMESTAMP` is breaking the CPIO archive. And it's around this time that a third developer, [Andrew](https://twitter.com/ajdlinux), who I'd roped into this bug hunt for having the (mis)fortune to sit next to me, pointed out that the generator script for this CPIO archive was passing the `KBUILD_BUILD_TIMESTAMP` to `date`. Whoop, we've found the murder weapon[^2]!

[^2]: Hindsight again would suggest it was obvious to look here because it shows up when searching for `KBUILD_BUILD_TIMESTAMP`. I unfortunately wasn't familiar with the `usr/` source folder initially, and focused on the core kernel components too much earlier. Oh well, we found it eventually.

The persistence bug could be explained now: because the script was only using `KBUILD_BUILD_TIMESTAMP` internally, `make` had no way of knowing that the archive generation depended on this variable. So even when I changed the variable to a valid value, `make` didn't know to rebuild the corrupt archive. Let's now get back to the main issue: why boot panics.


## Solving the case

Following along the CPIO generation script, the `KBUILD_BUILD_TIMESTAMP` variable is turned into a timestamp by `date -d"$KBUILD_BUILD_TIMESTAMP" +%s`. Testing this in the shell with `0000-01-01` we get this (somewhat amusing, but also painful) result
```text
date -d"$KBUILD_BUILD_TIMESTAMP" +%s
-62167255492
```

This timestamp is then passed to a C program that assigns it to a variable `default_mtime`. Looking over the source, it seems this variable is used to set the `mtime` field on the files in the CPIO archive. The timestamp is stored as a `time_t`, which is an alias for `int64_t`. That's 64 bits of data, up to 16 hexadecimal characters. And yes, that's relevant: CPIO stores the `mtime` (and all other numerical fields) as 32 bit unsigned integers represented by ASCII hexadecimal characters. The `sprintf()` call that ultimately embeds the timestamp uses the `%08lX` format specifier. This formats a `long` as hexadecimal, padded to at least 8 characters. Hang on... ***at least*** 8 characters? What if our timestamp happens to be more?

It turns out that large timestamps are already guarded against. The program will error during build if the date is later than 2106-02-07 (maximum unsigned 8 hex digit timestamp).

```C
/*
 * Timestamps after 2106-02-07 06:28:15 UTC have an ascii hex time_t
 * representation that exceeds 8 chars and breaks the cpio header
 * specification.
 */
if (default_mtime > 0xffffffff) {
	fprintf(stderr, "ERROR: Timestamp too large for cpio format\n");
	exit(1);
}
```

But we are using an `int64_t`. What would happen if one were to provide a negative timestamp?

Well, `sprintf()` happily spits out `FFFFFFF1868AF63C` when we pass in our negative timestamp representing `0000-01-01`. That's 16 characters, 8 too many for the CPIO header[^3].

[^3]: I almost missed this initially. Thanks to the ASCII header format, `strings` was able to print the headers without any CPIO specific tooling. I did a double take when I noticed the headers for the broken CPIO were a little longer than the headers in the working one.

So at last we've found the cause of the panic: the timestamp is being formatted too long, which breaks the CPIO header and the kernel doesn't create an initial filesystem correctly. This includes the `/dev` folder (which surprisingly is not hardcoded into kernel, but must be declared by the initramfs). So when the root disk mounter tries to open `/dev/vda2`, it correctly complains that it failed to create a device in the non-existent `/dev`.


## Postmortem

After discovering all this, I sent in a couple of patches to fix [the CPIO generation](https://lore.kernel.org/all/20230320040839.660475-1-bgray@linux.ibm.com/) and [rebuild logic](https://lore.kernel.org/all/20230320040839.660475-2-bgray@linux.ibm.com/). They were not complicated fixes, but wow were they time consuming to track down. I didn't see the error initially because I typically only boot with my own initramfs over the embedded one, and not with the intent to load a root disk. Then the panic itself was quite far away from the real issue, and there were many dead ends to explore.

I also got curious as to why the kernel didn't complain about a corrupt initramfs earlier. A brief investigation showed a streaming parser that is _extremely_ fault tolerant, silently skipping invalid entries (like ones missing or having too long a name). The corrupted header was being interpreted as an entry with an empty name and 2 gigabyte body contents, which meant that (1) the kernel skipped inserting it due to the empty name, and (2) the kernel skipped the rest of the initramfs because it thought that up to 2 GB of the remaining content was part of that first entry.

Perhaps this could be improved to require that all input is consumed without unexpected EOF, such as how the userspace `cpio` tool works (which, by the way, recognises the corrupt archive as such and refuses to decompress it). The parsing logic is mostly from the before-times though (i.e., pre initial git commit), so it's difficult to distinguish intentional leniency and bugs.


## Afterword

Incidentally, in investigating this I came across another bug. There is a helper function `panic_show_mem()` in the initramfs that's meant to dump memory information and then call `panic()`. It takes in standard `printf()` style format string and arguments, and tries to forward them to `panic()` which ultimately prints them.

```C
static void panic_show_mem(const char *fmt, ...)
{
	va_list args;

	show_mem(0, NULL);
	va_start(args, fmt);
	panic(fmt, args);
	va_end(args);
}

void panic(const char *fmt, ...);
```

But variadic arguments don't quite work this way: instead of forwarding the list `args` as intended, `panic()` will instead interpret `args` as a single argument for the format string `fmt`. Standard library functions address this by providing `v*` variants of `printf()` and friends. For example,

```C
int printf(char *fmt, ...);

int vprintf(char *fmt, va_list args);
```

We might create a `vpanic()` function in the kernel that follows this style, but it seems easier to just make `panic_show_mem()` a macro and 'forward' the arguments in the source code

```C
#define panic_show_mem(fmt, ...) \
	({ show_mem(0, NULL); panic(fmt, ##__VA_ARGS__); })
```

[Patch sent](https://lore.kernel.org/all/20230320230534.50174-1-bgray@linux.ibm.com/).

And that's where I've left things. Big thanks to Joel and Andrew for helping me with this bug. It was certainly a trip.
