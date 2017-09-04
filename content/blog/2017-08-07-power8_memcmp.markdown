Title: memcmp() for POWER8
Date: 2017-08-07 12:00
Modified: 2017-08-07 12:00
Tags: performance, power
Category: OpenPOWER
Author: Cyril Bur

## Userspace ##

When writing C programs in userspace there is libc which does so much
of the heavy lifting. One important thing libc provides is portability
in performing syscalls, that is, you don't need to know the
architectural details of performing a syscall on each architecture
your program might be compiled for. Another important feature that
libc provides for the average userspace programmer is highly optimised
routines to do things that are usually performance critical. It would
be extremely inefficient for each userspace programmer if they had to
implement even the naive version of these functions let alone
optimised versions. Let us take `memcmp()` for example, I could
trivially implement this in C like:

```c
int memcmp(uint8_t *p1, uint8_t *p2, int n)
{
	int i;

	for (i = 0; i < n; i++) {
		if (p1[i] < p2[i])
			return -1;
		if (p1[i] > p2[i])
			return 1;
	}

	return 0;
}
```

However, while it is incredibly portable it is simply not going to
perform, which is why the nice people who write libc have highly
optimised ones in assembly for each architecture.

## Kernel ##

When writing code for the Linux kernel, there isn't the luxury of a
fully featured libc since it expects (and needs) to be in userspace,
therefore we need to implement the features we need ourselves. Linux
doesn't need all the features but something like `memcmp()` is
definitely a requirement.

There have been some recent optimisations in [glibc][1] from which the
kernel could benefit too! The question to be asked is, does the glibc
optimised `power8_memcmp()` actually go faster or is it all smoke and
mirrors?

## Benchmarking `memcmp()` #

With things like `memcmp()` it is actually quite easy to choose
datasets which can make any implementation look good. For example; the
new `power8_memcmp()` makes use of the vector unit of the power8
processor, in order to do so in the kernel there must be a small
amount of setup code so that the rest of the kernel knows that the
vector unit has been used and it correctly saves and restores the
userspace vector registers. This means that `power8_memcmp()` has a
slightly larger overhead than the current one, so for small compares
or compares which are different early on then the newer 'faster'
`power8_memcmp()` might actually not perform as well. For any kind of
large compare however, using the vector unit should outperform a CPU
register load and compare loop. It is for this reason that I wanted to
avoid using micro benchmarks and use a 'real world' test as much as
possible.

The biggest user of `memcmp()` in the kernel, at least on POWER is Kernel
Samepage Merging (KSM). KSM provides code to inspect all the pages of
a running system to determine if they're identical and deduplicate
them if possible. This kind of feature allows for memory overcommit
when used in a KVM host environment as guest kernels are likely to
have a lot of similar, readonly pages which can be merged with no
overhead afterwards. In order to determine if the pages are the same
KSM must do a lot of page sized `memcmp()`.

## Performance ##

Performing a lot of page sized `memcmp()` is the one flaw with this
test, the sizes of the `memcmp()` don't vary, hopefully the data will be
'random' enough that we can still observe differences in the two
approaches.

My approach for testing involved getting the delta of `ktime_get()`
across calls to `memcmp()` in `memcmp_pages()` (mm/ksm.c). This actually
generated massive amounts of data, so, for consistency the following
analysis is performed on the first 400MB of deltas collected.

The host was compiled with `powernv_defconfig` and run out of a
ramdisk. For consistency the host was rebooted between each run so as
to not have any previous tests affect the next. The host was rebooted
a total of six times, the first three with my 'patched'
`power8_memcmp()` kernel was booted the second three times with just
my data collection patch applied, the 'vanilla' kernel. Both
kernels are based off `4.13-rc3`.

Each boot the following script was run and the resulting deltas file
saved somewhere before reboot. The command line argument was always
15.

