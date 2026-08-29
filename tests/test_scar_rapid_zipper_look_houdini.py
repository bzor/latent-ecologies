from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class ScarRapidZipperLookHoudiniTests(unittest.TestCase):
    def test_builds_basic_template_with_point_instancer_and_edge_basis_curves(self) -> None:
        root = Path(__file__).resolve().parents[1]
        hython = Path("C:/Program Files/Side Effects Software/Houdini 22.0.368/bin/hython.exe")
        if not hython.is_file():
            self.skipTest("Houdini 22.0.368 Hython is unavailable")
        builder = root / "houdini/build_scar_rapid_zipper_look_starter.py"
        selection = root / "studies/study_002_scar-tissue/01_behavior/03_selected/selection_002"
        template = root / "houdini/look_setups/basic/basic.hiplc"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "var_004_rapid-surgical-zipper.look_r001.hiplc"
            receipt = output.with_suffix(".starter-receipt.json")
            result = subprocess.run(
                [
                    str(hython), str(builder), "build",
                    "--selection", str(selection),
                    "--template", str(template),
                    "--output", str(output),
                    "--receipt", str(receipt),
                ],
                capture_output=True, text=True, timeout=240, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(output.is_file())
            data = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertTrue(data["passed"])
            self.assertEqual(data["source_component_id"], "component-behavior-4d1068fdc350")
            self.assertEqual(data["timeline"], {"fps": 30.0, "frame_range": [1, 300], "duration_seconds": 10.0})
            self.assertEqual(data["source_geometry"], {"points": 256, "edge_primitives": 384})
            self.assertEqual(data["render_geometry"]["point_instances"], 256)
            self.assertEqual(data["render_geometry"]["edge_polylines"], 384)
            self.assertIn("PointInstancer", data["usd_primitive_types"])
            self.assertIn("BasisCurves", data["usd_primitive_types"])
            self.assertEqual(data["active_cache_ancestor"], "/obj/PLAYGROUND_SIM/SOURCE_PROMOTED_SIMULATION")
            self.assertEqual(data["verified_frame_count"], 300)
            self.assertGreaterEqual(data["camera"]["fstop"], 8.0)
            self.assertGreaterEqual(data["camera"]["focus"], 15.0)
            self.assertGreaterEqual(abs(data["camera"]["rotation_y"]), 20.0)
            self.assertFalse(data["render_configuration"]["depth_of_field_enabled"])
            self.assertGreaterEqual(data["environment"]["floor_size"][0], 100.0)
            self.assertGreaterEqual(data["environment"]["floor_size"][1], 100.0)
            self.assertEqual(data["control_defaults"], {"point_radius": 0.028, "bank_width": 0.012, "zipper_width": 0.008})
            self.assertEqual(data["node_errors"], [])


if __name__ == "__main__":
    unittest.main()
