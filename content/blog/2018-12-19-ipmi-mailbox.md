Title: IPMI: Initiating Better Overrides
Date: 2018-12-19 10:08:00
Authors: Samuel Mendoza-Jonas
Category: Petitboot
Tags: linux, firmware, goodposts, realcontent, sparseposting, openpower, openbmc, ipmi, petitboot

On platforms that support it Petitboot can interact with the inband IPMI interface to pull information from the BMC. One particularly useful example of this is the "Get System Boot Options" command which we use to implement boot "overrides". By setting parameter 5 of the command a user can remotely force Petitboot to boot from only one class of device or disable autoboot completely. This is great for automation or debug purposes, but since it can only specify device types like "disk" or "network" it can't be used to boot from specific devices.

Introducing..

**The Boot Initiator Mailbox**

Alexander Amelkin [pointed out](https://github.com/open-power/petitboot/issues/45) that the "Get System Boot Options" command also specifies parameter 7, "Boot Initiator Mailbox". This parameter just defines a region of vendor-defined data that can be used to influence the booting behaviour of the system. The parameter description specifies that a BMC must support at least 80 bytes of data in that mailbox so as Alex pointed out we could easily use it to set a partition UUID. But why stop there? Let's go further and use the mailbox to provide an alterate "petitboot,bootdevs=.." parameter and let a user set a full substitute boot order!

**The Mailbox Format**

Parameter 7 has two fields, 1 byte for the "set selector", and up to 16 bytes of "block data". The spec sets the minimum amount of data to support at 80 bytes, which means a BMC must support at least 5 of these 16-byte "blocks" which can be individually accessed via the set selector. Aside from the first 3 bytes which must be an IANA ID number, the rest of the data is defined by us.

So if we want to set an alternate Petitboot boot order such as "network, usb, disk", the format of the mailbox would be:

```
Block # |		Block Data				|
-----------------------------------------
0		|2|0|0|p|e|t|i|t|b|o|o|t|,|b|o|o|
1		|t|d|e|v|s|=|n|e|t|w|o|r|k| |u|s|
2		|b| |d|i|s|k| | | | | | | | | | |
3		| | | | | | | | | | | | | | | | |
4		| | | | | | | | | | | | | | | | |
```

Where the string is null-terminated, `2,0,0` is the IBM IANA ID, and the contents of any remaining data is not important. The [ipmi-mailbox-config.py](https://github.com/open-power/petitboot/blob/master/utils/ipmi-mailbox-config.py) script constructs and sends the required IPMI commands from a given parameter string to make this easier, eg:
```
./utils/ipmi-mailbox-config.py -b bmc-ip -u user -p pass -m 5 \
		-c "petitboot,bootdevs=uuid:c6e4c4f9-a9a2-4c30-b0db-6fa00f433b3b"
```
![Active Mailbox Override][00]

----

That is basically all there is to it. Setting a boot order this way overrides the existing order from NVRAM if there is one. Parameter 7 doesn't have a 'persistent' flag so the contents need to either be manually cleared from the BMC or cleared via the "Clear" button in the System Configuration screen.

From the machines I've been able to test on at least AMI BMCs support the mailbox, and hopefully [OpenBMC](https://lists.ozlabs.org/pipermail/openbmc/2018-December/014224.html) will be able to add it to their IPMI implementation. This is supported in Petitboot as of v1.10.0 so go ahead and try it out!

[00]: /images/sammj/ipmi-mailbox.png
