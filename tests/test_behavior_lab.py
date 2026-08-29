import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from houdini_ai.behavior_lab import (
    _digest,
    config_from_experiment,
    materially_equivalent_behavior_metrics,
    render_instrument_frames,
    simulate_scar_tissue_reference,
    validate_behavior_metrics,
)


class BehaviorLabTests(unittest.TestCase):
    def test_versioned_mutation_records_share_seed_and_validate(self) -> None:
        from houdini_ai.studio_schema import validate_record

        root = Path(__file__).resolve().parents[1] / "studio/experiments/behavior/scar-tissue"
        records = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(root.glob("*.json"))]
        self.assertEqual({record["parameters"]["mutation"] for record in records}, {
            "saturation-repulsion", "directional-scar", "refractory-healing", "directional-refractory"
        })
        self.assertEqual({record["parameters"]["seed"] for record in records}, {9137})
        self.assertTrue(all(validate_record("experiment", record) == [] for record in records))

    def test_state_digest_includes_oriented_field_and_idle_state(self) -> None:
        base = _digest([[0.0, 0.0, 0.0]], [0.2], [1.0], [0.0], [0])
        self.assertNotEqual(base, _digest([[0.0, 0.0, 0.0]], [0.2], [0.0], [1.0], [0]))
        self.assertNotEqual(base, _digest([[0.0, 0.0, 0.0]], [0.2], [1.0], [0.0], [1]))

    def test_reference_checkpoints_preserve_oriented_field_and_idle_state(self) -> None:
        metrics = simulate_scar_tissue_reference(self.config(mutation="directional-scar"))
        record = metrics["review"][-1]
        self.assertEqual(len(record["direction_x"]), 48 * 72)
        self.assertEqual(len(record["direction_y"]), 48 * 72)
        self.assertEqual(len(record["idle"]), 48 * 72)
        self.assertTrue(any(abs(value) > 1e-6 for value in record["direction_x"] + record["direction_y"]))
        self.assertTrue(any(value > 0 for value in record["idle"]))
    def test_versioned_experiment_converts_to_reference_config(self) -> None:
        experiment = {
            "id": "experiment-scar-tissue-base",
            "parameters": {"seed": 3, "frame_start": 1, "frame_end": 30, "fps": 30, **self.config()["system"]},
        }
        config = config_from_experiment(experiment)
        self.assertEqual(config["id"], "experiment-scar-tissue-base")
        self.assertEqual(config["system"]["mutation"], "saturation-repulsion")

    def config(self, seed=9137, mutation="saturation-repulsion"):
        return {
            "id": "scar-tissue-base",
            "seed": seed,
            "frame_start": 1,
            "frame_end": 60,
            "fps": 30,
            "system": {
                "agent_count": 96,
                "grid_width": 48,
                "grid_height": 72,
                "domain_width": 9.0,
                "domain_height": 13.5,
                "speed": 1.2,
                "deposit": 0.15,
                "decay": 0.992,
                "attraction_threshold": 0.12,
                "saturation_threshold": 0.42,
                "field_strength": 1.1,
                "sensor_distance": 0.32,
                "mutation": mutation,
            },
        }

    def test_reference_simulation_is_deterministic_and_seed_sensitive(self) -> None:
        first = simulate_scar_tissue_reference(self.config())
        second = simulate_scar_tissue_reference(self.config())
        changed = simulate_scar_tissue_reference(self.config(seed=9138))
        self.assertTrue(materially_equivalent_behavior_metrics(first, second))
        self.assertNotEqual(first["state_sha256"], changed["state_sha256"])

    def test_metrics_expose_reinforcement_saturation_abandonment_and_regrowth(self) -> None:
        metrics = simulate_scar_tissue_reference(self.config())
        validated = validate_behavior_metrics(metrics, self.config())
        self.assertEqual(validated["agent_count"], 96)
        self.assertEqual(validated["frame_end"], 60)
        self.assertTrue({"reinforced_cells", "saturated_cells", "abandoned_cells", "regrown_cells"} <= set(metrics["checkpoints"][-1]))
        self.assertGreater(metrics["checkpoints"][-1]["reinforced_cells"], 0)
        self.assertGreater(metrics["checkpoints"][-1]["saturated_cells"], 0)

    def test_three_mutations_produce_distinct_state(self) -> None:
        signatures = {
            simulate_scar_tissue_reference(self.config(mutation=mutation))["state_sha256"]
            for mutation in ("saturation-repulsion", "directional-scar", "refractory-healing")
        }
        self.assertEqual(len(signatures), 3)

    def test_directional_refractory_combines_alignment_and_idle_healing(self) -> None:
        combined = simulate_scar_tissue_reference(self.config(mutation="directional-refractory"))
        directional = simulate_scar_tissue_reference(self.config(mutation="directional-scar"))
        refractory = simulate_scar_tissue_reference(self.config(mutation="refractory-healing"))
        self.assertNotEqual(combined["state_sha256"], directional["state_sha256"])
        self.assertNotEqual(combined["state_sha256"], refractory["state_sha256"])
        self.assertGreater(combined["checkpoints"][-1]["regrown_cells"], 0)

    def test_instrument_renderer_outputs_sharp_agent_and_field_views(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            metrics = simulate_scar_tissue_reference(self.config())
            outputs = render_instrument_frames(metrics, self.config(), Path(directory), size=(270, 405))
            self.assertEqual(set(outputs), {"agent_state", "field_state", "transition"})
            for path in outputs.values():
                image = Image.open(path)
                self.assertEqual(image.size, (270, 405))
                self.assertGreater(len(image.getcolors(maxcolors=270 * 405)), 4)

    def test_validator_rejects_escaped_agents(self) -> None:
        metrics = simulate_scar_tissue_reference(self.config())
        metrics = json.loads(json.dumps(metrics))
        metrics["checkpoints"][-1]["bounds"][2] = 99.0
        with self.assertRaisesRegex(ValueError, "bounds"):
            validate_behavior_metrics(metrics, self.config())


if __name__ == "__main__":
    unittest.main()
