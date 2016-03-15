Title: linux.conf.au 2016: A set of brief thoughts
Authors: Daniel Axtens
Date: 2016-03-15 11:30
Category: Education
Tags: lca2016 conferences

Recently most of us attended LCA2016. This is one set of reflections on what we heard and what we've thought since. (Hopefully not the only set of reflections that will be posted on this blog either!)

LCA was 2 days of miniconferences plus 3 days of talks. Here, I've picked some of the more interesting talks I attended, and I've written down some thoughs. If you find the thoughts interesting, you can click through and watch the whole talk video, because LCA is awesome like that.

#### Life is better with Rust's community automation

[This talk](https://www.youtube.com/watch?v=dIageYT0Vgg) is probably the one that's had the biggest impact on our team so far. We were really impressed by the community automation that Rust has: the way they can respond to pull requests from new community memebers in a way that lets them keep their code quality high and be nice to everyone at the same time.

The system that they've developed is fascinating (and seems fantastic). However, their system uses pull requests, while we use mailing lists. Pull requests are easy, because github has good hook support, but how do we link mailing lists to an automatic test system?

As it turns out, this is something we're working on: we already have [Patchwork](http://patchwork.ozlabs.org/), and [Jenkins](https://openpower.xyz/): how do we link them? We have something brewing, which we'll open source real soon now - stay tuned!

#### Usable formal methods - are we there yet?

I liked [this talk](https://www.youtube.com/watch?v=RxHjhBVOCSU), as I have a soft spot for formal methods (as I have a soft spot for maths). It covers applying a bunch of static analysis and some of the less intrusive formal methods (in particular [cbmc](http://www.cprover.org/cbmc/)) to an operating system kernel. They were looking at eChronos rather than Linux, but it's still quite an interesting set of results.

We've also tried to increase our use of static analysis, which has already found a [real bug](http://patchwork.ozlabs.org/patch/580629/). We're hoping to scale this up, especially the use of sparse and cppcheck, but we're a bit short on developer cycles for it at the moment.

#### Adventures in OpenPower Firmware

Stewart Smith - another OzLabber - gave [this talk](https://www.youtube.com/watch?v=a4XGvssR-ag) about, well, OpenPOWER firmware. This is a large part of our lives in OzLabs, so it's a great way to get a picture of what we do each day. It's also a really good explanation of the open source stack we have: a POWER8 CPU runs open-source from the first cycle.

#### What Happens When 4096 Cores `All Do synchronize_rcu_expedited()`?

Paul McKenney is a parallel programming genius - he literally ['wrote the book'](https://www.kernel.org/pub/linux/kernel/people/paulmck/perfbook/perfbook.html) (or at least, wrote _a_ book!) on it. [His talk](https://www.youtube.com/watch?v=1nfpjHTWaUc) is - as always - a brain-stretching look at parallel programming within the RCU subsystem of the Linux kernel. In particular, the tree structure for locking that he presents is really interesting and quite a clever way of scaling what at first seems to be a necessarily global lock.

I'd also really recommed [RCU Mutation Testing](https://www.youtube.com/watch?v=tFmajPt0_hI), from the kernel miniconf, also by Paul.

#### What I've learned as the kernel docs maintainer

As an extra bonus: I mention [this talk](https://www.youtube.com/watch?v=gsJXf6oSbAE), just to say "why on earth have we still not fixed the Linux kernel [README](https://www.kernel.org/doc/linux/README)"?!!?