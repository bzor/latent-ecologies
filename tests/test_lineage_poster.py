import tempfile
import unittest
from pathlib import Path

from PIL import Image

from houdini_ai import lineage_poster as lp

try:
    CHROME = lp._discover_chrome()
except FileNotFoundError:
    CHROME = None


def sample_spec(plate: Path | None = None) -> dict:
    spec = {
        "study": {"number": 7, "title": "Test Study", "subtitle": "a <test> subtitle", "completed": "2026-08-31"},
        "palette": {"ground": "#b4b5b7", "ink": "#2f183c", "accent": "#c76666"},
        "stages": [
            {"label": "BEHAVIOR", "gate": True, "hash": "abc1234", "facts": ["seed 1 & 2"]},
            {"label": "PACKAGE", "date": "2026-08-31", "facts": ["done"]},
        ],
        "footer": ["LINE ONE"],
    }
    if plate is not None:
        spec["plate"] = {"image": str(plate), "caption": "PLATE"}
    return spec


class SpecValidationTests(unittest.TestCase):
    def test_valid_spec_passes(self) -> None:
        self.assertEqual(lp.validate_spec(sample_spec()), [])

    def test_missing_fields_are_reported(self) -> None:
        errors = lp.validate_spec({"study": {}, "palette": {}, "stages": []})
        self.assertTrue(any("study.number" in error for error in errors))
        self.assertTrue(any("palette.ground" in error for error in errors))
        self.assertTrue(any("stages" in error for error in errors))

    def test_missing_plate_image_is_rejected(self) -> None:
        spec = sample_spec()
        spec["plate"] = {"image": "does-not-exist.png"}
        self.assertTrue(any("plate.image" in error for error in lp.validate_spec(spec)))


class PosterHtmlTests(unittest.TestCase):
    def test_html_carries_escaped_facts_and_padded_number(self) -> None:
        html_text = lp.build_poster_html(sample_spec())
        self.assertIn(">007<", html_text)
        self.assertIn("TEST STUDY", html_text)
        self.assertIn("a &lt;test&gt; subtitle", html_text)
        self.assertIn("seed 1 &amp; 2", html_text)
        self.assertIn("abc1234", html_text)
        self.assertIn("node gate", html_text)


@unittest.skipUnless(CHROME, "Chrome is not available")
class PosterRenderTests(unittest.TestCase):
    def test_renders_at_declared_size_with_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plate = root / "plate.png"
            Image.new("RGB", (108, 135), (60, 60, 70)).save(plate)
            receipt = lp.render_poster(sample_spec(plate), root / "poster.png", scale=1)
            with Image.open(root / "poster.png") as image:
                self.assertEqual(image.size, tuple(lp.POSTER_SIZE))
            self.assertTrue((root / "poster.receipt.json").is_file())
            self.assertEqual(receipt["size"], [lp.POSTER_SIZE[0], lp.POSTER_SIZE[1]])


if __name__ == "__main__":
    unittest.main()
