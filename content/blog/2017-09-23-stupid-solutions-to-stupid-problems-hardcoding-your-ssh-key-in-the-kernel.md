Title: Stupid Solutions to Stupid Problems: Hardcoding Your SSH Key in the Kernel
Date: 2017-09-23 03:00:00
Authors: Andrew Donnellan
Category: Development
Tags: kernel, stupid ideas

The "problem"
-------------

I'm currently working on firmware and kernel support for [OpenCAPI](http://opencapi.org/) on POWER9.

I've recently been allocated a machine in the lab for development purposes. We use an internal IBM tool running on a secondary machine that triggers hardware initialisation procedures, then loads a specified [skiboot](https://github.com/open-power/skiboot) firmware image, a kernel image, and a root file system directly into RAM. This allows us to get skiboot and Linux running without requiring the usual [hostboot](https://github.com/open-power/hostboot) initialisation and gives us a lot of options for easier tinkering, so it's super-useful for our developers working on bringup.

When I got access to my machine, I figured out the necessary scripts, developed a workflow, and started fixing my code... so far, so good.

One day, I was trying to debug something and get logs off the machine using `ssh` and `scp`, when I got frustrated with having to repeatedly type in our ultra-secret, ultra-secure root password, `abc123`. So, I ran `ssh-copy-id` to copy over my public key, and all was good.

Until I rebooted the machine, when strangely, my key stopped working. It took me longer than it should have to realise that this is an obvious consequence of running entirely from an initrd that's reloaded every boot...

The "solution"
--------------

I mentioned something about this to Jono, my housemate/partner-in-stupid-ideas, one evening a few weeks ago. We decided that clearly, the best way to solve this problem was to hardcode my SSH public key in the kernel.

