import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from houdini_ai.lookdev_lab import build_lookdev_probes


class LookdevLabTests(unittest.TestCase):
    def test_builds_three_distinct_looks_from_promoted_behavior(self) -> None:
        root = Path(__file__).resolve().parents[1]
        behavior = {
            "id": "component-behavior-test",
            "component_kind": "behavior",
            "state": "promoted",
            "content_hash": "sha256:" + "a" * 64,
        }
        metrics = json.loads(
            (root / "work/studio/probes/scar-tissue/directional-refractory-v3/metrics.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = build_lookdev_probes(behavior, metrics, output, size=(360, 540))
            self.assertEqual(set(result["looks"]), {"fibrous-memory", "etched-substrate", "membrane-stress"})
            digests = set()
            for look, relative in result["looks"].items():
                path = output / relative
                image = Image.open(path)
                self.assertEqual(image.size, (360, 540), look)
                self.assertGreater(len(image.getcolors(maxcolors=360 * 540)), 12, look)
                digests.add(hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(len(digests), 3)
            self.assertTrue((output / "comparison.png").is_file())
            self.assertTrue((output / "receipt.json").is_file())

    def test_rejects_unpromoted_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "promoted behavior"):
                build_lookdev_probes({"component_kind": "look", "state": "promoted"}, {"review": []}, Path(directory))


if __name__ == "__main__":
    unittest.main()