Title: NAMD on NVLink
Date: 2017-02-01 08:32:00
Authors: Daniel Axtens, Rashmica Gupta, Daniel Black
Category: OpenPOWER
Tags: nvlink, namd, cuda, gpu, hpc, minsky, S822LC for hpc

NAMD is a molecular dynamics program that can use GPU acceleration to speed up its calculations. Recent OpenPOWER machines like the IBM Power Systems S822LC for High Performance Computing (Minsky) come with a new interconnect for GPUs called NVLink, which offers extremely high bandwidth to a number of very powerful Nvidia Pascal P100 GPUs. So they're ideal machines for this sort of workload.

Here's how to set up NAMD 2.12 on your Minsky, and how to debug some common issues. We've targeted this script for CentOS, but we've successfully compiled NAMD on Ubuntu as well.

## Prerequisites

### GPU Drivers and CUDA

Firstly, you'll need CUDA and the NVidia drivers.

You can install CUDA by following the instructions on NVidia's [CUDA Downloads](https://developer.nvidia.com/cuda-downloads) page.

    yum install epel-release
    yum install dkms
    # download the rpm from the NVidia website
    rpm -i cuda-repo-rhel7-8-0-local-ga2-8.0.54-1.ppc64le.rpm
    yum clean expire-cache
    yum install cuda
    # this will take a while...

Then, we set up a profile file to automatically load CUDA into our path:

    cat >  /etc/profile.d/cuda_path.sh <<EOF
    # From http://developer.download.nvidia.com/compute/cuda/8.0/secure/prod/docs/sidebar/CUDA_Quick_Start_Guide.pdf - 4.4.2.1
    export PATH=/usr/local/cuda-8.0/bin${PATH:+:${PATH}}
    export LD_LIBRARY_PATH=/usr/local/cuda-8.0/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
    EOF

Now, open a new terminal session and check to see if it works:

    cuda-install-samples-8.0.sh ~
    cd ~/NVIDIA_CUDA-8.0_Samples/1_Utilities/bandwidthTest
    make && ./bandwidthTest

If you see a figure of ~32GB/s, that means NVLink is working as expected. A figure of ~7-8GB indicates that only PCI is working, and more debugging is required.

### Compilers

You need a c++ compiler:

    yum install gcc-c++

## Building NAMD

Once CUDA and the compilers are installed, building NAMD is reasonably straightforward. The one hitch is that because we're using CUDA 8.0, and the NAMD build scripts assume CUDA 7.5, we need to supply an updated [Linux-POWER.cuda file](/images/namd/Linux-POWER.cuda). (We also enable code generation for the Pascal in this file.)

We've documented the entire process as a script which you can [download](/images/namd/install-namd.sh). We'd recommend executing the commands one by one, but if you're brave you can run the script directly.

The script will fetch NAMD 2.12 and build it for you, but won't install it. It will look for the CUDA override file in the directory you are running the script from, and will automatically move it into the correct place so it is picked up by the build system..

The script compiles for a single multicore machine setup, rather than for a cluster. However, it should be a good start for an Ethernet or Infiniband setup.

If you're doing things by hand, you may see some errors during the compilation of charm - as long as you get `charm++ built successfully.` at the end, you should be OK.

## Testing NAMD

We have been testing NAMD using the STMV files available from the [NAMD website](http://www.ks.uiuc.edu/Research/namd/utilities/):

    cd NAMD_2.12_Source/Linux-POWER-g++
    wget http://www.ks.uiuc.edu/Research/namd/utilities/stmv.tar.gz
    tar -xf stmv.tar.gz
    sudo ./charmrun +p80 ./namd2 +pemap 0-159:2 +idlepoll +commthread stmv/stmv.namd
    
This binds a namd worker thread to every second hardware thread. This is because hardware threads share resources, so using every hardware thread costs overhead and doesn't give us access to any more physical resources.

You should see messages about finding and using GPUs:

    Pe 0 physical rank 0 binding to CUDA device 0 on <hostname>: 'Graphics Device'  Mem: 4042MB  Rev: 6.0

This should be *significantly* faster than on non-NVLink machines - we saw a gain of about 2x in speed going from a machine with Nvidia K80s to a Minsky. If things aren't faster for you, let us know!

## Downloads

 * [Install script for CentOS](/images/namd/install-namd.sh)
 * [Linux-POWER.cuda file](/images/namd/Linux-POWER.cuda)

## Other notes

Namd requires some libraries, some of which they supply as binary downloads on [their website](http://www.ks.uiuc.edu/Research/namd/libraries/).
Make sure you get the ppc64le versions, not the ppc64 versions, otherwise you'll get errors like:

    /bin/ld: failed to merge target specific data of file .rootdir/tcl/lib/libtcl8.5.a(regfree.o)
    /bin/ld: .rootdir/tcl/lib/libtcl8.5.a(regerror.o): compiled for a big endian system and target is little endian
    /bin/ld: failed to merge target specific data of file .rootdir/tcl/lib/libtcl8.5.a(regerror.o)
    /bin/ld: .rootdir/tcl/lib/libtcl8.5.a(tclAlloc.o): compiled for a big endian system and target is little endian

The script we supply should get these right automatically.
