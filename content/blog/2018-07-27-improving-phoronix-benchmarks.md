Title: Improving performance of Phoronix benchmarks on POWER9
Date: 2018-08-15 14:22
Authors: Rashmica Gupta, Daniel Black, Anton Blanchard, Nick Piggin, Joel Stanley
Category: Performance
Tags: performance, phoronix, benchmarks
 


Recently Phoronix ran a range of
[benchmarks](https://www.phoronix.com/scan.php?page=article&item=power9-talos-2&num=1)
comparing the performance of our POWER9 processor against the Intel Xeon and AMD
EPYC processors. 

We did well in the Stockfish, LLVM Compilation, Zstd compression, and the
Tinymembench benchmarks. A few of my colleagues did a bit of investigating into
some the benchmarks where we didn't perform quite so well.


### LBM / Parboil 

The [Parboil benchmarks](http://impact.crhc.illinois.edu/parboil/parboil.aspx) are a
collection of programs from various scientific and commercial fields that are
useful for examining the performance and development of different architectures
and tools.  In this round of benchmarks Phoronix used the lbm
[benchmark](https://www.spec.org/cpu2006/Docs/470.lbm.html): a fluid dynamics
simulation using the Lattice-Boltzmann Method.

lbm is an iterative algorithm - the problem is broken down into discrete
time steps, and at each time step a bunch of calculations are done to
simulate the change in the system. Each time step relies on the results
of the previous one.

The benchmark uses OpenMP to parallelise the workload, spreading the
calculations done in each time step across many CPUs. The number of
calculations scales with the resolution of the simulation.

Unfortunately, the resolution (and therefore the work done in each time
step) is too small for modern CPUs with large numbers of SMT (simultaneous multi-threading) threads. OpenMP 
doesn't have enough work to parallelise and the system stays relatively idle. This
means the benchmark scales relatively poorly, and is definitely
not making use of the large POWER9 system

Also this benchmark is compiled without any optimisation. Recompiling with -O3 improves the
   results 3.2x on POWER9.



### x264 Video Encoding
x264 is a library that encodes videos into the H.264/MPEG-4 format. x264 encoding
requires a lot of integer kernels doing operations on image elements. The math
and vectorisation optimisations are quite complex, so Nick only had a quick look at
the basics. The systems and environments (e.g. gcc version 8.1 for Skylake, 8.0
for POWER9) are not completely apples to apples so for now patterns are more
important than the absolute results. Interestingly the output video files between
architectures are not the same, particularly with different asm routines and 
compiler options used, which makes it difficult to verify the correctness of any changes.

All tests were run single threaded to avoid any SMT effects.

With the default upstream build of x264, Skylake is significantly faster than POWER9 on this benchmark
(Skylake: 9.20 fps, POWER9: 3.39 fps). POWER9 contains some vectorised routines, so an
initial suspicion is that Skylake's larger vector size may be responsible for its higher throughput.

Let's test our vector size suspicion by restricting
Skylake to SSE4.2 code (with 128 bit vectors, the same width as POWER9). This hardly
slows down the x86 CPU at all (Skylake: 8.37 fps, POWER9: 3.39 fps), which indicates it's
not taking much advantage of the larger vectors.

So the next guess would be that x86 just has more and better optimized versions of costly
functions (in the version of x264 that Phoronix used there are only six powerpc specific
files compared with 21 x86 specific files). Without the time or expertise to dig into the
complex task of writing vector code, we'll see if the compiler can help, and turn
on autovectorisation (x264 compiles with -fno-tree-vectorize by default, which disables 
auto vectorization). Looking at a perf profile of the benchmark we can see
that one costly function, quant_4x4x4, is not autovectorised. With a small change to the
code, gcc does vectorise it, giving a slight speedup with the output file checksum unchanged
(Skylake: 9.20 fps, POWER9: 3.83 fps).

We got a small improvement with the compiler, but it looks like we may have gains left on the
table with our vector code. If you're interested in looking into this, we do have some
[active bounties](https://www.bountysource.com/teams/ibm/bounties) for x264 (lu-zero/x264).


| Test |Skylake |POWER9|
|-------|---------|-------|
| Original - AVX256 |9.20 fps |3.39 fps|
| Original - SSE4.2 | 8.37 fps | 3.39 fps|
| Autovectorisation enabled, quant_4x4x4 vectorised| 9.20 fps | 3.83 fps |

Nick also investigated running this benchmark with SMT enabled and across multiple cores, and it looks like the code is
not scalable enough to feed 176 threads on a 44 core system. Disabling SMT in parallel runs
actually helped, but there was still idle time. That may be another thing to look at,
although it may not be such a problem for smaller systems.



### Primesieve

[Primesieve](https://primesieve.org/) is a program and C/C++
library that generates all the prime numbers below a given number. It uses an
optimised [Sieve of Eratosthenes](https://upload.wikimedia.org/wikipedia/commons/b/b9/Sieve_of_Eratosthenes_animation.gif)
implementation.

The algorithm uses the L1 cache size as the sieve size for the core loop.  This
is an issue when we are running in SMT mode (aka more than one thread per core)
as all threads on a core share the same L1 cache and so will constantly be 
invalidating each others cache-lines. As you can see
in the table below, running the benchmark in single threaded mode is 30% faster
than in SMT4 mode!

This means in SMT-4 mode the workload is about 4x too large for the L1 cache.  A
better sieve size to use would be the L1 cache size / number of
threads per core. Anton posted a [pull request](https://github.com/kimwalisch/primesieve/pull/54) 
to update the sieve size.

It is interesting that the best overall performance on POWER9 is with the patch applied and in
SMT2 mode:

|SMT level   |    baseline   |     patched|
|------------|---------------|----------|
|1           |    14.728s     | 14.899s	|
|2           |    15.362s     | 14.040s	|
|4           |    19.489s     | 17.458s	|


### LAME 

Despite its name, a recursive acronym for "LAME Ain't an MP3 Encoder",
[LAME](http://lame.sourceforge.net/) is indeed an MP3 encoder.

Due to configure options [not being parsed correctly](https://sourceforge.net/p/lame/mailman/message/36371506/) this
benchmark is built without any optimisation regardless of architecture. We see a
massive speedup by turning optimisations on, and a further 6-8% speedup by
enabling
[USE_FAST_LOG](https://sourceforge.net/p/lame/mailman/message/36372005/) (which
is already enabled for Intel).

| LAME | Duration | Speedup |
|---------|-------------|--|
| Default | 82.1s | n/a |
| With optimisation flags | 16.3s | 5.0x |
| With optimisation flags and USE_FAST_LOG set | 15.6s | 5.3x  |

For more detail see Joel's
[writeup](https://shenki.github.io/LameMP3-on-Power9/).



### FLAC

[FLAC](https://xiph.org/flac/) is an alternative encoding format to
MP3. But unlike MP3 encoding it is lossless!  The benchmark here was encoding
audio files into the FLAC format. 

The key part of this workload is missing
vector support for POWER8 and POWER9. Anton and Amitay submitted this
[patch series](http://lists.xiph.org/pipermail/flac-dev/2018-July/006351.html) that
adds in POWER specific vector instructions. It also fixes the configuration options
to correctly detect the POWER8 and POWER9 platforms. With this patch series we get see about a 3x
improvement in this benchmark.


### OpenSSL

[OpenSSL](https://www.openssl.org/) is among other things a cryptographic library. The Phoronix benchmark
measures the number of RSA 4096 signs per second:
```
$ openssl speed -multi $(nproc) rsa4096

```

Phoronix used OpenSSL-1.1.0f, which is almost half as slow for this benchmark (on POWER9) than mainline OpenSSL.
Mainline OpenSSL has some powerpc multiplication and squaring assembly code which seems
to be responsible for most of this speedup.
 


To see this for yourself, add these four powerpc specific commits on top of OpenSSL-1.1.0f:

1. [perlasm/ppc-xlate.pl: recognize .type directive](https://github.com/openssl/openssl/commit/b17ff188b17499e83ca3b9df0be47a2f513ac3c5)
2. [bn/asm/ppc-mont.pl: prepare for extension](https://github.com/openssl/openssl/commit/0310becc82d240288a4ab5c6656c10c18cab4454)
3. [bn/asm/ppc-mont.pl: add optimized multiplication and squaring subroutines](https://github.com/openssl/openssl/commit/68f6d2a02c8cc30c5c737fc948b7cf023a234b47)
4. [ppccap.c: engage new multipplication and squaring subroutines](https://github.com/openssl/openssl/commit/80d27cdb84985c697f8fabb7649abf1f54714d13)




The following results were from a dual 16-core POWER9:

| Version of OpenSSL | Signs/s | Speedup |
|--------------------|----------|---------|
|1.1.0f              |    1921   |  n/a   |
|1.1.0f with 4 patches|   3353   | 1.74x  |
|1.1.1-pre1          |    3383   | 1.76x   | 



### SciKit-Learn

[SciKit-Learn](http://scikit-learn.org/) is a bunch of python tools for data mining and
analysis (aka machine learning).

Joel noticed that the benchmark spent 92% of the time in libblas. Libblas is a
very basic BLAS (basic linear algebra subprograms) library that python-numpy
uses to do vector and matrix operations.  The default libblas on Ubuntu is only
compiled with -O2. Compiling with -Ofast and using alternative BLAS's that have
powerpc optimisations (such as libatlas or libopenblas) we see big improvements
in this benchmark:


| BLAS used | Duration | Speedup |
|---------|-------------|--|
| libblas -O2 |64.2s | n/a |
| libblas -Ofast |  36.1s | 1.8x |
| libatlas | 8.3s | 7.7x  |
|libopenblas | 4.2s | 15.3x |


You can read more details about this
[here](https://shenki.github.io/Scikit-Learn-on-Power9/).


### Blender

[Blender](https://www.blender.org/) is a 3D graphics suite that supports image rendering,
animation, simulation and game creation. On the surface it appears that Blender
2.79b (the distro package version that Phoronix used by system/blender-1.0.2)
failed to use more than 15 threads, even when "-t 128" was added to the Blender
command line.

It turns out that even though this benchmark was supposed to be run on CPUs only
(you can choose to render on CPUs or GPUs), the GPU file was always being used.
The GPU file is configured with a very large tile size (256x256) -
which is [fine for
GPUs](https://docs.blender.org/manual/en/dev/render/cycles/settings/scene/render/performance.html#tiles)
but not great for CPUs. The image size (1280x720) to tile size ratio limits the
number of jobs created and therefore the number threads used.


To obtain a realistic CPU measurement with more that 15 threads you can force
the use of the CPU file by overwriting the GPU file with the CPU one:

```
$ cp
~/.phoronix-test-suite/installed-tests/system/blender-1.0.2/benchmark/pabellon_barcelona/pavillon_barcelone_cpu.blend
~/.phoronix-test-suite/installed-tests/system/blender-1.0.2/benchmark/pabellon_barcelona/pavillon_barcelone_gpu.blend
```

As you can see in the image below, now all of the cores are being utilised!
![Blender with CPU Blend file][00]


Fortunately this has already been fixed in 
[pts/blender-1.1.1](https://openbenchmarking.org/test/pts/blender).
Thanks to the [report](https://github.com/phoronix-test-suite/test-profiles/issues/24) by Daniel it
has also been fixed in [system/blender-1.1.0](http://openbenchmarking.org/test/system/blender-1.1.0).



Pinning the pts/bender-1.0.2, Pabellon Barcelona, CPU-Only test to a single
22-core POWER9 chip (```sudo ppc64_cpu --cores-on=22```) and two POWER9 chips
(```sudo ppc64_cpu --cores-on=44```) show a huge speedup:

| Benchmark | Duration (deviation over 3 runs) | Speedup |
|--------------------------------|------------------------------|---------|
|Baseline (GPU blend file) |  1509.97s (0.30%) | n/a |
| Single 22-core POWER9 chip (CPU blend file)  | 458.64s (0.19%) | 3.29x  |
| Two 22-core POWER9 chips (CPU blend file)  | 241.33s (0.25%) | 6.25x |




### tl;dr

Some of the benchmarks where we don't perform as well as Intel are where the
benchmark has inline assembly for x86 but uses generic C compiler generated
assembly for POWER9. We could probably benefit with some more powerpc optimsed functions.

We also found a couple of things that should result in better performance for all three architectures,
not just POWER.

A summary of the performance improvements we found:

| Benchmark | Approximate Improvement |
|-----------|-------------|
| Parboil   |    3x	  |
| x264      |	 1.1x	  |
| Primesieve|	 1.1x	  |
| LAME      |  	 5x	  |
| FLAC      |	 3x	  |
| OpenSSL   |	 2x	  |
| SciKit-Learn | 7-15x   |
| Blender   | 	 3x	  |	

There is obviously room for more improvements, especially with the Primesieve and x264 benchmarks,
but it would be interesting to see a re-run of the Phoronix benchmarks with these changes. 

Thanks to Anton, Daniel, Joel and Nick for the analysis of the above benchmarks.

[00]: /images/phoronix/blender-88threads.png "Blender with CPU Blend file"