This would definitely be the easiest and most sensible way to solve the problem, as opposed to, say, just keeping my own copy of the root filesystem image. Or asking [Mikey](https://twitter.com/mikeyneuling), whose desk is three metres away from mine, whether he could use his write access to add my key to the image. Or just writing a wrapper around [sshpass](https://linux.die.net/man/1/sshpass)...

One Tuesday afternoon, I was feeling bored...

The approach
------------

The SSH daemon looks for authorised public keys in `~/.ssh/authorized_keys`, so we need to have a read of `/root/.ssh/authorized_keys` return a specified hard-coded string.

I did a bit of investigation. My first thought was to put some kind of hook inside whatever filesystem driver was being used for the root. After some digging, I found out that the filesystem type `rootfs`, as seen in `mount`, is actually backed by the `tmpfs` filesystem. I took a look around the `tmpfs` code for a while, but didn't see any way to hook in a fake file without a lot of effort - the `tmpfs` code wasn't exactly designed with this in mind.

I thought about it some more - what would be the easiest way to create a file such that it just returns a string?

Then I remembered sysfs, the filesystem normally mounted at `/sys`, which is used by various kernel subsystems to expose configuration and debugging information to userspace in the form of files. The sysfs API allows you to define a file and specify callbacks to handle reads and writes to the file.

That got me thinking - could I create a file in `/sys`, and then use a [bind mount](https://unix.stackexchange.com/questions/198590/what-is-a-bind-mount) to have that file appear where I need it in `/root/.ssh/authorized_keys`? This approach seemed fairly straightforward, so I decided to give it a try.

First up, creating a pseudo-file. It had been a while since the last time I'd used the sysfs API...

sysfs
-----

The sysfs pseudo file system was first introduced in Linux 2.6, and is generally used for exposing system and device information.

Per the [sysfs documentation](https://www.kernel.org/doc/Documentation/filesystems/sysfs.txt), sysfs is tied in very closely with the [kobject](https://www.kernel.org/doc/Documentation/kobject.txt) infrastructure. sysfs exposes kobjects as directories, containing "attributes" represented as files. The kobject infrastructure provides a way to define kobjects representing entities (e.g. devices) and ksets which define collections of kobjects (e.g. devices of a particular type).

Using kobjects you can do lots of fancy things such as sending events to userspace when devices are hotplugged - but that's all out of the scope of this post. It turns out there's some fairly straightforward wrapper functions if all you want to do is create a kobject just to have a simple directory in sysfs.

```c
#include <linux/kobject.h>

static int __init ssh_key_init(void)
{
        struct kobject *ssh_kobj;
        ssh_kobj = kobject_create_and_add("ssh", NULL);
        if (!ssh_kobj) {
                pr_err("SSH: kobject creation failed!\n");
                return -ENOMEM;
        }
}
late_initcall(ssh_key_init);
```

This creates and adds a kobject called `ssh`. And just like that, we've got a directory in `/sys/ssh/`!

The next thing we have to do is define a sysfs attribute for our `authorized_keys` file. sysfs provides a framework for subsystems to define their own custom types of attributes with their own metadata - but for our purposes, we'll use the generic `bin_attribute` attribute type.

```c
#include <linux/sysfs.h>

const char key[] = "PUBLIC KEY HERE...";

static ssize_t show_key(struct file *file, struct kobject *kobj,
                        struct bin_attribute *bin_attr, char *to,
                        loff_t pos, size_t count)
{
        return memory_read_from_buffer(to, count, &pos, key, bin_attr->size);
}

static const struct bin_attribute authorized_keys_attr = {
        .attr = { .name = "authorized_keys", .mode = 0444 },
        .read = show_key,
        .size = sizeof(key)
};
```

We provide a simple callback, `show_key()`, that copies the key string into the file's buffer, and we put it in a `bin_attribute` with the appropriate name, size and permissions.

To actually add the attribute, we put the following in `ssh_key_init()`:

```c
int rc;
rc = sysfs_create_bin_file(ssh_kobj, &authorized_keys_attr);
if (rc) {
        pr_err("SSH: sysfs creation failed, rc %d\n", rc);
        return rc;
}
```

Woo, we've now got `/sys/ssh/authorized_keys`! Time to move on to the bind mount.

Mounting
--------

Now that we've got a directory with the key file in it, it's time to figure out the bind mount.

Because I had no idea how any of the file system code works, I started off by running `strace` on `mount --bind ~/tmp1 ~/tmp2` just to see how the userspace `mount` tool uses the `mount` syscall to request the bind mount.

```c
execve("/bin/mount", ["mount", "--bind", "/home/ajd/tmp1", "/home/ajd/tmp2"], [/* 18 vars */]) = 0

...

mount("/home/ajd/tmp1", "/home/ajd/tmp2", 0x18b78bf00, MS_MGC_VAL|MS_BIND, NULL) = 0
```

The first and second arguments are the source and target paths respectively. The third argument, looking at the signature of the `mount` syscall, is a pointer to a string with the file system type. Because this is a bind mount, the type is irrelevant (upon further digging, it turns out that this particular pointer is to the string "none").

The fourth argument is where we specify the flags bitfield. `MS_MGC_VAL` is a magic value that was required before Linux 2.4 and can now be safely ignored. `MS_BIND`, as you can probably guess, signals that we want a bind mount.

(The final argument is used to pass file system specific data - as you can see it's ignored here.)

Now, how is the syscall actually handled on the kernel side? The answer is found in [fs/namespace.c](http://elixir.free-electrons.com/linux/latest/source/fs/namespace.c#L2969).

```c
SYSCALL_DEFINE5(mount, char __user *, dev_name, char __user *, dir_name,
                char __user *, type, unsigned long, flags, void __user *, data)
{
        int ret;

        /* ... copy parameters from userspace memory ... */

        ret = do_mount(kernel_dev, dir_name, kernel_type, flags, options);

        /* ... cleanup ... */
}
```

So in order to achieve the same thing from within the kernel, we just call `do_mount()` with exactly the same parameters as the syscall uses:

```c
rc = do_mount("/sys/ssh", "/root/.ssh", "sysfs", MS_BIND, NULL);
if (rc) {
        pr_err("SSH: bind mount failed, rc %d\n", rc);
        return rc;
}
```

...and we're done, right? Not so fast:

```
SSH: bind mount failed, rc -2
```

-2 is `ENOENT` - no such file or directory. For some reason, we can't find `/sys/ssh`... of course, that would be because even though we've created the sysfs entry, we haven't actually mounted sysfs on `/sys`.

```c
rc = do_mount("sysfs", "/sys", "sysfs",
              MS_NOSUID | MS_NOEXEC | MS_NODEV, NULL);
```

At this point, my key worked!

Note that this requires that your root file system has an empty directory created at `/sys` to be the mount point. Additionally, in a typical Linux distribution environment (as opposed to my hardware bringup environment), your initial root file system will contain an init script that mounts your real root file system somewhere and calls `pivot_root()` to switch to the new root file system. At that point, the bind mount won't be visible from children processes using the new root - I think this could be worked around but would require some effort.

Kconfig
-------

The final piece of the puzzle is building our new code into the kernel image.

To allow us to switch this important functionality on and off, I added a config option to `fs/Kconfig`:

```
config SSH_KEY
        bool "Andrew's dumb SSH key hack"
        default y
        help
          Hardcode an SSH key for /root/.ssh/authorized_keys.
         
          This is a stupid idea. If unsure, say N.
```

This will show up in `make menuconfig` under the `File systems` menu.

And in `fs/Makefile`:

```
obj-$(CONFIG_SSH_KEY)           += ssh_key.o
```

If `CONFIG_SSH_KEY` is set to `y`, `obj-$(CONFIG_SSH_KEY)` evaluates to `obj-y` and thus `ssh-key.o` gets compiled. Conversely, `obj-n` is completely ignored by the build system.

I thought I was all done... then [Andrew](https://twitter.com/mramboar) suggested I make the contents of the key configurable, and I had to oblige. Conveniently, Kconfig options can also be strings:

```
config SSH_KEY_VALUE
        string "Value for SSH key"
        depends on SSH_KEY
        help
          Enter in the content for /root/.ssh/authorized_keys.
```

Including the string in the C file is as simple as:

```c
const char key[] = CONFIG_SSH_KEY_VALUE;
```

And there we have it, a nicely configurable albeit highly limited kernel SSH backdoor!

Conclusion
----------

I've put the [full code](https://github.com/ajdlinux/linux/commit/052c0cb7296f7510fd482fecbe572b641c29239f) up on GitHub for perusal. Please don't use it, I will be extremely disappointed in you if you do.

Thanks to Jono for giving me stupid ideas, and the rest of OzLabs for being very angry when they saw the disgusting things I was doing.

Comments and further stupid suggestions welcome!
