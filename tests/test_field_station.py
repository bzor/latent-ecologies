import tempfile
import unittest
from pathlib import Path

from houdini_ai.field_station import build_field_note, build_index


class FieldStationTests(unittest.TestCase):
    def test_build_index_links_projected_field_notes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            index = build_index(
                [
                    {"id": "scar-tissue", "title": "Scar Tissue", "summary": "Path memory."},
                    {"id": "mass-flow", "title": "Mass Flow", "summary": "Prototype archive."},
                ],
                output,
            )
            text = index.read_text(encoding="utf-8")
            self.assertIn('href="scar-tissue.html"', text)
            self.assertIn("Prototype archive.", text)

    def test_build_field_note_labels_claims_and_escapes_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            page = build_field_note(
                {
                    "id": "scar-tissue",
                    "title": "Scar <Tissue>",
                    "summary": "A field becomes memory.",
                    "license": "CC-BY-NC-SA-4.0",
                    "artifacts": [
                        {
                            "id": "loop",
                            "path": "media/scar-loop.mp4",
                            "sha256": "a" * 64,
                            "role": "field-observation",
                            "download": False,
                        }
                    ],
                    "claims": [
                        {"status": "measured", "text": "Peak saturation reached 0.84."},
                        {"status": "hypothesized", "text": "Dormancy may preserve corridors."},
                    ],
                },
                output,
            )
            text = page.read_text(encoding="utf-8")
            self.assertIn("Scar &lt;Tissue&gt;", text)
            self.assertIn("MEASURED", text)
            self.assertIn("HYPOTHESIZED", text)
            self.assertIn("media/scar-loop.mp4", text)
            self.assertNotIn("Scar <Tissue>", text)

    def test_build_field_note_rejects_unsafe_artifact_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "relative"):
                build_field_note(
                    {
                        "id": "unsafe",
                        "title": "Unsafe",
                        "summary": "No.",
                        "license": "private",
                        "artifacts": [{"id": "x", "path": "../secret", "sha256": "a" * 64, "role": "x"}],
                        "claims": [],
                    },
                    Path(directory),
                )

    def test_build_field_note_rejects_traversal_record_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            with self.assertRaisesRegex(ValueError, "relative"):
                build_field_note({"id": "../escaped", "artifacts": [], "claims": []}, output)
            self.assertFalse((Path(directory) / "escaped.html").exists())


if __name__ == "__main__":
    unittest.main()
