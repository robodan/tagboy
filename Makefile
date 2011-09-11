NAME = tagboy
TARDIR = ~/dload

tar:
	eval `grep '^VERSION' tagboy.py`; echo $$VERSION; \
	(cd ..; tar czf $(TARDIR)/$(NAME)-$$VERSION.tgz $(NAME)/*.{py,txt} $(NAME)/Makefile $(NAME)/tests)
