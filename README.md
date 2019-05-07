Guide for documentation writers:

# Setting up an environment:

git clone --recurse-submodules git@github.com:sthbrx/sthbrx-blog.git

if you already have this cloned, git submodule update

Install pelican (package: python[2|3]-pelican) for local testing, as well
as markdown support for Python (either "pip install markdown" or a package
from your distro).

# Create a document:

Get up to date:

git pull --recurse-submodules

edit your document content/blog/{YYYY}-{MM}-{DD}-{meaningful title}.markdown

add images to directory content/images/{meaningful title}/

View:

make html devserver

Examine at http://localhost:8000/blog/{YYYY}/{MM}/{DD}/{meaningful title}/

edit/rinse/repeat.

# Publishing:

Note: asking people to review your blog post before release into the wild optional but preferred! 

In output directory 'git add' required files, commit and push.

In top level directory, 'git add' the source files, images and the output directory.

git commit && push this.
