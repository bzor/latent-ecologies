import tempfile
import unittest
from pathlib import Path

from PIL import Image

from houdini_ai.scar_mechanics_package import render_mechanics_frames


class ScarMechanicsPackageTests(unittest.TestCase):
    def test_excitable_zipper_render_exposes_cyan_wave_and_yellow_fusion(self) -> None:
        points = [
            {"id": 0, "bank": -1, "edge_index": 0, "P": [-1.0, -1.0, 0.0], "activator": 1.0, "myosin": 0.7, "ratchet": 0.2, "fused": 0},
            {"id": 1, "bank": -1, "edge_index": 1, "P": [-0.8, 1.0, 0.0], "activator": 0.0, "myosin": 0.2, "ratchet": 0.4, "fused": 0},
            {"id": 2, "bank": 1, "edge_index": 0, "P": [1.0, -1.0, 0.0], "activator": 0.0, "myosin": 0.1, "ratchet": 0.2, "fused": 0},
            {"id": 3, "bank": 1, "edge_index": 1, "P": [0.8, 1.0, 0.0], "activator": 0.0, "myosin": 0.2, "ratchet": 0.4, "fused": 1},
        ]
        primitives = [
            {"kind": 0, "points": [0, 1], "bond": 0.0, "latched": 0, "tension": 0.7},
            {"kind": 0, "points": [2, 3], "bond": 0.0, "latched": 0, "tension": 0.2},
            {"kind": 1, "points": [1, 3], "bond": 1.0, "latched": 1, "tension": 0.1},
        ]
        metrics = {
            "mode": "excitable-purse-string-zipper",
            "review": [{"frame": frame, "points": points, "primitives": primitives} for frame in range(1, 5)],
        }
        config = {"parameters": {"bank_half_width": 1.15, "wound_height": 11.5}}
        with tempfile.TemporaryDirectory() as directory:
            frame = render_mechanics_frames(metrics, config, Path(directory), size=(360, 540))[-1]
            image = Image.open(frame).convert("RGB")
            colors = list(image.get_flattened_data())
            self.assertTrue(any(b > 180 and g > 140 and r < 120 for r, g, b in colors))
            self.assertTrue(any(r > 210 and g > 160 and b < 120 for r, g, b in colors))

    def test_fasciculation_render_exposes_loose_fibres_tugs_and_latched_graph(self) -> None:
        points = [
            {"id": 0, "class": 2, "P": [-1.0, -1.0, 0.0], "fdir": [1.0, 0.0, 0.0], "mass": 0.8, "crimp": 0.9, "fibre_tension": 0.0, "stability": 0.1, "bundle_degree": 0.0, "lox": 0.0},
            {"id": 1, "class": 2, "P": [1.0, 1.0, 0.0], "fdir": [0.7, 0.7, 0.0], "mass": 1.0, "crimp": 0.1, "fibre_tension": 0.8, "stability": 0.9, "bundle_degree": 1.0, "lox": 0.8},
            {"id": 0, "class": 0, "P": [0.0, 0.0, 0.0], "heading": 0.0, "phase": 2, "anchor": 1, "traction": 0.8},
        ]
        primitives = [{"kind": 2, "points": [0, 1], "bond": 0.9, "latched": 1, "tension": 0.7, "contact_dwell": 1.0, "bond_age": 8}]
        metrics = {"mode": "tug-zip-fasciculation", "review": [{"frame": frame, "points": points, "primitives": primitives} for frame in range(1, 4)]}
        config = {"parameters": {"domain_width": 8.0, "domain_height": 12.0}}
        with tempfile.TemporaryDirectory() as directory:
            frame = render_mechanics_frames(metrics, config, Path(directory), size=(360, 540))[-1]
            image = Image.open(frame).convert("RGB")
            colors = list(image.get_flattened_data())
            self.assertTrue(any(b > 170 and g > 160 and r < 120 for r, g, b in colors))
            self.assertTrue(any(r > 210 and 70 < g < 190 and b < 90 for r, g, b in colors))
            self.assertTrue(any(abs(r - g) < 20 and abs(g - b) < 20 and r > 100 for r, g, b in colors))

    def test_flow_guided_render_shows_coherent_agent_trajectory_trails(self) -> None:
        review = []
        for frame in range(1, 7):
            review.append({
                "frame": frame,
                "points": [
                    {"id": 0, "class": 2, "P": [0.0, 0.0, 0.0], "fdir": [0.0, 1.0, 0.0], "mass": 0.8, "crimp": 0.8, "fibre_tension": 0.0, "bundle_degree": 0.0},
                    {"id": 0, "class": 0, "P": [-1.0 + frame * 0.25, -2.0 + frame * 0.45, 0.0], "heading": 1.0, "phase": 0, "anchor": -1, "flow_alignment": 0.9},
                ],
                "primitives": [],
            })
        metrics = {"mode": "tug-zip-fasciculation", "review": review}
        config = {"parameters": {"domain_width": 8.0, "domain_height": 12.0, "flow_mode": 1}}
        with tempfile.TemporaryDirectory() as directory:
            frame = render_mechanics_frames(metrics, config, Path(directory), size=(360, 540))[-1]
            colors = list(Image.open(frame).convert("RGB").get_flattened_data())
            self.assertIn((65, 145, 170), colors)


if __name__ == "__main__":
    unittest.main()
