Title: Optical Action at a Distance
Date: 2016-07-05 15:23
Authors: Samuel Mendoza-Jonas
Category: Petitboot
Tags: petitboot, power, p8, openpower, goodposts, realcontent, netboot, pxe

Generally when someone wants to install a Linux distro they start with an ISO
file. Now we could burn that to a DVD, walk into the server room, and put it in
our machine, but that's a pain. Instead let's look at how to do this over the
network with Petitboot!

At the moment Petitboot won't be able to handle an ISO file unless it's
mounted in an expected place (eg. as a mounted DVD), so we need to unpack it
somewhere. Choose somewhere to host the result and unpack the ISO via whatever
method you prefer. (For example `bsdtar -xf /path/to/image.iso`).

You'll get a bunch of files but for our purposes we only care about a few; the
kernel, the initrd, and the bootloader configuration file. Using
the Ubuntu 16.04 ppc64el ISO as an example, these are:
```
./install/vmlinux
./install/initrd.gz.
./boot/grub/grub.cfg
```

In grub.cfg we can see that the boot arguments are actually quite simple:
```
set timeout=-1

menuentry "Install" {
	linux	/install/vmlinux tasks=standard pkgsel/language-pack-patterns= pkgsel/install-language-support=false --- quiet
	initrd	/install/initrd.gz
}

menuentry "Rescue mode" {
	linux	/install/vmlinux rescue/enable=true --- quiet
	initrd	/install/initrd.gz
}
```

So all we need to do is create a PXE config file that points Petitboot towards
the correct files.

We're going to create a PXE config file which you could serve from your DHCP
server, but that does not mean we need to use PXE - if you just want a quick
install you only need make these files accessible to Petitboot, and then we can
use the 'Retrieve config from URL' option to download the files.

Create a petitboot.conf file somewhere accessible that contains (for Ubuntu):
```
label Install Ubuntu 16.04 Xenial Xerus
	kernel http://myaccesibleserver/path/to/vmlinux
	initrd http://myaccesibleserver/path/to/initrd.gz
	append tasks=standard pkgsel/language-pack-patterns= pkgsel/install-language-support=false --- quiet
```

Then in Petitboot, select 'Retrieve config from URL' and enter
`http://myaccesibleserver/path/to/petitboot.conf`. In the main menu your new
option should appear - select it and away you go!
