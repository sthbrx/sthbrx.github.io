Title: Quirks of parsing SSH configs 
Date: 2023-08-03 00:00:00 
Authors: Benjamin Gray 
Category: Development 
Tags: ssh


## Introduction

I've been using the VSCodium 
[Open Remote - SSH](https://open-vsx.org/extension/jeanp413/open-remote-ssh)
extension recently to great results. I can treat everything as a single
environment, without any worry about syncing between my local development files
and the remote. This is very different to mounting the remote as a network drive
and opening a local instance of VSCodium on it: in addition to crippling latency
on every action, a locally mounted drive doesn't bring the build context that
tools like `clangd` require (e.g., system headers).

Instead, the remote extension runs a server on the remote that performs most
actions, and the local VSCodium instance acts as a client that buffers and
caches data seamlessly, so the experience is nearly as good as developing
locally. 

For example, a project wide file search on a network drive is unusably slow
because every file and directory read requires a round trip back to the remote,
and the latency is just too large to finish getting results back in a reasonable
time. But with the client-server approach, the client just sends the search
request to the server for it to fulfil, and all the server has to do is send the
matches back. This eliminates nearly all the latency effects, except for the
initial request and receiving any results.

However there has been one issue with using this for everything: the extension
failed to connect when I wasn't on the same network as the host machine. So I
wasn't able to use it when working from home over a VPN. In this post we find
out why this happened, and in the process look at some of the weird quirks of
parsing an SSH config.


## The issue

As above, I wasn't able to connect to my remote machines when working from home.
The extension would abort with the following error:

```text
[Error  - 00:23:10.592] Error resolving authority
Error: getaddrinfo ENOTFOUND remotename.ozlabs.ibm.com
	at GetAddrInfoReqWrap.onlookup [as oncomplete] (node:dns:109:26)
```

So it's a DNS issue. This would make sense, as the remote machine is not exposed
to the internet, and must instead be accessed through a proxy. What's weird is
that the integrated terminal in VSCodium has no problem connecting to the
remote. So the extension seems to be doing something different than just a plain
SSH connection.

You might think that the extension is not reading the SSH config. But the
extension panel lists all the host aliases I've declared in the config, so it's
clearly aware of the config at least. Possibly it doesn't understand the proxy
config correctly? If it was trying to connect directly from the host, it would
make sense to fail a DNS lookup.


## Investigating

Enough theorising, time to debug the extension as it tries to connect.

From the error above, the string `"Error resolving authority"` looks like
something I can search for. This takes me to the
[`catch` case for a large try-catch block](https://github.com/jeanp413/open-remote-ssh/blob/521098e24f48b4b9e04d476895f9097b03f8c984/src/authResolver.ts#L226).
It could be annoying to narrow down which part of the block
throws the exception, but fortunately debugging is as easy as installing the
dependencies and running the pre-configured 'Extension' debug target. This opens
a new window with the local copy of the extension active, and I can debug it in
the original window.

In this block, there is a conditional statement on whether the `ProxyJump` field
is present in the config. This is a good place to break on and see what the
computed config looks like. If it doesn't find a proxy then of course it's going
to run everything on the host.

And indeed, it doesn't think there is a proxy. This is progress, but why does
the extension's view of the config not match up with what SSH does? After all,
invoking SSH directly connects properly. Tracing back the source of the config
in the extension, it ultimately comes from manually reading in and parsing the
SSH config. When resolving the host argument it manually computes the config as
per [`ssh_config(5)`](https://man7.org/linux/man-pages/man5/ssh_config.5.html).
Yet somewhere it makes a mistake, because it doesn't include the `ProxyJump`
field.


## Parsing SSH config

To get to the bottom of this, we need to know the rules behind parsing SSH
configs. The `ssh_config(5)` manpage does a pretty decent job of explaining
this, but I'm going to go over the relevant information here. I reckon most
people have a vague idea of how it works, and can write enough to meet their
needs, but have never looked deeper into the actual rules behind how SSH parses
the config.

1. For starters, the config is parsed line by line. Leading whitespace (i.e.,
   indentation) is ignored. So, while indentation makes it look like you are
   configuring properties for a particular host, this isn't quite correct.
   Instead, the `Host` and `Match` lines are special statements that enable or
   disable all subsequent lines until the next `Host` or `Match`.

    There is no backtracking; previous conditions and lines are not re-evaluated
    after learning more about the config later on.

2. When a config line is seen, and is active thanks to the most recent `Host` or
   `Match` succeeding, its value is selected if it is the first of that config
   to be selected. So the earliest place a value is set takes priority; this may
   be a little counterintuitive if you are used to having the latest value be
   picked, such as enable/disable command line flags tend to work.

3. When `HostName` is set, it replaces the value used in `Host` matches and the
   `host` value in `Match` matches.

4. The last behaviour of interest is the `Match final` rule. There are several
   conditions a `Match` statement can have, and the `final` rule says make this
   active on the final pass over the config.

Wait, final pass? Multiple passes? Yes. If `final` is a condition on a `Match`,
SSH will do another pass over the config, following all the rules above. Except
this time all the configs we read on the first pass are still active (and can't
be changed). But all the `Host` and `Matches` are re-evaluated, allowing other
configs to potentially be set. I guess that means rule (1) ought to have a big
asterisk next to it.

Together, these rules can lead to some quirky behaviours. Consider the following
config

```text
Host *.ozlabs.ibm.com
    ProxyJump proxy

Host example
    HostName example.ozlabs.ibm.com
```

If I run `ssh example` on the command line, will it use the proxy?

By rule (1), no. When testing the first `Host` condition, our host value is
currently `example`. It is not until we reach the `HostName` config that we
start using `example.ozlabs.ibm.com` for any host matches.

But by rule (4), the answer turns into _maybe_. If we end up doing a second pass
over the config thanks to a `Match final` that could be _anywhere_ else, we
would now be matching `example.ozlabs.ibm.com` against the first `Host` on the
second go around. This will pass, and, since nothing has set `ProxyJump` yet, we
would gain the proxy.

You may think, yes, but we don't have a `Match final` in that example. But if
you thought that, then you forgot about the system config.

The system config is effectively appended to the user config, to allow any
system wide settings. Most of the time this isn't an issue because of the
first-come-first-served rule with config matches (rule 2). But if the system
config includes a `Match final`, it will trigger the entire config to be
re-parsed, including the user section. And it so happens that, at least on
Fedora with the `openssh-clients` package installed, the system config does
contain a `Match final`.

But wait, there's more! If we want to specify a custom SSH config file, then we
can use `-F path/to/config` in the command line. But this disables loading a
system config, so we would no longer get the proxy!

To sum up, for the above config:

1. `ssh example` doesn't have a proxy
2. ...unless a system config contains `Match final`
3. ...but invoking it as `ssh -F ~/.ssh/config example` definitely won't have
   the proxy
4. ...but if a subprocess invokes `ssh example` while trying to resolve another
   host, it'll probably not add the `-F ~/.ssh/config`, so we might get the
   proxy again (in the child process).

Wait, how did that last one slip in? Well, unlike environment variables, it's a
lot harder for processes to propagate command line flags correctly. If resolving
the config involves running a script that itself tries to run SSH, chances are
the `-F` flag won't be propagated and you'll see some weird behaviour.

I swear that's all for now, you've probably learned more about SSH configs than
you will ever need to care about.


## Back to VSCodium

Alright, armed now with this knowledge on SSH config parsing, we can work out
what's going on with the extension. It ends up being a simple issue: it doesn't
apply rule (3), so all `Host` matches are done against the original host name.

In my case, there are several machines behind the proxy, but they all share a
common suffix, so I had a `Host *.ozlabs.ibm.com` rule to apply the proxy. I
also use aliases to refer to the machines without the `.ozlabs.ibm.com` suffix,
so failing to follow rule (3) lead to the situation where the extension didn't
think there was a proxy.

However, even if this were to be fixed, it still doesn't respect rule (4), or
most complex match logic in general. If the hostname bug is fixed then my setup
would work, but it's less than ideal to keep playing whack-a-mole with parsing
bugs. It would be a lot easier if there was a way to just ask SSH for the config
that a given host name resolves to.

Enter `ssh -G`. The `-G` flag asks SSH to dump the complete resolved config,
without actually opening the connection (it may execute arbitrary code while
resolving the config however!). So to fix the extension once and for all, we
could swap the manual parser to just invoking `ssh -G example`, and parsing the
output as the final config. No `Host` or `Match` or `HostName` or `Match final`
quirks to worry about.

Sure enough, if we replace the config backend with this 'native' resolver, we
can connect to all the machines with no problem.

In general, I'd suggest avoiding any dependency on a second pass being done on
the config. Resolve your aliases early, so that the rest of the rules work
against the full hostname. If you later need to match against the name passed in
the command line, you can use `Match originalhost=example`. The example above
should always be written as

```text
Host example
    HostName example.ozlabs.ibm.com

Host *.ozlabs.ibm.com
    ProxyJump proxy
```

even if the reversed order might appear to work thanks to the weird interactions
described above.
