import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from houdini_ai.doctor import discover_tools


ROOT = Path(__file__).resolve().parents[1]


class ScarMechanicsHoudiniTests(unittest.TestCase):
    def run_mechanic(self, mode: str, frame_end: int = 90, parameters: dict | None = None) -> dict:
        hython = next(tool.path for tool in discover_tools() if tool.name == "hython")
        if hython is None:
            self.skipTest("Houdini is unavailable")
        experiment = {
            "id": f"test-{mode}",
            "schema_version": 1,
            "mode": mode,
            "seed": 9137,
            "frame_start": 1,
            "frame_end": frame_end,
            "fps": 30,
            "parameters": parameters or {},
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            config = output / "experiment.json"
            config.write_text(json.dumps(experiment), encoding="utf-8")
            result = subprocess.run(
                [str(hython), str(ROOT / "houdini/simulate_scar_mechanics.py"), str(config), str(output / "run")],
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
                env={**os.environ, "HOUDINI_TEMP_DIR": str(output / "temp")},
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return json.loads((output / "run/metrics.json").read_text(encoding="utf-8"))

    def test_excitable_zipper_propagates_pulses_ratchets_and_fuses_banks(self) -> None:
        metrics = self.run_mechanic("excitable-purse-string-zipper", frame_end=120)
        self.assertEqual(metrics["engine"], "houdini-vex-authoritative")
        self.assertEqual(metrics["mutation_branch"], 0)
        self.assertEqual(metrics["vex_cook_count"], 120)
        self.assertEqual(metrics["vex_errors"], [])
        self.assertGreaterEqual(metrics["traveling_pulse_events"], 3)
        self.assertLess(metrics["peak_excited_fraction_after_initialization"], 0.4)
        self.assertGreater(metrics["ratchet_total"], 0.0)
        self.assertGreater(metrics["closure_fraction"], 0.25)
        self.assertGreater(metrics["latched_zipper_count"], 0)
        self.assertGreater(metrics["zipper_front_span"], 0.1)
        self.assertEqual(metrics["cache_count"], 120)
        self.assertEqual(len(metrics["state_sha256"]), 64)
        self.assertEqual(metrics["state_digest_source"], "reloaded-display-cache")

    def test_tug_zip_builds_persistent_load_bearing_fascicle_graph(self) -> None:
        metrics = self.run_mechanic("tug-zip-fasciculation", frame_end=150)
        self.assertEqual(metrics["engine"], "houdini-vex-authoritative")
        self.assertEqual(metrics["mutation_branch"], 1)
        self.assertEqual(metrics["vex_errors"], [])
        self.assertGreater(metrics["candidate_bond_count"], 0)
        self.assertEqual(metrics["candidate_bond_count"], metrics["candidate_bond_count_initial"])
        self.assertGreater(metrics["tug_events"], 0)
        self.assertGreater(metrics["uncrimped_fibre_count"], 0)
        self.assertGreater(metrics["latched_bond_count"], 0)
        self.assertGreater(metrics["largest_bond_component_fraction"], 0.1)
        self.assertLess(metrics["largest_bond_component_fraction"], 0.8)
        self.assertGreater(metrics["late_bond_event_fraction"], 0.05)
        self.assertGreater(metrics["empty_domain_fraction"], 0.25)
        self.assertGreater(metrics["adhesion_phase_fraction"], 0.1)
        self.assertLess(metrics["adhesion_phase_fraction"], 0.6)
        self.assertEqual(metrics["cache_count"], 150)
        self.assertEqual(len(metrics["state_sha256"]), 64)

    def test_flow_guided_fasciculation_aligns_agents_and_builds_denser_paths(self) -> None:
        metrics = self.run_mechanic(
            "tug-zip-fasciculation",
            frame_end=150,
            parameters={
                "fibre_count": 192,
                "agent_count": 24,
                "candidate_radius": 1.18,
                "max_candidate_neighbors": 4,
                "flow_mode": 1,
                "flow_strength": 0.32,
                "flow_scale": 0.52,
                "flow_time_rate": 0.025,
                "flow_center_pull": 0.18,
                "flow_recruit_radius": 0.55,
                "flow_recruit_gain": 0.12,
            },
        )
        self.assertEqual(metrics["mutation_branch"], 1)
        self.assertGreater(metrics["flow_alignment_mean"], 0.58)
        self.assertGreater(metrics["candidate_bond_count"], 250)
        self.assertGreater(metrics["latched_bond_count"], 20)
        self.assertGreater(metrics["tug_events"], 100)
        self.assertGreater(metrics["flow_recruit_events"], 100)
        self.assertGreater(metrics["empty_domain_fraction"], 0.25)
        self.assertEqual(metrics["state_digest_source"], "reloaded-display-cache")

    def test_cylindrical_zipper_preserves_planar_state_while_contracting_in_xyz(self) -> None:
        rapid_parameters = {
            "activator_decay": 0.34,
            "refractory_decay": 0.055,
            "wave_transfer": 0.82,
            "myosin_response": 0.58,
            "ratchet_rate": 0.28,
            "ratchet_heterogeneity": 0.0,
            "closure_gain": 0.82,
            "zip_capture": 1.55,
            "zip_rate": 0.16,
            "zip_front_boost": 0.22,
        }
        planar = self.run_mechanic(
            "excitable-purse-string-zipper", frame_end=96,
            parameters={**rapid_parameters, "zipper_space_mode": 0},
        )
        cylindrical = self.run_mechanic(
            "excitable-purse-string-zipper", frame_end=96,
            parameters={
                **rapid_parameters,
                "zipper_space_mode": 1,
                "tube_azimuth": 0.61,
            },
        )
        self.assertEqual(cylindrical["zipper_space_mode"], 1)
        self.assertEqual(cylindrical["kinetic_state_sha256"], planar["kinetic_state_sha256"])
        self.assertGreater(cylindrical["z_extent"], 0.10)
        self.assertLess(cylindrical["axis_antipodal_error_max"], 0.025)
        self.assertAlmostEqual(
            cylindrical["closure_fraction"], planar["closure_fraction"], delta=0.00003,
        )
        self.assertEqual(cylindrical["latched_zipper_count"], planar["latched_zipper_count"])

    def test_ratchet_settlement_winds_cylindrical_zipper_twice_without_changing_kinetics(self) -> None:
        rapid_parameters = {
            "activator_decay": 0.34,
            "refractory_decay": 0.055,
            "wave_transfer": 0.82,
            "myosin_response": 0.58,
            "ratchet_rate": 0.28,
            "ratchet_heterogeneity": 0.0,
            "closure_gain": 0.82,
            "zip_capture": 1.55,
            "zip_rate": 0.16,
            "zip_front_boost": 0.22,
            "zipper_space_mode": 1,
            "tube_azimuth": 0.61,
        }
        straight = self.run_mechanic(
            "excitable-purse-string-zipper", frame_end=96,
            parameters={**rapid_parameters, "tube_twist_turns": 0.0},
        )
        helical = self.run_mechanic(
            "excitable-purse-string-zipper", frame_end=96,
            parameters={**rapid_parameters, "tube_twist_turns": 2.0},
        )
        self.assertEqual(helical["kinetic_state_sha256"], straight["kinetic_state_sha256"])
        self.assertEqual(helical["tube_twist_turns"], 2.0)
        self.assertGreater(helical["helix_winding_turns"], 1.5)
        self.assertEqual(helical["latched_zipper_count"], straight["latched_zipper_count"])
        self.assertAlmostEqual(helical["closure_fraction"], straight["closure_fraction"], delta=0.00002)

    def test_long_wave_helix_preserves_planar_capture_history(self) -> None:
        parameters = {
            "activator_decay": 0.48,
            "refractory_decay": 0.035,
            "wave_transfer": 0.88,
            "myosin_response": 0.5,
            "ratchet_rate": 0.08,
            "ratchet_heterogeneity": 0.0,
            "closure_gain": 0.58,
            "zip_capture": 1.18,
            "zip_rate": 0.04,
            "zip_front_boost": 0.0,
        }
        planar = self.run_mechanic(
            "excitable-purse-string-zipper", frame_end=150,
            parameters={**parameters, "zipper_space_mode": 0},
        )
        helical = self.run_mechanic(
            "excitable-purse-string-zipper", frame_end=150,
            parameters={
                **parameters,
                "zipper_space_mode": 1,
                "tube_azimuth": 0.61,
                "tube_twist_turns": 2.0,
            },
        )
        self.assertEqual(helical["kinetic_state_sha256"], planar["kinetic_state_sha256"])
        self.assertEqual(helical["latched_zipper_count"], planar["latched_zipper_count"])
        self.assertAlmostEqual(helical["closure_fraction"], planar["closure_fraction"], delta=0.00003)


if __name__ == "__main__":
    unittest.main()
