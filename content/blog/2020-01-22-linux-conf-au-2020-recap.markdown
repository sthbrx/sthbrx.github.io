Title: linux.conf.au 2020 recap
Date: 2020-01-22 16:00:00
Authors: Andrew Donnellan
Category: Education
Tags: conferences

It's that time of year again. Most of OzLabs headed up to the Gold Coast for linux.conf.au 2020.

linux.conf.au is one of the longest-running community-led Linux and Free Software events in the world, and attracts a crowd from Australia, New Zealand and much further afield. OzLabbers have been involved in LCA since the very beginning and this year was no exception with myself running the Kernel Miniconf and several others speaking.

The list below contains some of our highlights that we think you should check out. This is just a few of the talks that we managed to make it to - there's plenty more worthwhile stuff on the [linux.conf.au YouTube channel](https://www.youtube.com/user/linuxconfau2019/featured).

We'll see you all at LCA2021 right here in Canberra...

Keynotes
========

A couple of the keynotes really stood out:

* [Sean Brady - Drop Your Tools - Does Expertise have a Dark Side?](https://www.youtube.com/watch?v=Yv4tI6939q0)

  Sean is a forensic structural engineer who shows us a variety of examples, from structural collapses and firefighting disasters, where trained professionals were blinded by their expertise and couldn't bring themselves to do things that were obvious.

* [Vanessa Teague - Who cares about Democracy?](https://www.youtube.com/watch?v=xfpy5c3thQo)

  There's nothing quite like cryptography proofs presented to a keynote audience at 9:30 in the morning. Vanessa goes over the issues with electronic voting systems in Australia, and especially internet voting as used in NSW, including flaws in their implementation of cryptographic algorithms. There continues to be no good way to do internet voting, but with developments in methodologies like risk-limiting audits there may be reasonably safe ways to do in-person electronic voting.

OpenPOWER
=========

There was an OpenISA miniconf, co-organised by none other than Hugh Blemings of the OpenPOWER Foundation.

* [Michael Neuling / Anton Blanchard - Power OpenISA and Microwatt Introduction](https://www.youtube.com/watch?v=RU6RPYAqFzE)

  Anton (on Mikey's behalf) introduces the Power OpenISA and the Microwatt FPGA core which has been released to go with it.

* [Anton Blanchard - Build your own Open Hardware CPU in 25 minutes or less](https://www.youtube.com/watch?v=g3slH03MCmo)

  Anton live demos Microwatt in simulation, and also tries to synthesise it for his FPGA but runs out of time...

* [Paul Mackerras - Microwatt Microarchitecture](https://www.youtube.com/watch?v=JkDx_y0onSk)

  Paul presents an in-depth overview of the design of the Microwatt core.

Kernel
======

There were quite a few kernel talks, both in the [Kernel Miniconf](http://lca-kernel.ozlabs.org) and throughout the main conference. These are just some of them:

* [Aleksa Sarai - Designing Extensible Syscalls](https://www.youtube.com/watch?v=ggD-eb3yPVs)

  There's been many cases where we've introduced a syscall only to find out later on that we need to add some new parameters - how do we make our syscalls extensible so we can add new parameters later on without needing to define a whole new syscall, while maintaining both forward and backward compatibility? It turns out it's pretty simple but needs a few more kernel helpers.

* [Russell Currey - Kernel hacking like it's 2020](https://www.youtube.com/watch?v=heib48KG-YQ)

  There are a bunch of tools out there which you can use to make your kernel hacking experience much more pleasant. You should use them.

* [Aleksa Sarai - Securing Container Runtimes - How Hard Can It Be?](https://www.youtube.com/watch?v=tGseJW_uBB8)

  Among other security issues with container runtimes, using procfs to setup security controls during the startup of a container is fraught with hilarious problems, because procfs and the Linux filesystem API aren't really designed to do this safely, and also have a bunch of amusing bugs.

* [Kees Cook - Control Flow Integrity in the Linux Kernel](https://www.youtube.com/watch?v=0Bj6W7qrOOI)

  Control Flow Integrity is a technique for restricting exploit techniques that hijack a program's control flow (e.g. by overwriting a return address on the stack (ROP), or overwriting a function pointer that's used in an indirect jump). Kees goes through the current state of CFI supporting features in hardware and what is currently available to enable CFI in the kernel.

* [Matthew Wilcox - Large Pages in Linux](https://www.youtube.com/watch?v=p5u-vbwu3Fs)

  Linux has supported huge pages for many years, which has significantly improved CPU performance. However, the huge page mechanism was driven by hardware advancements and is somewhat inflexible, and it's just as important to consider software overhead. Matthew has been working on supporting more flexible "large pages" in the page cache to do just that.

* [Russell Currey - The magical fantasy land of Linux kernel testing](https://www.youtube.com/watch?v=9Fzd6MapG3Y)

  Spoiler: the magical fantasy land is a trap.

Community
=========

Lots of community and ethics discussion this year - one talk which stood out to me:

* [Bradley M. Kuhn / Karen Sandler - Open Source Won, but Software Freedom Hasn't Yet: A Guide & Commisseration Session for FOSS activists](https://www.youtube.com/watch?v=n55WClalwHo)

  Bradley and Karen argue that while open source has "won", software freedom has regressed in recent years, and present their vision for what modern, pragmatic Free Software activism should look like.

Other
=====

Among the variety of other technical talks at LCA...

* [Matthew Treinish - Building a Compiler for Quantum Computers](https://www.youtube.com/watch?v=L2P501Iy6J8)

  Quantum compilers are not really like regular classical compilers (indeed, they're really closer to FPGA synthesis tools). Matthew talks through how quantum compilers map a program on to IBM's quantum hardware and the types of optimisations they apply.

* [Fraser Tweedale - Clevis and Tang: securing your secrets at rest](https://www.youtube.com/watch?v=Dk6ZuydQt9I)

  Clevis and Tang provide an implementation of "network bound encryption", allowing you to magically decrypt your secrets when you are on a secure network with access to the appropriate Tang servers. This talk outlines use cases and provides a demonstration.

* [Christoph Lameter - How to capture 100G Ethernet traffic at wire speed to local disk](https://www.youtube.com/watch?v=uBBaVtHkiOI)

  Christoph discusses how to deal with the hardware and software limitations that make it difficult to capture traffic at wire speed on fast fibre networks.