Title: "OpenPOWER Powers Forward"
Authors: Cyril Bur
Date: 2015-05-21 11:29
Category:  OpenPower
Tags: open-power

I wrote this blog post late last year, it is very relevant for this blog though so I'll repost it here.

With the launch of [TYAN's OpenPOWER reference system](http://www.tyan.com/campaign/openpower/) now is a good time to reflect on the team responsible for so much of the research, design and development behind this very first ground breaking step of [OpenPOWER](http://openpowerfoundation.org/) with their start to finish involvement of this new Power platform.

ADL Canberra have been integral to the success of this launch providing the Open Power Abstraction Layer (OPAL) firmware. OPAL breathes new life into Linux on Power finally allowing Linux to run on directly on the hardware.
While OPAL harnesses the hardware, ADL Canberra significantly improved Linux to sit on top and take direct control of IBMs new Power8 processor without needing to negotiate with a hypervisor. With all the Linux expertise present at ADL Canberra it's no wonder that a Linux based bootloader was developed to make this system work. Petitboot leverage's all the resources of the Linux kernel to create a light, fast and yet extremely versatile bootloader. Petitboot provides a massive amount of tools for debugging and system configuration without the need to load an operating system.

TYAN have developed great and highly customisable hardware. ADL Canberra have been there since day 1 performing vital platform enablement (bringup) of this new hardware. ADL Canberra have put all the work into the entire software stack, low level work to get OPAL and Linux to talk to the new BMC chip as well as the higher level, enabling to run Linux in either endian and Linux is even now capable of virtualising KVM guests in either endian irrespective of host endian. Furthermore a subset of ADL Canberra have been key to getting the Coherent Accelerator Processor Interface (CAPI) off the ground, enabling more almost endless customisation and greater diversity within the OpenPOWER ecosystem.

ADL Canberra is the home for Linux on Power and the beginning of the OpenPOWER hardware sees much of the hard work by ADL Canberra come to fruition.
