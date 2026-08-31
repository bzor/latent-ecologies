import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from houdini_ai import post_kit as pk
from houdini_ai.study_card import STUDY_CARD_NAME

try:
    FFMPEG = pk._discover_tool("ffmpeg")
except FileNotFoundError:
    FFMPEG = None


def sample_card() -> dict:
    return {
        "schema_version": 1,
        "study_id": "study-003-nonlocal-affinity-dance",
        "number": 3,
        "title": "NONLOCAL AFFINITY GRAPH DYNAMICS",
        "subtitle": "synchronous point-agent updates with nonlocal attraction and repulsion",
        "summary": (
            "Simulation of 100 000 point agents. Partner assignment is independent of spatial "
            "proximity and changes on a deterministic schedule over 960 steps."
        ),
        "bullets": [
            "interaction partners are indexed independently of spatial distance",
            "one attractive and one repulsive relation per agent",
        ],
        "params": [["AGENTS", "100 000"], ["HORIZON", "960 STEPS"]],
        "variation_behavior_number": 1,
        "variation_number": 1,
        "variation_title": "Primary Treatment",
        "variation_slug": "primary-treatment",
        "variation_file_stem": "bhvr_001_var_001_primary-treatment",
        "variation_id": "variation-bhvr001-001-primary-treatment",
    }


def write_study(root: Path) -> Path:
    study = root / "study_003_nonlocal-affinity-dance"
    (study / "00_study").mkdir(parents=True)
    (study / "00_study" / STUDY_CARD_NAME).write_text(json.dumps(sample_card()), encoding="utf-8")
    return study


def write_frames(directory: Path, count: int = 12) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for index in range(count):
        Image.new("RGB", (720, 720), (236, 0, 140)).save(directory / f"frame-{index:04d}.png")
    return directory


class CaptionTests(unittest.TestCase):
    def test_short_captions_fit_platform_limits(self) -> None:
        captions = pk.build_captions(sample_card(), "delivery")
        self.assertLessEqual(len(captions["x"]), pk.PLATFORMS["x"]["caption_limit"])
        self.assertLessEqual(len(captions["bluesky"]), pk.PLATFORMS["bluesky"]["caption_limit"])
        self.assertIn("STUDY 003", captions["x"])
        self.assertIn("NONLOCAL AFFINITY GRAPH DYNAMICS", captions["x"])
        self.assertNotIn("#houdini", captions["x"])

    def test_instagram_caption_carries_summary_bullets_params_hashtags(self) -> None:
        caption = pk.build_captions(sample_card(), "delivery")["instagram"]
        self.assertIn("Simulation of 100 000 point agents.", caption)
        self.assertIn("- one attractive and one repulsive relation per agent", caption)
        self.assertIn("AGENTS 100 000", caption)
        self.assertIn("#houdini", caption)

    def test_stage_lines_appear_for_behavior_and_recap_only(self) -> None:
        behavior = pk.build_captions(sample_card(), "behavior")["x"]
        recap = pk.build_captions(sample_card(), "recap")["x"]
        delivery = pk.build_captions(sample_card(), "delivery")["x"]
        self.assertIn("Behavior-stage diagnostic render.", behavior)
        self.assertIn("Study 003 is complete.", recap)
        self.assertNotIn("diagnostic", delivery)

    def test_long_summary_is_dropped_before_breaking_the_limit(self) -> None:
        card = sample_card()
        card["summary"] = "A" * 400 + ". Second sentence."
        caption = pk.build_captions(card, "delivery")["x"]
        self.assertLessEqual(len(caption), pk.PLATFORMS["x"]["caption_limit"])
        self.assertIn("STUDY 003", caption)

    def test_rejects_unknown_stage(self) -> None:
        with self.assertRaises(ValueError):
            pk.build_captions(sample_card(), "seed")

    def test_display_text_violations_fail_loudly(self) -> None:
        card = sample_card()
        card["summary"] = "At its core, this is a simulation of agents."
        with self.assertRaises(ValueError):
            pk.build_captions(card, "delivery")


class AltTextTests(unittest.TestCase):
    def test_alt_text_combines_title_subtitle_summary(self) -> None:
        alt = pk.build_alt_text(sample_card())
        self.assertIn("STUDY 003 · NONLOCAL AFFINITY GRAPH DYNAMICS.", alt)
        self.assertIn("synchronous point-agent updates", alt)
        self.assertIn("Simulation of 100 000 point agents.", alt)


class PlatformCheckTests(unittest.TestCase):
    def test_flags_over_duration_and_missing_derivative(self) -> None:
        derivatives = {"feed": {"duration_seconds": 200.0}}
        captions = {platform: "caption" for platform in pk.PLATFORMS}
        checks = pk.platform_checks(derivatives, captions)
        self.assertFalse(checks["x"]["duration_ok"])
        self.assertTrue(checks["bluesky"]["duration_ok"] is False)
        self.assertFalse(checks["instagram"]["derivative_built"])
        self.assertIsNone(checks["instagram"]["duration_ok"])
        self.assertTrue(all(check["caption_ok"] for check in checks.values()))

    def test_unknown_duration_is_reported_as_none(self) -> None:
        derivatives = {name: {"duration_seconds": None} for name in pk.DERIVATIVES}
        checks = pk.platform_checks(derivatives, {platform: "c" for platform in pk.PLATFORMS})
        self.assertIsNone(checks["x"]["duration_ok"])


@unittest.skipUnless(FFMPEG, "FFmpeg is not available")
class KitBuildTests(unittest.TestCase):
    def test_builds_full_kit_from_frames(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            study = write_study(root)
            frames = write_frames(root / "frames")
            out = root / "kit"
            receipt = pk.build_post_kit(study, frames, out, stage="delivery", source_fps=30)

            stem = "bhvr_001_var_001_primary-treatment"
            for name, (width, height) in pk.DERIVATIVES.items():
                path = Path(receipt["derivatives"][name]["path"])
                self.assertTrue(path.exists())
                self.assertEqual(path.name, f"{stem}.{name}.mp4")
                self.assertEqual(receipt["derivatives"][name]["size"], [width, height])
                self.assertAlmostEqual(receipt["derivatives"][name]["duration_seconds"], 0.4)
            for platform in pk.PLATFORMS:
                self.assertTrue((out / f"caption.{platform}.txt").exists())
                self.assertTrue(receipt["platforms"][platform]["caption_ok"])
                self.assertTrue(receipt["platforms"][platform]["duration_ok"])
            self.assertTrue((out / "alt-text.txt").exists())
            self.assertTrue((out / "post-kit.md").exists())
            saved = json.loads((out / "post-kit.receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["kind"], "post-kit")
            self.assertEqual(saved["stage"], "delivery")
            self.assertEqual(saved["study_id"], "study-003-nonlocal-affinity-dance")
            summary = (out / "post-kit.md").read_text(encoding="utf-8")
            self.assertIn("STUDY 003", summary)
            self.assertIn("tiktok", summary)

    def test_only_limits_derivatives(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            study = write_study(root)
            frames = write_frames(root / "frames")
            receipt = pk.build_post_kit(
                study, frames, root / "kit", stage="behavior", source_fps=30, only=("feed",)
            )
            self.assertEqual(list(receipt["derivatives"]), ["feed"])
            self.assertFalse(receipt["platforms"]["tiktok"]["derivative_built"])

    def test_rejects_unknown_derivative_before_encoding(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            study = write_study(root)
            with self.assertRaises(ValueError):
                pk.build_post_kit(
                    study, root / "missing", root / "kit", stage="delivery", only=("square",)
                )


if __name__ == "__main__":
    unittest.main()
