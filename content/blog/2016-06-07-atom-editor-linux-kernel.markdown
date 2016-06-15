Title: Using the Atom editor for Linux kernel development
Date: 2016-06-07 17:03
Authors: Russell Currey
Category: Development
Tags: education, kernel, development, tools

[Atom](https://atom.io) is a text editor.  It's new, it's shiny, and it has a lot of good and bad sides.  I work in a lab full of kernel developers, and in the kernel, there are no IDEs.  There's no real metadata you can get out of your compiler (given the kernel isn't very clang friendly), there's certainly nothing like that you can get out of your build system, so "plain old" text editors reign supreme.  It's a vim or Emacs show.

And so Atom comes along.  Unlike other shiny new text editors to emerge in the past 10 or so years, it's open source (unlike Sublime Text), it works well on Linux, and it's very configurable.  When it first came out, Atom was an absolute mess.  There was a noticeable delay whenever you typed a key.  That has gone, but the sour impression that comes from replacing a native application with a web browser in a frame remains.

Like the curious person I am, I'm always trying out new things to see if they're any good.  I'm not particularly tied to any editor; I prefer modal editing, but I'm no vim wizard.  I eventually settled on using Emacs with evil-mode (which I assumed would make both Emacs and vim people like me, but the opposite happened), which was decent.  It was configurable, it was good, but it had issues.

![The Atom editor](http://i.imgur.com/36lOiMT.png)

So, let's have a look at how Atom stacks up for low-level work.  First of all, it's X only.  You wouldn't use it to change one line of a file in /etc/, and a lot of kernel developers only edit code inside a terminal emulator.  Most vim people do this since gvim is a bit wonky, and Emacs people can double-dip; using Emacs without X for small things and Emacs with X for programming.  You don't want to do that with Atom, if nothing else because of its slow startup time.

Now let's look at configurability.  In my opinion, no editor will ever match the level of configurability of Emacs, however the barrier to entry is much lower here.  Atom has lots of options exposed in a config file, and you can set them there or you can use an equivalent GUI.  In addition, a perk of being a browser in a frame is that you can customise a lot of UI things with CSS, for those inclined.  Overall, I'd say Emacs > Atom > vim here, but for a newbie, it's probably Atom > Emacs > vim.

Okay, package management.  Atom is the clear winner here.  The package repository is very easy to use, for users and developers.  I wrote my own package, typed `apm publish` and within a minute a friend could install it.  For kernel development though, you don't really need to install anything, Atom is pretty batteries-included.  This includes good syntax highlighting, ctags support, and a few themes.  In this respect, Atom feels like an editor that was created this century.

![Atom's inbuilt package management](https://i.imgur.com/DAx7GqD.png)

What about actually editing text?  Well, I only use modal editing, and Atom is very far from being the best vim.  I think evil-mode in Emacs is the best vim, followed closely by vim itself.  Atom has a vim-mode, and it's fine for insert/normal/visual mode, but anything involving a : is a no-go.  There's a plugin that's entirely useless.  If I tried to do a replacement with :s, Atom would lock up *and* fail to replace the text.  vim replaced thousands of occurrences with in a second.  Other than that, Atom's pretty good.  I can move around pretty much just as well as I could in vim or Emacs, but not quite.  Also, it support ligatures!  The first kernel-usable editor that does.

Autocompletions feel very good in Atom.  It completes within a local scope automatically, without any knowledge of the type of file you're working on.  As far as intelligence goes, Atom's support for tags outside of ctags is very lacking, and ctags is stupid.  Go-to definition *sometimes* works, but it lags when dealing with something as big as the Linux kernel.  Return-from definition is very good, though.  Another downside is that it can complete from any open buffer, which is a huge problem if you're writing Rust in one tab and C in the other.

![Atom's fuzzy file matching is pretty good](http://i.imgur.com/0PRiIUS.png)

An experience I've had with Atom that I haven't had with other editors is actually writing a plugin.  It was really easy, mostly because I stole a lot of it from an existing plugin, but it was easy.  I wrote a syntax highlighting package for POWER assembly, which was much more fighting with regular expressions than it was fighting with anything in Atom.  Once I had it working, it was very easy to publish; just push to GitHub and run a command.

Sometimes, Atom can get too clever for its own good.  For some completely insane reason, it automatically "fixes" whitespace in every file you open, leading to a huge amount of git changes you didn't intend.  That's easy to disable, but I don't want my editor doing that, it'd be much better if it highlighted whitespace it didn't like by default, like you can get vim and Emacs to do.  For an editor designed around git, I can't comprehend that decision.

![Atom can also fuzzy match its commands](https://i.imgur.com/arbWXHx.png)

Speaking of git, the editor pretty much has everything you'd expect for an editor written at GitHub.  The sidebar shows you what lines you've added, removed and modified, and the gutter shows you what branch you're on and how much you've changed all-up.  There's no in-built support for doing git things inside the editor, but there's a package for it.  It's pretty nice to get something "for free" that you'd have to tinker with in other editors.

Overall, Atom has come a long way and still has a long way to go.  I've been using it for a few weeks and I'll continue to use it.  I'll encourage new developers to use it, but it needs to be better for experienced programmers who are used to their current workflow to consider switching.  If you're in the market for a new editor, Atom might just be for you.
