import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from houdini_ai import detail_promote as dp


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "design-overlay-generator" / "web"

CHROME = dp.discover_chrome()
try:
    FFMPEG = dp._discover_ffmpeg("ffmpeg")
except FileNotFoundError:
    FFMPEG = None


def sample_study(frames: int = 2) -> dict:
    return {
        "id": "STUDY-TST",
        "number": 99,
        "title": "PROMOTE TEST",
        "subtitle": "detail-pass regression",
        "source": "",
        "date": "2026-08-21",
        "solver": {"name": "POP/VEX", "dt": "1/240", "substeps": 1, "seed": 7},
        "params": [["AGENTS", "1 000"]],
        "fps": 24,
        "frames": frames,
        "variation": {
            "id": "variation-bhvr001-001-primary-treatment",
            "number": 1,
            "title": "Primary Treatment",
            "slug": "primary-treatment",
            "file_stem": "bhvr_001_var_001_primary-treatment",
        },
        "series": {"energy": [index / max(1, frames - 1) for index in range(frames)]},
        "bbox": [[0.3, 0.3, 0.7, 0.7] for _ in range(frames)],
    }


def sample_config() -> dict:
    return {
        "studyId": "STUDY-TST",
        "aspect": "1:1 — 320×320",
        "palette": "bone / signal red",
        "type": {},
        "components": {},
    }


