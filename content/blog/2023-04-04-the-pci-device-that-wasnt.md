Title: Dumb bugs: the PCI device that wasn't
Date: 2023-03-24 00:00:00
Authors: Russell Currey
Category: Development
Tags: linux

I was happily minding my own business one fateful afternoon when I receive the following kernel bug report:

```text
BUG: KASAN: slab-out-of-bounds in vga_arbiter_add_pci_device+0x60/0xe00
Read of size 4 at addr c000000264c26fdc by task swapper/0/1

Call Trace:
dump_stack_lvl+0x1bc/0x2b8 (unreliable)
print_report+0x3f4/0xc60
kasan_report+0x244/0x698
__asan_load4+0xe8/0x250
vga_arbiter_add_pci_device+0x60/0xe00
pci_notify+0x88/0x444
notifier_call_chain+0x104/0x320
blocking_notifier_call_chain+0xa0/0x140
device_add+0xac8/0x1d30
device_register+0x58/0x80
vio_register_device_node+0x9ac/0xce0
vio_bus_scan_register_devices+0xc4/0x13c
__machine_initcall_pseries_vio_device_init+0x94/0xf0
do_one_initcall+0x12c/0xaa8
kernel_init_freeable+0xa48/0xba8
kernel_init+0x64/0x400
ret_from_kernel_thread+0x5c/0x64
```

