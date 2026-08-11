import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from houdini_ai.mass_flow import determinism_signature, render_mass_flow_review, validate_mass_flow_metrics


class MassFlowTests(unittest.TestCase):
    def config(self):
        return {
            "study": {
                "simulation": {
                    "frame_start": 1,
                    "frame_end": 60,
                    "rule_genome": {
                        "system": {
                            "agent_count": 100000,
                            "domain_width": 9.0,
                            "domain_height": 16.0,
                            "max_speed": 2.4,
                        }
                    },
                },
                "render": {"width": 360, "height": 640},
            }
        }

    def metrics(self):
        return {
            "seed": 7,
            "agent_count": 100000,
            "frame_start": 1,
            "frame_end": 8,
            "cache_sha256": {"state.0001.bgeo.sc": "a", "state.0008.bgeo.sc": "b"},
            "state_sha256": {"1": "canonical-a", "8": "canonical-b"},
            "checkpoints": [
                {
                    "frame": 1,
                    "agent_count": 100000,
                    "mean_speed": 0.3,
                    "max_speed": 0.5,
                    "bounds": [-4.0, -7.0, 4.0, 7.0],
                    "elapsed_seconds": 0.0,
                },
                {
                    "frame": 8,
                    "agent_count": 100000,
                    "mean_speed": 0.8,
                    "max_speed": 1.4,
                    "bounds": [-4.4, -7.9, 4.4, 7.9],
                    "elapsed_seconds": 2.0,
                },
            ],
        }

    def test_metrics_validate_and_signature_ignores_timing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.json"
            metrics = self.metrics()
            path.write_text(json.dumps(metrics), encoding="utf-8")
            self.assertEqual(validate_mass_flow_metrics(path, self.config())["agent_count"], 100000)
            changed_timing = json.loads(json.dumps(metrics))
            changed_timing["checkpoints"][-1]["elapsed_seconds"] = 99.0
            self.assertEqual(determinism_signature(metrics), determinism_signature(changed_timing))
            changed_timing["state_sha256"]["8"] = "different"
            self.assertNotEqual(determinism_signature(metrics), determinism_signature(changed_timing))

    def test_review_bundle_is_portrait_and_visible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            review = root / "review.json"
            points = [[-2.0, -4.0, 0.5, 0], [0.0, 0.0, 1.2, 1], [2.0, 4.0, 2.0, 2]]
            review.write_text(
                json.dumps({"frames": [{"frame": frame, "points": points} for frame in (1, 20, 40, 60)]}),
                encoding="utf-8",
            )
            outputs = render_mass_flow_review(review, self.config(), root / "output")
            image = Image.open(outputs["contact_sheet"])
            self.assertEqual(image.size, (360, 640))
            self.assertGreater(len(image.getcolors(maxcolors=100000)), 2)


if __name__ == "__main__":
    unittest.main()
