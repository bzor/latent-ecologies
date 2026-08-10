import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from houdini_ai.jobs import STAGES, job_status, load_job, prepare_job, set_stage_state


class JobTests(unittest.TestCase):
    def make_root(self, directory: str) -> tuple[Path, Path]:
        root = Path(directory)
        (root / "config").mkdir()
        (root / "studies" / "test").mkdir(parents=True)
        (root / "config" / "project.json").write_text(json.dumps({"work_dir": "work"}), encoding="utf-8")
        manifest = root / "studies" / "test" / "study.json"
        manifest.write_text(json.dumps({"id": "test", "seed": 7, "presentation": {"quality": "probe"}}), encoding="utf-8")
        return root, manifest

    @patch("houdini_ai.jobs.source_state", return_value="abc123")
    def test_job_identifier_is_stable_and_descriptive(self, _state) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, manifest = self.make_root(directory)
            first = load_job(root, manifest)
            second = load_job(root, manifest)
            self.assertEqual(first.job_id, second.job_id)
            self.assertTrue(first.job_id.startswith("test-s7-probe-"))

    @patch("houdini_ai.jobs.source_state", return_value="abc123")
    def test_plan_creates_snapshot_and_pending_receipts(self, _state) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, manifest = self.make_root(directory)
            job = load_job(root, manifest)
            receipts = prepare_job(job)
            self.assertTrue((job.directory / "effective-config.json").is_file())
            self.assertEqual([item["stage"] for item in receipts], list(STAGES))
            self.assertTrue(all(item["state"] == "pending" for item in receipts))

    @patch("houdini_ai.jobs.source_state", return_value="abc123")
    def test_stage_states_are_persisted(self, _state) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, manifest = self.make_root(directory)
            job = load_job(root, manifest)
            prepare_job(job)
            set_stage_state(job, "validate", "running")
            set_stage_state(job, "validate", "complete", summary="ok")
            validate = job_status(job)[0]
            self.assertEqual(validate["state"], "complete")
            self.assertEqual(validate["summary"], "ok")

    @patch("houdini_ai.jobs.subprocess.run", side_effect=OSError("git unavailable"))
    def test_source_state_falls_back_without_git(self, _run) -> None:
        from houdini_ai.jobs import source_state

        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(source_state(Path(directory)), "unknown")


if __name__ == "__main__":
    unittest.main()
