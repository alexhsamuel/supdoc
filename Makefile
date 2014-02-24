include config.mk

# FIXME
.PHONY:	src/js/apidoc.json

all: src/js/apidoc.json

src/js/apidoc.json: src/python/apidoc
		env PYTHONPATH=src/python $(PYTHON) -m apidoc.inspector $^ > $@

