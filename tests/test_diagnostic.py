import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from houdini_ai.diagnostic import build_receipt, validate_diagnostic_png, write_receipt


class DiagnosticTests(unittest.TestCase):
    def test_valid_rgba_png_reports_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.png"
            image = Image.new("RGBA", (320, 180), (0, 0, 0, 255))
            image.putpixel((10, 10), (20, 80, 160, 255))
            image.save(path)
            metadata = validate_diagnostic_png(path)
            self.assertEqual(metadata["mode"], "RGBA")
            self.assertEqual((metadata["width"], metadata["height"]), (320, 180))

    def test_invalid_images_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = {
                "wrong-size.png": Image.new("RGBA", (1, 1), (1, 2, 3, 255)),
                "wrong-mode.png": Image.new("RGB", (320, 180), (1, 2, 3)),
                "blank.png": Image.new("RGBA", (320, 180), (1, 1, 1, 255)),
                "transparent.png": Image.new("RGBA", (320, 180), (1, 2, 3, 0)),
            }
            for name, image in cases.items():
                path = root / name
                image.save(path)
                with self.subTest(name=name), self.assertRaises(RuntimeError):
                    validate_diagnostic_png(path)

    @patch("houdini_ai.diagnostic._source_revision", return_value="abc123")
    def test_receipt_is_stable_and_contains_checksums(self, _revision) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            (root / "studies" / "001-memory-field").mkdir(parents=True)
            (root / "config" / "project.json").write_text('{"project":"test"}', encoding="utf-8")
            (root / "studies" / "001-memory-field" / "study.json").write_text(
                '{"schema_version":1}', encoding="utf-8"
            )
            image = root / "image.png"
            hip = root / "scene.hiplc"
            image.write_bytes(b"image")
            hip.write_bytes(b"hip")
            receipt = build_receipt(root, image, hip, {"width": 320}, {"build": "22.0"})
            first = root / "first.json"
            second = root / "second.json"
            write_receipt(first, receipt)
            write_receipt(second, receipt)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            parsed = json.loads(first.read_text(encoding="utf-8"))
            self.assertEqual(parsed["source_revision"], "abc123")
            self.assertEqual(len(parsed["artifacts"]["image"]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
