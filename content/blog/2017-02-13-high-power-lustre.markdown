Title: High Power Lustre
Date: 2017-02-13 16:29:00
Authors: Daniel Axtens, Rashmica Gupta
Category: OpenPOWER
Tags: lustre, hpc

(Most of the hard work here was done by fellow blogger Rashmica - I just verified her instructions and wrote up this post.)

Lustre is a high-performance clustered file system. Traditionally the Lustre client and server have run on x86, but both the server and client will also work on Power. Here's how to get them running.

# Server

Lustre normally requires a patched 'enterprise' kernel - normally an old RHEL, CentOS or SUSE kernel. We tested with a CentOS 7.3 kernel. We tried to follow [the Intel instructions](https://wiki.hpdd.intel.com/pages/viewpage.action?pageId=52104622) for building the kernel as much as possible - any deviations we had to make are listed below.

## The kernel source RPM

I first tried to grab the recommended source RPM - but had some issues with the package giving us a 404.

    [build@dja-centos-guest kernel]$ rpm -ivh http://vault.centos.org/7.3.1611/updates/Source/SPackages/kernel-3.10.0-514.6.1.el7.src.rpm
    Retrieving http://vault.centos.org/7.3.1611/updates/Source/SPackages/kernel-3.10.0-514.6.1.el7.src.rpm
    curl: (22) The requested URL returned error: 404 Not Found

It seems the package had temporarily vanished from the mirrors: it's now back.

### A brief diversion

While waiting for the package to return, I briefly attempted to use an older CentOS 7.2 kernel: 3.10.0-327.36.3

That did *not* work: it compiled fine, but displayed the following error message on boot:

    IBM,CPBW-1.0 NOT FOUND
    ler_entry NOT FOUND

I then tried to build the RPM with a config from my running 514 series kernel. That required me to turn off the kABI check, and then also failed on boot:

    Memory reserve map exhausted !
                                   NOT FOUND
    tent resource <%016llx-%016llx>
                                    NOT FOUND


I didn't try to debug those errors, instead I gave up on the old kernel and found the correct source RPM for the more up to date kernel. You should also build with the correct source rpm!

## Issues with the given instructions

I had to fix a couple of minor quirks with their instructions.

We are told to edit `~/kernel/rpmbuild/SPEC/kernel.spec`. This doesn't exist because the directory is `SPECS` not `SPEC`: you need to edit `~/kernel/rpmbuild/SPECS/kernel.spec`.

I also found there was an extra quote mark in the supplied patch script after `-lustre.patch`. I removed that and ran this instead:

    for patch in $(<"3.10-rhel7.series"); do \
          patch_file="$HOME/lustre-release/lustre/kernel_patches/patches/${patch}" \
          cat "${patch_file}" >> $HOME/lustre-kernel-x86_64-lustre.patch \
    done

The fact that there is 'x86_64' in the patch name doesn't matter as you're about to copy it under a different name to a place where it will be included by the spec file.

## Building for ppc64le

Building for ppc64le was reasonably straight-forward. I had one small issue

    [build@dja-centos-guest rpmbuild]$ rpmbuild -bp --target=`uname -m` ./SPECS/kernel.spec
    Building target platforms: ppc64le
    Building for target ppc64le
    error: Failed build dependencies:
           net-tools is needed by kernel-3.10.0-327.36.3.el7.ppc64le

Fixing this was as simple as a `yum install net-tools`.

This was sufficient to build the kernel rpms. I installed them and booted to my patched kernel - so far so good!

# Building the client packages: CentOS

I then tried to build and install the RPMs from `lustre-release`. This repository provides the client and utility RPMs.

`./configure` and `make` succeeded, but when I went to install the packages with `rpm`, I found I aws missing some dependencies:

    error: Failed dependencies:
            ldiskfsprogs >= 1.42.7.wc1 is needed by kmod-lustre-osd-ldiskfs-2.9.52_60_g1d2fbad_dirty-1.el7.centos.ppc64le
	    sg3_utils is needed by lustre-iokit-2.9.52_60_g1d2fbad_dirty-1.el7.centos.ppc64le
            attr is needed by lustre-tests-2.9.52_60_g1d2fbad_dirty-1.el7.centos.ppc64le
            lsof is needed by lustre-tests-2.9.52_60_g1d2fbad_dirty-1.el7.centos.ppc64le
				

I was able to install `sg3_utils`, `attr` and `lsof`, but I was still missing `ldiskfsprogs`.

It seems we need the lustre-patched version of `e2fsprogs` - I found a [mailing list post](https://groups.google.com/forum/#!topic/lustre-discuss-list/U93Ja6Xkxfk) to that effect.

So, following the instructions on the walkthrough, I grabbed [the SRPM](https://downloads.hpdd.intel.com/public/e2fsprogs/latest/el7/SRPMS/e2fsprogs-1.42.13.wc5-7.el7.src.rpm) and installed the dependencies: `yum install -y texinfo libblkid-devel libuuid-devel`

I then tried `rpmbuild -ba SPECS/e2fsprogs-RHEL-7.spec`. This built but failed tests. Some failed because I ran out of disk space: I found that there were some comments in the spec file about this with suggested tests to disable, so I did that. Even with that fix, I was still failing two tests:

 * `f_pgsize_gt_blksize`: Intel added this to their fork, and no equivalent exists in the master e2fsprogs branches.
 * `f_eofblocks`: This may need fixing for large page sizes, see [this bug](https://jira.hpdd.intel.com/browse/LU-4677?focusedCommentId=78814&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-78814).

But with those disabled I was able to build the packages successfully. I installed them with `yum localinstall *1.42.13.wc5*` (I needed that rather weird pattern to pick up important RPMs that didn't fit the `e2fs*` pattern - things like `libcom_err` and `libss`)

Following that I went back to the `lustre-release` build products and was able to successfully run `yum localinstall *ppc64le.rpm`!

# Testing the server

After disabling SELinux and rebooting, I ran the test script:

    sudo /usr/lib64/lustre/tests/llmount.sh

This spat out one scary warning:

    mount.lustre FATAL: unhandled/unloaded fs type 0 'ext3'

The test did seem to succeed overall, and it would seem that is a [known problem](https://jira.hpdd.intel.com/browse/LU-9059), so I pressed on undeterred.

I then attached a couple of virtual harddrives for the metadata and object store volumes, and having set them up, proceeded to try to mount my freshly minted lustre volume from some clients.

# Testing with a ppc64le client

My first step was to test whether another ppc64le machine would work as a client.

I tried with an existing Ubuntu 16.04 VM that I use for much of my day to day development.

A quick google suggested that I could grab the `lustre-release` repository and run `make debs` to get debian packages for my system.

I needed the following dependencies:

    sudo apt install module-assistant debhelper dpatch libsnmp-dev quilt

With those the packages built sucessfully, and could be easily installed:

    dpkg -i lustre-client-modules-4.4.0-57-generic_2.9.52-60-g1d2fbad-dirty-1_ppc64el.deblustre-utils_2.9.52-60-g1d2fbad-dirty-1_ppc64el.deb

I tried to connect to the server:

    sudo mount -t lustre $SERVER_IP@tcp:/lustre /lustre/

Initially I wasn't able to connect to the server at all. I remembered that (unlike Ubuntu), CentOS comes with quite an agressive firewall by default. I ran the following on the server:

    systemctl stop firewalld

And voila! I was able to connect, mount the lustre volume, and successfully read and write to it. This is very much an over-the-top hack - I should have poked holes in the firewall to allow just the ports lustre needed. This is left as an exercise for the reader.

# Testing with an x86_64 client

I then tried to run `make debs` on my Ubuntu 16.10 x86_64 laptop.

This did not go well - I got the following error:

    liblustreapi.c: In function ‘llapi_get_poollist’:
    liblustreapi.c:1201:3: error: ‘readdir_r’ is deprecated [-Werror=deprecated-declarations]

This looks like one of the new errors intruduced in recent GCC versions: I found the following stanza in a `lustre/autoconf/lustre-core.m4`, and removed the `-Werror`:

    AS_IF([test $target_cpu == "i686" -o $target_cpu == "x86_64"],
            [CFLAGS="$CFLAGS -Wall -Werror"])

Even this wasn't enough: I got the following errors:

    /home/dja/dev/lustre-release/debian/tmp/modules-deb/usr_src/modules/lustre/lustre/llite/dcache.c:387:22: error: initialization from incompatible pointer type [-Werror=incompatible-pointer-types]
             .d_compare = ll_dcompare,
	                  ^~~~~~~~~~~
    /home/dja/dev/lustre-release/debian/tmp/modules-deb/usr_src/modules/lustre/lustre/llite/dcache.c:387:22: note: (near initialization for ‘ll_d_ops.d_compare’)

I figured this was probably because Ubuntu 16.10 has a 4.8 kernel, and Ubutu 16.04 has a 4.4 kernel. Sure enough, when I fired up a 16.04 x86_64 VM with a 4.4 kernel, I was able to build an install fine.

Connecting didn't work first time - the guest failed to mount, but I did get the following helpful error on the server:

    LNetError: 2595:0:(acceptor.c:406:lnet_acceptor()) Refusing connection from 10.61.2.227: insecure port 1024

Refusing insecure port 1024 made me thing that perhaps the NATing that qemu was performing for me was interfering - perhaps the server expected to get a connection where the source port was privileged, and qemu wouldn't be able to do that with NAT.

Sure enough, switching NAT to bridging was enough to get the x86 VM to talk to the ppc64le server. I verified that `ls`, reading and writing all succeeded.

# Next steps

The obvious next steps are following up the disabled tests in e2fsprogs, and doing a lot of internal performance and functionality testing.

Happily, it looks like Lustre might be in the mainline kernel before too long - parts have already started to go in to staging. This will make our lives a lot easier: for example, the breakage between 4.4 and 4.8 would probably have already been picked up and fixed if it was the main kernel tree rather than an out-of-tree patch set.

In the long run, we'd like to make Lustre on Power just as easy as Lustre on x86. (And, of course, more performant!) We'll keep you up to date!
