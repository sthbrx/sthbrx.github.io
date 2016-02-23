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
#FEED_DOMAIN = SITEURL
FEED_ALL_ATOM = 'atom.xml'
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = (('OzLabs', 'http://ozlabs.org'),)

THEME = "../pelican-octopress-theme"

ARTICLE_PATHS = ['blog']
ARTICLE_URL = 'blog/{date:%Y}/{date:%m}/{date:%d}/{slug}/'
ARTICLE_SAVE_AS = 'blog/{date:%Y}/{date:%m}/{date:%d}/{slug}/index.html'
PAGE_URL = 'pages/{slug}/'
PAGE_SAVE_AS = 'pages/{slug}/index.html'

# Social widget
SOCIAL = (('twitter', 'http://twitter.com', '#'),
          ('Google plus', 'https://plus.google.com/collections/featured', '#'),)
          ('reddit', 'https://www.reddit.com', '#'),)
          ('Hacker News', 'https://news.ycombinator.com', '#'),)
          ('github', 'https://github.com', '#'),)

DEFAULT_PAGINATION = 2

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True