class DetailPromoteUnitTests(unittest.TestCase):
    def test_variation_package_names_are_carried_into_delivery(self) -> None:
        self.assertEqual(
            dp.variation_package_names(sample_study()),
            {
                "delivery": "bhvr_001_var_001_primary-treatment.delivery.mp4",
                "overlay_frames": "bhvr_001_var_001_primary-treatment.overlay_frames",
                "receipt": "bhvr_001_var_001_primary-treatment.delivery.json",
            },
        )

    def test_parse_aspect(self) -> None:
        self.assertEqual(dp.parse_aspect("9:16 — 1080×1920"), (1080, 1920))
        self.assertEqual(dp.parse_aspect("4:5 — 1080x1350"), (1080, 1350))
        with self.assertRaises(ValueError):
            dp.parse_aspect("portrait")

    def test_overlay_source_version_pins_web_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory) / "web"
            web.mkdir()
            (web / "overlay.js").write_text("draw", encoding="utf-8")
            (web / "capture.html").write_text("page", encoding="utf-8")
            first = dp.overlay_source_version(Path(directory))
            self.assertEqual(first, dp.overlay_source_version(Path(directory)))
            (web / dp.CAPTURE_INPUT_NAME).write_text("window.CAPTURE_INPUT={}", encoding="utf-8")
            self.assertEqual(first, dp.overlay_source_version(Path(directory)), "per-run input must not affect the version")
            (web / "overlay.js").write_text("draw2", encoding="utf-8")
            self.assertNotEqual(first, dp.overlay_source_version(Path(directory)))

    def test_sidecar_and_config_validation(self) -> None:
        study = sample_study()
        self.assertEqual(dp.validate_study_sidecar(study), [])
        self.assertEqual(dp.validate_overlay_config(sample_config(), study), [])

        broken = sample_study()
        broken["series"]["energy"] = [0.5]
        broken["bbox"] = broken["bbox"][:1]
        del broken["title"]
        errors = dp.validate_study_sidecar(broken)
        self.assertEqual(len(errors), 3)

        config = sample_config()
        config["studyId"] = "STUDY-OTHER"
        config["aspect"] = "square"
        config.pop("components")
        self.assertEqual(len(dp.validate_overlay_config(config, study)), 3)

    def test_sidecar_requires_canonical_variation_identity(self) -> None:
        study = sample_study()
        del study["variation"]
        self.assertEqual(
            dp.validate_study_sidecar(study),
            ["study.json is missing canonical variation identity"],
        )

    def test_verify_overlay_frame(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            good = Path(directory) / "good.png"
            image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            image.putpixel((5, 5), (255, 255, 255, 255))
            image.save(good)
            self.assertEqual(dp.verify_overlay_frame(good, 64, 64), [])
            self.assertTrue(dp.verify_overlay_frame(good, 32, 64))

            opaque_rgb = Path(directory) / "rgb.png"
            Image.new("RGB", (64, 64), (10, 10, 10)).save(opaque_rgb)
            self.assertTrue(dp.verify_overlay_frame(opaque_rgb, 64, 64))

            empty = Path(directory) / "empty.png"
            Image.new("RGBA", (64, 64), (0, 0, 0, 0)).save(empty)
            self.assertTrue(dp.verify_overlay_frame(empty, 64, 64))
            self.assertTrue(dp.verify_overlay_frame(Path(directory) / "missing.png", 64, 64))

    def test_capture_page_static_contract(self) -> None:
        page = (WEB / "capture.html").read_text(encoding="utf-8")
        order = ["fonts.js", "sample-study.js", "overlay.js", "components.js", "capture-input.js", "capture.js"]
        indexes = [page.index(f'src="{name}"') for name in order]
        self.assertEqual(indexes, sorted(indexes))
        code = "\n".join(
            line for line in (WEB / "capture.js").read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("//")
        )
        self.assertNotIn("Math.random(", code)
        self.assertNotIn("Date.now(", code)
        self.assertIn("capture-input.js", (ROOT / ".gitignore").read_text(encoding="utf-8"))

    def test_panel_offers_canonical_promote_export(self) -> None:
        self.assertIn('id="promoteExportBtn"', (WEB / "index.html").read_text(encoding="utf-8"))
        app = (WEB / "app.js").read_text(encoding="utf-8")
        self.assertIn('"overlay-config.json"', app)
        self.assertIn("promoteExportBtn", app)


class DetailPromoteToolTests(unittest.TestCase):
    @unittest.skipUnless(CHROME, "Chrome is not available")
    def test_render_overlay_sequence_is_resumable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "frames"
            first = dp.render_overlay_sequence(
                sample_study(), sample_config(), output, jobs=2, log=lambda *_: None
            )
            self.assertEqual(first["rendered"], [0, 1])
            self.assertEqual(first["width"], 320)
            for frame in range(2):
                path = output / (dp.FRAME_PATTERN % frame)
                self.assertEqual(dp.verify_overlay_frame(path, 320, 320), [])
            self.assertFalse((WEB / dp.CAPTURE_INPUT_NAME).exists(), "per-run capture input must be cleaned up")

            second = dp.render_overlay_sequence(
                sample_study(), sample_config(), output, jobs=2, log=lambda *_: None
            )
            self.assertEqual(second["rendered"], [])
            self.assertEqual(second["reused_existing"], [0, 1])

    @unittest.skipUnless(FFMPEG, "FFmpeg is not available")
    def test_composite_overlay_over_png_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            overlay = base / "overlay"
            overlay.mkdir()
            for frame in range(2):
                Image.new("RGB", (320, 320), (40, 40, 40)).save(base / f"render.{frame:04d}.png")
                mark = Image.new("RGBA", (320, 320), (0, 0, 0, 0))
                for x in range(10, 60):
                    for y in range(10, 20):
                        mark.putpixel((x, y), (232, 68, 46, 255))
                mark.save(overlay / (dp.FRAME_PATTERN % frame))
            output = base / "post.mp4"
            result = dp.composite_overlay(
                base / "render.%04d.png", overlay, output,
                fps=24, frames=2, render_start_number=0,
            )
            self.assertTrue(output.is_file())
            self.assertEqual(result["sha256"], dp.sha256_file(output))
            probe = subprocess.run(
                [str(dp._discover_ffmpeg("ffprobe")), "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height,nb_frames", "-of", "json", str(output)],
                capture_output=True, text=True, check=True,
            )
            stream = json.loads(probe.stdout)["streams"][0]
            self.assertEqual((stream["width"], stream["height"]), (320, 320))
            with self.assertRaises(FileNotFoundError):
                dp.composite_overlay(base / "render.%04d.png", overlay, base / "again.mp4",
                                     fps=24, frames=3, render_start_number=0)


if __name__ == "__main__":
    unittest.main()
