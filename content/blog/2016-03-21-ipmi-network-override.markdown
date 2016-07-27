Title: No Network For You
Date: 2016-03-21 15:23
Authors: Samuel Mendoza-Jonas
Category: Petitboot
Tags: petitboot, goodposts, realcontent, ipmi, bmc, based16

In POWER land [IPMI](https://en.wikipedia.org/wiki/Intelligent_Platform_Management_Interface) is mostly known as the method to access the machine's console and start interacting with Petitboot. However it also has a plethora of other features, handily described in the 600ish page [IPMI specification](http://www.intel.com/content/www/us/en/servers/ipmi/ipmi-second-gen-interface-spec-v2-rev1-1.html) (which you can go read yourself).

One especially relevant feature to Petitboot however is the 'chassis bootdev' command, which you can use to tell Petitboot to ignore any existing boot order, and only consider boot options of the type you specify (eg. 'network', 'disk', or 'setup' to not boot at all). Support for this has been in Petitboot for a while and should work on just about any machine you can get your hands on.

Network Overrides
-----------------

Over in OpenPOWER<sup>1</sup> land however, someone took this idea and pushed it further - why not allow the network configuration to be overwritten too? This isn't in the IPMI spec, but if you cast your gaze down to page 398 where the spec lays out the entire format of the IPMI request, there is a certain field named "OEM Parameters". This is an optional amount of space set aside for whatever you like, which in this case is going to be data describing an override of the network config.

This allows a user to tell Petitboot over IPMI to either;

- Disable the network completely,
- Set a particular interface to use DHCP, or
- Set a particular interface to use a specific static configuration.

Any of these options will cause any existing network configurations to be ignored.

Building the Request
--------------------
Since this is an OEM-specific command, your average ipmitool package isn't going to have a nice way of making this request, such as 'chassis bootdev network'. Rather you need to do something like this:

```
ipmitool -I lanplus -H $yourbmc -U $user -P $pass raw 0x00 0x08 0x61 0x80 0x21 0x70 0x62 0x21 0x00 0x01 0x06 0x04 0xf4 0x52 0x14 0xf3 0x01 0xdf 0x00 0x01 0x0a 0x3d 0xa1 0x42 0x10 0x0a 0x3d 0x2 0x1
```

Horrific right? In the near future the Petitboot tree will include a helper program to format this request for you, but in the meantime (and for future reference), lets lay out how to put this together:

```
Specify the "chassis bootdev" command, field 96, data field 1:
	0x00 0x08 0x61 0x80

Unique value that Petitboot recognises:
	0x21 0x70 0x62 0x21

Version field (1)
	0x00 0x01 ..   ..

Size of the hardware address (6):
	..   ..	  0x06 ..

Size of the IP address (IPv4/IPv6):
	..   ..	  ..   0x04

Hardware (MAC) address:
	0xf4 0x52 0x14 0xf3
	0x01 0xdf ..   ..

'Ignore flag' and DHCP/Static flag (DHCP is 0)
	..   ..	  0x00 0x01

(Below fields only required if setting a static IP)

IP Address:
	0x0a 0x3d 0xa1 0x42

Subnet Mask (eg, /16):
	0x10 ..   ..   ..
Gateway IP Address:
	..   0x0a 0x3d 0x02
	0x01
```

Clearing a network override is as simple as making a request empty aside from the header:
```
0x00 0x08 0x61 0x80 0x21 0x70 0x62 0x21 0x00 0x01 0x00 0x00
```

You can also read back the request over IPMI with this request:
```
0x00 0x09 0x61 0x00 0x00
```


That's it! Ideally this is something you would be scripting rather than bashing out on the keyboard - the main use case at the moment is as a way to force a machine to netboot against a known good source, rather than whatever may be available on its other interfaces.


[1] The reason this is only available on OpenPOWER machines at the moment is that support for the IPMI command itself depends on the BMC firmware, and non-OpenPOWER machines use an FSP which is a different platform.
