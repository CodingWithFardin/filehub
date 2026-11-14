"""Threading HTTP server for a single directory."""
import mimetypes
import os
import posixpath
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .paths import UnsafePath, parse_range, safe_join

CHUNK = 64 * 1024


def serve_file(root, relative, range_header=None, token=None, provided=None):
    """Return (status, headers, body_iter) for one file request."""
    if token and provided != token:
        return 401, {"Content-Type": "text/plain"}, [b"unauthorized"]
    try:
        path = safe_join(root, relative)
    except UnsafePath:
        return 403, {"Content-Type": "text/plain"}, [b"forbidden"]
    if os.path.isdir(path):
        listing = sorted(os.listdir(path))
        body = ("\n".join(listing) + "\n").encode()
        return 200, {"Content-Type": "text/plain; charset=utf-8"}, [body]
    if not os.path.isfile(path):
        return 404, {"Content-Type": "text/plain"}, [b"not found"]

    size = os.path.getsize(path)
    ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
    span = parse_range(range_header, size)

    def read(start, length):
        with open(path, "rb") as fh:
            fh.seek(start)
            left = length
            while left > 0:
                block = fh.read(min(CHUNK, left))
                if not block:
                    break
                left -= len(block)
                yield block

    headers = {"Content-Type": ctype, "Accept-Ranges": "bytes"}
    if span:
        start, end = span
        headers["Content-Range"] = "bytes %d-%d/%d" % (start, end, size)
        return 206, headers, read(start, end - start + 1)
    return 200, headers, read(0, size)


def make_server(root, host="127.0.0.1", port=8000, token=None):
    root = os.path.realpath(root)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            relative = urllib.parse.unquote(parsed.path).lstrip("/")
            relative = posixpath.normpath(relative) if relative else ""
            provided = self.headers.get("X-Auth-Token") or ""
            if not provided:
                query = urllib.parse.parse_qs(parsed.query)
                provided = (query.get("token") or [""])[0]
            status, headers, chunks = serve_file(root, relative, self.headers.get("Range"),
                                                 token, provided)
            body = b"".join(chunks)
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

        do_HEAD = do_GET

        def log_message(self, fmt, *args):
            return

    return ThreadingHTTPServer((host, port), Handler)
