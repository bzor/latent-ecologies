import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from houdini_ai.doctor import discover_tools
from houdini_ai.nonlocal_affinity import AffinityConfig, AffinityParameters, prepare_canvas_run, relationship_digest, simulate_prepared
from houdini_ai.studio_api import StudioAPI


ROOT = Path(__file__).resolve().parents[1]


class NonlocalAffinityProductionTests(unittest.TestCase):
    def test_live_3d_runner_rotates_transient_state_and_keeps_sparse_verified_checkpoints(self) -> None:
        hython = next(tool.path for tool in discover_tools() if tool.name == "hython")
        if hython is None:
            self.skipTest("Houdini is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            api = StudioAPI(root)
            preset = api.save_affinity_preset({
                "schema_version": 1,
                "mechanism": "nonlocal-affinity-v1",
                "project_id": "study-003-nonlocal-affinity-dance",
                "title": "Production tracer",
                "note": "Tiny live 3D runner acceptance fixture.",
                "dimensions": 2,
                "seed": 7,
                "parameters": {
                    "contraction": 0.9898,
                    "attraction": 0.023,
                    "repulsion": 0.01,
                    "softening": 0.012,
                },
                "rewiring": {
                    "probability_per_simulation_step": 1.0,
                    "rewires_per_event": 3,
                    "ordering": "before-synchronous-position-update",
                },
                "preview": {
                    "agent_count": 100,
                    "steps_per_display_frame": 1,
                    "rng": "mulberry32-v1",
                    "initialization": "uniform-square-minus-one-to-one",
                },
                "display": {
                    "point_size": 1.5,
                    "trail_alpha": 0.16,
                    "viewport_scale": 1.25,
                    "show_links": False,
                },
                "production_hint": {
                    "state": "candidate",
                    "execution_authorized": False,
                    "integration_authority": "houdini-vex",
                },
            })
            preset_path = root / "studio" / "affinity-presets" / f'{preset["id"]}.json'
            output = root / "production"
            result = subprocess.run(
                [
                    str(hython),
                    str(ROOT / "houdini" / "simulate_nonlocal_affinity_3d.py"),
                    str(preset_path),
                    str(output),
                    "--agent-count", "64",
                    "--dimensions", "3",
                    "--steps", "6",
                    "--checkpoint-interval", "3",
                    "--review-interval", "1",
                    "--review-count", "32",
                    "--compare-reference",
                ],
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "HOUDINI_TEMP_DIR": str(output / "temp")},
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            metrics = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["engine"], "hython-vex-rotating-cache")
            self.assertEqual(metrics["state_authority"], "vex-geometry")
            self.assertEqual(metrics["preset_id"], preset["id"])
            self.assertEqual(metrics["agent_count"], 64)
            self.assertEqual(metrics["dimensions"], 3)
            self.assertEqual(metrics["steps"], 6)
            self.assertEqual(metrics["vex_cook_count"], 6)
            self.assertEqual(metrics["rewire_count"], 18)
            self.assertEqual(metrics["vex_errors"], [])
            self.assertEqual(metrics["durable_checkpoint_steps"], [0, 3, 6])
            self.assertEqual(metrics["state_digest_source"], "reloaded-final-cache")
            self.assertTrue(metrics["reference_tolerance_passed"])
            self.assertTrue(metrics["reference_material_tolerance_passed"])
            self.assertTrue(metrics["relationship_indices_match"])
            self.assertGreater(metrics["checkpoints"][0]["bounds"][5] - metrics["checkpoints"][0]["bounds"][2], 0.5)
            review = json.loads((output / "review.json").read_text())
            self.assertEqual([frame["step"] for frame in review["frames"]], list(range(7)))
            self.assertTrue((output / "cache" / "state.0000.bgeo.sc").is_file())
            self.assertTrue((output / "cache" / "state.0003.bgeo.sc").is_file())
            self.assertTrue((output / "cache" / "state.0006.bgeo.sc").is_file())
            self.assertTrue((output / "cache" / "state.transient.bgeo.sc").is_file())
            self.assertTrue((output / "nonlocal-affinity-3d.hiplc").is_file())

            canvas_config = AffinityConfig(
                seed=7,
                agent_count=64,
                steps=6,
                dimensions=2,
                rewires_per_event=3,
                parameters=AffinityParameters(contraction=0.9898, attraction=0.023, repulsion=0.01, softening=0.012),
            )
            prepared = prepare_canvas_run(canvas_config, rewire_probability=1.0)
            prepared_path = root / "canvas-prepared.json"
            prepared_path.write_text(
                json.dumps(prepared), encoding="utf-8",
            )
            planar_output = root / "planar-production"
            planar = subprocess.run(
                [
                    str(hython),
                    str(ROOT / "houdini" / "simulate_nonlocal_affinity_3d.py"),
                    str(preset_path),
                    str(planar_output),
                    "--agent-count", "64",
                    "--dimensions", "2",
                    "--steps", "6",
                    "--checkpoint-interval", "6",
                    "--review-interval", "1",
                    "--review-count", "32",
                    "--prepared", str(prepared_path),
                    "--compare-reference",
                ],
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "HOUDINI_TEMP_DIR": str(planar_output / "temp")},
            )
            self.assertEqual(planar.returncode, 0, planar.stdout + planar.stderr)
            planar_metrics = json.loads((planar_output / "metrics.json").read_text())
            self.assertEqual(planar_metrics["dimensions"], 2)
            self.assertEqual(planar_metrics["prepared_source"], "external-receipt")
            self.assertEqual(planar_metrics["checkpoints"][0]["bounds"][2], 0.0)
            self.assertEqual(planar_metrics["checkpoints"][-1]["bounds"][5], 0.0)
            self.assertTrue(planar_metrics["reference_tolerance_passed"])
            self.assertTrue(planar_metrics["reference_material_tolerance_passed"])
            self.assertTrue(planar_metrics["relationship_indices_match"])
            planar_reference = simulate_prepared(canvas_config, prepared)
            self.assertEqual(
                planar_metrics["final_relationship_sha256"],
                relationship_digest(planar_reference["friends"], planar_reference["enemies"]),
            )


if __name__ == "__main__":
    unittest.main()
