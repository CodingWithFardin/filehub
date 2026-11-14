"""Path containment and Range parsing. Both are security relevant."""
import os
import urllib.parse


class UnsafePath(Exception):
    pass


def safe_join(root, relative):
    """Resolve relative inside root, refusing anything that escapes it."""
    root = os.path.realpath(root)
    decoded = urllib.parse.unquote(relative)
    candidate = os.path.realpath(os.path.join(root, decoded.lstrip("/")))
    if candidate != root and not candidate.startswith(root + os.sep):
        raise UnsafePath("path escapes root: %s" % relative)
    return candidate


def parse_range(header, size):
    """Parse a single-range header into (start, end) inclusive, or None."""
    if not header or not header.startswith("bytes=") or size <= 0:
        return None
    spec = header[6:].strip()
    if "," in spec:
        return None
    start_text, _, end_text = spec.partition("-")
    try:
        if start_text == "":
            length = int(end_text)
            if length <= 0:
                return None
            return max(0, size - length), size - 1
        start = int(start_text)
        end = int(end_text) if end_text else size - 1
    except ValueError:
        return None
    if start < 0 or start >= size or end < start:
        return None
    return start, min(end, size - 1)
