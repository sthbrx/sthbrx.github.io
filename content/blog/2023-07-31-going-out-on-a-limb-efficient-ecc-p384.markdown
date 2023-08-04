Title: Going out on a Limb: Efficient Elliptic Curve Arithmetic in OpenSSL
Authors: Rohan McLure
Date: 2023-08-04 13:15
Category: Cryptography

So I've just submitted a [pull request](https://github.com/openssl/openssl/pull/21471) to OpenSSL for a new strategy I've been developing for efficient arithmetic used in secp384r1, a curve prescribed by NIST for digital signatures and key exchange. In spite of its prevalence, its implementation in OpenSSL has remained somewhat unoptimised, even as less frequently used curves (P224, P256, P521) each have their own optimisations.

The strategy I have used could be called a 56-bit redundant limb implementation with _Solinas reduction_. Without too much micro-optimisation, we get ~5.5x speedup over the default (Montgomery Multiplication) implementation for creation of digital signatures.

How is this possible? Well first let's quickly explain some language:

## Elliptic Curves

When it comes to cryptography, it's highly likely that those with a computer science background will be familiar with ideas such as key-exchange and private-key signing. The stand-in asymmetric cipher in a typical computer science curriculum is typically RSA. However, the heyday of Elliptic Curve ciphers has well and truly arrived, and their operation seems no less mystical than when they were just a toy for academia.

