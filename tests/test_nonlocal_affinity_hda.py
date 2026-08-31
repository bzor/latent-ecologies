import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from houdini_ai.affinity_presets import load_affinity_preset
from houdini_ai.doctor import discover_tools
from houdini_ai.nonlocal_affinity import lift_prepared_to_3d, prepare_canvas_run


ROOT = Path(__file__).resolve().parents[1]
PRESET = ROOT / "studio/affinity-presets/affinity-preset-32e76e5d39d0.json"


class NonlocalAffinityHDATests(unittest.TestCase):
    def test_hda_rebake_matches_batch_backend_and_exposes_artist_controls(self) -> None:
        hython = next(tool.path for tool in discover_tools() if tool.name == "hython")
        if hython is None:
            self.skipTest("Houdini is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            config = load_affinity_preset(PRESET, agent_count=64, dimensions=2, steps=6)
            preset = json.loads(PRESET.read_text(encoding="utf-8"))
            planar = prepare_canvas_run(
                config,
                rewire_probability=float(preset["rewiring"]["probability_per_simulation_step"]),
            )
            shallow = lift_prepared_to_3d(planar, seed=config.seed, depth=0.15)
            prepared = shallow
            prepared_path = output / "prepared.json"
            prepared_path.write_text(json.dumps(prepared), encoding="utf-8")
            batch = output / "batch"
            environment = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "HOUDINI_TEMP_DIR": str(output / "temp")}
            reference = subprocess.run(
                [
                    str(hython), str(ROOT / "houdini/simulate_nonlocal_affinity_3d.py"),
                    str(PRESET), str(batch), "--agent-count", "64", "--dimensions", "3",
                    "--steps", "6", "--checkpoint-interval", "6", "--review-interval", "6",
                    "--review-count", "32", "--prepared", str(prepared_path),
                ],
                capture_output=True, text=True, timeout=180, check=False, env=environment,
            )
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)

            build = subprocess.run(
                [
                    str(hython), str(ROOT / "houdini/build_nonlocal_affinity_hda.py"),
                    str(PRESET), str(prepared_path), str(output / "hda"),
                    "--verify-steps", "6", "--cohort-size", "1", "--prepared-schedule-steps", "6",
                    "--expected-metrics", str(batch / "metrics.json"),
                ],
                capture_output=True, text=True, timeout=180, check=False, env=environment,
            )
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            audit = json.loads((output / "hda/audit.json").read_text(encoding="utf-8"))
            metrics = json.loads((batch / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(audit["state_authority"], "vex-geometry")
            self.assertEqual(audit["point_count"], 64)
            self.assertEqual(audit["initial_point_count"], 64)
            self.assertEqual(audit["verified_steps"], 6)
            self.assertEqual(audit["final_state_sha256"], metrics["final_state_sha256"])
            self.assertEqual(audit["final_relationship_sha256"], metrics["final_relationship_sha256"])
            self.assertTrue(audit["batch_backend_match"])
            self.assertEqual(audit["procedural_count_probe"]["num_points"], 16)
            self.assertEqual(audit["procedural_count_probe"]["total_points"], 16)
            self.assertEqual(audit["procedural_count_probe"]["simstep_at_frame_2"], 3)
            self.assertEqual(audit["procedural_count_probe"]["node_errors"], [])
            self.assertEqual(audit["maximum_count_probe"]["num_points"], 500000)
            self.assertEqual(audit["maximum_count_probe"]["total_points"], 500000)
            self.assertTrue(audit["maximum_count_probe"]["relationships_in_range"])
            self.assertTrue(audit["maximum_count_probe"]["positions_finite"])
            self.assertEqual(audit["maximum_count_probe"]["node_errors"], [])
            self.assertEqual(audit["node_errors"], [])
            self.assertEqual(
                set(audit["artist_parameters"]),
                {
                    "contraction", "attraction", "repulsion", "softening",
                    "apply_rewires", "depth_scale",
                    "start_frame", "point_size", "reset_simulation",
                    "seed", "new_seed", "num_points", "total_points",
                    "rewire_probability", "rewires_per_event", "steps_per_frame",
                    "event_schedule_steps", "overlay_variation_number", "overlay_variation_title",
                    "overlay_manifest_path", "export_overlay_manifest",
                },
            )
            self.assertNotIn("num_cohorts", audit["artist_parameters"])
            self.assertNotIn("cohort_radius", audit["artist_parameters"])
            self.assertEqual(audit["num_points_hard_maximum"], 500000)
            self.assertEqual(audit["num_points_ui_maximum"], 500000)
            manifest_probe = audit["overlay_parameter_manifest_probe"]
            self.assertEqual(manifest_probe["variation"]["number"], 7)
            self.assertEqual(manifest_probe["variation"]["file_stem"], "bhvr_001_var_007_graph-tension")
            self.assertIn("behavior.attraction", manifest_probe["parameter_keys"])
            self.assertIn("look.point_size", manifest_probe["parameter_keys"])
            manifest_path = output / "hda/audit-overlay-parameter-manifest.json"
            self.assertTrue(manifest_path.is_file())
            exported = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(exported["source"]["node_path"], "/obj/HDA_FRESH_SESSION_AUDIT/NONLOCAL_AFFINITY_PARALLEL")
            self.assertTrue((output / "hda/nonlocal-affinity-parallel.hda").is_file())
            self.assertTrue((output / "hda/nonlocal-affinity-parallel-demo.hiplc").is_file())
            self.assertTrue((output / "hda/initial-state.bgeo.sc").is_file())


if __name__ == "__main__":
    unittest.main()
