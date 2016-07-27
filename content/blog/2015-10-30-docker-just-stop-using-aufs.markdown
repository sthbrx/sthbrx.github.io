Title: Docker: Just Stop Using AUFS
Date: 2015-10-30 13:30
Authors: Daniel Axtens
Tags: aufs, overlay, performance
Category: Docker

Docker's default storage driver on most Ubuntu installs is AUFS.

Don't use it. Use Overlay instead. Here's why.

First, some background. I'm testing the performance of the basic LAMP
stack on POWER. (LAMP is Linux + Apache + MySQL/MariaDB + PHP, by the
way.) To do more reliable and repeatable tests, I do my builds and
tests in Docker containers. (See [my previous post](/blog/2015/10/12/a-tale-of-two-dockers/) for more info.)

Each test downloads the source of Apache, MariaDB and PHP, and builds
them. This should be quick: the POWER8 system I'm building on has 160
hardware threads and 128 GB of memory. But I was finding that it was
only just keeping pace with a 2 core Intel VM on BlueMix.

Why? Well, my first point of call was to observe a compilation under
`top`. The header is below.

![top header, showing over 70 percent of CPU time spent in the kernel](/images/dja/aufs/top-bad.png)

Over 70% of CPU time is spent in the kernel?! That's weird. Let's dig
deeper.

My next port of call for analysis of CPU-bound workloads is
`perf`. `perf top` reports astounding quantities of time in
spin-locks:

![display from perf top, showing 80 percent of time in a spinlock](/images/dja/aufs/perf-top-spinlock.png)

`perf top -g` gives us some more information: the time is in system
calls. `open()` and `stat()` are the key culprits, and we can see a
number of file system functions are in play in the call-chains of the
spinlocks.

![display from perf top -g, showing syscalls and file ops](/images/dja/aufs/perf-top-syscalls.png)

Why are open and stat slow? Well, I know that the files are on an AUFS
mount. (`docker info` will tell you what you're using if you're not
sure.) So, being something of a kernel hacker, I set out to find out
why. This did not go well. AUFS isn't upstream, it's a separate patch
set. Distros have been trying to deprecate it for years. Indeed, RHEL
doesn't ship it. (To it's credit, Docker seems to be trying to move
away from it.)

Wanting to avoid the minor nightmare that is an out-of-tree patchset,
I looked at other storage drivers for Docker. [This presentation is particularly good.](https://jpetazzo.github.io/assets/2015-03-03-not-so-deep-dive-into-docker-storage-drivers.html)
My choices are pretty simple: AUFS, btrfs, device-mapper or
Overlay. Overlay was an obvious choice: it doesn't need me to set up
device mapper on a cloud VM, or reformat things as btrfs.

It's also easy to set up on Ubuntu:

 - export/save any docker containers you care about.

 - add `--storage-driver=overlay` option to `DOCKER_OPTS` in `/etc/default/docker`, and restart docker (`service docker restart`)

 - import/load the containters you exported

 - verify that things work, then clear away your old storage directory (`/var/lib/docker/aufs`). 

Having moved my base container across, I set off another build.

The first thing I noticed is that images are much slower to create with Overlay. But once that finishes, and a compile starts, things run much better:

![top, showing close to zero system time, and around 90 percent user time](/images/dja/aufs/top-good.png)

The compiles went from taking painfully long to astonishingly fast. Winning.

So in conclusion:

 - If you use Docker for something that involves open()ing or stat()ing files

 - If you want your machine to do real work, rather than spin in spinlocks

 - If you want to use code that's upstream and thus much better supported

 - If you want something less disruptive than the btrfs or dm storage drivers

...then drop AUFS and switch to Overlay today.
