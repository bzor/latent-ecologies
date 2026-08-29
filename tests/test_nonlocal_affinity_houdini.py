import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from houdini_ai.doctor import discover_tools
from houdini_ai.nonlocal_affinity import AffinityConfig, prepare_reference_run, simulate_reference


ROOT = Path(__file__).resolve().parents[1]


class NonlocalAffinityHoudiniTests(unittest.TestCase):
    def test_live_vex_tracer_owns_state_and_matches_python_reference(self) -> None:
        hython = next(tool.path for tool in discover_tools() if tool.name == "hython")
        if hython is None:
            self.skipTest("Houdini is unavailable")
        config = AffinityConfig(
            seed=7,
            agent_count=8,
            steps=3,
            rewire_gate_denominator=1,
            rewire_gate_exclusive_max=2,
            rewires_per_event=3,
        )
        prepared = prepare_reference_run(config)
        reference = simulate_reference(config)
        payload = {
            "config": {
                "seed": config.seed,
                "agent_count": config.agent_count,
                "steps": config.steps,
                "dimensions": config.dimensions,
                "parameters": reference["parameters"],
            },
            "prepared": prepared,
            "reference": {
                "final_positions": reference["final_positions"],
                "friends": reference["friends"],
                "enemies": reference["enemies"],
                "state_sha256": reference["state_sha256"],
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            input_path = output / "input.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                [str(hython), str(ROOT / "houdini/probe_nonlocal_affinity.py"), str(input_path), str(output)],
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
                env={**os.environ, "HOUDINI_TEMP_DIR": str(output / "temp")},
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            metrics = json.loads((output / "vex-parity.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["engine"], "hython-vex")
            self.assertEqual(metrics["state_authority"], "vex-geometry")
            self.assertEqual(metrics["reference_comparison"], "measured")
            self.assertEqual(metrics["vex_cook_count"], 3)
            self.assertEqual(metrics["agent_count"], 8)
            self.assertEqual(metrics["vex_errors"], [])
            self.assertLess(metrics["maximum_position_error"], 1e-6)
            self.assertTrue(metrics["reference_tolerance_passed"])
            self.assertLessEqual(metrics["maximum_position_error"], metrics["comparison_tolerance"])
            self.assertTrue(metrics["relationship_indices_match"])
            self.assertEqual(metrics["state_digest_source"], "reloaded-final-cache")
            self.assertEqual(metrics["trajectory_frame_count"], 4)
            self.assertEqual(len(prepared["rewire_events"]), 9)
            trajectory = json.loads((output / "trajectory.json").read_text(encoding="utf-8"))
            self.assertEqual([frame["step"] for frame in trajectory["frames"]], [0, 1, 2, 3])
            self.assertEqual(len(trajectory["frames"][-1]["positions"]), 8)
            self.assertTrue((output / "cache/nonlocal-affinity.0003.bgeo.sc").is_file())
            self.assertTrue((output / "nonlocal-affinity-parity.hiplc").is_file())


if __name__ == "__main__":
    unittest.main()
