#!/usr/bin/env python3

import http.server
import socketserver

#-------------------------------------------------------------------------------

class Handler(http.server.SimpleHTTPRequestHandler):

    n = 0

    def translate_path(self, path):
        if path.startswith("/apyi"):
            path = "/apyi.html"
        new_path = super().translate_path(path)
        return new_path



#-------------------------------------------------------------------------------

if __name__ == "__main__":
    port = 8000
    server = socketserver.TCPServer(("", port), Handler)
    server.serve_forever()


