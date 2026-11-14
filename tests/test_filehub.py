import os
import tempfile
import unittest

from filehub.paths import UnsafePath, parse_range, safe_join
from filehub.server import serve_file


class RangeTest(unittest.TestCase):
    def test_full_and_partial(self):
        self.assertEqual(parse_range("bytes=0-3", 10), (0, 3))
        self.assertEqual(parse_range("bytes=5-", 10), (5, 9))
        self.assertEqual(parse_range("bytes=-4", 10), (6, 9))

    def test_out_of_bounds_is_ignored(self):
        self.assertIsNone(parse_range("bytes=20-30", 10))
        self.assertIsNone(parse_range("bytes=3-1", 10))
        self.assertIsNone(parse_range("bytes=0-1,3-4", 10))

    def test_garbage(self):
        for header in ("", "items=0-1", "bytes=abc-def", None):
            self.assertIsNone(parse_range(header, 10))
        self.assertIsNone(parse_range("bytes=0-1", 0))


class PathTest(unittest.TestCase):
    def test_inside_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "a", "b.txt")
            os.makedirs(os.path.dirname(target))
            open(target, "w").write("x")
            self.assertEqual(safe_join(tmp, "a/b.txt"), os.path.realpath(target))

    def test_escape_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            for attempt in ("../etc/passwd", "a/../../x", "..%2f.."):
                with self.assertRaises(UnsafePath):
                    safe_join(tmp, attempt)

    def test_absolute_path_is_contained(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(safe_join(tmp, "/a.txt"),
                             os.path.realpath(os.path.join(tmp, "a.txt")))


class ServeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "data.txt")
        open(self.path, "wb").write(b"0123456789")

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_file(self):
        status, headers, chunks = serve_file(self.tmp.name, "data.txt")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"].split(";")[0], "text/plain")
        self.assertEqual(b"".join(chunks), b"0123456789")

    def test_range_response(self):
        status, headers, chunks = serve_file(self.tmp.name, "data.txt", "bytes=2-5")
        self.assertEqual(status, 206)
        self.assertEqual(headers["Content-Range"], "bytes 2-5/10")
        self.assertEqual(b"".join(chunks), b"2345")

    def test_token_required(self):
        status, _, _ = serve_file(self.tmp.name, "data.txt", token="secret", provided="")
        self.assertEqual(status, 401)
        status, _, _ = serve_file(self.tmp.name, "data.txt", token="secret", provided="secret")
        self.assertEqual(status, 200)

    def test_escape_is_forbidden(self):
        status, _, _ = serve_file(self.tmp.name, "../data.txt")
        self.assertEqual(status, 403)

    def test_missing(self):
        status, _, _ = serve_file(self.tmp.name, "nope.txt")
        self.assertEqual(status, 404)

    def test_directory_listing(self):
        status, headers, chunks = serve_file(self.tmp.name, "")
        self.assertEqual(status, 200)
        self.assertIn(b"data.txt", b"".join(chunks))


if __name__ == "__main__":
    unittest.main()
