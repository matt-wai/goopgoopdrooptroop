"""Static file server for the GoopGoopDroopTroop web frontend.

Serves docs/ on port 9500 by default.

Usage:
    ggdt-frontend
    ggdt-frontend --port 9500 --host 0.0.0.0
"""

from __future__ import annotations

import argparse
import http.server
import logging
import os
from pathlib import Path

log = logging.getLogger("ggdt.frontend")

DOCS_DIR = Path(__file__).parent.parent / "docs"


def main():
    parser = argparse.ArgumentParser(description="GoopGoopDroopTroop web frontend server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=9500, help="Bind port (default: 9500)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(message)s")

    if not DOCS_DIR.exists():
        log.error(f"docs/ directory not found at {DOCS_DIR}")
        raise SystemExit(1)

    os.chdir(DOCS_DIR)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, fmt, *a):
            if args.verbose:
                log.debug(fmt % a)

    log.info(f"Serving frontend from {DOCS_DIR}")
    log.info(f"Open http://localhost:{args.port} in your browser")
    with http.server.HTTPServer((args.host, args.port), Handler) as httpd:
        httpd.serve_forever()
