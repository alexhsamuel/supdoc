import flask
import sys

from   . import gen
from   .. import inspector
from   ..path import Path

#-------------------------------------------------------------------------------

app = flask.Flask(__name__)
docsrc = inspector.DocSource(source=True)

@app.route("/<modname>/<qualname>", methods=("GET", ))
def get_docs(modname, qualname):
    path = Path(modname, qualname)
    objdoc = docsrc.get(path)
    docs = gen.generate(docsrc, objdoc, path)
    return "<!DOCTYPE html>" + str(docs)


if __name__ == "__main__":
    import logging
    logging.getLogger().setLevel(logging.DEBUG)

    app.run()


