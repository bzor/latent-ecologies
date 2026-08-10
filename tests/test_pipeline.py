import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from houdini_ai.doctor import Tool
from houdini_ai.jobs import job_status, load_job, prepare_job
from houdini_ai.pipeline import run_milestone3


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
                    "seed": 7,
                    "presentation": {"quality": "probe"},
                    "simulation": {"frame_start": 1},
                    "render": {"width": 32, "height": 18},
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


if __name__ == "__main__":
    unittest.main()
