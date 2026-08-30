import math
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from houdini_ai.scar_cylindrical_review import (
    _project,
    _project_review_point,
    render_cylindrical_review_frames,
)


class ScarCylindricalReviewTests(unittest.TestCase):
    def test_source_projection_rotates_about_irregular_tube_axis(self) -> None:
        y = 1.7
        radius = 1.15
        azimuth = 0.61
        seam = 0.10 * math.sin(y * 0.78) + 0.035 * math.sin(y * 2.17)
        position = [
            seam + radius * math.cos(azimuth),
            y,
            radius * math.sin(azimuth),
        ]
        projected = _project(position, azimuth, "source")
        self.assertAlmostEqual(projected[0], seam + radius, places=6)
        self.assertAlmostEqual(projected[1], y, places=6)
        self.assertAlmostEqual(projected[2], 0.0, places=6)

    def test_source_panel_unwraps_settled_helix_back_to_signed_radius(self) -> None:
        y = 2.2
        angle = 5.4
        radius = 0.72
        seam = 0.10 * math.sin(y * 0.78) + 0.035 * math.sin(y * 2.17)
        point = {
            "P": [seam + radius * math.cos(angle), y, radius * math.sin(angle)],
            "bank": 1,
            "tube_radius": radius,
            "tube_angle": angle,
        }
        projected = _project_review_point(point, 0.61, "source", tube_twist_turns=2.0)
        self.assertAlmostEqual(projected[0], seam + radius, places=6)
        self.assertAlmostEqual(projected[1], y, places=6)
        self.assertAlmostEqual(projected[2], 0.0, places=6)

    def test_source_panel_prefers_authoritative_unwrapped_wound_coordinate(self) -> None:
        point = {
            "P": [0.2, 1.0, 0.6], "bank": 1,
            "tube_radius": 0.72, "tube_angle": 5.4,
            "unwrapped_x": 0.93,
        }
        projected = _project_review_point(point, 0.61, "source", tube_twist_turns=2.0)
        self.assertAlmostEqual(projected[0], 0.93, places=6)

    def test_review_renders_matched_source_oblique_and_combined_frames(self) -> None:
        points = [
            {"P": [-0.94, -2.0, -0.66], "bank": -1, "edge_index": 0, "activator": 0.0, "myosin": 0.1, "fused": 0},
            {"P": [-0.42, 2.0, -0.30], "bank": -1, "edge_index": 1, "activator": 0.8, "myosin": 0.7, "fused": 0},
            {"P": [0.94, -2.0, 0.66], "bank": 1, "edge_index": 0, "activator": 0.0, "myosin": 0.1, "fused": 0},
            {"P": [0.42, 2.0, 0.30], "bank": 1, "edge_index": 1, "activator": 0.8, "myosin": 0.7, "fused": 0},
        ]
        primitives = [
            {"points": [0, 1], "kind": 0, "tension": 0.2, "bond": 0.0, "latched": 0},
            {"points": [2, 3], "kind": 0, "tension": 0.2, "bond": 0.0, "latched": 0},
            {"points": [0, 2], "kind": 1, "tension": 0.0, "bond": 0.8, "latched": 1},
        ]
        metrics = {
            "variant_label": "CYLINDRICAL RAPID ZIPPER",
            "tube_azimuth": 0.61,
            "tube_radius_initial": 1.15,
            "review": [
                {"frame": frame, "points": points, "primitives": primitives}
                for frame in (1, 2)
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            outputs = render_cylindrical_review_frames(metrics, Path(directory), size=(960, 540))
            self.assertEqual(len(outputs["source"]), 2)
            self.assertEqual(len(outputs["oblique"]), 2)
            self.assertEqual(len(outputs["combined"]), 2)
            for family in outputs.values():
                for path in family:
                    self.assertTrue(path.exists())
                    with Image.open(path) as image:
                        self.assertEqual(image.size, (960, 540) if family is not outputs["combined"] else (1920, 540))
            with Image.open(outputs["oblique"][0]) as image:
                colors = set(image.getdata())
            self.assertTrue(any(b > 80 and abs(r - g) < 18 for r, g, b in colors))
            self.assertTrue(any(r > 220 and g > 175 and b < 130 for r, g, b in colors))


if __name__ == "__main__":
    unittest.main()
