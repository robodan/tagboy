SHELL := /bin/bash
NAME = tagboy
TARDIR = ~/Downloads
PREFIX = /usr/local
INSTALL = install

.PHONY: tar tarall check check-py check-sh
.PHONY: install install-bin install-man

# Install on system (run under sudo)
install:	install-bin install-man

# TODO: package util.py as an egg (or equivalent)
install-bin:
	$(INSTALL) -v -m 755 tagboy $(PREFIX)/bin/

install-man:
	$(INSTALL) -v -m 644 tagboy.1 $(PREFIX)/share/man/man1/

# BROKEN, do not use
tagboy.pex:	tagboy.py util.py Makefile
	pex -o $? --python=/usr/bin/python2 -c tagboy -- tagboy.py util.py

# Build tarball for distribution (no space hogging tests/testdata)
tar:
	eval `grep '^VERSION' tagboy/tbcmd.py`; echo $$VERSION; \
	(cd ..; tar czf $(TARDIR)/$(NAME)-$$VERSION.tgz --exclude-backups \
	$(NAME)/COPYING $(NAME)/*.{py,txt,1} $(NAME)/tb-*[A-z] \
	$(NAME)/Makefile)

# Build tarball for development (with tests)
tarall:
	eval `grep '^VERSION' tagboy/tbcmd.py`; echo $$VERSION; \
	(cd ..; tar czf $(TARDIR)/$(NAME)_all-$$VERSION.tgz --exclude-backups \
	$(NAME)/COPYING $(NAME)/*.{py,txt,1} $(NAME)/tb-*[A-z] \
        $(NAME)/Makefile $(NAME)/tests/*test.{py,sh} \
	$(NAME)/tests/testdata/*.{jpg,JPG} $(NAME)/tests/testdata/*.{py,sh} )

# Run all tests
check:	check-py check-sh

check-py:
	-for f in tests/*test.py ; do echo ==== $$f; PYTHONPATH=. $$f; done

check-sh:
	-for f in tests/*test.sh ; do echo ==== $$f; PYTHONPATH=. $$f; done
