#!/usr/bin/env python3
"""Dev-only static server for previewing webui/ with correct MIME types.

Usage: python tests/serve_webui.py [port]
Then open http://127.0.0.1:8022/webui/index.html?mock=1
"""
import sys
import http.server
import socketserver
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        '.js': 'text/javascript',
        '.mjs': 'text/javascript',
        '.css': 'text/css',
        '.json': 'application/json',
    }

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, *a):
        pass

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8022
    with socketserver.TCPServer(('127.0.0.1', port), Handler) as httpd:
        print(f'serving {ROOT} at http://127.0.0.1:{port}/webui/index.html?mock=1')
        httpd.serve_forever()