The word 'Elliptic' may seem to imply continuous mathematics. As a useful cryptographic problem, we fundamentally are just interested with the algebraic properties of these curves, whose points are elements of a [finite field](https://en.wikipedia.org/wiki/Finite_field). Irrespective of the underlying finite field, the algebraic properties of the elliptic curve group can be shown to exist by an application of [Bézout's Theorem](https://en.wikipedia.org/wiki/Bézout%27s_theorem#:~:text=Bézout%27s%20theorem%20is%20a%20statement,the%20degrees%20of%20the%20polynomials.). The [group operator](https://en.wikipedia.org/wiki/Algebraic_group) on points on an elliptic curve for a particular choice of field involves the intersection of lines intersecting either once, twice or thrice with the curve, granting notions of addition and doubling for the points of intersection, and giving the 'point at infinity' as the group identity. A closed form exists for computing a point double/addition in arbitrary fields (different closed forms can apply, but determined by the field's [characteristic](https://en.wikipedia.org/wiki/Characteristic_(algebra)), and the same closed form applies for all large prime fields).

Our algorithm uses a field of the form $\mathbb{F}_p$, that is the [unique](https://en.wikipedia.org/wiki/Finite_field#Existence_and_uniqueness) field with $p$ (a prime) elements. The most straightforward construction of this field is arithmetic modulo $p$. The other finite fields used in practise in ECC are of the form $\mathbb{F}_{2^m}$ and are sometimes called 'binary fields' (representible as polynomials with binary coefficients). Their field structure is also used in AES through byte substitution, implemented by inversion modulo $\mathbb{F}_{2^8}$.

From a performance perspective, great optimisations can be made by implementing efficient fixed-point arithmetic specialised to modulo by single prime constant, $p$. From here on out, I'll be speaking from this abstraction layer alone.

## Limbs

We wish to multiply two $m$-bit numbers, each of which represented with $n$ 64-bit machine words in some way. Let's suppose just for now that $n$ divides $m$ neatly, then the quotient $d$ is the minimum number of bits in each machine word that will be required for representing our number. Suppose we use the straightforward representation whereby the least significant $d$ bits are used for storing parts of our number, which we better call $x$ because this is crypto and descriptive variable names are considered harmful (apparently).

$$x = \sum_{k = 0}^{n-1} 2^{dk} l_k$$

If we then drop the requirement for each of our $n$ machine words (also referred to as a 'limb' from hereon out) to have no more than the least significant $d$ bits populated, we say that such an implementation uses 'redundant limbs', meaning that the $k$-th limb has high bits which overlap with the place values represented in the $(k+1)$-th limb.

## Multiplication (mod p)

The fundamental difficulty with making modulo arithmetic fast is to do with the following property of multiplication.

Let $a$ and $b$ be $m$-bit numbers, then $0 \leq a < 2^m$ and $0 \leq b < 2^m$, but critically we cannot say the same about $ab$. Instead, the best we can say is that $0 \leq ab < 2^{2m}$. Multiplication can in the worst case double the number of bits that must be stored, unless we can reduce modulo our prime.

If we begin with non-redundant, 56-bit limbs, then for $a$ and $b$ not too much larger than $2^{384} > p_{384}$ that are 'reduced sufficiently' then we can multiply our limbs in the following ladder, so long as we are capable of storing the following sums without overflow.

```c
    /* and so on ... */

    out[5] = ((uint128_t) in1[0]) * in2[5]
           + ((uint128_t) in1[1]) * in2[4]
           + ((uint128_t) in1[2]) * in2[3]
           + ((uint128_t) in1[3]) * in2[2]
           + ((uint128_t) in1[4]) * in2[1]
           + ((uint128_t) in1[5]) * in2[0];

    out[6] = ((uint128_t) in1[0]) * in2[6]
           + ((uint128_t) in1[1]) * in2[5]
           + ((uint128_t) in1[2]) * in2[4]
           + ((uint128_t) in1[3]) * in2[3]
           + ((uint128_t) in1[4]) * in2[2]
           + ((uint128_t) in1[5]) * in2[1]
           + ((uint128_t) in1[6]) * in2[0];

    out[7] = ((uint128_t) in1[1]) * in2[6]
           + ((uint128_t) in1[2]) * in2[5]
           + ((uint128_t) in1[3]) * in2[4]
           + ((uint128_t) in1[4]) * in2[3]
           + ((uint128_t) in1[5]) * in2[2]
           + ((uint128_t) in1[6]) * in2[1];

    out[8] = ((uint128_t) in1[2]) * in2[6]
           + ((uint128_t) in1[3]) * in2[5]
           + ((uint128_t) in1[4]) * in2[4]
           + ((uint128_t) in1[5]) * in2[3]
           + ((uint128_t) in1[6]) * in2[2];

    /* ... and so forth */
```

This is possible, if we back each of the 56-bit limbs with a 64-bit machine word, with products being stored in 128-bit machine words. The numbers $a$ and $b$ were able to be stored with 7 limbs, whereas we use 13 limbs for storing the product. If $a$ and $b$ were stored non-redundantly, than each of the output (redundant) limbs must contain values less than $6 \cdot 2^{56} \cdot 2^{56} < 2^{115}$, so there is no possibility of overflow in 128 bits. We even have room spare to do some additions/subtractions in cheap, redundant limb arithmetic.

But we can't keep doing our sums in redundant limb arithmetic forever, we must eventually reduce. Doing so may be expensive, and so we would rather reduce only when strictly necessary!

## Solinas-ish Reduction

Our prime is a _Solinas_ (_Pseudo/Generalised-Mersenne_) _Prime_. Mersenne Primes are primes expressible as $2^m - 1$. This can be generalised to low-degree polynomials in $2^m$. For example, another NIST curve uses $p_{224} = 2^{224} - 2^{96} + 1$ (a 224-bit number) where $p_{224} = f(2^{32})$ for $f(t) = t^7 - t^3 + 1$. The simpler the choice of polynomial, the simpler the modular reduction logic.

Our choice of $t$ is $2^{56}$. Wikipedia provides a ideal example of the Solinas reduction algorithm for when the bitwidth of the prime is divisible by $\log_2{t}$, but that is not our scenario. We choose 56-bits for some pretty simple realities of hardware. 56 is less than 64 (standard machine word size) but not by too much, and the difference is byte-addressible ($64-56=8$). Let me explain:

## Just the Right Amount of Reduction (mod p)

Let's first describe the actual prime that is our modulus.

$$p_{384} = 2^{384} - 2^{128} - 2^{96} + 2^{32} - 1$$

Yuck. This number is so yuck in fact, that noone has so far managed to upstream a Solinas' reduction method for it in OpenSSL, in spite of `secp384r1` being the preferred curve for ECDH (Elliptic Curve Diffie-Hellman key exchange) and ECDSA (Elliptic Curve Digital Signature Algorithm) by NIST.

In 56-bit limbs, we would express this number so:

Let $f(t) = 2^{48} t^6 - 2^{16} t^2 - 2^{40} t + (2^{32} - 1)$, then observe that all coefficients are smaller than $2^{56}$, and that $p_{384} = f(2^{56})$.

Now let $\delta(t) = 2^{16} t^2 + 2^{40} t - 2^{32} + 1$, consider that $p_{384} = 2^{384} - \delta(2^{56})$, and thus $2^{384} \equiv \delta(2^{56}) \mod{p_{384}}$. From now on let's call $\delta(2^{56})$ just $\delta$. Thus, 'reduction' can be achieved as follows for suitable $X$ and $Y$:

$$ab = X + 2^{384} Y \equiv X + \delta Y \mod{p_{384}}$$

### Calculating $\delta Y$

#### First Substitution

First make a choice of $X$ and $Y$. The first thing to observe here is that this can actually be made a large number of ways! We choose:

$$X_1 = \sum_{k=0}^8\texttt{in[k]} t^k$$
$$Y_1 = 2^8 t^2 \sum_{k=9}^{12}\texttt{in[k]} t^{k-9} = 2^8 \sum_{k=9}^{12}\texttt{in[k]} t^{k-7}$$

'Where does the $2^8 t^{2}$ come from?' I hear you ask. See $t^9 = t^2 \cdot t^7 = t^2 (2^8 \cdot 2^{384}) \equiv (2^8 t^2) \delta \mod{f(t)}$. It's clear to see that the place value of `in[9] ... in[12]` is greater than $2^{384}$.

I'm using the subscripts here because we're in fact going to do a series of these reductions to reach a suitably small answer. That's because our equation for reducing $t^7$ terms is as follows:

$$t^7 \equiv 2^8\delta \equiv 2^{24} t^2 + 2^{48} t + (-2^{40} + 2^8) \mod{f(t)}$$

Thus reducing `in[12]` involves computing:

$$\texttt{in[12]} t^{12} = \texttt{in[12]} (t^5)(t^7) \equiv 2^8\delta \cdot \texttt{in[12]} t^5 \mod{f(t)}$$

But $\delta$ is a degree two polynomial, and so our numbers can still have two more limbs than we would want them to have. To be safe, let's store $X_1 + \delta Y_1$ in accumulator limbs `acc[0] ... acc[8]` (this will at first appear to be one more limb than necessary), then we can eliminate `in[12]` with the following logic.

```c
    /* assign accumulators to begin */
    for (int i = 0; i < 9; i++)
        acc[i] = in[i];

    /* X += 2^128 Y */
    acc[8] += in[12] >> 32;
    acc[7] += (in[12] & 0xffffffff) << 24;

    /* X += 2^96 Y */
    acc[7] += in[12] >> 8;
    acc[6] += (in[12] & 0xff) << 48;

    /* X += (-2^32 + 1) Y */
    acc[6] -= in[12] >> 16;
    acc[5] -= ((in[12] & 0xffff) << 40);
    acc[6] += in[12] >> 48;
    acc[5] += (in[12] & 0xffffffffffff) << 8;
```

Notice that for each term in $\delta = 2^{128} + 2^{96} + (2^{32} - 1)$ we do two additions/subtractions. This is in order to split up operands in order to minimise the final size of numbers and prevent over/underflows. Consequently, we need an `acc[8]` to receive the high bits of our `in[12]` substitution given above.

#### Second Substitution

Let's try and now eliminate through substitution `acc[7]` and `acc[8]`. Let

$$X_2 = \sum^{6}_{k=0}\texttt{acc[k]}t^k $$
$$Y_2 = 2^8(\texttt{acc[7]} t^7 + \texttt{acc[8]} t^8)$$

But this time, $\delta Y_2$ is a number that comfortably can take up just five limbs, so we can update `acc[0], ..., acc[5]` comfortably in-place.

#### Third Substitution

Finally, let's reduce all the high bits of `in[6]`. Since `in[6]` has place value `t^6 = 2^{336}`, thus we wish to reduce all but the least significant $384 - 336 = 48$ bits.

A goal in designing this algorithm is to ensure that `acc[6]` has as tight a bound as reasonably possible. Intuitively, if we can cause `acc[6]` to be as large as possible by absorbing the high bits of lower limbs, we reduce the number of bits that must be carried forward later on. As such, we perform a carry of the high-bits of `acc[4]`, `acc[5]` into `acc[6]` before we begin our substitution.

Again, let

$$X_3 = \sum^{5}_{k=0}\texttt{acc[k]}t^k + (\texttt{acc[6]} \text{(low bits)})t^6$$
$$Y_3 = 2^{48}(\texttt{acc[6]} \text{(high bits, right shifted)}) t^6$$

The equation for eliminating $2^{48}t^6$ is pretty straightforward:

$$2^{384} = 2^{48}t^6 \equiv 2^{16}t^2 + 2^{40}t + (-2^{32} + 1) \mod{f(t)}$$

#### Carries

Finally, as each of `acc[0], ..., acc[6]` can contain values larger than $2^{56}$, we carry their respective high bits into `acc[6]` so as to remove any redundancy. Conveniently, our preemptive carrying before the third substitution has granted us a pretty tight bound on our final calculation - the final reduced number has the range $[0, 2^{384}]$.

#### Canonicalisation

This is 'just the right amount of reduction' but not _canonicalisation_. That is, since $0 < p_{384} < 2^{384}$, there can be multiple possible reduced values for a given congruence class. `felem_contract` is a method which uses the fact that $0  \leq x < 2 p_{384}$ to further reduce the output of `felem_reduce` into the range $[0, p_{384})$ in constant time.

This code has many more dragons I won't explain here, but the basic premise to the calculations performed there is as follows:

Given a 385 bit input, checking whether our input (expressed as a concatenation of bits) $b_{384}b_{383} \ldots b_1b_0$ is greater than or equal to $p_{384}$ whose bits we denote $q_{384}, \ldots, q_0$ ($q_{384} = 0$) is determined by the following logical predicate ($G(384)$):

$$G(k) \equiv (b_k \land \lnot q_k) \lor ((b_k = q_k) \land G(k-1))$$
$$G(0) \equiv b_k = q_k$$

With $p_{384}$ being a Solinas'/Pseudo-Mersenne Prime, it has a large number of contiguous runs of repeated bits, so we can of course use this to massively simplify our predicate. Doing this in constant time involves some interesting bit-shifting/masking schenanigans. Essentially, you want a bit vector of all ones/zeros depending on the value of $G(384)$, we then logically 'and' with this bitmask to 'conditionally' subtract $p_{384}$ from our result.

### A Side Note about the Weird Constants

Okay so we're implementing our modular arithmetic with unsigned integer limbs that together represent a number of the following form:

$$x = \sum_{k = 0}^{n-1} 2^{dk} l_k$$

How do we then do subtractions in a way which will make overflow impossible? Well computing $a - b$ is really straightforward if every limb of $a$ is larger than every limb of $b$. We then add a suitable multiple of $p_{384}$ to $a$ that causes each limb of $a$ to be sufficiently large.

Thankfully, with redundant-limb arithmetic, we can do this easily by means of *telescopic sums*. For example, in `felem_reduce` we wanted all limbs of our $p_{384}$ multiple to be sufficiently large. We overshot any requirement and provided such a multiple which gives a lower bound $2^{123}$. We first scale our prime accordingly so that its 'lead term' (speaking in the polynomial representation) is $2^{124}$.

$$2^{76} f(t) = 2^{124} t^6 - 2^{92} t^2 - 2^{116} t + (2^{108} - 2^{76}) t^0$$

Notice that most limbs of this multiple (the limbs will be the coefficients) are either too small or negative. We then transform this expression into a suitable telescopic sum. Observe that when $t = 2^{56}$, $2^{124} t^k = 2^{124-56}t^{k+1} = 2^{68} t^{k+1}$, and so simply introduce into each limb where required a $2^{124}$ term by means of addition, subtracting the same number from a higher limb.

$$
\begin{align*}
2^{76} f(t) &= (2^{124} - 2^{68}) t^6 \\
            &+ (2^{124} - 2^{68}) t^5 \\
            &+ (2^{124} - 2^{68}) t^4 \\
            &+ (2^{124} - 2^{68}) t^3 \\
            &+ (2^{124} - 2^{92} - 2^{68}) t^2 \\
            &+ (2^{124} - 2^{116} - 2^{68}) t \\
            &+ (2^{124} + 2^{108} - 2^{76})
\end{align*}
$$

We can then subtract values whose limbs are no larger than the least of these limbs above without fear of underflows providing us with an incorrect result. In our case, that upper bound for limb value is $2^{124} - 2^{116} - 2^{68} > 2^{123}$. Very comfortable.

## Concerning Timing Side-Channels

Cryptographic routines must perform all of their calculations in constant time. More specifically, it is important that timing cryptography code should not reveal any private keys or random nonces used during computation. Ultimately, all of our work so far has been to speed up field arithmetic in the modulo field with prime $p_{384}$. But this is done in order to facilitate calculations in the secp384r1 elliptic curve, and ECDSA/ECDH each depend on being able to perform scalar 'point multiplication' (repeat application of the group operator). Since such an operation is inherently iterative, it presents the greatest potential for timing attacks.

We implement constant-time multiplication with the *wNAF* ladder method. This relies on pre-computing a window of multiples of the group generator, and then scaling and selectively adding multiples when required. [Wikipedia](https://en.wikipedia.org/wiki/Elliptic_curve_point_multiplication#Point_multiplication) provides a helpful primer to this method  by cumulatively building upon more naive approaches.

## Conclusion

While the resulting code borrows from and uses common language of Solinas reduction, ultimately there are a number of implementation decisions that were guided by heuristic - going from theory to implementation was far from cut-and-dry. The limb size, carry order, choice of substitutions as well as pre and post conditions made here are ultimately arbitrary. You could easily imagine there being further refinements obtaining a better result. For now, I hope this post serves to demystify the inner workings of ECC implementations in OpenSSL. These algorithms, although particular and sophisticated, need not be immutable.
