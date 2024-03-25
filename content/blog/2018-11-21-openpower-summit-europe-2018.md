Title: OpenPOWER Summit Europe 2018: A Software Developer's Introduction to OpenCAPI
Date: 2018-11-21 18:20:00
Authors: Andrew Donnellan
Category: OpenPOWER
Tags: linux, firmware, openpower, opencapi, openpower summit

Last month, I was in Amsterdam at [OpenPOWER Summit Europe](https://openpowerfoundation.org/summit-2018-10-eu/). It was great to see so much interest in OpenPOWER, with a particularly strong contingent of researchers sharing how they're exploiting the unique advantages of OpenPOWER platforms, and a number of OpenPOWER hardware partners announcing products.

(It was also my first time visiting Europe, so I had a lot of fun exploring Amsterdam, taking a few days off in Vienna, then meeting some of my IBM Linux Technology Centre colleagues in Toulouse. I also now appreciate just what ~50 hours on planes does to you!)

One particular area which got a lot of attention at the Summit was [OpenCAPI](https://opencapi.org), an open coherent high-performance bus interface designed for accelerators, which is supported on POWER9. We had plenty of talks about OpenCAPI and the interesting work that is already happening with OpenCAPI accelerators.

I was invited to present on the Linux Technology Centre's work on enabling OpenCAPI from the software side. In this talk, I outline the OpenCAPI software stack and how you can interface with an OpenCAPI device through the ocxl kernel driver and the [libocxl](https://github.com/opencapi/libocxl) userspace library.

<iframe width="560" height="315" src="https://www.youtube.com/embed/zCIMHbZDRS0" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

My [slides]({static}/misc/OPFEU2018_OpenCAPI.pdf) are available, though you'll want to watch the presentation for context.

Apart from myself, the OzLabs team were well represented at the Summit:

 * [Daniel Black](https://github.com/grooverdan) spoke on Power performance optimisation
 * [Stewart Smith](https://www.flamingspork.com/) gave an overview of the Power boot process
 * [Joel Stanley](https://shenki.github.io/) presented on recent developments in OpenBMC
 * [Jeremy Kerr](http://jk.ozlabs.org/) talked about the various OpenPOWER firmware projects

Unfortunately none of their videos are up yet, but they'll be there over the next few weeks. Keep an eye on the [Summit website](https://openpowerfoundation.org/summit-2018-10-eu/) and the [Summit YouTube playlist](https://www.youtube.com/playlist?list=PLEqfbaomKgQo5CimgYbVxdtiVtyloWc9e), where you'll find all the rest of the Summit content.

If you've got any questions about OpenCAPI feel free to leave a comment!