SHELL := /bin/bash
NAME = tagboy
TARDIR = ~/Downloads
PREFIX = /usr/local
INSTALL = install

.PHONY: tar tarall check check-py check-sh
.PHONY: install install-bin install-man

# Install on system (run under sudo)
install:	install-bin install-man

install-bin:	tagboy.pex
	$(INSTALL) -v -m 755 tagboy.pex $(PREFIX)/bin/tagboy

install-man:
	$(INSTALL) -v -m 644 tagboy.1 $(PREFIX)/share/man/man1/

# Make an executable, zipped form of the program
# Could use pex to build this, but choose to just do it by hand
tagboy.pex:	Makefile __main__.py \
	tagboy/tbcmd.py tagboy/tbutil.py tagboy/tbcore.py tagboy/__init__.py
	(tmp=._tb.zip; \
	zip $$tmp $(filter %.py,$^) \
	&& ((echo '#!/usr/bin/env python2'; cat $$tmp) > $@) \
	&& rm -f $$tmp \
	&& chmod +x $@)

# Build tarball for distribution (no space hogging tests/testdata)
tar:
	eval `grep '^VERSION' tagboy/tbcmd.py`; echo $$VERSION; \
	(cd ..; tar czf $(TARDIR)/$(NAME)-$$VERSION.tgz --exclude-backups \
	$(NAME)/COPYING $(NAME)/*.{py,txt,1} $(NAME)/tagboy/*.py $(NAME)/tb-*[A-z] \
	$(NAME)/Makefile)

# Build tarball for development (with tests)
tarall:
	eval `grep '^VERSION' tagboy/tbcmd.py`; echo $$VERSION; \
	(cd ..; tar czf $(TARDIR)/$(NAME)_all-$$VERSION.tgz --exclude-backups \
	$(NAME)/COPYING $(NAME)/*.{py,txt,1} $(NAME)/tagboy/*.py $(NAME)/tb-*[A-z] \
        $(NAME)/Makefile $(NAME)/tests/*test.{py,sh} \
	$(NAME)/tests/testdata/*.{jpg,JPG} $(NAME)/tests/testdata/*.{py,sh} )

# Run all tests
check:	check-py check-sh

check-py:
	-for f in tests/*test.py ; do echo ==== $$f; PYTHONPATH=. $$f; done

check-sh:
	-for f in tests/*test.sh ; do echo ==== $$f; PYTHONPATH=. $$f; done
