from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from houdini_ai.doctor import discover_tools
from houdini_ai.look_execution import make_hython_playground_builder


class LookPlaygroundHoudiniTests(unittest.TestCase):
    def test_builds_and_freshly_verifies_real_karma_playground(self) -> None:
        hython = next((tool.path for tool in discover_tools() if tool.name == "hython"), None)
        if hython is None:
            self.skipTest("Hython is not installed")
        repository = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "houdini").mkdir()
            shutil.copy2(repository / "houdini/build_look_playground.py", root / "houdini")
            cache_dir = root / "cache"
            cache_dir.mkdir()
            cache_path = cache_dir / "simulation.0201.bgeo.sc"
            fixture_script = root / "create_fixture.py"
            fixture_script.write_text(
                "import hou\n"
                "g=hou.Geometry()\n"
                "for p in ((-1,-1,0),(1,-1,.2),(1,1,.4),(-1,1,.1)):\n"
                " q=g.createPoint(); q.setPosition(p)\n"
                f"g.saveToFile({str(cache_path)!r})\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [str(hython), str(fixture_script)], capture_output=True, text=True, timeout=120, check=False
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            second_cache_path = cache_dir / "simulation.0202.bgeo.sc"
            shutil.copy2(cache_path, second_cache_path)
            cache_sha = hashlib.sha256(cache_path.read_bytes()).hexdigest()
            output_dir = root / "round/00_look"
            output_dir.mkdir(parents=True)
            packet_path = output_dir / "playground-packet.json"
            packet = {
                "schema_version": 1,
                "round_id": "look-round-001",
                "study_id": "study-001-test",
                "source_behavior": {
                    "id": "component-behavior-test",
                    "component_kind": "behavior",
                    "state": "promoted",
                    "content_hash": "sha256:" + "a" * 64,
                    "cache_paths": [
                        "cache/simulation.0201.bgeo.sc", "cache/simulation.0202.bgeo.sc",
                    ],
                },
                "source_cache_receipt": [
                    {
                        "path": "cache/simulation.0201.bgeo.sc",
                        "bytes": cache_path.stat().st_size,
                        "sha256": cache_sha,
                    },
                    {
                        "path": "cache/simulation.0202.bgeo.sc",
                        "bytes": second_cache_path.stat().st_size,
                        "sha256": hashlib.sha256(second_cache_path.read_bytes()).hexdigest(),
                    },
                ],
                "purpose": "private-non-competing-artist-playground",
                "features": {
                    "simulation_import": "read-only",
                    "camera": "editable-lookdev-camera",
                    "environment": "neutral-floor-and-background",
                    "material": "editable-materialx-standard-surface",
                    "lighting_modes": ["dome", "photographer"],
                    "photographer_lights": ["key", "fill", "rim"],
                    "renderer": "karma",
                },
                "workspace_layout": {
                    "hip_path": "00_look.hiplc",
                    "receipt_path": "playground-receipt.json",
                    "audit_path": "playground-audit.json",
                    "render_directory": "renders",
                },
            }
            packet_path.write_text(json.dumps(packet), encoding="utf-8")

            builder = make_hython_playground_builder(root, hython, timeout=180)
            builder(packet_path, output_dir)

            hip_path = output_dir / "00_look.hiplc"
            audit = json.loads((output_dir / "playground-audit.json").read_text(encoding="utf-8"))
            receipt = json.loads((output_dir / "playground-receipt.json").read_text(encoding="utf-8"))
            self.assertGreater(hip_path.stat().st_size, 0)
            self.assertTrue(audit["passed"])
            self.assertEqual(audit["verification_engine"], "fresh-hython-reopen")
            self.assertEqual(audit["lighting_modes"], ["dome", "photographer"])
            self.assertEqual(audit["photographer_lights"], ["KEY", "FILL", "RIM"])
            self.assertEqual(audit["frame_range"], [201, 202])
            self.assertEqual(Path(audit["source_cache_path"]).resolve(), cache_path.resolve())
            self.assertEqual(audit["source_cache_bytes"], cache_path.stat().st_size)
            self.assertTrue(audit["camera_framing"]["auto_framed"])
            self.assertEqual(audit["render_configuration"]["renderer"], "BRAY_HdKarma")
            self.assertEqual(audit["node_errors"], [])
            self.assertEqual(receipt["hip_sha256"], hashlib.sha256(hip_path.read_bytes()).hexdigest())

            disconnected_hip = root / "disconnected.hiplc"
            shutil.copy2(hip_path, disconnected_hip)
            mutator = root / "disconnect_scene.py"
            mutator.write_text(
                "import hou\n"
                f"hou.hipFile.load({str(disconnected_hip)!r}, suppress_save_prompt=True)\n"
                "sim=hou.node('/obj/PLAYGROUND_SIM')\n"
                "box=sim.createNode('box', 'UNRELATED_GEOMETRY')\n"
                f"hou.node('/obj/PLAYGROUND_SIM/SOURCE_PROMOTED_SIMULATION').parm('file').set({str(cache_path)!r})\n"
                "hou.node('/obj/PLAYGROUND_SIM/OUT_SIMULATION').setInput(0, box)\n"
                "hou.node('/stage/ASSIGN_STARTER_MATERIALS').parm('matspecpath1').set('/materials/WRONG')\n"
                f"hou.hipFile.save({str(disconnected_hip)!r})\n",
                encoding="utf-8",
            )
            mutation = subprocess.run(
                [str(hython), str(mutator)], capture_output=True, text=True, timeout=120, check=False
            )
            self.assertEqual(mutation.returncode, 0, mutation.stdout + mutation.stderr)
            rejected_audit = root / "disconnected-audit.json"
            rejection = subprocess.run(
                [
                    str(hython), str(root / "houdini/build_look_playground.py"), "verify",
                    str(packet_path), str(disconnected_hip), str(rejected_audit),
                ],
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            self.assertNotEqual(rejection.returncode, 0)
            rejected = json.loads(rejected_audit.read_text(encoding="utf-8"))
            self.assertFalse(rejected["passed"])
            self.assertTrue(any("did not evaluate to this frozen frame" in error for error in rejected["node_errors"]))
            self.assertTrue(any("OUT_SIMULATION is not connected" in error for error in rejected["node_errors"]))
            self.assertTrue(any("material assignment 1" in error for error in rejected["node_errors"]))

            original_hip_sha = receipt["hip_sha256"]
            (output_dir / "playground-audit.json").unlink()
            (output_dir / "playground-receipt.json").unlink()
            builder(packet_path, output_dir)
            recovered_receipt = json.loads(
                (output_dir / "playground-receipt.json").read_text(encoding="utf-8")
            )
            self.assertEqual(recovered_receipt["hip_sha256"], original_hip_sha)

            (output_dir / "playground-audit.json").unlink()
            (output_dir / "playground-receipt.json").unlink()
            hip_path.write_bytes(b"truncated partial Houdini scene")
            corrupt_sha = hashlib.sha256(hip_path.read_bytes()).hexdigest()
            builder(packet_path, output_dir)
            rebuilt_receipt = json.loads(
                (output_dir / "playground-receipt.json").read_text(encoding="utf-8")
            )
            self.assertNotEqual(rebuilt_receipt["hip_sha256"], corrupt_sha)
            self.assertTrue(list((output_dir / "failed-builds").glob("invalid-canonical-hip-*.artifact")))


if __name__ == "__main__":
    unittest.main()
