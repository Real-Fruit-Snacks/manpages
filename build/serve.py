#!/usr/bin/env python3
"""Dev server for docs/: http.server with Cache-Control: no-cache so the
browser always revalidates (python's default emits only Last-Modified,
which lets Chrome serve stale JS/CSS from its heuristic cache)."""
import http.server
import sys


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8321
    directory = sys.argv[2] if len(sys.argv) > 2 else 'docs'
    handler = lambda *a, **kw: NoCacheHandler(*a, directory=directory, **kw)
    http.server.ThreadingHTTPServer(('127.0.0.1', port), handler).serve_forever()
