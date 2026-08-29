import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from houdini_ai.behavior_package import (
    encode_mp4,
    render_comparison_contact,
    render_temporal_frames,
    write_receipt,
)


class BehaviorPackageTests(unittest.TestCase):
    def config(self):
        return {
            "id": "scar-test",
            "fps": 6,
            "system": {
                "domain_width": 2.0,
                "domain_height": 2.0,
                "attraction_threshold": 0.2,
                "saturation_threshold": 0.6,
            },
        }

    def metrics(self):
        return {
            "mutation": "refractory-healing",
            "grid": [2, 2],
            "review": [
                {"frame": 1, "agents": [], "field": [0.05, 0.3, 0.8, 0.4]},
                {"frame": 10, "agents": [], "field": [0.05, 0.3, 0.8, 0.05]},
            ],
            "checkpoints": [
                {"frame": 1, "reinforced_cells": 3, "saturated_cells": 1, "regrown_cells": 0},
                {"frame": 10, "reinforced_cells": 2, "saturated_cells": 1, "regrown_cells": 1},
            ],
        }

    def test_temporal_frames_encode_low_attractive_saturated_and_healed_states(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            frames = render_temporal_frames(
                self.metrics(), self.config(), Path(directory), size=(200, 140), hold_frames=2
            )

            self.assertEqual(
                [path.name for path in frames],
                ["frame-0000.png", "frame-0001.png", "frame-0002.png", "frame-0003.png"],
            )
            image = Image.open(frames[-1]).convert("RGB")
            self.assertEqual(image.getpixel((50, 45)), (24, 32, 38))
            self.assertEqual(image.getpixel((150, 45)), (45, 180, 110))
            self.assertEqual(image.getpixel((50, 105)), (235, 82, 72))
            self.assertEqual(image.getpixel((150, 105)), (90, 145, 240))

    def test_temporal_frames_overlay_oriented_field_vectors_when_present(self) -> None:
        metrics = self.metrics()
        for record in metrics["review"]:
            record["direction_x"] = [1.0, 0.0, 0.0, 0.0]
            record["direction_y"] = [0.0, 0.0, 0.0, 0.0]
        with tempfile.TemporaryDirectory() as directory:
            frames = render_temporal_frames(metrics, self.config(), Path(directory), size=(200, 140))
            image = Image.open(frames[-1]).convert("RGB")
            self.assertEqual(image.getpixel((50, 35)), (210, 225, 235))
            self.assertEqual(image.getpixel((58, 35)), (210, 225, 235))

    def test_fibrotic_frames_distinguish_provisional_matrix_from_mature_collagen(self) -> None:
        metrics = self.metrics()
        metrics["mutation"] = "fibrotic-remodeling"
        for record in metrics["review"]:
            record["provisional_matrix"] = [0.5, 0.0, 0.0, 0.0]
            record["mature_collagen"] = [0.0, 0.5, 0.0, 0.0]
        with tempfile.TemporaryDirectory() as directory:
            frame = render_temporal_frames(metrics, self.config(), Path(directory), size=(200, 140))[-1]
            image = Image.open(frame).convert("RGB")
            provisional = image.getpixel((50, 35))
            mature = image.getpixel((150, 35))
            self.assertGreater(provisional[1], provisional[0])
            self.assertGreater(mature[0], mature[1])
            self.assertNotEqual(provisional, mature)

    def test_wound_contractile_frames_expose_contraction_as_raised_purple_signal(self) -> None:
        metrics = self.metrics()
        metrics["mutation"] = "wound-contractile-remodeling"
        for record in metrics["review"]:
            record["provisional_matrix"] = [0.0, 0.0, 0.0, 0.0]
            record["mature_collagen"] = [0.0, 0.5, 0.0, 0.0]
            record["wound_signal"] = [0.0, 1.0, 0.0, 0.0]
            record["contraction"] = [0.0, 0.8, 0.0, 0.0]
        with tempfile.TemporaryDirectory() as directory:
            frame = render_temporal_frames(metrics, self.config(), Path(directory), size=(200, 140))[-1]
            image = Image.open(frame).convert("RGB")
            background = image.getpixel((50, 35))
            contracted = image.getpixel((150, 35))
            self.assertGreater(contracted[0], background[0])
            self.assertGreater(contracted[2], background[2])
            self.assertGreater(contracted[2], contracted[1])

    def test_purse_string_frames_show_bright_edges_around_open_wound_core(self) -> None:
        metrics = self.metrics()
        metrics["mutation"] = "purse-string-closure"
        for record in metrics["review"]:
            record["provisional_matrix"] = [0.0] * 4
            record["mature_collagen"] = [0.5, 0.0, 0.5, 0.0]
            record["wound_signal"] = [0.38, 1.0, 0.38, 0.0]
            record["contraction"] = [0.8, 0.05, 0.8, 0.0]
        with tempfile.TemporaryDirectory() as directory:
            frame = render_temporal_frames(metrics, self.config(), Path(directory), size=(200, 140))[-1]
            image = Image.open(frame).convert("RGB")
            edge = image.getpixel((50, 35))
            core = image.getpixel((150, 35))
            self.assertGreater(edge[0], core[0])
            self.assertGreater(edge[2], edge[1])
            self.assertGreater(core[2], core[0])

    def test_crosslink_weave_frames_turn_collagen_crossings_gold(self) -> None:
        metrics = self.metrics()
        metrics["mutation"] = "collagen-crosslink-weave"
        for record in metrics["review"]:
            record["provisional_matrix"] = [0.0] * 4
            record["mature_collagen"] = [0.5, 0.5, 0.0, 0.0]
            record["crosslink"] = [0.0, 0.9, 0.0, 0.0]
        with tempfile.TemporaryDirectory() as directory:
            frame = render_temporal_frames(metrics, self.config(), Path(directory), size=(200, 140))[-1]
            image = Image.open(frame).convert("RGB")
            collagen = image.getpixel((50, 35))
            crossing = image.getpixel((150, 35))
            self.assertGreater(collagen[2], collagen[0])
            self.assertGreater(crossing[0], collagen[0])
            self.assertGreater(crossing[1], collagen[1])
            self.assertGreater(crossing[0], crossing[2])

    def test_keloid_bloom_frames_show_hot_signal_foci_inside_collagen(self) -> None:
        metrics = self.metrics()
        metrics["mutation"] = "keloid-signal-bloom"
        for record in metrics["review"]:
            record["provisional_matrix"] = [0.0] * 4
            record["mature_collagen"] = [0.3, 0.3, 0.0, 0.0]
            record["fibrotic_signal"] = [0.0, 0.9, 0.0, 0.0]
        with tempfile.TemporaryDirectory() as directory:
            frame = render_temporal_frames(metrics, self.config(), Path(directory), size=(200, 140))[-1]
            image = Image.open(frame).convert("RGB")
            collagen = image.getpixel((50, 35))
            bloom = image.getpixel((150, 35))
            self.assertGreater(bloom[0], collagen[0])
            self.assertGreater(bloom[1], collagen[1])
            self.assertGreater(bloom[0], bloom[2])
            self.assertGreater(bloom[1], bloom[2])

    def test_encode_mp4_uses_supplied_ffmpeg_and_receipt_checksums_outputs(self) -> None:
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            self.skipTest("ffmpeg is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frames = render_temporal_frames(self.metrics(), self.config(), root / "frames", size=(200, 140))
            video = encode_mp4(frames, root / "diagnostic.mp4", fps=6, ffmpeg_executable=ffmpeg)
            receipt = write_receipt(
                root / "receipt.json",
                experiment_id="scar-test",
                mutation="refractory-healing",
                files=[*frames, video],
            )

            self.assertGreater(video.stat().st_size, 0)
            stored = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(stored["files"]["diagnostic.mp4"]["sha256"], hashlib.sha256(video.read_bytes()).hexdigest())
            self.assertEqual(stored["mutation"], "refractory-healing")

    def test_three_mutation_contact_has_labeled_panels_and_metrics_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = []
            for index, mutation in enumerate(("saturation-repulsion", "directional-scar", "refractory-healing")):
                image = Image.new("RGB", (80, 60), (40 + index * 50, 20, 30))
                path = root / f"{mutation}.png"
                image.save(path)
                entries.append({"mutation": mutation, "image": path, "metrics": {"saturated_cells": index + 1}})

            outputs = render_comparison_contact(entries, root / "comparison.png", root / "comparison.json")

            with Image.open(outputs["contact"]) as contact:
                self.assertEqual(contact.size, (240, 88))
            comparison = json.loads(outputs["comparison"].read_text(encoding="utf-8"))
            self.assertEqual([entry["mutation"] for entry in comparison["mutations"]], [entry["mutation"] for entry in entries])
            self.assertEqual(comparison["mutations"][2]["metrics"]["saturated_cells"], 3)


if __name__ == "__main__":
    unittest.main()
