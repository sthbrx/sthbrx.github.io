Title: Erasure Coding for Programmers, Part 1
Date: 2017-03-20 10:43:00
Authors: Daniel Axtens
Category: Development
Tags: erasure, raid, storage

Erasure coding is an increasingly popular storage technology - allowing the same level of fault tolerance as replication with a significantly reduced storage footprint.

Increasingly, erasure coding is available 'out of the box' on storage solutions such as Ceph and OpenStack Swift. Normally, you'd just pull in a library like [ISA-L](https://github.com/01org/isa-l) or [jerasure](http://jerasure.org), and set some config options, and you'd be done.

This post is not about that. This post is about how I went from knowing nothing about erasure coding to writing POWER optimised routines to make it go fast. (These are in the process of being polished for upstream at the moment.) If you want to understand how erasure coding works under the hood - and in particular if you're interested in writing optimised routines to make it run quickly in your platform - this is for you.

## What are erasure codes anyway?

I think the easiest way to begin thinking about erasure codes is "RAID 6 on steroids". RAID 6 allows you to have up to 255 data disks and 2 parity disks (called P and Q), thus allowing you to tolerate the failure of up to 2 arbitrary disks without data loss.

Erasure codes allow you to have k data disks and m 'parity' or coding disks. You then have a total of m + k disks, and you can tolerate the failure of up to m without losing data.

The downside of erasure coding is that computing what to put on those parity disks is CPU intensive. Lets look at what we put on them.

## RAID 6

RAID 6 is the easiest way to get started on understanding erasure codes for a number of reasons. H Peter Anvin's paper on RAID 6 in the Linux kernel is an excellent start, but does dive in a bit quickly to the underlying mathematics. So before reading that, read on!

## Rings and Fields

As programmers we're pretty comfortable with modular arithmetic - the idea that if you have:

    unsigned char a = 255;
    a++;

the new value of `a` will be 0, not 256.

This is an example of an algebraic structure called a *ring*.

Rings obey certain laws. For our purposes, we'll consider the following incomplete and somewhat simplified list:

 * There is an addition operation.
 * There is an additive identity (normally called 0), such that 'a + 0 = a'.
 * Every element has an additive inverse, that is, for every element 'a', there is an element -a such that 'a + (-a) = 0'
 * There is a multiplication operation.
 * There is a multiplicative identity (normally called 1), such that 'a * 1 = a'.

These operations aren't necessarily addition or multiplication as we might expect from the integers or real numbers. For example, in our modular arithmetic example, we have 'wrap around'. (There are also certain rules the addition and multiplication rules must satisfy - we are glossing over them here.)

One thing a ring doesn't have a 'multiplicative inverse'. The multiplicative inverse of some non-zero element of the ring (call it a), is the value b such that a * b = 1. (Often instead of b we write 'a^-1', but that looks bad in plain text, so we shall stick to b for now.)

We do have some inverses in 'mod 256': the inverse of 3 is 171 as 3 * 171 = 513, and 513 = 1 mod 256, but there is no b such that 2 * b = 1 mod 256.

If every non-zero element of our ring had a multiplicative inverse, we would have what is called a *field*.

Now, let's look at a the integers modulo 2, that is, 0 and 1.

We have this for addition:

| + | 0 | 1 |
|---|---|---|
| **0** | 0 | 1 |
| **1** | 1 | 0 |

Eagle-eyed readers will notice that this is the same as XOR.

For multiplication: 
 
| * | 0 | 1 |
|---|---|---|
| **0** | 0 | 0 |
| **1** | 0 | 1 |


As we said, a field is a ring where every non-zero element has a multiplicative inverse. As we can see, the integers modulo 2 shown above is a field: it's a ring, and 1 is its own multiplicative inverse.

So this is all well and good, but you can't really do very much in a field with 2 elements. This is sad, so we make bigger fields. For this application, we consider the Galois Field with 256 elements - GF(2^8). This field has some surprising and useful properties.

Remember how we said that integers modulo 256 weren't a field because they didn't have multiplicative inverses? I also just said that GF(2^8) also has 256 elements, but is a field - i.e., it does have inverses! How does that work?

Consider an element in GF(2^8). There are 2 ways to look at an element in GF(2^8). The first is to consider it as an 8-bit number. So, for example, let's take 100. We can express that as as an 8 bit binary number: 0b01100100.

We can write that more explicitly as a sum of powers of 2:

    0 * 2^7 + 1 * 2^6 + 1 * 2^5 + 0 * 2^4 + 0 * 2^3 + 1 * 2^2 + 0 * 2 + 0 * 1
    = 2^6 + 2^5 + 2^2

Now the other way we can look at elements in GF(2^8) is to replace the '2's with 'x's, and consider them as polynomials. Each of our bits then represents the coefficient of a term of a polynomial, that is:

    0 x^7 + 1 x^6 + 1 x^5 + 0 x^4 + 0 x^3 + 1 x^2 + 0 x + 0 * 1

