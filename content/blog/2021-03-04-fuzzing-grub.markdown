Title: Fuzzing grub: part 1
Date: 2021-03-04 17:10:00
Authors: Daniel Axtens
Category: Development
Tags: testing

Recently a set of 8 vulnerabilities were disclosed for the [grubbootloader](https://wiki.ubuntu.com/SecurityTeam/KnowledgeBase/GRUB2SecureBootBypass2021). I
found 2 of them (CVE-2021-20225 and CVE-2021-20233), and contributed a number of
other fixes for crashing bugs which we don't believe are exploitable. I found
them by applying fuzz testing to grub. Here's how.

This is a multi-part series: I think it will end up being 4 posts. I'm hoping to
cover:

 * Part 1 (this post): getting started with fuzzing grub
 * Part 2: going faster by doing lots more work
 * Part 3: fuzzing filesystems and more
 * Part 4: potential next steps and avenues for further work


Fuzz testing
============

Let's begin with part one: getting started with fuzzing grub.

One of my all-time favourite techniques for testing programs, especially
programs that handle untrusted input, and especially-especially programs written
in C that parse untrusted input, is fuzz testing. Fuzz testing (or fuzzing) is
the process of repeatedly throwing randomised data at your program under test
and seeing what it does.

(For the secure boot threat model, untrusted input is anything not validated by
a cryptographic signature - so config files are untrusted for our purposes, but
grub modules can only be loaded if they are signed, so they are trusted.)

Fuzzing has a long history and has recently received a new lease on life with
coverage-guided fuzzing tools like [AFL](https://lcamtuf.coredump.cx/afl/) and
more recently [AFL++](https://aflplus.plus/).


Building grub for AFL++
=======================

AFL++ is extremely easy to use ... if your program:

 1. is built as a single binary with a regular tool-chain
 2. runs as a regular user-space program on Linux
 3. reads a small input files from disk and then exits
 4. doesn't do anything fancy with threads or signals

Beyond that, it gets a bit more complex.

On the face of it, grub fails 3 of these 4 criteria:

 - grub is a highly modular program: it loads almost all of its functionality as
   modules which are linked as separate ELF relocatable files. (Not runnable
   programs, but not shared libraries either.)

 - grub usually runs as a bootloader, not as a regular app.

 - grub reads all sorts of things, ranging in size from small files to full
   disks. After loading most things, it returns to a command prompt rather than
   exiting.

Fortunately, these problems are not insurmountable.

We'll start with the 'running as a bootloader' problem. Here, grub helps us out
a bit, because it provides an 'emulator' target, which runs most of grub
functionality as a userspace program. It doesn't support actually booting
anything (unsurprisingly) but it does support most other modules, including
things like the config file parser.

We can configure grub to build the emulator. We disable the graphical frontend
for now.

```
:::shell
./bootstrap
./configure --with-platform=emu --disable-grub-emu-sdl
```

At this point in building a fuzzing target, we'd normally try to configure with
`afl-cc` to get the instrumentation that makes AFL(++) so powerful. However, the
grub configure script is not a fan:

```
:::text
./configure --with-platform=emu --disable-grub-emu-sdl CC=$AFL_PATH/afl-cc
...
checking whether target compiler is working... no
configure: error: cannot compile for the target
```

It also doesn't work with `afl-gcc`.

Hmm, ok, so what if we just... lie a bit?

```
:::shell
./configure --with-platform=emu --disable-grub-emu-sdl
make CC="$AFL_PATH/afl-gcc" 
```

(Normally I'd use `CC=clang` and `afl-cc`, but clang support is slightly broken
upstream at the moment.)

After a small fix for gcc-10 compatibility, we get the userspace tools
(potentially handy!) but a bunch of link errors for `grub-emu`:

```
:::text
/usr/bin/ld: disk.module:(.bss+0x20): multiple definition of `__afl_global_area_ptr'; kernel.exec:(.bss+0xe078): first defined here
/usr/bin/ld: regexp.module:(.bss+0x70): multiple definition of `__afl_global_area_ptr'; kernel.exec:(.bss+0xe078): first defined here
/usr/bin/ld: blocklist.module:(.bss+0x28): multiple definition of `__afl_global_area_ptr'; kernel.exec:(.bss+0xe078): first defined here
```

The problem is the module linkage that I talked about earlier: because there is
a link stage of sorts for each module, some AFL support code gets linked in to
both the grub kernel (`kernel.exec`) and each module (here `disk.module`,
`regexp.module`, ...). The linker doesn't like it being in both, which is fair
enough.

To get started, let's instead take advantage of the smarts of AFL++ using Qemu
mode instead. This builds a specially instrumented qemu user-mode emulator
that's capable of doing coverage-guided fuzzing on uninstrumented binaries at
the cost of a significant performance penalty.

```
:::shell
make clean
make
```

Now we have a grub-emu binary. If you run it directly, you'll pick up your
system boot configuration, but the `-d` option can point it to a directory of
your choosing. Let's set up one for fuzzing:

```
:::shell
mkdir stage
echo "echo Hello sthbrx readers" > stage/grub.cfg
cd stage
../grub-core/grub-emu -d .
```

You probably won't see the message because the screen gets blanked at the end of
running the config file, but if you pipe it through `less` or something you'll
see it.

Running the fuzzer
==================

So, that seems to work - let's create a test input and try fuzzing:

```
:::shell
cd ..
mkdir in
echo "echo hi" > in/echo-hi

cd stage
# -Q qemu mode
# -M main fuzzer
# -d don't do deterministic steps (too slow for a text format)
# -f create file grub.cfg
$AFL_PATH/afl-fuzz -Q -i ../in -o ../out -M main -d -- ../grub-core/grub-emu -d .
```

Sadly:

```
:::text
[-] The program took more than 1000 ms to process one of the initial test cases.
    This is bad news; raising the limit with the -t option is possible, but
    will probably make the fuzzing process extremely slow.

    If this test case is just a fluke, the other option is to just avoid it
    altogether, and find one that is less of a CPU hog.

[-] PROGRAM ABORT : Test case 'id:000000,time:0,orig:echo-hi' results in a timeout
         Location : perform_dry_run(), src/afl-fuzz-init.c:866
```

What we're seeing here (and indeed what you can observe if you run `grub-emu`
directly) is that `grub-emu` isn't exiting when it's done. It's waiting for more
input, and will keep waiting for input until it's killed by `afl-fuzz`.

We need to patch grub to sort that out. It's on [my GitHub](https://github.com/daxtens/grub/commit/ad2e84224e674eb1f9dcd8efc3d8efe78ed62bec).

Apply that, rebuild with `FUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION`, and voila:

```
:::shell
cd ..
make CFLAGS="-DFUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION"
cd stage
$AFL_PATH/afl-fuzz -Q -i ../in -o ../out -M main -d -f grub.cfg -- ../grub-core/grub-emu -d .
```

And fuzzing is happening!

![afl-fuzz fuzzing grub, showing fuzzing happening](/images/dja/grub-fuzzing-pt1.png)

This is enough to find some of the (now-fixed) bugs in the grub config file
parsing!

Fuzzing beyond the config file
==============================

You can also extend this to fuzzing other things that don't require the
graphical UI, such as grub's transparent decompression support:

```
:::shell
cd ..
rm -rf in out stage
mkdir in stage
echo hi > in/hi
gzip in/hi
cd stage
echo "cat thefile" > grub.cfg
$AFL_PATH/afl-fuzz -Q -i ../in -o ../out -M main -f thefile -- ../grub-core/grub-emu -d .
```

You should be able to find a hang pretty quickly with this, an as-yet-unfixed
bug where grub will print output forever from a corrupt file: (your mileage may
vary, as will the paths.)

```
:::shell
cp ../out/main/hangs/id:000000,src:000000,time:43383,op:havoc,rep:16 thefile
../grub-core/grub-emu -d . | less # observe this going on forever
```

`zcat`, on the other hand, reports it as simply corrupt:

```
:::text
$ zcat thefile

gzip: thefile: invalid compressed data--format violated
```

(Feel free to fix that and send a patch to the list!)

That wraps up part 1. Eventually I'll be back with part 2, where I explain the
hoops to jump through to go faster with the `afl-cc` instrumentation.
