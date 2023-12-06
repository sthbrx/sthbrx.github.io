Title: linux.conf.au 2017 review
Date: 2017-01-31 16:07:00
Authors: Daniel Axtens
Category: Education
Tags: conferences

I recently attended LCA 2017, where I gave a talk at the Linux Kernel miniconf (run by fellow sthbrx blogger Andrew Donnellan!) and a talk at the main conference.

I received some really interesting feedback so I've taken the opportunity to write some of it down to complement the talk videos and slides that are online. (And to remind me to follow up on it!)

## Miniconf talk: Sparse Warnings

My kernel miniconf talk was on sparse warnings ([pdf slides](https://github.com/daxtens/sparse-warnings-talk/blob/master/talk.pdf), [23m video](https://www.youtube.com/watch?v=hmCukzpevUc)).

The abstract read (in part):

> sparse is a semantic parser for C, and is one of the static analysis tools available to kernel devs.
>
> Sparse is a powerful tool with good integration into the kernel build system. However, we suffer from warning overload - there are too many sparse warnings to spot the serious issues amongst the trivial. This makes it difficult to use, both for developers and maintainers.

Happily, I received some feedback that suggests it's not all doom and gloom like I had thought!

 * Dave Chinner told me that the xfs team uses sparse regularly to make sure that the file system is endian-safe. This is good news - we really would like that to be endian-safe!
  
 * Paul McKenney let me know that the 0day bot does do some sparse checking - it would just seem that it's not done on PowerPC.

## Main talk: 400,000 Ephemeral Containers

My main talk was entitled "400,000 Ephemeral Containers: testing entire ecosystems with Docker". You can read the [abstract](https://linux.conf.au/schedule/presentation/81/) for full details, but it boils down to:

> What if you want to test how _all_ the packages in a given ecosystem work in a given situation?

My main example was testing how many of the Ruby packages successfully install on Power, but I also talk about other languages and other cool tests you could run.

The [44m video](https://www.youtube.com/watch?v=v7wSqOQeGhA) is online. I haven't put the slides up yet but they should be available [on GitHub](https://github.com/daxtens/400000-ephemeral-containers) soonish.

Unlike with the kernel talk, I didn't catch the names of most of the people with feedback.

### Docker memory issues

One of the questions I received during the talk was about running into memory issues in Docker. I attempted to answer that during the Q&A. The person who asked the question then had a chat with me afterwards, and it turns out I had completely misunderstood the question. I thought it was about memory usage of running containers in parallel. It was actually about memory usage in the docker daemon when running lots of containers in serial. Apparently the docker daemon doesn't free memory during the life of the process, and the question was whether or not I had observed that during my runs.

I didn't have a good answer for this at the time other than "it worked for me", so I have gone back and looked at the docker daemon memory usage.

After a full Ruby run, the daemon is using about 13.9G of virtual memory, and 1.975G of resident memory. If I restart it, the memory usage drops to 1.6G of virtual and 43M of resident memory. So it would appear that the person asking the question was right, and I'm just not seeing it have an effect.

### Other interesting feedback

  * Someone was quite interested in testing on Sparc, once they got their Go runtime nailed down.

  * A Rackspacer was quite interested in Python testing for OpenStack - this has some intricacies around Py2/Py3, but we had an interesting discussion around just testing to see if packages that claim Py3 support provide Py3 support.
    
  * A large jobs site mentioned using this technique to help them migrate their dependencies between versions of Go.

  * I was 'gently encouraged' to try to do better with how long the process takes to run - if for no other reason than to avoid burning more coal. This is a fair point. I did not explain very well what I meant with diminishing returns in the talk: there's *lots* you could do to make the process faster, it's just comes at the cost of the simplicity that I really wanted when I first started the project. I am working (on and off) on better ways to deal with this by considering the dependency graph.

