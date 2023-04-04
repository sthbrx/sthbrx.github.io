Title: Detecting rootless Docker
Date: 2023-04-05 13:00:00
Authors: Andrew Donnellan
Category: Development
Tags: Docker, syzkaller

## Trying to do some fuzzing...

The other day, for the first time in a while, I wanted to do something with [syzkaller](https://github.com/google/syzkaller), a system call fuzzer that has been used to find literally thousands of kernel bugs. As it turns out, since the last time I had done any work on syzkaller, I switched to a new laptop, and so I needed to set up a few things in my development environment again.

While I was doing this, I took a look at the syzkaller source again and found a neat little script called [`syz-env`](https://github.com/google/syzkaller/blob/master/tools/syz-env), which uses a Docker image to provide you with a standardised environment that has all the necessary tools and dependencies preinstalled.

I decided to give it a go, and then realised I hadn't actually installed Docker since getting my new laptop. So I went to do that, and along the way I discovered [rootless mode](https://docs.docker.com/engine/security/rootless/), and decided to give it a try.

## What's rootless mode?

As of relatively recently, Docker supports rootless mode, which allows you to run your `dockerd` as a non-root user. This is helpful for security, as traditional "rootful" Docker can trivially be used to obtain root privileges outside of a container. Rootless Docker is implemented using [RootlessKit](https://github.com/rootless-containers/rootlesskit) (a fancy replacement for [fakeroot](https://wiki.debian.org/FakeRoot) that uses user namespaces) to create a new user namespace that maps the UID of the user running `dockerd` to 0.

You can find more information, including details of the various restrictions that apply to rootless setups, [in the Docker documentation](https://docs.docker.com/engine/security/rootless/).

## The problem

I ran `tools/syz-env make` to test things out. It pulled the container image, then gave me some strange errors:

```text
ajd@jarvis-debian:~/syzkaller$ tools/syz-env make NCORES=1
gcr.io/syzkaller/env:latest
warning: Not a git repository. Use --no-index to compare two paths outside a working tree
usage: git diff --no-index [<options>] <path> <path>

    ...
 
fatal: detected dubious ownership in repository at '/syzkaller/gopath/src/github.com/google/syzkaller'
To add an exception for this directory, call:
 
        git config --global --add safe.directory /syzkaller/gopath/src/github.com/google/syzkaller
fatal: detected dubious ownership in repository at '/syzkaller/gopath/src/github.com/google/syzkaller'
To add an exception for this directory, call:
 
        git config --global --add safe.directory /syzkaller/gopath/src/github.com/google/syzkaller
go list -f '{{.Stale}}' ./sys/syz-sysgen | grep -q false || go install ./sys/syz-sysgen
error obtaining VCS status: exit status 128
        Use -buildvcs=false to disable VCS stamping.
error obtaining VCS status: exit status 128
        Use -buildvcs=false to disable VCS stamping.
make: *** [Makefile:155: descriptions] Error 1
```

After a bit of digging, I found that `syz-env` mounts the syzkaller source directory inside the container as a volume. `make` was running with UID 1000, while the files in the mounted volume appeared to be owned by root.

Reading the script, it turns out that `syz-env` invokes `docker run` with the `--user` option to set the UID inside the container to match the user's UID outside the container, to ensure that file ownership and permissions behave as expected.

This works in rootful Docker, where files appear inside the container to be owned by the same UID as they are outside the container. However, it breaks in rootless mode: due to the way RootlessKit sets up the namespaces, the user's UID is mapped to 0, causing the files to appear to be owned by root.

The workaround seemed pretty obvious: just skip the `--user` flag if running rootless.

## How can you check whether your Docker daemon is running in rootless mode?

It took me quite a while, as a total Docker non-expert, to figure out how to definitively check whether the Docker daemon is running rootless or not. There's a variety of ways you could do this, such as checking the name of the current Docker context to see if it's called `rootless` (as used by the Docker rootless setup scripts), but I think the approach I settled on is the most correct one.

If you want to check whether your Docker daemon is running in rootless mode, use `docker info` to query the daemon's security options, and check for the `rootless` option.

```text
docker info -f "{{println .SecurityOptions}}" | grep rootless
```

If this prints something like:

```text
[name=seccomp,profile=builtin name=rootless name=cgroupns]
```

then you're running rootless.

If not, then you're running the traditional rootful.

Easy! (And I sent a fix which is now [merged into syzkaller!](https://github.com/google/syzkaller/commit/340a1b9094e4b3fad232c98c62de653ec48954ab))
