import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from houdini_ai import cli
from houdini_ai.studio_store import StudioStore
from tests.test_look_execution import direction as make_direction
from tests.test_look_execution import fake_hip_verifier
from tests.test_look_execution import write_receipt
from tests.test_look_execution import write_playground


def direction() -> dict:
    return make_direction("look-direction-weave", "Affinity Weave", "affinity", "strand density")


def write_scaffold(packet_path: Path, output: Path) -> None:
    design = output / "00_design"
    design.mkdir(exist_ok=True)
    (design / "PARENT_SCAFFOLD.json").write_text(json.dumps({
        "schema_version": 1,
        "protected_nodes": {
            "final_output": {
                "path": "/obj/LOOK_DIRECTION/OUT_FINAL",
                "type": "null",
                "scaffold_id": "a" * 64,
            },
        },
    }), encoding="utf-8")


class LookExecutionCliTests(unittest.TestCase):
    def run_cli(self, root: Path, *args: str) -> tuple[int, str]:
        output = StringIO()
        with patch.object(cli, "ROOT", root), redirect_stdout(output):
            result = cli.main(["studio", *args])
        return result, output.getvalue()

    def test_cli_prepares_runs_and_releases_one_aggregate_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "source.json"
            directions_path = root / "directions.json"
            cache_relatives = [
                f"studies/study_003_test/01_behavior/03_selected/selection_001/cache.{frame:04d}.bgeo.sc"
                for frame in range(1, 9)
            ]
            for cache_relative in cache_relatives:
                cache_path = root / cache_relative
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_bytes(f"canonical cache {cache_relative}".encode())
            StudioStore(root).create("components", "component-behavior-a", {
                "schema_version": 1,
                "id": "component-behavior-a",
                "track": "behavior",
                "state": "promoted",
                "component_kind": "behavior",
                "source_experiment_id": "experiment-behavior-a",
                "source_artifact_ref": cache_relatives[0],
                "rationale": "KC selected and locked this Behavior.",
                "content_hash": "sha256:" + "d" * 64,
                "visibility": "private",
            })
            source_path.write_text(json.dumps({
                "id": "component-behavior-a",
                "component_kind": "behavior",
                "state": "promoted",
                "content_hash": "sha256:" + "d" * 64,
                "cache_paths": cache_relatives,
            }), encoding="utf-8")
            directions_path.write_text(json.dumps([direction()]), encoding="utf-8")

            code, prepared = self.run_cli(
                root, "look-round-prepare", "study-003-test", str(source_path), str(directions_path),
            )
            self.assertEqual(code, 0)
            manifest_path = Path(prepared.splitlines()[0].split("manifest: ", 1)[1])
            self.assertTrue(manifest_path.is_file())

            with (
                patch("houdini_ai.studio_cli.make_hermes_worker", return_value=write_receipt),
                patch("houdini_ai.studio_cli.make_hython_hip_verifier", return_value=fake_hip_verifier),
                patch("houdini_ai.studio_cli.make_hython_playground_builder", return_value=write_playground),
                patch("houdini_ai.studio_cli.make_hython_direction_scaffold_builder", return_value=write_scaffold),
            ):
                code, completed = self.run_cli(root, "look-round-run", str(manifest_path))
            self.assertEqual(code, 0)
            self.assertIn("decision-ready-awaiting-comparative-review", completed)
            code, reviewed = self.run_cli(root, "look-round-review", str(manifest_path))
            self.assertEqual(code, 0)
            review_path = Path(reviewed.splitlines()[0].split("review: ", 1)[1])
            self.assertTrue(review_path.is_file())
            self.assertTrue(review_path.with_name("COMPARISON.md").is_file())


if __name__ == "__main__":
    unittest.main()