OK, so [KASAN](https://www.kernel.org/doc/html/latest/dev-tools/kasan.html) has helpfully found an out-of-bounds access in `vga_arbiter_add_pci_device()`.  What the heck is that?


# Why does my VGA require arbitration?

I'd never heard of the [VGA](https://en.wikipedia.org/wiki/VGA_connector) arbiter in the kernel (do kids these days know what VGA is?), or `vgaarb` as it's called.  What it does is irrelevant to this bug, but I found the history pretty interesting!  [Benjamin Herrenschmidt proposed VGA arbitration back in 2005](https://lists.freedesktop.org/archives/xorg/2005-March/006663.html) as a way of resolving conflicts between multiple legacy VGA devices that want to use the same address assignments.  This was previously handled in userspace by the X server, but issues arose with multiple X servers on the same machine.  Plus, it's probably not a good idea for this kind of thing to be handled by userspace.  [You can read more about the VGA arbiter in the kernel docs](https://docs.kernel.org/gpu/vgaarbiter.html), but it's probably not something anyone has thought much about in a long time.


# The bad access

```c
static bool vga_arbiter_add_pci_device(struct pci_dev *pdev)
{
        struct vga_device *vgadev;
        unsigned long flags;
        struct pci_bus *bus;
        struct pci_dev *bridge;
        u16 cmd;

        /* Only deal with VGA class devices */
        if ((pdev->class >> 8) != PCI_CLASS_DISPLAY_VGA)
                return false;
```

We're blowing up on the read to `pdev->class`, and it's not something like the data being uninitialised, it's out-of-bounds.  If we look back at the call trace:

```text
vga_arbiter_add_pci_device+0x60/0xe00
pci_notify+0x88/0x444
notifier_call_chain+0x104/0x320
blocking_notifier_call_chain+0xa0/0x140
device_add+0xac8/0x1d30
device_register+0x58/0x80
vio_register_device_node+0x9ac/0xce0
vio_bus_scan_register_devices+0xc4/0x13c
```

This thing is a VIO device, not a PCI device!  Let's jump into the caller, `pci_notify()`, to find out how we got our `pdev`.

```c
static int pci_notify(struct notifier_block *nb, unsigned long action,
                      void *data)
{
        struct device *dev = data;
        struct pci_dev *pdev = to_pci_dev(dev);
```

So `pci_notify()` gets called with our VIO device (somehow), and we're converting that `struct device` into a `struct pci_dev` with no error checking.  We could solve this particular bug by just checking that our device is *actually* a PCI device before we proceed - but we're in a function called `pci_notify`, we're expecting a PCI device to come in, so this would just be a bandaid.

`to_pci_dev()` works like other struct containers in the kernel - `struct pci_dev` contains a `struct device` as a member, so the `container_of()` function returns an address based on where a `struct pci_dev` would have to be if the given `struct device` was actually a PCI device.  Since we know it's not actually a PCI device and this `struct device` does not actually sit inside a `struct pci_dev`, our `pdev` is now pointing to some random place in memory, hence our access to a member like `class` is caught by KASAN.

Now we know why and how we're blowing up, but we still don't understand how we got here, so let's back up further.


# Notifiers

The kernel's device subsystem allows consumers to register callbacks to be notified on given events.  I'm not going to go into a ton of detail on how they work, because I don't fully understand myself, and there's a lot of internals of the device subsystem involved.
The best references I could find for this are [notifier.h](https://elixir.bootlin.com/linux/latest/source/include/linux/notifier.h), and for our purposes here, [the register notifier functions in bus.h](https://elixir.bootlin.com/linux/latest/source/include/linux/device/bus.h#L260).

Something's clearly gone awry if we can end up in a function named `pci_notify()` without passing it a PCI device.  We find where the notifier is registered in `vgaarb.c` here:

```c
static struct notifier_block pci_notifier = {
        .notifier_call = pci_notify,
};

static int __init vga_arb_device_init(void)
{
        /* some stuff removed here... */

        bus_register_notifier(&pci_bus_type, &pci_notifier);
```

This all looks sane.  A blocking notifier is registered so that `pci_notify()` gets called whenever there's a notification going out to PCI buses.  Our VIO device is distinctly *not* on a PCI bus, and in my debugging I couldn't find any potential causes of such confusion, so how on earth is a notification for PCI buses being applied to our non-PCI device?

Deep in the guts of the device subsystem, if we have a look at `device_add()` we find the following:

```c
int device_add(struct device *dev)
{
        /* lots of device init stuff... */

        if (dev->bus)
                blocking_notifier_call_chain(&dev->bus->p->bus_notifier,
                                             BUS_NOTIFY_ADD_DEVICE, dev);
```

If the device we're initialising is attached to a bus, then we call the bus notifier of that bus with the `BUS_NOTIFY_ADD_DEVICE` notification, and the device in question.  So we're going through the process of adding a VIO device, and somehow calling into a notifier that's only registered for PCI devices.  I did a bunch of debugging to see if our VIO device was somehow malformed and pointing to a PCI bus, or the `struct subsys_private` (that's the `bus->p` above) was somehow pointing to the wrong place, but everything seemed sane.  My thesis of there being confusion between matching devices to buses was getting harder to justify - everything still looked sane.


# Debuggers

I do not like debuggers.  I am an avid `printk()` enthusiast.  There's no real justification for this, a bunch of my problems could almost certainly be solved easier by using actual tools, but my brain seemingly enjoys the routine of printing and building and running until I figure out what's going on.  It was becoming increasingly obvious, however, that `printk` could not save me here, and we needed to go deeper.

Very thankfully for me, even though this bug was discovered on real hardware, it reproduces easily in [QEMU](https://www.qemu.org), making iteration easy.  With [GDB attached to QEMU](https://qemu-project.gitlab.io/qemu/system/gdb.html), it's time to dive in to the guts of this issue and figure out what's happening.

Somehow, VIO buses are ending up with `pci_notify()` in their `bus_notifier` list.  Let's break down the data structures here with a look at `struct notifier_block`:

```c
struct notifier_block {
        notifier_fn_t notifier_call;
        struct notifier_block __rcu *next;
        int priority;
};
```

So notifier chains are [singly linked lists](https://en.wikipedia.org/wiki/Linked_list#Singly_linked_list).  When callbacks are registered through functions like `bus_register_notifier()`, after a long chain of breadcrumbs we reach [notifier_chain_register()](https://elixir.bootlin.com/linux/latest/source/kernel/notifier.c#L22) which walks the list of `->next` pointers until it reaches `NULL`, at which point it sets `->next` of the tail node to the `struct notifier_block` that was passed in.  It's very important to note here that the data being appended to the list here is *not just the callback function* (i.e. `pci_notify()`), but the `struct notifier_block` itself (i.e. `struct notifier_block pci_notifier` from earlier).  There's no new data being initialised, just updating a pointer to the object that was passed by the caller.

If you've guessed what our bug is at this point, great job!  If the same `struct notifier_block` gets registered to two different bus types, then both of their `bus_notifier` fields will point to the *same memory*, and any further notifiers registered to either bus will end up being referenced by both since they walk through the same node.

So we bust out the debugger and start looking at what ends up in `bus_notifier` for PCI and VIO buses with breakpoints and watchpoints.


# Candidates

Walking the `bus_notifier` list gave me the following:

```text
__gcov_.perf_trace_module_free
fail_iommu_bus_notify
isa_bridge_notify
ppc_pci_unmap_irq_line
eeh_device_notifier
iommu_bus_notifier
tce_iommu_bus_notifier
pci_notify
```

Time to find out if our assumption is correct - the same `struct notifier_block` is being registered to both bus types.  Let's start going through them!

First up, we have `__gcov_.perf_trace_module_free`.  Thankfully, I recognised this as complete bait.  Trying to figure out what gcov and perf are doing here is going to be its own giant rabbit hole, and unless building without gcov makes our problem disappear, we skip this one and keep on looking.  Rabbit holes in the kernel never end, we have to be strategic with our time!

Next, we reach `fail_iommu_bus_notify`, so let's take a look at that.

```c
static struct notifier_block fail_iommu_bus_notifier = {
        .notifier_call = fail_iommu_bus_notify
};

static int __init fail_iommu_setup(void)
{
#ifdef CONFIG_PCI
        bus_register_notifier(&pci_bus_type, &fail_iommu_bus_notifier);
#endif
#ifdef CONFIG_IBMVIO
        bus_register_notifier(&vio_bus_type, &fail_iommu_bus_notifier);
#endif

        return 0;
}
```

Sure enough, here's our bug.  The same node is being registered to two different bus types:

```text
+------------------+
| PCI bus_notifier \
+------------------+\
                     \+-------------------------+    +-----------------+    +------------+
                      | fail_iommu_bus_notifier |----| PCI + VIO stuff |----| pci_notify |
                     /+-------------------------+    +-----------------+    +------------+
+------------------+/
| VIO bus_notifier /
+------------------+
```

when it should be like:

```text
+------------------+    +-----------------------------+    +-----------+    +------------+
| PCI bus_notifier |----| fail_iommu_pci_bus_notifier |----| PCI stuff |----| pci_notify |
+------------------+    +-----------------------------+    +-----------+    +------------+

+------------------+    +-----------------------------+    +-----------+
| VIO bus_notifier |----| fail_iommu_vio_bus_notifier |----| VIO stuff |
+------------------+    +-----------------------------+    +-----------+
```

# The fix

Ultimately, the fix turned out to be pretty simple:

```diff
Author: Russell Currey <ruscur@russell.cc>
Date:   Wed Mar 22 14:37:42 2023 +1100

    powerpc/iommu: Fix notifiers being shared by PCI and VIO buses

    fail_iommu_setup() registers the fail_iommu_bus_notifier struct to both
    PCI and VIO buses.  struct notifier_block is a linked list node, so this
    causes any notifiers later registered to either bus type to also be
    registered to the other since they share the same node.

    This causes issues in (at least) the vgaarb code, which registers a
    notifier for PCI buses.  pci_notify() ends up being called on a vio
    device, converted with to_pci_dev() even though it's not a PCI device,
    and finally makes a bad access in vga_arbiter_add_pci_device() as
    discovered with KASAN:

    [stack trace redacted, see above]

    Fix this by creating separate notifier_block structs for each bus type.

    Fixes: d6b9a81b2a45 ("powerpc: IOMMU fault injection")
    Reported-by: Nageswara R Sastry <rnsastry@linux.ibm.com>
    Signed-off-by: Russell Currey <ruscur@russell.cc>

diff --git a/arch/powerpc/kernel/iommu.c b/arch/powerpc/kernel/iommu.c
index ee95937bdaf1..6f1117fe3870 100644
--- a/arch/powerpc/kernel/iommu.c
+++ b/arch/powerpc/kernel/iommu.c
@@ -171,17 +171,26 @@ static int fail_iommu_bus_notify(struct notifier_block *nb,
         return 0;
 }

-static struct notifier_block fail_iommu_bus_notifier = {
+/*
+ * PCI and VIO buses need separate notifier_block structs, since they're linked
+ * list nodes.  Sharing a notifier_block would mean that any notifiers later
+ * registered for PCI buses would also get called by VIO buses and vice versa.
+ */
+static struct notifier_block fail_iommu_pci_bus_notifier = {
+        .notifier_call = fail_iommu_bus_notify
+};
+
+static struct notifier_block fail_iommu_vio_bus_notifier = {
         .notifier_call = fail_iommu_bus_notify
 };

 static int __init fail_iommu_setup(void)
 {
 #ifdef CONFIG_PCI
-        bus_register_notifier(&pci_bus_type, &fail_iommu_bus_notifier);
+        bus_register_notifier(&pci_bus_type, &fail_iommu_pci_bus_notifier);
 #endif
 #ifdef CONFIG_IBMVIO
-        bus_register_notifier(&vio_bus_type, &fail_iommu_bus_notifier);
+        bus_register_notifier(&vio_bus_type, &fail_iommu_vio_bus_notifier);
 #endif

         return 0;
```

Easy!  Problem solved.  The [commit that introduced this bug back in 2012](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=d6b9a81b2a45) was written by the legendary [Anton Blanchard](https://antonblanchardfacts.com), so it's always a treat to discover an Anton bug.  Ultimately this bug is of little consequence, but it's always fun to catch dormant issues with powerful tools like KASAN.


# In conclusion

I think this bug provides a nice window into what kernel debugging can be like.  Thankfully, things are made easier by not dealing with any specific hardware and being easily reproducible in QEMU.

Bugs like this have an absurd amount of underlying complexity, but you rarely need to understand all of it to comprehend the situation and discover the issue.  I spent way too much time digging into device subsystem internals, when the odds of the issue lying within were quite low - the combination of IBM VIO devices and VGA arbitration isn't exactly common, so searching for potential issues within the guts of a heavily utilised subsystem isn't going to yield results very often.

Is there something haunted in the device subsystem?  Is there something haunted inside the notifier handlers?  It's possible, but assuming the core guts of the kernel have a baseline level of sanity helps to let you stay focused on the parts more likely to be relevant.

Finally, the process was made much easier by having good code navigation.  A ludicrous amount of kernel developers still use plain vim or Emacs, maybe with tags if you're lucky, and get by on `git grep` (not even ripgrep!) and memory.  Sort yourselves out and get yourself an editor with LSP support.  I personally use [Doom Emacs](https://github.com/doomemacs/doomemacs) with [clangd](https://clangd.llvm.org/), and with the amount of jumping around the kernel I had to do to solve this bug, it would've been a much bigger ordeal without that power.

If you enjoyed the read, why not follow me on [Mastodon](https://ozlabs.house/@ruscur) or checkout [Ben's recount of another cursed bug!](https://sthbrx.github.io/blog/2023/03/24/dumb-bugs-when-a-date-breaks-booting-the-kernel/)  Thanks for stopping by.
