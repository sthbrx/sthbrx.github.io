Title: Lifecycle of a kernel task
Date: 2023-12-01 08:00:00
Authors: Benjamin Gray
Category: Development
Tags: linux

## Introduction

CPU cores are limited. If we required each core run a single workload to completion, we would be looking at a very different kind of experience. Right now my computer tells me it's running around 500 processes, and I definitely do not have that many CPU cores. The ability for the operating system to virtualise the concept of an 'execution unit' and swap them in and out of running on CPU cores is vital to modern computing.

Linux kernel calls these virtual execution units _tasks_. Each task encapsulates all the information the kernel needs to swap it in and out of running on a CPU core, including register state, memory mappings, file descriptor table, and any other resource that needs to be tied to a particular task. Nearly every workload in the kernel, including kernel background jobs and userspace threads, is handled by this unified task concept. The exception to this is exception handlers, which don't necessarily run in a task context.

In this article, we'll dive into the lifecycle of a task in the kernel.


## Booting

This wouldn't be a complete description of tasks if we didn't start at the very beginning. Upon booting the kernel, we have almost nothing initialised. Tasks are but a distant glimmer on the horizon. The bootloader has initialised just enough memory to get us started, and sent the CPU to go execute wherever the `_stext` symbol is.
