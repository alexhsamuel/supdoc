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
module_names = None

# FIXME: Move elsewhere.
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


get_module_docs = memoize(inspector.inspect_module)

class Handler(http.server.SimpleHTTPRequestHandler):

    def send_json(self, jso):
        data = json.dumps(jso).encode("UTF-8")
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Last-Modified", self.date_time_string(time.time()))
        self.end_headers()
        self.wfile.write(data)


    def do_GET(self):
        try:
            if self.path.startswith("/doc/"):
                modname = self.path[5 :]
                if modname == "module-list":
                    logging.info("getting module list")
                    jso = module_names
                else:
                    logging.info("inspecting doc for {}".format(modname))
                    jso = get_module_docs(modname)
                self.send_json(jso)

            elif self.path.startswith("/src/"):
                modname = self.path[5 :]
                logging.info("getting module source")
                jso = inspector.get_module_source(modname)
                self.send_json(jso)

            else:
                super().do_GET()

        except Exception as exc:
            logging.error("problem: {}".format(exc))
            self.send_error(404, "exception: {!r}".format(exc))


    def translate_path(self, path):
        if path.startswith("/supdoc"):
            path = "/index.html"
        new_path = super().translate_path(path)
        return new_path



#-------------------------------------------------------------------------------

list_sum = lambda ls: sum(( list(l) for l in ls ), [])


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    port = 8000
    
    _, *paths = sys.argv
    module_names = list_sum( 
        ( str(n) for n in modules.find_modules(p) ) 
        for p in paths )

    module_names.sort()
    for modname in module_names:
        logging.info("serving module {}".format(modname))

    # Include the standard library.
    module_names.extend( str(n) for n in modules.find_std_modules() )
    logging.info("serving standard library modules")

    server = socketserver.TCPServer(("", port), Handler)
    print("serving from port {}".format(port))
    server.serve_forever()


