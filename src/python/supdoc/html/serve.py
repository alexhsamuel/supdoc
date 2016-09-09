import flask
import json
import sys

from   . import gen
from   .. import inspector
from   ..path import Path

#-------------------------------------------------------------------------------

app = flask.Flask(__name__)
docsrc = inspector.DocSource(source=True)

@app.route("/<modname>/<qualname>", methods=("GET", ))
def get_docs(modname, qualname):
    fmt = flask.request.args.get("format", "html")

    path = Path(modname, qualname)
    objdoc = docsrc.get(path)

    if fmt == "html":
        docs = gen.generate(docsrc, objdoc, path)
        return "<!DOCTYPE html>" + str(docs)
    elif fmt == "json":
        return flask.jsonify(objdoc)
    else:
        flask.abort(400)


