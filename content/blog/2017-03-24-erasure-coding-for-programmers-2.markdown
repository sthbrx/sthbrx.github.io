Title: Erasure Coding for Programmers, Part 2
Date: 2017-03-24 10:08:00
Authors: Daniel Axtens
Category: Development
Tags: erasure, raid, storage

We left [part 1](/blog/2017/03/20/erasure-coding-for-programmers-part-1/) having explored GF(2^8) and RAID 6, and asking the question "what does all this have to do with Erasure Codes?"

Basically, the thinking goes "RAID 6 is cool, but what if, instead of two parity disks, we had an arbitrary number of parity disks?"

How would we do that? Well, let's introduce our new best friend: Coding Theory!

Say we want to transmit some data across an error-prone medium. We don't know where the errors might occur, so we add some extra information to allow us to detect and possibly correct for errors. This is a code. Codes are a largish field of engineering, but rather than show off my knowledge about systematic linear block codes, let's press on.

Today, our error-prone medium is an array of inexpensive disks. Now we make this really nice assumption about disks, namely that they are either perfectly reliable or completely missing. In other words, we consider that a disk will either be present or 'erased'. We come up with 'erasure codes' that are able to reconstruct data when it is known to be missing. (This is a slightly different problem to being able to verify and correct data that might or might not be subtly corrupted. Disks also have to deal with this problem, but it is *not* something erasure codes address!)

The particular code we use is a Reed-Solomon code. The specific details are unimportant, but there's a really good graphical outline of the broad concepts in sections 1 and 3 of [the Jerasure paper/manual](http://jerasure.org/jerasure-2.0/). (Don't go on to section 4.)

That should give you some background on how this works at a pretty basic mathematical level. Implementation is a matter of mapping that maths (matrix multiplication) onto hardware primitives, and making it go fast.

## Scope

I'm deliberately *not* covering some pretty vast areas of what would be required to write your own erasure coding library from scratch. I'm not going to talk about how to compose the matricies, how to invert them, or anything like that. I'm not sure how that would be a helpful exercise - ISA-L and jerasure already exist and do that for you.

What I want to cover is an efficient implementation of the some algorithms, once you have the matricies nailed down.

I'm also going to assume your library already provides a generic multiplication function in GF(2^8). That's required to construct the matrices, so it's a pretty safe assumption.

## The beginnings of an API

Let's make this a bit more concrete.

