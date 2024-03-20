Title: memcmp() for POWER8 - part II
Date: 2017-09-01 12:00
Modified: 2017-09-01 12:00
Tags: performance, power
Category: OpenPOWER
Author: Cyril Bur

This entry is a followup to part I which you should absolutely read
[here]({filename}2017-08-07-power8_memcmp.md) before continuing
on.

## Where we left off ##
We concluded that while a vectorised `memcmp()` is a win, there are
some cases where it won't quite perform.

## The overhead of enabling ALTIVEC ##
In the kernel we explicitly don't touch ALTIVEC unless we need to,
this means that in the general case we can leave the userspace
registers in place and not have do anything to service a syscall for a
process.

This means that if we do want to use ALTIVEC in the kernel, there is
some setup that must be done. Notably, we must enable the facility (a
potentially time consuming move to MSR), save off the registers (if
userspace we using them) and an inevitable restore later on.

If all this needs to be done for a `memcmp()` in the order of tens of
bytes then it really wasn't worth it.

There are two reasons that `memcmp()` might go for a small number of
bytes, firstly and trivially detectable is simply that parameter n is
small. The other is harder to detect, if the memcmp() is going to fail
(return non zero) early then it also wasn't worth enabling ALTIVEC.

## Detecting early failures ##
Right at the start of `memcmp()`, before enabling ALTIVEC, the first
64 bytes are checked using general purpose registers. Why the first 64
bytes, well why not? In a strange twist of fate 64 bytes happens to be
the amount of bytes in four ALTIVEC registers (128 bits per register,
so 16 bytes multiplied by 4) and by utter coincidence that happens to
be the stride of the ALTIVEC compare loop.

## What does this all look like ##
Well unlike part I the results appear slightly less consistent across
three runs of measurement but there are some very key differences with
part I. The trends do appear to be the same across all three runs,
just less pronounced - why this is is unclear.

The difference between run two and run three clipped at deltas of
1000ns is interesting:
![Sample 2: Deltas below 1000ns][1]

vs

![Sample 3: Deltas below 1000ns][2]

The results are similar except for a spike in the amount of deltas in
the unpatched kernel at around 600ns. This is not present in the first
sample (deltas1) of data. There are a number of reasons why this spike
could have appeared here, it is possible that the kernel or hardware
did something under the hood, prefetch could have brought deltas for a
`memcmp()` that would otherwise have yielded a greater delta into the
600ns range.

What these two graphs do both demonstrate quite clearly is that
optimisations down at the sub 100ns end have resulted in more sub
100ns deltas for the patched kernel, a significant win over the
original data. Zooming out and looking at a graph which includes
deltas up to 5000ns shows that the sub 100ns delta optimisations
haven't noticeably slowed the performance of long duration `memcmp()`,
![Samply 2: Deltas below 5000ns][3].

## Conclusion ##
The small amount of extra development effort has yielded tangible
results in reducing the low end `memcmp()` times. This second round of
data collection and performance analysis only confirms the that for
any significant amount of comparison, a vectorised loop is
significantly quicker.

The results obtained here show no downside to adopting this approach
for all power8 and onwards chips as this new version of the patch
solves the performance regression for small compares.

[1]: /images/power8_memcmp/v2deltas2-1000.png "Sample 2: Deltas below 1000ns"
[2]: /images/power8_memcmp/v2deltas3-1000.png "Sample 3: Deltas below 1000ns"
[3]: /images/power8_memcmp/v2deltas2-5000.png "Sample 2: Deltas below 5000ns"