or more simply

    x^6 + x^5 + x^2

Now, and this is **important**: each of the coefficients are elements of the integers modulo 2: x + x = 2x = 0 as 2 mod 2 = 0. There is no concept of 'carrying' in this addition.

Let's try: what's 100 + 79 in GF(2^8)?

    100 = 0b01100100 => x^6 + x^5 +       x^2
     79 = 0b01001111 => x^6 +       x^3 + x^2 + x + 1

    100 + 79         =>   0 + x^5 + x^3 +   0 + x + 1
                     =    0b00101011 = 43


So, 100 + 79 = 43 in GF(2^8)

You may notice we could have done that much more efficiently: we can add numbers in GF(2^8) by just XORing their binary representations together. Subtraction, amusingly, is the same as addition: 0 + x = x =  0 - x, as -1 is congruent to 1 modulo 2.

So at this point you might be wanting to explore a few additions yourself. Fortuantely there's a lovely tool that will allow you to do that:

    sudo apt install gf-complete-tools
    gf_add $A $B 8

This will give you A + B in GF(2^8).

    > gf_add 100 79 8
    43

Excellent!

So, hold on to your hats, as this is where things get really weird. In modular arithmetic example, we considered the elements of our ring to be numbers, and we performed our addition and multiplication modulo 256. In GF(2^8), we consider our elements as polynomials and we perform our addition and multiplication modulo a polynomial. There is one conventional polynomial used in applications:

    0x11d => 0b1 0001 1101 => x^8 + x^4 + x^3 + x^2 + 1

It is possible to use other polynomials if they satisfy particular requirements, but for our applications we don't need to worry as we will always use 0x11d. I am not going to attempt to explain anything about this polynomial - take it as an article of faith.

So when we multiply two numbers, we multiply their polynomial representations. Then, to find out what that is modulo 0x11d, we do polynomial long division by 0x11d, and take the remainder.

Some examples will help.

Let's multiply 100 by 3.

    100 = 0b01100100 => x^6 + x^5 + x^2
      3 = 0b00000011 => x + 1

    (x^6 + x^5 + x^2)(x + 1) = x^7 + x^6 + x^3 + x^6 + x^5 + x^2
                             = x^7 + x^5 + x^3 + x^2

Notice that some of the terms have disappeared: x^6 + x^6 = 0.

The degree (the largest power of a term) is 7. 7 is less than the degree of 0x11d, which is 8, so we don't need to do anything: the remainder modulo 0x11d is simply x^7 + x^5 + x^3 + x^2.

In binary form, that is 0b10101100 = 172, so 100 * 3 = 172 in GF(2^8).

Fortunately `gf-complete-tools` also allows us to check multiplications:

    > gf_mult 100 3 8
    172

Excellent!

Now let's see what happens if we multiply by a larger number. Let's multiply 100 by 5.

    100 = 0b01100100 => x^6 + x^5 + x^2
      5 = 0b00000101 => x^2 + 1

    (x^6 + x^5 + x^2)(x^2 + 1) = x^8 + x^7 + x^4 + x^6 + x^5 + x^2
                               = x^8 + x^7 + x^6 + x^5 + x^4 + x^2


Here we have an x^8 term, so we have a degree of 8. This means will get a different remainder when we divide by our polynomial. We do this with polynomial long division, which you will hopefully remember if you did some solid algebra in high school.

                                  1
                               ---------------------------------------------
    x^8 + x^4 + x^3 + x^2 + 1 | x^8 + x^7 + x^6 + x^5 + x^4       + x^2
                              - x^8                   + x^4 + x^3 + x^2 + 1
                                -------------------------------------------
                              =       x^7 + x^6 + x^5       + x^3       + 1

So we have that our original polynomial (x^8 + x^4 + x^3 + x^2 + 1) is congruent to (x^7 + x^6 + x^5 + x^3 + 1) modulo the polynomial 0x11d.
Looking at the binary representation of that new polynomial, we have 0b11101001 = 233.

Sure enough:

    > gf_mult 100 5 8
    233

Just to solidify the polynomial long division a bit, let's try a slightly larger example, 100 * 9:

    100 = 0b01100100 => x^6 + x^5 + x^2
      9 = 0b00001001 => x^3 + 1

    (x^6 + x^5 + x^2)(x^3 + 1) = x^9 + x^8 + x^5 + x^6 + x^5 + x^2
                               = x^9 + x^8 + x^6 + x^2


Doing long division to reduce our result:

                                  x
                               -----------------------------------
    x^8 + x^4 + x^3 + x^2 + 1 | x^9 + x^8       + x^6                   + x^2
                              - x^9                   + x^5 + x^4 + x^3       + x
                                -------------------------------------------------
                              =       x^8       + x^6 + x^5 + x^4 + x^3 + x^2 + x

