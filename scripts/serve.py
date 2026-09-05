#!/usr/bin/env python3
"""
scripts/serve.py - Local development server that automatically binds to IPv4 (127.0.0.1)
and opens your default web browser.
"""

import http.server
import threading
import time
import webbrowser
from pathlib import Path

PORT = 8080
HOST = "127.0.0.1"

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        directory = "dist" if Path("dist/index.html").exists() else "."
        super().__init__(*args, directory=directory, **kwargs)

def open_browser():
    time.sleep(0.8)
    url = f"http://{HOST}:{PORT}/"
    print(f"Opening browser at: {url}")
    webbrowser.open(url)

def main():
    threading.Thread(target=open_browser, daemon=True).start()
    with http.server.ThreadingHTTPServer((HOST, PORT), CustomHandler) as httpd:
        print(f"Serving at http://{HOST}:{PORT}/ (Press Ctrl+C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")

if __name__ == "__main__":
    main()
