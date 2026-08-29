import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from houdini_ai.review_studio import make_handler


class OverlayServingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        (root / "website").mkdir()
        (root / "website" / "index.html").write_text("studio", encoding="utf-8")
        web = root / "design-overlay-generator" / "web"
        web.mkdir(parents=True)
        (web / "index.html").write_text("<title>overlay</title>", encoding="utf-8")
        (web / "app.js").write_text("// app", encoding="utf-8")
        renders = root / "studies" / "study_777_thing" / "02_look" / "renders"
        renders.mkdir(parents=True)
        (renders / "look.0207.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
        (root / "secret.txt").write_text("private", encoding="utf-8")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(root))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.directory.cleanup()

    def get(self, path: str) -> tuple[int, bytes]:
        try:
            with urllib.request.urlopen(self.base + path) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()

    def test_overlay_app_is_served(self) -> None:
        status, body = self.get("/overlay/")
        self.assertEqual(status, 200)
        self.assertIn(b"overlay", body)
        self.assertEqual(self.get("/overlay")[0], 200)
        self.assertEqual(self.get("/overlay/app.js")[0], 200)

    def test_overlay_media_serves_study_files_only(self) -> None:
        status, body = self.get("/overlay-media/studies/study_777_thing/02_look/renders/look.0207.png")
        self.assertEqual(status, 200)
        self.assertTrue(body.startswith(b"\x89PNG"))

        for escape in (
            "/overlay-media/secret.txt",
            "/overlay-media/studies/../secret.txt",
            "/overlay-media/website/index.html",
            "/overlay/../../secret.txt",
            "/overlay/%2e%2e/%2e%2e/secret.txt",
        ):
            status, body = self.get(escape)
            self.assertEqual(status, 404, escape)
            self.assertNotIn(b"private", body, escape)

    def test_review_site_untouched(self) -> None:
        status, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"studio")

    def test_overlay_csp_allows_inline_styles_and_blob_media(self) -> None:
        with urllib.request.urlopen(self.base + "/overlay/") as response:
            overlay_csp = response.headers.get("Content-Security-Policy", "")
        self.assertIn("'unsafe-inline'", overlay_csp)
        self.assertIn("blob:", overlay_csp)
        with urllib.request.urlopen(self.base + "/") as response:
            site_csp = response.headers.get("Content-Security-Policy", "")
        self.assertNotIn("'unsafe-inline'", site_csp)
        self.assertNotIn("blob:", site_csp)


if __name__ == "__main__":
    unittest.main()