We still have a polynomial of degree 8, so we can do another step:

                                  x +   1
                               -----------------------------------
    x^8 + x^4 + x^3 + x^2 + 1 | x^9 + x^8       + x^6                   + x^2
                              - x^9                   + x^5 + x^4 + x^3       + x
                                -------------------------------------------------
                              =       x^8       + x^6 + x^5 + x^4 + x^3 + x^2 + x
                              -       x^8                   + x^4 + x^3 + x^2     + 1
                                      -----------------------------------------------
                              =                   x^6 + x^5                   + x + 1

We now have a polynomial of degree less than 8 that is congruent to our original polynomial modulo 0x11d, and the binary form is 0x01100011 = 99.

    > gf_mult 100 9 8
    99


This process can be done more efficiently, of course - but understanding what is going on will make you *much* more comfortable with what is going on!

I will not try to convince you that all multiplicative inverses exist in this magic shadow land of GF(2^8), but it's important for the rest of the algorithms to work that they do exist. Trust me on this.

## Back to RAID 6

Equipped with this knowledge, you are ready to take on [RAID6 in the kernel](https://www.kernel.org/pub/linux/kernel/people/hpa/raid6.pdf) (PDF) sections 1 - 2.

Pause when you get to section 3 - this snippet is a bit magic and benefits from some explanation:

> Multiplication by {02} for a single byte can be implemeted using the C code:

    uint8_t c, cc;
    cc = (c << 1) ^ ((c & 0x80) ? 0x1d : 0);

How does this work? Well:

Say you have a binary number 0bNMMM MMMM. Mutiplication by 2 gives you 0bNMMMMMMM0, which is 9 bits. Now, there are two cases to consider.

If your leading bit (N) is 0, your product doesn't have an x^8 term, so we don't need to reduce it modulo the irreducible polynomial.

If your leading bit is 1 however, your product is x^8 + something, which does need to be reduced. Fortunately, because we took an 8 bit number and multiplied it by 2, the largest term is x^8, so we only need to reduce it once. So we xor our number with our polynomial to subtract it.

We implement this by letting the top bit overflow out and then xoring the lower 8 bits with the low 8 bits of the polynomial (0x1d)

So, back to the original statement:

    (c << 1) ^ ((c & 0x80) ? 0x1d : 0)
        |          |          |     |
        > multiply by 2       |     |
                   |          |     |
                   > is the high bit set - will the product have an x^8 term?
                              |     |
                              > if so, reduce by the polynomial
                                    |
                                    > otherwise, leave alone

Hopefully that makes sense.

### Key points

It's critical you understand the section on Altivec (the vperm stuff), so let's cover it in a bit more detail.

Say you want to do A * V, where A is a constant and V is an 8-bit variable. We can express V as V_a + V_b, where V_a is the top 4 bits of V, and V_b is the bottom 4 bits. A * V = A * V_a + A * V_b

We can then make lookup tables for multiplication by A.

If we did this in the most obvious way, we would need a 256 entry lookup table. But by splitting things into the top and bottom halves, we can reduce that to two 16 entry tables. For example, say A = 02.

| V_a | A * V_a |
|-----|---------|
| 00  | 00      |
| 01  | 02      |
| 02  | 04      |
| ... | ...     |
| 0f  | 1e      |

| V_b | A * V_b |
|-----|---------|
| 00  | 00      |
| 10  | 20      |
| 20  | 40      |
| ... | ...     |
| f0  | fd      |

We then use vperm to look up entries in these tables and vxor to combine our results.

So - and this is a key point - for each A value we wish to multiply by, we need to generate a new lookup table.

So if we wanted A = 03:

| V_a | A * V_a |
|-----|---------|
| 00  | 00      |
| 01  | 03      |
| 02  | 06      |
| ... | ...     |
| 0f  | 11      |

| V_b | A * V_b |
|-----|---------|
| 00  | 00      |
| 10  | 30      |
| 20  | 60      |
| ... | ...     |
| f0  | 0d      |


One final thing is that Power8 adds a vpermxor instruction, so we can reduce the entire 4 instruction sequence in the paper:

    vsrb v1, v0, v14
    vperm v2, v12, v12, v0
    vperm v1, v13, v13, v1
    vxor v1, v2, v1

to 1 vpermxor:

    vpermxor v1, v12, v13, v0

Isn't POWER grand?

## OK, but how does this relate to erasure codes?

I'm glad you asked.

Galois Field arithmetic, and its application in RAID 6 is the basis for erasure coding. (It's also the basis for CRCs - two for the price of one!)

But, that's all to come in part 2, which will definitely be published before 7 April!

Many thanks to Sarah Axtens who reviewed the mathematical content of this post and suggested significant improvements. All errors and gross oversimplifications remain my own. Thanks also to the OzLabs crew for their feedback and comments.