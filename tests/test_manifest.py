import json
import tempfile
import unittest
from pathlib import Path

from houdini_ai.cli import ROOT, validate_manifest


class ManifestTests(unittest.TestCase):
    def test_study_001_is_valid(self) -> None:
        manifest = ROOT / "studies" / "001-memory-field" / "study.json"
        self.assertEqual(validate_manifest(manifest), [])

    def test_publication_requires_approval(self) -> None:
        source = ROOT / "studies" / "001-memory-field" / "study.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        data["publication"]["approval_required"] = False
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "study.json"
            manifest.write_text(json.dumps(data), encoding="utf-8")
            self.assertIn(
                "publication.approval_required must be true in the initial scaffold",
                validate_manifest(manifest),
            )


if __name__ == "__main__":
    unittest.main()

