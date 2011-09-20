NAME = tagboy
TARDIR = ~/dload
PREFIX = /usr/local

.PHONY: tar, tarall, check, install

# Install on system (run under sudo)
install:
	cp tagboy $(PREFIX)/bin/
	cp tagboy.1 $(PREFIX)/share/man/man1/

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
