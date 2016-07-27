Title: Running ppc64le_hello on real hardware
Date: 2015-06-03 12:16
Category: OpenPOWER
Authors: Daniel Axtens
Slug: ppc64le-hello-on-real-hardware

So today I saw [Freestanding “Hello World” for OpenPower](https://github.com/andreiw/ppc64le_hello) on [Hacker News](https://news.ycombinator.com/item?id=9649490). Sadly Andrei hadn't been able to test it on real hardware, so I set out to get it running on a real OpenPOWER box. Here's what I did.

Firstly, clone the repo, and, as mentioned in the README, comment out `mambo_write`. Build it.
 
Grab [op-build](https://github.com/open-power/op-build), and build a Habanero defconfig. To save yourself a fair bit of time, first edit `openpower/configs/habanero_defconfig` to answer `n` about a custom kernel source. That'll save you hours of waiting for git.
 
This will build you a PNOR that will boot a linux kernel with Petitboot. This is almost what you want: you need Skiboot, Hostboot and a bunch of the POWER specific bits and bobs, but you don't actually want the Linux boot kernel.

Then, based on `op-build/openpower/package/openpower-pnor/openpower-pnor.mk`, we look through the output of `op-build` for a  `create_pnor_image.pl` command, something like this monstrosity:

`
PATH="/scratch/dja/public/op-build/output/host/bin:/scratch/dja/public/op-build/output/host/sbin:/scratch/dja/public/op-build/output/host/usr/bin:/scratch/dja/public/op-build/output/host/usr/sbin:/home/dja/bin:/home/dja/bin:/home/dja/bin:/usr/local/bin:/usr/bin:/bin:/usr/local/games:/usr/games:/opt/openpower/common/x86_64/bin" /scratch/dja/public/op-build/output/build/openpower-pnor-ed1682e10526ebd85825427fbf397361bb0e34aa/create_pnor_image.pl -xml_layout_file /scratch/dja/public/op-build/output/build/openpower-pnor-ed1682e10526ebd85825427fbf397361bb0e34aa/"defaultPnorLayoutWithGoldenSide.xml" -pnor_filename /scratch/dja/public/op-build/output/host/usr/powerpc64-buildroot-linux-gnu/sysroot/pnor/"habanero.pnor" -hb_image_dir /scratch/dja/public/op-build/output/host/usr/powerpc64-buildroot-linux-gnu/sysroot/hostboot_build_images/ -scratch_dir /scratch/dja/public/op-build/output/host/usr/powerpc64-buildroot-linux-gnu/sysroot/openpower_pnor_scratch/ -outdir /scratch/dja/public/op-build/output/host/usr/powerpc64-buildroot-linux-gnu/sysroot/pnor/ -payload /scratch/dja/public/op-build/output/images/"skiboot.lid" -bootkernel /scratch/dja/public/op-build/output/images/zImage.epapr -sbe_binary_filename "venice_sbe.img.ecc" -sbec_binary_filename "centaur_sbec_pad.img.ecc" -wink_binary_filename "p8.ref_image.hdr.bin.ecc" -occ_binary_filename /scratch/dja/public/op-build/output/host/usr/powerpc64-buildroot-linux-gnu/sysroot/occ/"occ.bin" -targeting_binary_filename "HABANERO_HB.targeting.bin.ecc" -openpower_version_filename /scratch/dja/public/op-build/output/host/usr/powerpc64-buildroot-linux-gnu/sysroot/openpower_version/openpower-pnor.version.txt
`

Replace the `-bootkernel` arguement with the path to ppc64le_hello, e.g.: `-bootkernel /scratch/dja/public/ppc64le_hello/ppc64le_hello`

Don't forget to move it into place! 

```sh
mv output/host/usr/powerpc64-buildroot-linux-gnu/sysroot/pnor/habanero.pnor output/images/habanero.pnor
```

Then we can use skiboot's boot test script (written by Cyril and me, coincidentally!) to flash it.

```sh
ppc64le_hello/skiboot/external/boot-tests/boot_test.sh -vp -t hab2-bmc -P <path to>/habanero.pnor
```

It's not going to get into Petitboot, so just interrupt it after it powers up the box and connect with IPMI. It boots, kinda:

```text
[11012941323,5] INIT: Starting kernel at 0x20010000, fdt at 0x3044db68 (size 0x11cc3)
Hello OPAL!
           _start = 0x20010000
                              _bss   = 0x20017E28
                                                 _stack = 0x20018000
                                                                    _end   = 0x2001A000
                                                                                       KPCR   = 0x20017E50
                                                                                                          OPAL   = 0x30000000
                                                                                                                             FDT    = 0x3044DB68
                                                                                                                                                CPU0 not found?

                                                                                                                                                               Pick your poison:
                                                                                                                                                                                Choices: (MMU = disabled):
                                                                                                                                                                                                             (d) 5s delay
                                                                                                                                                                                                                            (e) test exception
    (n) test nested exception
                                (f) dump FDT
                                               (M) enable MMU
                                                                (m) disable MMU
                                                                                  (t) test MMU
                                                                                                 (u) test non-priviledged code
                                                                                                                                 (I) enable ints
                                                                                                                                                   (i) disable ints
                                                                                                                                                                      (H) enable HV dec
                                                                                                                                                                                          (h) disable HV dec
                                                                                                                                                                                                               (q) poweroff
                                                                                                                                                                                                                             1.42486|ERRL|Dumping errors reported prior to registration
```

Yes, it does wrap horribly. However, the big issue here (which you'll have to scroll to see!) is the "CPU0 not found?". Fortunately, we can fix this with a little patch to `cpu_init` in main.c to test for a PowerPC POWER8:


```C
	cpu0_node = fdt_path_offset(fdt, "/cpus/cpu@0");
	if (cpu0_node < 0) {
		cpu0_node = fdt_path_offset(fdt, "/cpus/PowerPC,POWER8@20");
	}
	if (cpu0_node < 0) {
		printk("CPU0 not found?\n");
		return;
	}
```

This is definitely the _wrong_ way to do this, but it works for now.

Now, correcting for weird wrapping, we get:

```text
Hello OPAL!
_start = 0x20010000
_bss   = 0x20017E28
_stack = 0x20018000
_end   = 0x2001A000
KPCR   = 0x20017E50
OPAL   = 0x30000000
FDT    = 0x3044DB68
Assuming default SLB size
SLB size = 0x20
TB freq = 512000000
[13205442015,3] OPAL: Trying a CPU re-init with flags: 0x2
Unrecoverable exception stack top @ 0x20019EC8
HTAB (2048 ptegs, mask 0x7FF, size 0x40000) @ 0x20040000
SLB entries:
1: E 0x8000000 V 0x4000000000000400
EA 0x20040000 -> hash 0x20040 -> pteg 0x200 = RA 0x20040000
EA 0x20041000 -> hash 0x20041 -> pteg 0x208 = RA 0x20041000
EA 0x20042000 -> hash 0x20042 -> pteg 0x210 = RA 0x20042000
EA 0x20043000 -> hash 0x20043 -> pteg 0x218 = RA 0x20043000
EA 0x20044000 -> hash 0x20044 -> pteg 0x220 = RA 0x20044000
EA 0x20045000 -> hash 0x20045 -> pteg 0x228 = RA 0x20045000
EA 0x20046000 -> hash 0x20046 -> pteg 0x230 = RA 0x20046000
EA 0x20047000 -> hash 0x20047 -> pteg 0x238 = RA 0x20047000
EA 0x20048000 -> hash 0x20048 -> pteg 0x240 = RA 0x20048000
...
```

The weird wrapping seems to be caused by NULLs getting printed to OPAL, but I haven't traced what causes that.

Anyway, now it largely works! Here's a transcript of some things it can do on real hardware.

```text
Choices: (MMU = disabled):
   (d) 5s delay
   (e) test exception
   (n) test nested exception
   (f) dump FDT
   (M) enable MMU
   (m) disable MMU
   (t) test MMU
   (u) test non-priviledged code
   (I) enable ints
   (i) disable ints
   (H) enable HV dec
   (h) disable HV dec
   (q) poweroff
<press e>
Testing exception handling...
sc(feed) => 0xFEEDFACE
Choices: (MMU = disabled):
   (d) 5s delay
   (e) test exception
   (n) test nested exception
   (f) dump FDT
   (M) enable MMU
   (m) disable MMU
   (t) test MMU
   (u) test non-priviledged code
   (I) enable ints
   (i) disable ints
   (H) enable HV dec
   (h) disable HV dec
   (q) poweroff
<press t>
EA 0xFFFFFFF000 -> hash 0xFFFFFFF -> pteg 0x3FF8 = RA 0x20010000
mapped 0xFFFFFFF000 to 0x20010000 correctly
EA 0xFFFFFFF000 -> hash 0xFFFFFFF -> pteg 0x3FF8 = unmap
EA 0xFFFFFFF000 -> hash 0xFFFFFFF -> pteg 0x3FF8 = RA 0x20011000
mapped 0xFFFFFFF000 to 0x20011000 incorrectly
EA 0xFFFFFFF000 -> hash 0xFFFFFFF -> pteg 0x3FF8 = unmap
Choices: (MMU = disabled):
   (d) 5s delay
   (e) test exception
   (n) test nested exception
   (f) dump FDT
   (M) enable MMU
   (m) disable MMU
   (t) test MMU
   (u) test non-priviledged code
   (I) enable ints
   (i) disable ints
   (H) enable HV dec
   (h) disable HV dec
   (q) poweroff
<press u>
EA 0xFFFFFFF000 -> hash 0xFFFFFFF -> pteg 0x3FF8 = RA 0x20080000
returning to user code
returning to kernel code
EA 0xFFFFFFF000 -> hash 0xFFFFFFF -> pteg 0x3FF8 = unmap
```

I also tested the other functions and they all seem to work. Running non-priviledged code with the MMU on works. Dumping the FDT and the 5s delay both worked, although they tend to stress IPMI a *lot*. The delay seems to correspond well with real time as well.

It does tend to error out and reboot quite often, usually on the menu screen, for reasons that are not clear to me. It usually starts with something entirely uninformative from Hostboot, like this:

```text
1.41801|ERRL|Dumping errors reported prior to registration
  2.89873|Ignoring boot flags, incorrect version 0x0
```

That may be easy to fix, but again I haven't had time to trace it.

All in all, it's very exciting to see something come out of the simulator and in to real hardware. Hopefully with the proliferation of OpenPOWER hardware, prices will fall and these sorts of systems will become increasingly accessible to people with cool low level projects like this!
