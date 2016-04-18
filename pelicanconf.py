# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = u'OzLabs'
SITENAME = u'Store Half Byte-Reverse Indexed'
SITEURL = 'https://sthbrx.github.io'
SITESUBTITLE = 'A Power Technical Blog'

DISQUS_SITENAME = 'sthbrx'

PATH = 'content'

TIMEZONE = 'Australia/Canberra'

DEFAULT_LANG = u'en'

# Feed generation is usually not desired when developing
FEED_DOMAIN = SITEURL
FEED_ALL_ATOM = 'atom.xml'
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
FEED_RSS = "rss.xml"

# Blogroll
LINKS = (('OzLabs', 'http://ozlabs.org'),)

THEME = "../pelican-octopress-theme"

ARTICLE_PATHS = ['blog']
ARTICLE_URL = 'blog/{date:%Y}/{date:%m}/{date:%d}/{slug}/'
ARTICLE_SAVE_AS = 'blog/{date:%Y}/{date:%m}/{date:%d}/{slug}/index.html'
PAGE_URL = 'pages/{slug}/'
PAGE_SAVE_AS = 'pages/{slug}/index.html'

# Social widget
SOCIAL = (('GitHub', 'https://github.com/sthbrx/'),
          ('linuxppc mailing list', 'https://lists.ozlabs.org/listinfo/linuxppc-dev'),
          ('Skiboot mailing list', 'https://lists.ozlabs.org/listinfo/skiboot'),
)

SIDEBLOCK_TITLE = 'Disclaimer'
SIDEBLOCK_CONTENT = "This blog represents the views of the individual authors, and doesn't necessarily represent IBM's positions, strategies or opinions."

DEFAULT_PAGINATION = 5

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True

# Don't summarise posts on the home page.
# Replicates old Octopress behaviour.
SUMMARY_MAX_LENGTH=None

IGNORE_FILES = ['*WIP*']

# Author page generation settings
AUTHORS_SAVE_AS = 'authors.html'
