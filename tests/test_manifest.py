import json
import tempfile
import unittest
from pathlib import Path

from houdini_ai.cli import ROOT, validate_manifest


class ManifestTests(unittest.TestCase):
    def validate_data(self, data: object) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "study.json"
            manifest.write_text(json.dumps(data), encoding="utf-8")
            return validate_manifest(manifest)

    def test_study_001_is_valid(self) -> None:
        manifest = ROOT / "studies" / "001-memory-field" / "study.json"
        self.assertEqual(validate_manifest(manifest), [])

    def test_publication_requires_approval(self) -> None:
        source = ROOT / "studies" / "001-memory-field" / "study.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        data["publication"]["approval_required"] = False
        errors = self.validate_data(data)
        self.assertTrue(any("approval_required" in error for error in errors))

    def test_malformed_root_and_nested_values_return_errors(self) -> None:
        for data in ([], None, {"render": None}, {"simulation": {"frame_start": "one", "frame_end": []}}):
            with self.subTest(data=data):
                self.assertTrue(self.validate_data(data))

    def test_frame_end_cannot_precede_start(self) -> None:
        source = ROOT / "studies" / "001-memory-field" / "study.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        data["simulation"]["frame_start"] = 10
        data["simulation"]["frame_end"] = 9
        self.assertIn("simulation.frame_end must not precede frame_start", self.validate_data(data))

    def test_unknown_fields_are_rejected(self) -> None:
        source = ROOT / "studies" / "001-memory-field" / "study.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        data["unexpected"] = True
        self.assertTrue(any("Additional properties" in error for error in self.validate_data(data)))


if __name__ == "__main__":
    unittest.main()

