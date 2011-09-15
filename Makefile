NAME = tagboy
TARDIR = ~/dload

# distribution version (no space hogging tests/testdata)
tar:
	eval `grep '^VERSION' tagboy.py`; echo $$VERSION; \
	(cd ..; tar czf $(TARDIR)/$(NAME)-$$VERSION.tgz --exclude-backups \
	$(NAME)/COPYING $(NAME)/*.{py,txt} $(NAME)/tb-*[A-z] $(NAME)/Makefile)

# development version (with tests)
tarall:
	eval `grep '^VERSION' tagboy.py`; echo $$VERSION; \
	(cd ..; tar czf $(TARDIR)/$(NAME)_all-$$VERSION.tgz --exclude-backups \
	$(NAME)/COPYING $(NAME)/*.{py,txt} $(NAME)/tb-*[A-z] $(NAME)/Makefile \
        $(NAME)/tests)
