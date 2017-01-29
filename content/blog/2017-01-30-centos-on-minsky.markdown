Title: Installing Centos 7.2 on IBM Power System's S822LC for High Performance Computing (Minksy) with USB device
Date: 2017-01-30 08:54:33
Authors: Daniel Black
Category: OpenPOWER
Tags: S822LC for hpc, hpc, centos, centos7, p8, bmc

## Introduction

If you are installing Linux on your IBM Power System's S822LC server then the instructions in this article will help you to start and run your system.  These instructions are specific to installing CentOS 7 on an IBM Power System S822LC for High Performance Computing (Minsky).

### Prerequisites

Before you power on the system, ensure that you have the following items:

* Ethernet cables;
* USB storage device of 7G or greater;
* An installed ethernet network with a DHCP server;
* Access to the DHCP server's logs;
* Power cords and outlet for your system;
* PC or notebook that has IPMItool level 1.8.15 or greater; and 
* a VNC client.


Download CentOS ISO file from the [Centos Mirror](http://mirror.centos.org/altarch/7/isos/ppc64le/). Select the "Everything" ISO file.

Note: You must use the 1611 release (dated 2016-12-22) or later due to Linux Kernel support for the server hardware.

## Step 1: Preparing to power on your system

Follow these steps to prepare your system:

1. If your system belongs in a rack, install your system into that rack. For instructions, see IBM POWER8 Systems information.
1. Connect an Ethernet cable to the left embedded Ethernet port next to the serial port on the back of your system and the other end to your network. This Ethernet port is used for the BMC/IPMI interface.
1. Connect another Enternet cable to the right Ethernet port for network connection for the operating system.
1. Connect the power cords to the system and plug them into the outlets. 

At this point, your firmware is booting.

## Step 2: Determining the BMC firmware IP address

To determine the IP address of the BMC, examine the latest DHCP server logs for the network connected to the server. The IP address will be requested approximately 2 minutes after being powered on.

It is possible to set the BMC to a static IP address by following the [IBM documentation on IPMI](https://www.ibm.com/support/knowledgecenter/en/TI0003H/p8eih/p8eih_managing_with_ipmi_ami.htm).

## Step 3: Connecting to the BMC firmware with IPMItool

After you have a network connection set up for your BMC firmware, you can connect using Intelligent Platform Management Interface (IPMI).  IPMI is the default console to use when connecting to the Open Power Abstraction Layer (OPAL) firmware.

Use the default authentication for servers over IPMI is:

 * Default user: ADMIN 
 * Default password: admin 

To power on your server from a PC or notebook that is running Linux®, follow these steps:

Open a terminal program on your PC or notebook with [Activate Serial-Over-Lan using IPMI](#active-sol-ipmi). Use other steps here as needed.

For the following impitool commands, server_ip_address is the IP address of the BMC from Step 2, and ipmi_user and ipmi_password are the default user ID and password for IPMI.

### Power On using IPMI

If your server is not powered on, run the following command to power the server on:
```
ipmitool -I lanplus -H server_ip_address -U ipmi_user -P ipmi_password chassis power on
```

### <a name="active-sol-ipmi"></a>Activate Serial-Over-Lan using IPMI

Activate your IPMI console by running this command:
```
ipmitool -I lanplus -H server_ip_address -U ipmi_user -P ipmi_password sol activate
```

After powering on your system, the Petitboot interface loads. If you do not interrupt the boot process by pressing any key within 10 seconds, Petitboot automatically boots the first option. At this point the IPMI console will be connected to the Operating Systems serial. If you get to this stage accidently you can deactivate and reboot as per the following two commands.

### Deactivate Serial-Over-Lan using IPMI

If you need to power off or reboot your system, deactivate the console by running this command:
```
ipmitool -I lanplus -H server_ip_address -U user-name -P ipmi_password sol deactivate
```

### Reboot using IPMI

If you need to reboot the system, run this command: 
```
ipmitool -I lanplus -H server_ip_address -U user-name -P ipmi_password chassis power reset
```

## Step 4: Creating a USB device and booting

At this point, your IPMI console should be contain a Petitboot bootloader menu as illistrated below and you are ready to install Centos 7 on your server.

![Petitboot menu over IPMI](/images/centos7-minsky/petitboot-centos7-usb-topmenu.png) 

Use one of the following USB devices:

 * USB attached DVD player with a single USB cable to stay under 1.0 Amps, or
 * 7 GB (or more) 2.0 (or later) USB flash drive. 

Follow the following instructions:

 1. To create the bootable USB device, follow the instructions in the CentOS wiki [Host to Set Up a USB to Install CentOS](https://wiki.centos.org/HowTos/InstallFromUSBkey).
 1. Insert your bootable USB device into the front USB port. CentOS AltArch installer will automatically appear as a boot option on the Petitboot main screen. If the USB device does not appear select *Rescan devices*. If your device is not detected, you might have to try a different type.
 1. Arrow up to select the CentOS boot option. Press *e* (Edit) to open the Petitboot Option Editor window
 1. Move the cursor to the Boot arguments section and to include the following information: `ro inst.stage2=hd:LABEL=CentOS_7_ppc64le:/ console=hvc0 ip=dhcp`

![Petitboot edited "Install CentOS AltArch 7 (64-bit kernel)](/images/centos7-minsky/petitboot-centos7-usb-option-editor-menu.png)

Notes about the boot arguments:   

 * `ip=dhcp` to ensure network is started for VNC installation.
 * `console hvc0` is needed as this is not the default.
 * `inst.stage2` is needed as the boot process won't automatically find the stage2 install on the install disk.
 * append `inst.proxy=URL` where URL is the proxy URL if installing in a network that requires a proxy to connect externally.

You can find additional options at [Anaconda Boot Options](https://rhinstaller.github.io/anaconda/boot-options.html).

 1. Select *OK* to save your options and return to the Main menu 
 1. On the Petitboot main screen, select the CentOS AltArch option and then press *Enter*. 

## Step 5: Complete your installation

After you select to boot the CentOS installer, the installer wizard walks you through the steps.  

 1. If the CentOS installer was able to obtain a network address via DHCP, it will present an option to enable the VNC. If no option is presented check your network cables. ![VNC option](/images/centos7-minsky/anaconda-centos7-text-start.png)
 1. Select the *Start VNC* option and it will provide an OS server IP adress. Note that this will be different to the BMC address previously optained. ![VNC option selected](/images/centos7-minsky/anaconda-centos7-vnc-selected.png)
 1. Run a VNC client program on your PC or notebook and connect to the OS server IP address.

![VNC of Installer](/images/centos7-minsky/anaconda-centos7-vnc-start.png)

During the install over VNC, there are a couple of consoles active. To switch between them in the ipmitool terminal, press *ctrl-b* and then between *1*-*4* as indicated.

Using the VNC client program:

 1. Select "Install Destination" - after selecting a device - select "Full disk summary and boot device" - select "Do not install boot loader" from device. ![Disabling install of boot loader](/images/centos7-minsky/anaconda-centos7-vnc-installation-destination-do-not-install-boot-loader.png) results in ![Result after disabling boot loader install](/images/centos7-minsky/anaconda-centos7-vnc-installation-destination-do-not-install-boot-loader-result.png).

Without disabling boot loader, the installer complains about `an invalid stage1 device`. I suspect it needs a manual Prep partition of 10M to make the installer happy.

If you have a local Centos repository  you can set this by selecting "Install Source" - the directories at this url should look like [CentOS's Install Source for ppc64le](http://mirror.centos.org/altarch/7/os/ppc64le/).

## Step 6: Before reboot and using the IPMI Serial-Over-LAN

Before reboot, generate the grub.cfg file as Petitboot uses this to generate its boot menu: 

 1. Using the ipmitool's shell (*ctrl-b 2*):
 1. Enter the following commands to generate a grub.cfg file
```
chroot /mnt/sysimage
rm /etc/grub.d/30_os-prober
grub2-mkconfig -o /boot/grub2/grub.cfg
exit
```

`/etc/grub.d/30_os-prober` is removed as Petitboot probes the other devices anyway so including it would create lots of duplicate menu items.

The last step is to restart your system.

Note: While your system is restarting, remove the USB device. 

After the system restarts, Petitboot displays the option to boot CentOS 7.2. Select this option and press Enter. 

## Conclusion 

After you have booted CentOS, your server is ready to go!
For more information, see the following resources:

 * [IBM Knowledge Center](https://www.ibm.com/support/knowledgecenter/)
 * [The Linux on Power Community](https://www.ibm.com/developerworks/community/groups/service/html/communityview?communityUuid=fe313521-2e95-46f2-817d-44a4f27eba32)
 * [The Linux on Power Developer Center](https://developer.ibm.com/linuxonpower/category/announcements/)
 * [Follow us @ibmpowerlinux](https://twitter.com/ibmpowerlinux)
