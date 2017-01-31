Title: Extracting Early Boot Messages in QEMU
Date: 2017-01-30 16:47:00
Authors: Suraj Jitindar Singh
Category: Education, QEMU, Virtualisation
Tags: QEMU, debug, virtualisation, kernel, dmesg, printk, boot, early, error

Be me, you're a kernel hacker, you make some changes to your kernel, you boot
test it in QEMU, and it fails to boot. Even worse is the fact that it just hangs
without any failure message, no stack trace, no nothing. "Now what?" you think
to yourself.

You probably do the first thing you learnt in debugging101 and add abundant
print statements all over the place to try and make some sense of what's
happening and where it is that you're actually crashing. So you do this, you
recompile your kernel, boot it in QEMU and lo and behold, nothing... What
happened? You added all these shiny new print statements, where did the output
go? The kernel still failed to boot (obviously), but where you were hoping to
get some clue to go on you were again left with an empty screen. "Maybe I
didn't print early enough" or "maybe I got the code paths wrong" you think,
"maybe I just need more prints" even. So lets delve a bit deeper, why didn't
you see those prints, where did they go, and how can you get at them?

# __log_buf

So what happens when you call printk()? Well what normally happens is,
depending on the log level you set, the output is sent to the console or logged
so you can see it in dmesg. But what happens if we haven't registered a console
yet? Well then we can't print the message can we, so its logged in a buffer,
kernel log buffer to be exact helpfully named __log_buf.

# Console Registration

So how come I eventually see print statements on my screen? Well at some point
during the boot process a console is registered with the printk system, and any
buffered output can now be displayed. On ppc it happens that this occurs in
register_early_udbg_console() called in setup_arch() from start_kernel(),
which is the generic kernel entry point. From this point forward when you print
something it will be displayed on the console, but what if you crash before
this? What are you supposed to do then?

# Extracting Early Boot Messages in QEMU

And now the moment you've all been waiting for, how do I extract those early
boot messages in QEMU if my kernel crashes before the console is registered?
Well it's quite simple really, QEMU is nice enough to allow us to dump guest
memory, and we know the log buffer is in there some where, so we just need to
dump the correct part of memory which corresponds to the log buffer.

#### Locating __log_buf

Before we can dump the log buffer we need to know where it is. Luckily for us
this is fairly simple, we just need to dump all the kernel symbols and look for
the right one.


```c
> nm vmlinux > tmp; grep __log_buf tmp;
c000000000f5e3dc b __log_buf
```

We use the nm tool to list all the kernel symbols and output this into some
temporary file, we can then grep this for the log buffer (which we know to be
named __log_buf), and presto we are told that it's at kernel address 0xf5e3dc.

#### Dumping Guest Memory

It's then simply a case of dumping guest memory from the QEMU console. So first
we press ^a+c to get us to the QEMU console, then we can use the aptly named
dump-guest-memory.

```c
> help dump-guest-memory
dump-guest-memory [-p] [-d] [-z|-l|-s] filename [begin length] -- dump guest memory into file 'filename'.
			-p: do paging to get guest's memory mapping.
			-d: return immediately (do not wait for completion).
			-z: dump in kdump-compressed format, with zlib compression.
			-l: dump in kdump-compressed format, with lzo compression.
			-s: dump in kdump-compressed format, with snappy compression.
			begin: the starting physical address.
			length: the memory size, in bytes.
```

We just give it a filename for where we want our output to go, we know the
starting address, we just don't know the length. We could choose some arbitrary
length, but inspection of the kernel code shows us that:

```c
#define __LOG_BUF_LEN (1 << CONFIG_LOG_BUF_SHIFT)
static char __log_buf[__LOG_BUF_LEN] __aligned(LOG_ALIGN);
```

Looking at the pseries_defconfig file shows us that the LOG_BUF_SHIFT is set to
18, and thus we know that the buffer is 2^18 bytes or 256kb. So now we run:

```c
> dump-guest-memory tmp 0xf5e3dc 262144
```

And we now get our log buffer in the file tmp. This can simply be viewed with:

```c
> hexdump -C tmp
```

This gives a readable, if poorly formatted output. I'm sure you can find
something better but I'll leave that as an exercise for the reader.

# Conclusion

So if like me your kernel hangs somewhere early in the boot process and you're
left without your console output you are now fully equipped to extract the log
buffer in QEMU and hopefully therein lies the answer to why you failed to boot.
