# FIXME
.PHONY:	src/js/apidoc.json

all: src/js/apidoc.json

src/js/apidoc.json: src/python/apidoc
		python3 -m apidoc.inspector $^ > $@

