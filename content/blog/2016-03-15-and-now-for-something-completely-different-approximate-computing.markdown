Title: And now for something completely different: approximate computing
Authors: Daniel Axtens
Date: 2016-03-15 11:30
Category: Education
Tags: conferences

In early February I had the opportunity to go the the NICTA Systems Summer School, where Cyril and I were invited to represent IBM. There were a number of excellent talks across a huge range of systems related subjects, but the one that has stuck with me the most was a talk given by [Luis Ceze](http://homes.cs.washington.edu/~luisceze/)  on a topic called approximate computing. So here, in hopes that you too find it interesting, is a brief run-down on what I learned.

Approximate computing is fundamentally about trading off accuracy for something else - often speed or power consumption. Initially this sounded like a very weird proposition: computers do things like 'running your operating system' and 'reading from and writing to disks': things you need to always be absolutely correct if you want anything vaguely resembling reliability. It turns out that this is actually not as big a roadblock as I had assumed - you can work around it fairly easily.

The model proposed for approximate computing is as follows. You divide your computation up into two classes: 'precise', and 'approximate'. You use 'precise' computations when you need to get exact answers: so for example if you are constructing a JPEG file, you want the JPEG header to be exact. Then you have approximate computations: so for example the contents of your image can be approximate.

For correctness, you have to establish some boundaries: you say that precise data can be used in approximate calculations, but that approximate data isn't allowed to cross back over and pollute precise calculations. This, while intuitively correct, poses some problems in practise: when you want to write out your approximate JPEG data, you need an operation that allows you to 'bless' (or in their terms 'endorse') some approximate data so it can be used in the precise file system operations.

In the talk we were shown an implementation of this model in Java, called [EnerJ](http://sampa.cs.washington.edu/research/approximation/enerj.html). EnerJ allows you to label variables with either `@Precise` if you're dealing with precise data, or `@Approx` if you're dealing with approximate data. The compiler was modified so that it would do all sorts of weird things when it knew it was dealing with approximate data: for example, drop loop iterations entirely, do things in entirely non-determistic ways - all sorts of fun stuff. It turns out this works surprisingly well.

However, the approximate computing really shines when you can bring it all the way down to the hardware level. The first thing they tried was a CPU with both 'approximate' and precise execution engines, but this turned out not to have the power savings hoped for. What seemed to work really well was a model where some approximate calculations could be identified ahead of time, and then replaced with neural networks in hardware. These neural networks approximated the calculations, but did so at significantly lower power levels. This sounded like a really promising concept, and it will be interesting to see if this goes anywhere over the next few years.

There's a lot of work evaluating the quality of the approximate result, for cases where the set of inputs is known, and when the inputs is not known. This is largely beyond my understanding, so I'll simply refer you to some of the papers [listed on the website](http://sampa.cs.washington.edu/research/approximation/enerj.html).

The final thing covered in the talk was bringing approximate computing into current paradigms by just being willing to accept higher user-visible error rates. For example, they hacked up a network stack to accept packets with invalid checksums. This has had mixed results so far. A question I had (but didn't get around to asking!) would be whether the mathematical properties of checksums (i.e. that they can correct a certain number of bit errors) could be used to correct some of the errors, rather than just accepting/rejecting them blindly. Perhaps by first attempting to correct errors using the checksums, we will be able to fix the simpler errors, reducing the error rate visible to the user.

Overall, I found the NICTA Systems Summer School to be a really interesting experience (and I hope to blog more about it soon). If you're a university student in Australia, or an academic, see if you can make it in 2017!
