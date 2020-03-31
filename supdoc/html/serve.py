"""
Flask web server for supdoc documentation.

Invoke `bin/supdoc-serve` to start the server.
"""

#-------------------------------------------------------------------------------

import flask

from   supdoc import inspector
from   supdoc.path import Path
from   . import gen

#-------------------------------------------------------------------------------

DEFAULT_PORT = 5050

app = flask.Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 300

docsrc = inspector.DocSource()

@app.route("/favicon.ico/", methods=("GET", ))
def get_favicon():
    """
    Serves the application icon.
    """
    return app.send_static_file("favicon.png")


@app.route("/<modname>", methods=("GET", ))
@app.route("/<modname>/", methods=("GET", ))
@app.route("/<modname>/<qualname>", methods=("GET", ))
def get_docs(modname, qualname=None):
    """
    Serves documentation.
    """
    fmt = flask.request.args.get("format", "html")

    path = Path(modname, qualname)

    # FIXME: Handle exceptions.
    objdoc = docsrc.get(path)

    if fmt == "html":
        try:
            docs = gen.generate(docsrc, objdoc, path)
        except gen.Redirect as redirect:
            return flask.redirect(redirect.url, code=302)
        else:
            return "<!DOCTYPE html>\n" + str(docs)
    elif fmt == "json":
        return flask.jsonify(objdoc)
    else:
        flask.abort(400)


