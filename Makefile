NAME = tagboy
TARDIR = ~/dload

.PHONY: tar, tarall, check

# distribution version (no space hogging tests/testdata)
tar:
	eval `grep '^VERSION' tagboy.py`; echo $$VERSION; \
	(cd ..; tar czf $(TARDIR)/$(NAME)-$$VERSION.tgz --exclude-backups \
	$(NAME)/COPYING $(NAME)/*.{py,txt,1} $(NAME)/tb-*[A-z])

# development version (with tests)
tarall:
	eval `grep '^VERSION' tagboy.py`; echo $$VERSION; \
	(cd ..; tar czf $(TARDIR)/$(NAME)_all-$$VERSION.tgz --exclude-backups \
	$(NAME)/COPYING $(NAME)/*.{py,txt,1} $(NAME)/tb-*[A-z] \
        $(NAME)/Makefile $(NAME)/tests/*test.py \
	$(NAME)/tests/testdata/*.{jpg,JPG} $(NAME)/tests/testdata/*.{py,sh} )

check:
	-for f in tests/*test.py ; do echo ==== $$f; PYTHONPATH=. $$f; done
