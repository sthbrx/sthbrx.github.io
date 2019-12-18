Title: rfid and hrfid
Date: 2019-12-18 17:30:00
Authors: Andrew Donnellan
Category: OpenPOWER
Tags: Instruction Set Architecture, openpower

I was staring at some assembly recently, and for not the first time encountered _rfid_ and _hrfid_, two instructions that we use when doing things like returning to userspace, returning from OPAL to the kernel, or from a host kernel into a guest.

_rfid_ copies various bits from the register SRR1 (Machine Status Save/Restore Register 1) into the MSR (Machine State Register), and then jumps to an address given in SRR0 (Machine Status Save/Restore Register 0). _hrfid_ does something similar, using HSRR0 and HSRR1 (Hypervisor Machine Status Save/Restore Registers 0/1), and slightly different handling of MSR bits.

The various Save/Restore Registers are used to preserve the state of the CPU before jumping to an interrupt handler, entering the kernel, etc, and are set up as part of instructions like _sc_ (System Call), by the interrupt mechanism, or manually (using instructions like _mtsrr1_).

Anyway, the way in which _rfid_ and _hrfid_ restores MSR bits is documented somewhat obtusely in the ISA (if you don't believe me, look it up), and I was annoyed by this, so here, have a more useful definition. Leave a comment if I got something wrong.

rfid - Return From Interrupt Doubleword
=======================================

Machine State Register
----------------------

Copy all bits (except some reserved bits) from SRR1 into the MSR, with the following exceptions:

* MSR_3 (HV, Hypervisor State) = MSR_3 & SRR1_3  
[We won't put the thread into hypervisor state if we're not already in hypervisor state]

* If MSR_29:31 != 0b010 [Transaction State Suspended, TM not available], or SRR1_29:31 != 0b000 [Transaction State Non-transactional, TM not available] then:
    * MSR_29:30 (TS, Transaction State) = SRR1_29:30
    * MSR_31 (TM, Transactional Memory Available) = SRR1_31
    
    [See the ISA description for explanation on how rfid interacts with TM and resulting interrupts]

* MSR_48 (EE, External Interrupt Enable) = SRR1_48 | SRR1_49 (PR, Problem State)  
[If going into problem state, external interrupts will be enabled]

* MSR_51 (ME, Machine Check Interrupt Enable) = (MSR_3 (HV, Hypervisor State) & SRR1_51) | ((! MSR_3) & MSR_51)  
[If we're not already in hypervisor state, we won't alter ME]

* MSR_58 (IR, Instruction Relocate) = SRR1_58 | SRR1_49 (PR, Problem State)  
[If going into problem state, relocation will be enabled]

* MSR_59 (DR, Data Relocate) = SRR1_59 | SRR1_49 (PR, Problem State)  
[If going into problem state, relocation will be enabled]

Next Instruction Address
------------------------

* NIA = SRR0_0:61 || 0b00  
[Jump to SRR0, set last 2 bits to zero to ensure address is aligned to 4 bytes]

hrfid - Hypervisor Return From Interrupt Doubleword
===================================================

Machine State Register
----------------------

Copy all bits (except some reserved bits) from HSRR1 into the MSR, with the following exceptions:

* If MSR_29:31 != 0b010 [Transaction State Suspended, TM not available], or HSRR1_29:31 != 0b000 [Transaction State Non-transactional, TM not available] then:
    * MSR_29:30 (TS, Transaction State) = HSRR1_29:30
    * MSR_31 (TM, Transactional Memory Available) = HSRR1_31
    
    [See the ISA description for explanation on how rfid interacts with TM and resulting interrupts]

* MSR_48 (EE, External Interrupt Enable) = HSRR1_48 | HSRR1_49 (PR, Problem State)  
[If going into problem state, external interrupts will be enabled]

* MSR_58 (IR, Instruction Relocate) = HSRR1_58 | HSRR1_49 (PR, Problem State)  
[If going into problem state, relocation will be enabled]

* MSR_59 (DR, Data Relocate) = HSRR1_59 | HSRR1_49 (PR, Problem State)  
[If going into problem state, relocation will be enabled]

Next Instruction Address
------------------------

* NIA = HSRR0_0:61 || 0b00  
[Jump to HSRR0, set last 2 bits to zero to ensure address is aligned to 4 bytes]
