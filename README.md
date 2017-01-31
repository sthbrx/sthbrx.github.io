Guide for documentation writers:

# Setting up an environment:

git clone --recurse-submodules git@github.com:sthbrx/sthbrx-blog.git

if you already have this cloned, git submodule update

Install pelican (package: python[2|3]-pelican) for local testing.

# Create a document:

content/blog/{YYYY}-{MM}-{DD}-{meaningful title}.markdown

add images to directory content/images/{meaningful title}/

View:

make html serve

Examine at http://localhost:8000/blog/{YYYY}/{MM}/{DD}/{meaningful title}/

edit/rinse/repeat.

# Publishing:

Note: asking people to review your blog post before release into the wild optional but preferred! 

In output directory 'git add' required files, commit and push.

In top level directory, 'git add' the source files, images and the output directory.

git commit && push this.
