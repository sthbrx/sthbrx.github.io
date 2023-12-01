PY?=python
VENV?=venv
PELICAN?=pelican
PELICANOPTS=

BASEDIR=$(CURDIR)
INPUTDIR=$(BASEDIR)/content
OUTPUTDIR=$(BASEDIR)/output
CONFFILE=$(BASEDIR)/pelicanconf.py
PUBLISHCONF=$(BASEDIR)/publishconf.py
PY_VENV=. $(VENV)/bin/activate

DEBUG ?= 0
ifeq ($(DEBUG), 1)
	PELICANOPTS += -D
endif

RELATIVE ?= 0
ifeq ($(RELATIVE), 1)
	PELICANOPTS += --relative-urls
endif

help:
	@echo 'Makefile for a pelican Web site                                           '
	@echo '                                                                          '
	@echo 'Usage:                                                                    '
	@echo '   make install                        Install dependencies               '
	@echo '   make html                           (re)generate the web site          '
	@echo '   make clean                          remove the generated files         '
	@echo '   make regenerate                     regenerate files upon modification '
	@echo '   make publish                        generate using production settings '
	@echo '   make watch                          serve and rebuild on changes       '
	@echo '                                                                          '
	@echo 'Set the DEBUG variable to 1 to enable debugging, e.g. make DEBUG=1 html   '
	@echo 'Set the RELATIVE variable to 1 to enable relative urls                    '
	@echo '                                                                          '

html: install
	$(PY_VENV) && $(PELICAN) $(INPUTDIR) -o $(OUTPUTDIR) -s $(CONFFILE) $(PELICANOPTS)

clean:
	[ ! -d $(OUTPUTDIR) ] || rm -rf $(OUTPUTDIR)

regenerate: install
	$(PY_VENV) && $(PELICAN) -r $(INPUTDIR) -o $(OUTPUTDIR) -s $(CONFFILE) $(PELICANOPTS)

watch: install
	$(PY_VENV) && $(PELICAN)  $(PELICANOPTS) --relative-urls --listen --autoreload -s $(CONFFILE) $(INPUTDIR) -o $(OUTPUTDIR)

publish: install
	$(PY_VENV) && $(PELICAN) $(INPUTDIR) -o $(OUTPUTDIR) -s $(PUBLISHCONF) $(PELICANOPTS)

pelican-octopress-theme/.git: .gitmodules
	git submodule update --init

submodules: pelican-octopress-theme/.git

$(VENV)/makestamp: requirements.txt
	[ -d $(VENV) ] || $(PY) -m venv $(VENV)
	$(PY_VENV) && pip install -r requirements.txt
	touch $(VENV)/makestamp

venv: $(VENV)/makestamp

install: venv submodules

.PHONY: html help clean install regenerate watch publish venv submodules
