import hashlib
import json
import os
import subprocess
import unittest
from pathlib import Path

from houdini_ai.doctor import discover_tools

ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "studies/study_003_nonlocal-affinity-dance/01_behavior/03_selected/selection_002"
SOURCE = SELECTION / "look-source.json"
RECEIPT = SELECTION / "cache_sequence/receipt.json"


# The selection caches are local-only vault data (gitignored under 03_selected/);
# skip on checkouts without them instead of failing the suite.
@unittest.skipUnless(
    SELECTION.is_dir(),
    "study_003 03_selected caches are not present in this checkout",
)
class AffinitySelectedCacheSequenceTests(unittest.TestCase):
    def test_selected_cache_sequence_is_contiguous_and_houdini_readable(self) -> None:
        self.assertTrue(SOURCE.is_file(), f"missing {SOURCE}")
        self.assertTrue(RECEIPT.is_file(), f"missing {RECEIPT}")
        source = json.loads(SOURCE.read_text(encoding="utf-8"))
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        paths = [ROOT / path for path in source["cache_paths"]]
        component = json.loads((SELECTION / "component.json").read_text(encoding="utf-8"))
        self.assertEqual(source["id"], component["id"])
        self.assertEqual(source["state"], "promoted")
        self.assertEqual(len(paths), 450)
        self.assertEqual([int(path.name.split(".")[1]) for path in paths], list(range(201, 651)))
        self.assertEqual(receipt["frame_range"], [201, 650])
        self.assertEqual(receipt["simulation_step_range"], [200, 649])
        self.assertEqual(receipt["frame_to_simulation_step"], "frame - 1")
        self.assertEqual(receipt["agent_count"], 100000)
        self.assertEqual(receipt["state_authority"], "vex-geometry")
        self.assertEqual(receipt["identity"], "stable point number with constant 100000-point topology")
        self.assertEqual(receipt["point_attributes"], ["P", "enemy", "friend"])
        self.assertEqual(receipt["vex_errors"], [])
        self.assertTrue(receipt["original_240_step_schedule_is_exact_prefix"])
        self.assertEqual(receipt["last_visible_scheduled_rewire_frame"], 650)
        self.assertEqual(receipt["final_state_sha256"], "bf529ba28aa2725a5f7de54b81d4dd985b111c2d96f09daf8a273d31ac7753b3")
        self.assertEqual(len(receipt["cache_files"]), 450)
        for path, record in zip(paths, receipt["cache_files"]):
            self.assertTrue(path.is_file(), path)
            self.assertEqual(path.stat().st_size, record["bytes"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record["sha256"])

        hython = next(tool.path for tool in discover_tools() if tool.name == "hython")
        verifier = ROOT / "houdini/verify_affinity_behavior_cache.py"
        environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        result = subprocess.run(
            [str(hython), str(verifier), str(SOURCE), "--sample-only"],
            capture_output=True, text=True, timeout=300, check=False, env=environment,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        audit = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(audit["checked_frames"], [201, 426, 650])
        self.assertEqual(audit["point_counts"], [100000, 100000, 100000])
        self.assertEqual(audit["errors"], [])


if __name__ == "__main__":
    unittest.main()
