# Guide for blog writers

## Setting up an environment:

```
git clone --recurse-submodules git@github.com:sthbrx/sthbrx.github.io.git
```

if you already have this cloned, git submodule update

Install pelican (with pelican-render-math) and the Python markdown package for local testing.
You can do this through `pip install -r requirements.txt` or through your distro.

## Create a document:

Get up to date:

```
git pull --recurse-submodules
```

Create your post in: `content/blog/{YYYY}-{MM}-{DD}-{meaningful title}.markdown`.

Add images to the directory `content/images/{meaningful title}/`.

To preview:

```
make watch
```

Examine at `http://localhost:8000`.

Edit/rinse/repeat.

## Publishing:

*Note:* asking people to review your blog post before release into the wild is preferred!

`git add` the source files and images, then push it to a new branch and open a PR for review.