This will be heavily based on the [ISA-L API](https://01.org/intel%C2%AE-storage-acceleration-library-open-source-version/documentation/isa-l-open-source-api) but you probably want to plug into ISA-L anyway, so that shouldn't be a problem.

What I want to do is build up from very basic algorithmic components into something useful.

The first thing we want to do is to be able to is Galois Field multiplication of an entire region of bytes by an arbitrary constant.

We basically want `gf_vect_mul(size_t len, <something representing the constant>, unsigned char * src, unsigned char * dest)`

### Simple and slow approach

The simplest way is to do something like this:

    void gf_vect_mul_simple(size_t len, unsigned char c, unsigned char * src, unsigned char * dest) {

        size_t i;
        for (i=0; i<len; i++) {
            dest[i] = gf_mul(c, src[i]);
        }
    }

That does multiplication element by element using the library's supplied `gf_mul` function, which - as the name suggests - does GF(2^8) multiplication of a scalar by a scalar.

This works. The problem is that it is very, painfully, slow - in the order of a few hundred megabytes per second.

### Going faster

How can we make this faster?

There are a few things we can try: if you want to explore a whole range of different ways to do this, check out the [gf-complete](http://jerasure.org/gf-complete-1.02/) project. I'm going to assume we want to skip right to the end and know what is the fastest we've found.

Cast your mind back to the [RAID 6 paper](https://www.kernel.org/pub/linux/kernel/people/hpa/raid6.pdf) (PDF). I talked about in [part 1](/blog/2017/03/20/erasure-coding-for-programmers-part-1/). That had a way of doing an efficient multiplication in GF(2^8) using vector instructions.

To refresh your memory, we split the multiplication into two parts - low bits and high bits, looked them up separately in a lookup table, and joined them with XOR. We then discovered that on modern Power chips, we could do that in one instruction with `vpermxor`.

So, a very simple way to do this would be:

 - generate the table for `a`
 - for each 16-byte chunk of our input:
     * load the input
     * do the `vpermxor` with the table
     * save it out


Generating the tables is reasonably straight-forward, in theory. Recall that the tables are `a` * {{00},{01},...,{0f}} and `a` * {{00},{10},..,{f0}} - a couple of loops in C will generate them without difficulty. ISA-L has a function to do this, as does gf-complete in split-table mode, so I won't repeat them here.

So, let's recast our function to take the tables as an input rather than the constant `a`. Assume we're provided the two tables concatenated into one 32-byte chunk. That would give us:

    void gf_vect_mul_v2(size_t len, unsigned char * table, unsigned char * src, unsigned char * dest)

Here's how you would do it in C:

    void gf_vect_mul_v2(size_t len, unsigned char * table, unsigned char * src, unsigned char * dest) {
            vector unsigned char tbl1, tbl2, in, out;
            size_t i;

            /* Assume table, src, dest are aligned and len is a multiple of 16 */

            tbl1 = vec_ld(16, table);
            tbl2 = vec_ld(0, table);
            for (i=0; i<len; i+=16) {
                in = vec_ld(i, (unsigned char *)src);
                __asm__("vpermxor %0, %1, %2, %3" : "=v"(out) : "v"(tbl1), "v"(tbl2), "v"(in)
                vec_st(out, i, (unsigned char *)dest);
            }
    }

There's a few quirks to iron out - making sure the table is laid out in the vector register in the way you expect, etc, but that generally works and is quite fast - my Power 8 VM does about 17-18 GB/s with non-cache-contained data with this implementation.

We can go a bit faster by doing larger chunks at a time:

        for (i=0; i<vlen; i+=64) {
                in1 = vec_ld(i, (unsigned char *)src);
                in2 = vec_ld(i+16, (unsigned char *)src);
                in3 = vec_ld(i+32, (unsigned char *)src);
                in4 = vec_ld(i+48, (unsigned char *)src);
                __asm__("vpermxor %0, %1, %2, %3" : "=v"(out1) : "v"(tbl1), "v"(tbl2), "v"(in1));
                __asm__("vpermxor %0, %1, %2, %3" : "=v"(out2) : "v"(tbl1), "v"(tbl2), "v"(in2));
                __asm__("vpermxor %0, %1, %2, %3" : "=v"(out3) : "v"(tbl1), "v"(tbl2), "v"(in3));
                __asm__("vpermxor %0, %1, %2, %3" : "=v"(out4) : "v"(tbl1), "v"(tbl2), "v"(in4));
                vec_st(out1, i, (unsigned char *)dest);
                vec_st(out2, i+16, (unsigned char *)dest);
                vec_st(out3, i+32, (unsigned char *)dest);
                vec_st(out4, i+48, (unsigned char *)dest);
        }

This goes at about 23.5 GB/s.

We can go one step further and do the core loop in assembler - that means we control the instruction layout and so on. I tried this: it turns out that for the basic vector multiply loop, if we turn off ASLR and pin to a particular CPU, we can see a improvement of a few percent (and a decrease in variability) over C code.

## Building from vector multiplication

Once you're comfortable with the core vector multiplication, you can start to build more interesting routines.

A particularly useful one on Power turned out to be the multiply and add routine: like gf_vect_mul, except that rather than overwriting the output, it loads the output and xors the product in. This is a simple extension of the gf_vect_mul function so is left as an exercise to the reader.

The next step would be to start building erasure coding proper. Recall that to get an element of our output, we take a dot product: we take the corresponding input element of each disk, multiply it with the corresponding GF(2^8) coding matrix element and sum all those products. So all we need now is a dot product algorithm.

One approach is the conventional dot product:

 - for each element
     - zero accumulator
     - for each source
         - load `input[source][element]`
         - do GF(2^8) multiplication
         - xor into accumulator
     - save accumulator to `output[element]`

The other approach is multiply and add:

 - for each source
     - for each element
        - load `input[source][element]`
        - do GF(2^8) multiplication
        - load `output[element]`
        - xor in product
        - save `output[element]`

The dot product approach has the advantage of fewer writes. The multiply and add approach has the advantage of better cache/prefetch performance. The approach you ultimately go with will probably depend on the characteristics of your machine and the length of data you are dealing with.

For what it's worth, ISA-L ships with only the first approach in x86 assembler, and Jerasure leans heavily towards the second approach.

Once you have a vector dot product sorted, you can build a full erasure coding setup: build your tables with your library, then do a dot product to generate each of your outputs!

In ISA-L, this is implemented something like this:

    /*
     * ec_encode_data_simple(length of each data input, number of inputs,
     *                       number of outputs, pre-generated GF(2^8) tables,
     *                       input data pointers, output code pointers)
     */
    void ec_encode_data_simple(int len, int k, int rows, unsigned char *g_tbls,
                               unsigned char **data, unsigned char **coding)
    {
            while (rows) {
                    gf_vect_dot_prod(len, k, g_tbls, data, *coding);
                    g_tbls += k * 32;
                    coding++;
                    rows--;
            }
    }

## Going faster still

Eagle eyed readers will notice that however we generate an output, we have to read all the input elements. This means that if we're doing a code with 10 data disks and 4 coding disks, we have to read each of the 10 inputs 4 times.

We could do better if we could calculate multiple outputs for each pass through the inputs. This is a little fiddly to implement, but does lead to a speed improvement.

ISA-L is an excellent example here. Intel goes up to 6 outputs at once: the number of outputs you can do is only limited by how many vector registers you have to put the various operands and results in.

## Tips and tricks

 * Benchmarking is tricky. I do the following on a bare-metal, idle machine, with ASLR off and pinned to an arbitrary hardware thread. (Code is for the [fish shell](https://fishshell.com/))

        for x in (seq 1 50)
            setarch ppc64le -R taskset -c 24 erasure_code/gf_vect_mul_perf
        end | awk '/MB/ {sum+=$13} END {print sum/50, "MB/s"}'


 * Debugging is tricky; the more you can do in C and the less you do in assembly, the easier your life will be.

 * Vector code is notoriously alignment-sensitive - if you can't figure out why something is wrong, check alignment. (Pro-tip: ISA-L does *not* guarantee the alignment of the `gftbls` parameter, and many of the tests supply an unaligned table from the stack. For testing `__attribute__((aligned(16)))` is your friend!)

 * Related: GCC is moving towards assignment over vector intrinsics, at least on Power:

        vector unsigned char a;
        unsigned char * data;
        // good, also handles word-aligned data with VSX
        a = *(vector unsigned char *)data;
        // bad, requires special handling of non-16-byte aligned data
        a = vec_ld(0, (unsigned char *) data);
    

## Conclusion

Hopefully by this point you're equipped to figure out how your erasure coding library of choice works, and write your own optimised implementation (or maintain an implementation written by someone else).

I've referred to a number of resources throughout this series:

 * ISA-L [code](https://github.com/01org/isa-l), [API description]()
 * Jerasure [code](http://jerasure.org/), [docs](http://jerasure.org/jerasure-2.0/)
 * gf-complete [code](http://jerasure.org/), [docs](http://jerasure.org/gf-complete-1.02/) 
 * [The mathematics of RAID-6](https://www.kernel.org/pub/linux/kernel/people/hpa/raid6.pdf) (PDF), H. Peter Anvin

If you want to go deeper, I also read the following and found them quite helpful in understanding Galois Fields and Reed-Solomon coding:

 * [Tutorial on Reed-Solomon Error Correction Coding](https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/19900019023.pdf) (PDF), William A. Geisel, NASA
 * [Reed-Solomon error correction](https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/19900019023.pdf) (PDF), BBC R&D White Paper WHP 031, C. K. P. Clarke.

For a more rigorous mathematical approach to rings and fields, a university mathematics course may be of interest. For more on coding theory, a university course in electronics engineering may be helpful.