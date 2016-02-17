Title: "Evolving into a systems programmer"
Date: 2015-11-06 11:13
Authors: Cyril Bur
Category: Education
Tags: education, offtopic

In a previous life I tutored first year computing. The university I
attended had a policy of using C to introduce first years to programming.
One of the most rewarding aspects of teaching is opening doors of
possibility to people by sharing my knowledge.

Over the years I had a mixture of computer science or computer engineering
students as well as other disciplines of engineering who were required to
learn the basics (notably electrical and mechanical). Each class was
different and the initial knowledge always varied greatly. The beauty of
teaching C meant that there was never someone who truly knew it all, heck,
I didn't and still don't. The other advantage of teaching C is that I could
very quickly spot the hackers, the shy person at the back of the room who's
eyes light up when you know you've correctly explained pointers (to them
anyway) or when asked "What happens if you use a negative index into an
array" and the smile they would make upon hearing "What do you think happens".

Right there I would see the makings of a hacker, and this post is dedicated
to you or to anyone who wants to be a hacker. I've been asked "What did you
do to get where you are?", "How do I get into Linux?" (vague much) at
careers fairs. I never quite know what to say, here goes a braindump.

Start with the basics, one of the easiest way we tested the first years was
to tell them they can't use parts of libc. That was a great exam, taking
aside those who didn't read the question and used `strlen()` when they were
explicitly told they couldn't `#include <string.h>` a true hacker doesn't
need libc, understand it won't always be there. I thought of this example
because only two weeks ago I was writing code in an environment where I
didn't have libc. Ok sure, if you've got it, use it, just don't crumble
when you don't. Oh how I wish I could have told those students who argued
that it was a pointless question that they were objectively wrong.

Be a fan of assembly, don't be afraid of it, it doesn't bite and it can be
a lot of fun. I wouldn't encourage you to dive right into the PowerISA,
it's intense but perhaps understand the beauty of GCC, know what it's doing
for you. There is a variety of little 8 bit processors you can play with
these days.

At all levels of my teaching I saw almost everyone get something which
'worked', and that's fine, it probably does but I'm here to tell you that
it doesn't work until you know why it works. I'm all for the 'try it and
see' approach but once you've tried it you have to explain why the
behaviour changed otherwise you didn't fix it. As an extension to that,
know how your tools work, I don't think anyone would expect you to be able
to write tools to the level of complexity of GCC or GDB or Valgrind but
have a rough idea as to how they achieve their goals.

A hacker is paranoid, yes, `malloc()` fails. Linux might just decide now
isn't a good time for you to `open()` and your `fopen()` calling function had
better be cool with that. A hacker also doesn't rely on the kindness of the
operating system theres an `munmap()` for a reason. Nor should you even
completely trust it, what are you leaving around in memory?

Above all do a it for the fun of it, so many of my students asked how I
knew everything I knew (I was only a year ahead of them in my first year of
teaching) and put simply, write code on a Saturday night.

None of these things do or don't make you a hacker, being a hacker is a
frame of mind and a way of thinking but all of the above helps.

Unfortunately there isn't a single path, I might even say it is a path that
chooses you. Odds are you're here because you approached me at some point
and asked me one of those questions I never quite know how to answer.
Perhaps this is the path, at the very least you're asking questions and
approaching people. I'm hope I did on the day, but once again, all the very
best with your endeavours into the future
