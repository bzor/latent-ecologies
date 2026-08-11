import json
import os
import tempfile
import unittest
from pathlib import Path

from houdini_ai.storage import apply_cleanup, inventory_jobs, plan_cleanup, storage_report


class StorageTests(unittest.TestCase):
    def make_job(
        self, root: Path, name: str, study_id: str, modified: int, *, status: str = "prototype", packaged: bool = False
    ) -> Path:
        job = root / "work" / "jobs" / name
        (job / "simulation" / "smoke-a-cache").mkdir(parents=True)
        (job / "simulation" / "smoke-a-cache" / "state.bgeo.sc").write_bytes(b"cache" * 100)
        (job / "temp").mkdir()
        (job / "temp" / "scratch.tmp").write_bytes(b"temp" * 50)
        (job / "render" / "frames").mkdir(parents=True)
        (job / "render" / "frames" / "frame.png").write_bytes(b"frame" * 100)
        effective = {"study": {"id": study_id, "status": status, "publication": {"state": "private"}}}
        (job / "effective-config.json").write_text(json.dumps(effective), encoding="utf-8")
        if packaged:
            (job / "receipts").mkdir()
            (job / "receipts" / "package.json").write_text(json.dumps({"state": "complete"}), encoding="utf-8")
        os.utime(job, (modified, modified))
        return job

    def test_inventory_protects_selected_and_marks_latest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = self.make_job(root, "study-a-old", "study-a", 100)
            new = self.make_job(root, "study-a-new", "study-a", 200, packaged=True)
            selected = self.make_job(root, "study-b-selected", "study-b", 150, status="selected")
            jobs = {job.path: job for job in inventory_jobs(root)}
            self.assertFalse(jobs[old].latest)
            self.assertTrue(jobs[new].latest)
            self.assertTrue(jobs[selected].retention_protected)
            self.assertTrue(jobs[new].package_complete)

    def test_cleanup_defaults_are_bounded_and_dry_plan_is_non_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = self.make_job(root, "study-a-old", "study-a", 100)
            new = self.make_job(root, "study-a-new", "study-a", 200)
            selected = self.make_job(root, "study-b-selected", "study-b", 150, status="selected")
            items = plan_cleanup(root)
            self.assertIn(old, [item.path for item in items])
            self.assertIn(new / "simulation" / "smoke-a-cache", [item.path for item in items])
            self.assertNotIn(selected, [item.path for item in items])
            self.assertTrue(old.exists())
            reclaimed = apply_cleanup(root, items)
            self.assertGreater(reclaimed, 0)
            self.assertFalse(old.exists())
            self.assertTrue(new.exists())
            self.assertTrue(selected.exists())

    def test_packaged_sequences_are_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            job = self.make_job(root, "study-a-new", "study-a", 200, packaged=True)
            default_paths = [item.path for item in plan_cleanup(root)]
            sequence = job / "render" / "frames"
            self.assertNotIn(sequence, default_paths)
            self.assertIn(sequence, [item.path for item in plan_cleanup(root, ["packaged-sequences"])])

    def test_storage_report_uses_configured_budget(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            (root / "config" / "project.json").write_text(
                json.dumps({"storage": {"warning_gb": 0.0000001, "critical_gb": 1, "minimum_free_gb": 0}}),
                encoding="utf-8",
            )
            self.make_job(root, "study-a-new", "study-a", 200)
            self.assertEqual(storage_report(root)["level"], "warning")


if __name__ == "__main__":
    unittest.main()
