#!/usr/bin/env python3

import functools
import http.server
import json
import logging
import socketserver
import sys
import time

from   apidoc import modules, inspector

#-------------------------------------------------------------------------------

# FIXME
path = None


def memoize_with(memo=None):
    if memo is None:
        memo = {}

    def memoizer(fn):
        @functools.wraps(fn)
        def memoized(*args, **kw_args):
            # FIXME: Match args to signature first.
            key = (args, tuple(sorted(kw_args.items())))
            try:
                return memo[key]
            except KeyError:
                value = memo[key] = fn(*args, **kw_args)
                return value

        fn.__memo__ = memo
        return memoized

    return memoizer


def memoize(fn):
    return memoize_with({})(fn)


@memoize
def get_module_doc(modname):
    logging.info("inspecting doc for {}".format(modname))
    doc = inspector.inspect_module(modname)
    return json.dumps(doc).encode("UTF-8")


class Handler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        if self.path.startswith("/doc/"):
            try:
                modname = self.path[5 :]
                if modname == "module-list":
                    logging.info("getting module list")
                    names = [ str(n) for n in modules.find_modules(path) ]
                    data = json.dumps(names).encode("UTF-8")
                else:
                    data = get_module_doc(modname)
            except Exception as exc:
                logging.error("problem: {}".format(exc))
                self.send_error(404, "exception: {!r}".format(exc))
            else:
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                logging.info("content-length = {}".format(str(len(data))))
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Last-Modified", self.date_time_string(time.time()))
                self.end_headers()
                self.wfile.write(data)

        else:
            logging.info("starting GET {}".format(self.path))
            super().do_GET()
            logging.info("done with GET {}".format(self.path))


    def translate_path(self, path):
        if path.startswith("/supdoc"):
            path = "/index.html"
        new_path = super().translate_path(path)
        return new_path



#-------------------------------------------------------------------------------

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    port = 8000
    path = sys.argv[1]
    server = socketserver.TCPServer(("", port), Handler)
    print("serving from port {}".format(port))
    server.serve_forever()


