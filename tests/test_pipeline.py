import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from houdini_ai.doctor import Tool
from houdini_ai.jobs import job_status, load_job, prepare_job, set_stage_state
from houdini_ai.pipeline import run_encode, run_milestone3, run_package, run_render


class PipelineTests(unittest.TestCase):
    def make_job(self, directory: str):
        root = Path(directory)
        (root / "config").mkdir()
        (root / "studies" / "test").mkdir(parents=True)
        (root / "houdini").mkdir()
        (root / "houdini" / "build_study_scene.py").write_text("# test", encoding="utf-8")
        (root / "config" / "project.json").write_text(json.dumps({"work_dir": "work"}), encoding="utf-8")
        manifest = root / "studies" / "test" / "study.json"
        manifest.write_text(
            json.dumps(
                {
                    "id": "test",
                    "title": "Test Field",
                    "seed": 7,
                    "presentation": {"quality": "probe"},
                    "simulation": {
                        "frame_start": 1,
                        "frame_end": 3,
                        "fps": 30,
                        "rule_genome": {"system": {"agent_count": 4}},
                    },
                    "render": {"width": 32, "height": 18},
                    "publication": {"approval_required": True},
                }
            ),
            encoding="utf-8",
        )
        job = load_job(root, manifest)
        prepare_job(job)
        return job

    @patch("houdini_ai.pipeline.discover_tools", return_value=[Tool("hython", Path("hython"), "test")])
    @patch("houdini_ai.pipeline._run_logged")
    @patch("houdini_ai.jobs.source_state", return_value="abc123")
    def test_build_and_probe_write_complete_receipts(self, _state, run_logged, _discover) -> None:
        with tempfile.TemporaryDirectory() as directory:
            job = self.make_job(directory)

            def create_artifact(command, _log, _env, timeout=180):
                if "build" in command:
                    hip = Path(command[-2])
                    hip.parent.mkdir(parents=True, exist_ok=True)
                    hip.write_bytes(b"hip" * 400)
                else:
                    image = job.directory / "artifacts" / "frames" / "diagnostic.0001.png"
                    image.parent.mkdir(parents=True, exist_ok=True)
                    rendered = Image.new("RGBA", (32, 18), (0, 0, 0, 255))
                    rendered.putpixel((1, 1), (10, 20, 30, 255))
                    rendered.save(image)

            run_logged.side_effect = create_artifact
            messages = run_milestone3(job)
            self.assertEqual(messages, ["build: complete", "probe: complete"])
            receipts = {item["stage"]: item for item in job_status(job)}
            self.assertEqual(receipts["build"]["state"], "complete")
            self.assertEqual(receipts["probe"]["artifact"]["width"], 32)

            messages = run_milestone3(job)
            self.assertIn("reused verified HIP", messages[0])
            self.assertEqual(run_logged.call_count, 2)

    @patch("houdini_ai.pipeline.discover_tools", return_value=[Tool("hython", Path("hython"), "test")])
    @patch("houdini_ai.pipeline._run_logged")
    @patch("houdini_ai.jobs.source_state", return_value="abc123")
    def test_render_resumes_only_missing_frames(self, _state, run_logged, _discover) -> None:
        with tempfile.TemporaryDirectory() as directory:
            job = self.make_job(directory)
            frame_dir = job.directory / "render" / "frames"

            def create_frames(_command, _log, _env, timeout=180):
                requested = json.loads((job.directory / "render" / "missing-frames.json").read_text())
                frame_dir.mkdir(parents=True, exist_ok=True)
                for frame in requested:
                    image = Image.new("RGBA", (32, 18), (8, 12, 16, 255))
                    image.putpixel((frame, 1), (220, 240, 235, 255))
                    image.save(frame_dir / f"field-study.{frame:04d}.png")

            run_logged.side_effect = create_frames
            self.assertEqual(run_render(job), "render: complete (3 frames rendered)")
            (frame_dir / "field-study.0002.png").unlink()
            self.assertEqual(run_render(job), "render: complete (1 frame rendered)")
            self.assertEqual(run_logged.call_count, 2)
            self.assertEqual(json.loads((job.directory / "render" / "missing-frames.json").read_text()), [2])

    @patch("houdini_ai.pipeline.discover_tools", return_value=[Tool("hython", Path("hython"), "test")])
    @patch("houdini_ai.pipeline._run_logged")
    @patch("houdini_ai.jobs.source_state", return_value="abc123")
    def test_render_resumes_after_interruption_and_invalid_frame(self, _state, run_logged, _discover) -> None:
        with tempfile.TemporaryDirectory() as directory:
            spaced_root = Path(directory) / "workspace with spaces"
            spaced_root.mkdir()
            job = self.make_job(str(spaced_root))
            frame_dir = job.directory / "render" / "frames"

            def interrupt(_command, _log, _env, timeout=180):
                frame_dir.mkdir(parents=True, exist_ok=True)
                image = Image.new("RGBA", (32, 18), (8, 12, 16, 255))
                image.putpixel((1, 1), (220, 240, 235, 255))
                image.save(frame_dir / "field-study.0001.png")
                raise RuntimeError("interrupted")

            run_logged.side_effect = interrupt
            with self.assertRaisesRegex(RuntimeError, "interrupted"):
                run_render(job)
            self.assertEqual({item["stage"]: item for item in job_status(job)}["render"]["state"], "failed")

            def finish(_command, _log, _env, timeout=180):
                requested = json.loads((job.directory / "render" / "missing-frames.json").read_text())
                for frame in requested:
                    image = Image.new("RGBA", (32, 18), (8, 12, 16, 255))
                    image.putpixel((frame, 1), (220, 240, 235, 255))
                    image.save(frame_dir / f"field-study.{frame:04d}.png")

            run_logged.side_effect = finish
            self.assertEqual(run_render(job), "render: complete (2 frames rendered)")
            (frame_dir / "field-study.0002.png").write_bytes(b"partial")
            self.assertEqual(run_render(job), "render: complete (1 frame rendered)")

    @patch("houdini_ai.pipeline._probe_video")
    @patch("houdini_ai.pipeline._run_logged")
    @patch(
        "houdini_ai.pipeline.discover_tools",
        return_value=[Tool("ffmpeg", Path("ffmpeg"), "test"), Tool("ffprobe", Path("ffprobe"), "test")],
    )
    @patch("houdini_ai.jobs.source_state", return_value="abc123")
    def test_encode_and_package_are_reusable(self, _state, _discover, run_logged, probe_video) -> None:
        with tempfile.TemporaryDirectory() as directory:
            job = self.make_job(directory)
            set_stage_state(job, "render", "complete")
            frame_dir = job.directory / "render" / "frames"
            frame_dir.mkdir(parents=True)
            for frame in range(1, 4):
                image = Image.new("RGBA", (32, 18), (8, 12, 16, 255))
                image.putpixel((frame, 1), (220, 240, 235, 255))
                image.save(frame_dir / f"field-study.{frame:04d}.png")

            dimensions = {
                "archive-master.mov": (32, 18),
                "social-vertical.mp4": (1080, 1920),
                "feed-portrait.mp4": (1080, 1350),
                "website.mp4": (720, 1280),
                "preview-loop.mp4": (540, 960),
            }

            def create_video(command, _log, _env, timeout=180):
                Path(command[-1]).write_bytes(b"video" * 410)

            def video_metadata(_ffprobe, path):
                width, height = dimensions[path.name]
                return {"codec_name": "test", "width": width, "height": height, "r_frame_rate": "30/1", "duration": 0.1}

            run_logged.side_effect = create_video
            probe_video.side_effect = video_metadata
            self.assertEqual(run_encode(job), "encode: complete (5 variants encoded)")
            self.assertEqual(run_encode(job), "encode: complete (0 variants encoded)")
            self.assertEqual(run_logged.call_count, 5)
            self.assertIn("verified artifacts", run_package(job))
            self.assertTrue((job.directory / "package" / "poster.png").is_file())
            self.assertTrue((job.directory / "package" / "field-note.json").is_file())


if __name__ == "__main__":
    unittest.main()
