# filehub

A static file server with token auth, HTTP range requests and path containment that
is actually checked. Meant for handing a build directory or a set of reports to a
few people without exposing the rest of the disk.

## Install

Python 3.11+, no dependencies.

```
git clone https://github.com/CodingWithFardin/filehub.git
cd filehub
python -m unittest discover -s tests -t .
python -m filehub.server --root ./public --port 8080 --token s3cret
```

Then:

```
curl -H 'X-Auth-Token: s3cret' localhost:8080/report.pdf -o report.pdf
curl -r 0-1023 -H 'X-Auth-Token: s3cret' localhost:8080/report.pdf -o head.bin
```

The token can also arrive as `?token=s3cret`, which is convenient for browsers and
worse for logs; pick one and be consistent.

## Security properties

- Every request path is URL-decoded, joined to the root, and resolved with
  `realpath` before the containment check, so `..`, encoded `%2e%2e`, and symlinks
  that point outside the root are all refused with 403.
- Absolute paths are treated as root-relative, never as filesystem-absolute.
- Directories are listed, not executed; there is no index handler and no upload path.
- With `--token` unset the server is open, which is only sensible behind a firewall.

## Range requests

A single `Range: bytes=a-b`, `bytes=a-`, or `bytes=-n` is honoured with a 206 and a
correct `Content-Range`. Multi-range requests fall back to a full 200 rather than a
hand-rolled multipart body.

## Files

- `filehub/paths.py` - containment and range parsing, both security relevant.
- `filehub/server.py` - request handler and streaming reads.
- `tests/` - escape attempts, ranges, auth and listing.

MIT, 2026.
