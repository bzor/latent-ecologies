import json
import tempfile
import unittest
from pathlib import Path

from houdini_ai.nonlocal_affinity_review import render_comparison, render_single_review


class NonlocalAffinityReviewTests(unittest.TestCase):
    def test_renderer_accepts_named_cohort_strategy_branches(self) -> None:
        branches = (
            ("parallel", "Parallel cohorts"),
            ("neighbor", "Neighbor braid"),
            ("mixed", "Mixed cohorts"),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for branch_index, (slug, _title) in enumerate(branches):
                branch = root / "input" / slug
                branch.mkdir(parents=True)
                frames = [
                    {"step": step, "points": [[-0.5 + branch_index * 0.1, 0.0, 0.0], [0.5, step * 0.1, 0.1]]}
                    for step in (0, 1)
                ]
                (branch / "review.json").write_text(json.dumps({"frames": frames}), encoding="utf-8")

            receipt = render_comparison(
                root / "input",
                root / "output",
                branches=branches,
                hold_frames=1,
                fps=2,
                population_count=100000,
                heading="Cohort strategy tracer",
                video_name="cohort-strategy-tracer.mp4",
            )

            self.assertEqual(receipt["branches"], [
                {"slug": "parallel", "title": "Parallel cohorts"},
                {"slug": "neighbor", "title": "Neighbor braid"},
                {"slug": "mixed", "title": "Mixed cohorts"},
            ])
            self.assertEqual(receipt["review_sample_count_per_branch"], 2)
            self.assertEqual(receipt["video"], "cohort-strategy-tracer.mp4")
            self.assertTrue((root / "output" / receipt["video"]).is_file())
            self.assertTrue((root / "output" / receipt["contact_sheet"]).is_file())

    def test_single_review_uses_actual_endurance_horizon(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "parallel"
            source.mkdir()
            frames = [
                {"step": step, "points": [[-0.5, 0.0, 0.0], [0.5, step * 0.001, 0.1]]}
                for step in (0, 240, 720, 960)
            ]
            (source / "review.json").write_text(json.dumps({"frames": frames}), encoding="utf-8")

            receipt = render_single_review(
                source,
                root / "output",
                title="Parallel cohorts",
                hold_frames=1,
                fps=2,
                population_count=100000,
                video_name="parallel-endurance.mp4",
            )

            self.assertEqual(receipt["checkpoint_steps"], [0, 240, 720, 960])
            self.assertEqual(receipt["total_steps"], 960)
            self.assertEqual(receipt["review_sample_count"], 2)
            self.assertTrue((root / "output" / "parallel-endurance.mp4").is_file())
            self.assertTrue((root / "output" / receipt["contact_sheet"]).is_file())


if __name__ == "__main__":
    unittest.main()