```sh
#!/bin/sh

ppc64_cpu --smt=off

#Host actually boots with ksm off but be sure
echo 0 > /sys/kernel/mm/ksm/run

#Scan a lot of pages
echo 999999 > /sys/kernel/mm/ksm/pages_to_scan

echo "Starting QEMUs"
i=0
while [ "$i" -lt "$1" ] ; do
	qemu-system-ppc64 -smp 1 -m 1G -nographic -vga none \
		-machine pseries,accel=kvm,kvm-type=HV \
		-kernel guest.kernel  -initrd guest.initrd \
		-monitor pty -serial pty &
	i=$(expr $i + 1);
done

echo "Letting all the VMs boot"
sleep 30

echo "Turning KSM om"
echo 1 > /sys/kernel/mm/ksm/run

echo "Letting KSM do its thing"
sleep 2m

echo 0 > /sys/kernel/mm/ksm/run

dd if=/sys/kernel/debug/ksm/memcmp_deltas of=deltas bs=4096 count=100
```

The guest kernel was a `pseries_le_defconfig` `4.13-rc3` with the same
ramdisk the host used. It booted to the login prompt and was left to
idle.

## Analysis ##

A variety of histograms were then generated in an attempt to see how
the behaviour of `memcmp()` changed between the two implementations.
It should be noted here that the y axis in the following graphs is a
log scale as there were a lot of small deltas. The first observation
is that the vanilla kernel had more smaller deltas, this is made
particularly evident by the 'tally' points which are a running total
of all deltas with less than the tally value.

![Sample 1 - Deltas below 200ns][2]
Graph 1 depicting the vanilla kernel having a greater amount of small
(sub 20ns) deltas than the patched kernel. The green points rise
faster (left to right) and higher than the yellow points.

Still looking at the tallies, [graph 1][2] also shows that the tally
of deltas is very close by the 100ns mark, which means that the
overhead of `power8_memcmp()` is not too great.

The problem with looking at only deltas under 200ns is that the
performance results we want, that is, the difference between the
algorithms is being masked by things like cache effects. To avoid this
problem is may be wise to look at longer running (larger delta)
`memcmp()` calls.

The following graph plots all deltas below 5000ns - still relatively
short calls to `memcmp()` but an interesting trend emerges:
![Sample 1 - Deltas below 5000ns][3]
Graph 2 shows that above 500ns the blue (patched kernel) points appear
to have all shifted left with respect to the purple (vanilla kernel)
points. This shows that for any `memcmp()` which will take more than
500ns to get a result it is favourable to use `power8_memcmp()` and it
is only detrimental to use  `power8_memcmp()` if the time will be
under 50ns (a conservative estimate).

It is worth noting that [graph 1][2] and [graph 2][3] are generated by
combining the first run of data collected from the vanilla and patched
kernels. All the deltas for both runs are can be viewed separately
[here for vanilla][4] and [here for patched][5]. Finally, the results
from the other four runs look very much identical and provide me with
a fair amount of confidence that these results make sense.

## Conclusions ##

It is important to separate possible KSM optimisations with generic
`memcmp()` optimisations, for example, perhaps KSM shouldn't be
calling `memcmp()` if it suspects the first byte will differ. On the
other hand, things that `power8_memcmp()` could do (which it currently
doesn't) is check the length parameter and perhaps avoid the overhead
of enabling kernel vector if the compare is less than some small
amount of bytes.

It does seem like at least for the 'average case' glibcs
`power8_memcmp()` is an improvement over what we have now.

## Future work ##

A second round of data collection and plotting of delta vs position of
first byte to differ should confirm these results, this would mean a
more invasive patch to KSM.


[1]: https://sourceware.org/git/?p=glibc.git;a=blob_plain;f=sysdeps/powerpc/powerpc64/power8/memcmp.S;h=46b9c0067ad7cd74a36c4800ebfe03eb1be0311e;hb=dec4a7105edcdbabdcac5f358f5bc5dca4f4ed1b "power8 optimised memcmp"
[2]: /images/power8_memcmp/deltas1-200.png "Sample 1: Deltas below 200ns"
[3]: /images/power8_memcmp/deltas1-5000.png "Sample 1: Deltas below 5000ns"
[4]: /images/power8_memcmp/vanilla_deltas1.png "All vanilla deltas"
[5]: /images/power8_memcmp/patched_deltas1.png "All patched deltas"
