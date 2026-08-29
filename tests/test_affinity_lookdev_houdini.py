import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from houdini_ai.doctor import discover_tools

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/studio/handoffs/study-003-affinity-lookdev-source-400k-v2/nonlocal-affinity-lookdev.hiplc"


class AffinityLookdevHoudiniTests(unittest.TestCase):
    def test_builds_shared_attributes_and_four_non_destructive_looks(self) -> None:
        if not SOURCE.is_file():
            self.skipTest("superseded Look directions were intentionally removed during the Look-pipeline reset")
        hython = next(tool.path for tool in discover_tools() if tool.name == "hython")
        if hython is None:
            self.skipTest("Houdini is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            environment = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "HOUDINI_TEMP_DIR": str(output / "temp")}
            result = subprocess.run(
                [str(hython), str(ROOT / "houdini/build_affinity_lookdev.py"), str(SOURCE), str(output)],
                capture_output=True, text=True, timeout=300, check=False, env=environment,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            audit = json.loads((output / "audit.json").read_text(encoding="utf-8"))
            self.assertEqual(audit["source_point_count"], 400000)
            self.assertEqual(audit["frame"], 201)
            self.assertEqual(audit["source_simstep"], 200)
            self.assertEqual(audit["node_errors"], [])
            self.assertEqual(audit["layout"]["duplicate_node_positions"], [])
            self.assertEqual(audit["layout"]["overlapping_network_boxes"], [])
            self.assertGreaterEqual(audit["layout"]["minimum_node_separation"], 2.0)
            self.assertEqual(
                set(audit["derived_point_attributes"]),
                {
                    "v", "speed", "accel", "heading", "orient", "curvature",
                    "friend_dir", "enemy_dir", "friend_dist", "enemy_dist",
                    "affinity_balance", "social_stress", "local_density",
                    "displacement", "state",
                },
            )
            self.assertEqual(
                set(audit["looks"]),
                {"particle-trails", "affinity-weave", "tension-membrane", "flow-anatomy"},
            )
            for look in audit["looks"].values():
                self.assertGreater(look["primitive_count"], 0)
                self.assertEqual(look["node_errors"], [])
            self.assertTrue((output / "nonlocal-affinity-lookdev-directions.hiplc").is_file())


if __name__ == "__main__":
    unittest.main()
