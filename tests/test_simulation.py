import json
import tempfile
import unittest
from pathlib import Path

from houdini_ai.simulation import validate_metrics


class SimulationTests(unittest.TestCase):
    def config(self):
        return {
            "study": {
                "simulation": {
                    "frame_start": 1,
                    "frame_end": 2,
                    "rule_genome": {
                        "system": {
                            "agent_count": 1,
                            "domain": {"domain_width": 16.0, "domain_height": 9.0},
                            "relic": {
                                "relic_hub_radius": 0.7,
                                "relic_prong_length": 0.4,
                                "relic_prong_power": 5.0,
                                "relic_orientation": 1.5707963268,
                            },
                        }
                    },
                }
            }
        }

    def record(self, frame: int, position=(2.0, 0.0, 0.0)):
        return {
            "frame": frame,
            "active": 1,
            "dormant": 0,
            "terminated": 0,
            "mean_speed": 0.5,
            "max_speed": 0.5,
            "resource_total": 10.0,
            "inhibition_mean": 0.1,
            "inhibition_max": 0.2,
            "boundary_contacts": 0,
            "agents": [{"position": position, "velocity": [0.5, 0, 0], "relic_distance": 1.0}],
        }

    def write(self, directory: str, records) -> Path:
        path = Path(directory) / "metrics.json"
        path.write_text(json.dumps({"frames": records}), encoding="utf-8")
        return path

    def test_valid_metrics_are_summarized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            summary = validate_metrics(self.write(directory, [self.record(1), self.record(2)]), self.config())
            self.assertEqual(summary["frame_count"], 2)
            self.assertEqual(summary["agent_count"], 1)

    def test_invalid_domain_and_relic_positions_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for position in ((9.0, 0.0, 0.0), (0.0, 0.0, 0.0)):
                with self.subTest(position=position), self.assertRaises(RuntimeError):
                    validate_metrics(
                        self.write(directory, [self.record(1, position), self.record(2, position)]), self.config()
                    )

    def test_missing_frames_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(RuntimeError):
            validate_metrics(self.write(directory, [self.record(1)]), self.config())


if __name__ == "__main__":
    unittest.main()
