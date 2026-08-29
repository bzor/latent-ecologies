import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from houdini_ai.doctor import discover_tools

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/studio/handoffs/study-003-affinity-organism-lookdev-v1/nonlocal-affinity-lookdev-directions.hiplc"


class AffinityKarmaSetupTests(unittest.TestCase):
    def test_builds_backdrop_dome_camera_and_three_look_picker(self) -> None:
        if not SOURCE.is_file():
            self.skipTest("superseded Look directions were intentionally removed during the Look-pipeline reset")
        hython = next(tool.path for tool in discover_tools() if tool.name == "hython")
        if hython is None:
            self.skipTest("Houdini is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            environment = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "HOUDINI_TEMP_DIR": str(output / "temp")}
            result = subprocess.run(
                [str(hython), str(ROOT / "houdini/setup_affinity_karma.py"), str(SOURCE), str(output), "--skip-render"],
                capture_output=True, text=True, timeout=300, check=False, env=environment,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            audit = json.loads((output / "audit.json").read_text(encoding="utf-8"))
            self.assertTrue(audit["source_artist_edit_preserved"])
            self.assertEqual(audit["picker_labels"], ["Particle Organisms + Trails", "Affinity Weave", "Tension Membrane"])
            self.assertEqual(audit["picker_values"], [0, 1, 2])
            self.assertEqual(audit["stage_nodes"], [
                "IMPORT_SELECTED_LOOK", "IMPORT_BACKDROP", "MERGE_LOOK_AND_ENVIRONMENT",
                "LIGHT_DOME", "CAM_REVIEW", "RENDER_KARMA_SETTINGS", "OUT_KARMA",
            ])
            self.assertEqual(audit["node_errors"], [])
            self.assertEqual(audit["layout"]["overlapping_network_boxes"], [])
            self.assertTrue((output / "nonlocal-affinity-karma-lookdev.hiplc").is_file())


if __name__ == "__main__":
    unittest.main()
