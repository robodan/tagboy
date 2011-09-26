NAME = tagboy
TARDIR = ~/dload
PREFIX = /usr/local
INSTALL = install

.PHONY: tar tarall check
.PHONY: install install-bin install-man

# Install on system (run under sudo)
install:	install-bin install-man

install-bin:
	$(INSTALL) -v -m 755 tagboy $(PREFIX)/bin/

install-man:
	$(INSTALL) -v -m 644 tagboy.1 $(PREFIX)/share/man/man1/

# Build tarball for distribution (no space hogging tests/testdata)
tar:
	eval `grep '^VERSION' tagboy.py`; echo $$VERSION; \
	(cd ..; tar czf $(TARDIR)/$(NAME)-$$VERSION.tgz --exclude-backups \
	$(NAME)/COPYING $(NAME)/*.{py,txt,1} $(NAME)/tb-*[A-z] \
	$(NAME)/Makefile)

# Build tarball for development (with tests)
tarall:
	eval `grep '^VERSION' tagboy.py`; echo $$VERSION; \
	(cd ..; tar czf $(TARDIR)/$(NAME)_all-$$VERSION.tgz --exclude-backups \
	$(NAME)/COPYING $(NAME)/*.{py,txt,1} $(NAME)/tb-*[A-z] \
        $(NAME)/Makefile $(NAME)/tests/*test.py \
	$(NAME)/tests/testdata/*.{jpg,JPG} $(NAME)/tests/testdata/*.{py,sh} )

# Run all tests
check:
	-for f in tests/*test.py ; do echo ==== $$f; PYTHONPATH=. $$f; done
