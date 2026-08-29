import hashlib
import tempfile
import unittest
from pathlib import Path

from houdini_ai.promotions import PromotionError, promote_artifact
from houdini_ai.studio_store import StudioStore


class PromotionTests(unittest.TestCase):
    def canonical_chain(self, root: Path, *, artifact_track: str = "behavior") -> tuple[StudioStore, Path]:
        store = StudioStore(root)
        path = root / "work" / "jobs" / "job-a" / "review" / "preview.bin"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"artifact")
        store.create("ideas", "idea-a", {"id": "idea-a", "track": "behavior", "state": "proposed"})
        store.create(
            "proposals",
            "proposal-a",
            {"id": "proposal-a", "idea_id": "idea-a", "track": "behavior", "state": "approved"},
        )
        store.create(
            "experiments",
            "experiment-a",
            {"id": "experiment-a", "proposal_id": "proposal-a", "track": "behavior", "state": "completed"},
        )
        store.create(
            "artifacts",
            "artifact-a",
            {
                "schema_version": 1,
                "id": "artifact-a",
                "experiment_id": "experiment-a",
                "track": artifact_track,
                "state": "verified",
                "path": "work/jobs/job-a/review/preview.bin",
                "sha256": "sha256:" + hashlib.sha256(b"artifact").hexdigest(),
                "verified": True,
                "visibility": "private",
            },
        )
        return store, path

    def test_promotion_requires_complete_compatible_canonical_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store, _ = self.canonical_chain(root)

            component = promote_artifact(store, root, "artifact-a", "behavior", "KC chose the behavior")

            self.assertEqual(component["source_experiment_id"], "experiment-a")
            self.assertEqual(component["source_artifact_ref"], "work/jobs/job-a/review/preview.bin")
            self.assertEqual(component["visibility"], "private")

    def test_verified_study_selected_artifact_can_be_promoted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store, _ = self.canonical_chain(root)
            selected = (
                root / "studies" / "study_002_scar-tissue" / "01_behavior"
                / "03_selected" / "selection_002" / "package-manifest.json"
            )
            selected.parent.mkdir(parents=True)
            selected.write_bytes(b"selected package")
            artifact = {
                **store.read("artifacts", "artifact-a"),
                "path": "studies/study_002_scar-tissue/01_behavior/03_selected/selection_002/package-manifest.json",
                "sha256": "sha256:" + hashlib.sha256(b"selected package").hexdigest(),
            }
            store.update("artifacts", "artifact-a", artifact)

            component = promote_artifact(store, root, "artifact-a", "behavior", "KC chose the Study selection")

            self.assertEqual(component["source_artifact_ref"], artifact["path"])

    def test_promotion_rejects_incomplete_or_incompatible_lineage(self) -> None:
        cases = (
            ("missing proposal", lambda store: store.update("experiments", "experiment-a", {"id": "experiment-a", "proposal_id": "proposal-missing", "track": "behavior", "state": "completed"}), "missing referenced record"),
            ("wrong proposal state", lambda store: store.update("proposals", "proposal-a", {"id": "proposal-a", "idea_id": "idea-a", "track": "behavior", "state": "held"}), "lifecycle"),
            ("wrong experiment state", lambda store: store.update("experiments", "experiment-a", {"id": "experiment-a", "proposal_id": "proposal-a", "track": "behavior", "state": "running"}), "lifecycle"),
            ("track mismatch", lambda store: store.update("artifacts", "artifact-a", {**store.read("artifacts", "artifact-a"), "track": "look"}), "track"),
        )
        for label, mutate, message in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                store, _ = self.canonical_chain(root)
                mutate(store)
                with self.assertRaisesRegex(PromotionError, message):
                    promote_artifact(store, root, "artifact-a", "behavior", "KC chose it")

    def test_promotion_rejects_noncanonical_artifact_record_and_component_kind(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store, canonical_path = self.canonical_chain(root)
            alternate = root / "work" / "preview.bin"
            alternate.parent.mkdir(parents=True, exist_ok=True)
            alternate.write_bytes(canonical_path.read_bytes())
            artifact = {**store.read("artifacts", "artifact-a"), "path": "work/preview.bin"}
            store.update("artifacts", "artifact-a", artifact)
            with self.assertRaisesRegex(PromotionError, "path"):
                promote_artifact(store, root, "artifact-a", "behavior", "KC chose it")

            secret = root / "secret.bin"
            secret.write_bytes(b"secret")
            traversal = {
                **store.read("artifacts", "artifact-a"),
                "path": "work/jobs/job-a/../../../secret.bin",
                "sha256": "sha256:" + hashlib.sha256(b"secret").hexdigest(),
            }
            store.update("artifacts", "artifact-a", traversal)
            with self.assertRaisesRegex(PromotionError, "canonical"):
                promote_artifact(store, root, "artifact-a", "behavior", "KC chose it")

            config_path = root / "work" / "jobs" / "job-a" / "effective-config.json"
            config_path.write_bytes(b"config")
            internal = {
                **store.read("artifacts", "artifact-a"),
                "path": "work/jobs/job-a/effective-config.json",
                "sha256": "sha256:" + hashlib.sha256(b"config").hexdigest(),
            }
            store.update("artifacts", "artifact-a", internal)
            with self.assertRaisesRegex(PromotionError, "artifact output"):
                promote_artifact(store, root, "artifact-a", "behavior", "KC chose it")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store, _ = self.canonical_chain(root)
            with self.assertRaisesRegex(PromotionError, "component kind"):
                promote_artifact(store, root, "artifact-a", "look", "KC chose it")

    def test_promotion_rechecks_checksum_rationale_and_supersession_compatibility(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store, path = self.canonical_chain(root)
            first = promote_artifact(store, root, "artifact-a", "behavior", "first")
            before = dict(first)
            second = promote_artifact(store, root, "artifact-a", "behavior", "second", supersedes_id=first["id"])
            self.assertNotEqual(first["id"], second["id"])
            self.assertEqual(second["supersedes_id"], first["id"])
            self.assertEqual(store.read("components", first["id"]), before)

            path.write_bytes(b"changed")
            with self.assertRaisesRegex(PromotionError, "checksum"):
                promote_artifact(store, root, "artifact-a", "behavior", "again")
            with self.assertRaisesRegex(PromotionError, "rationale"):
                promote_artifact(store, root, "artifact-a", "behavior", "")

    def test_verified_studio_handoff_can_be_promoted_as_cinematography(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StudioStore(root)
            path = root / "work" / "studio" / "handoffs" / "shot-a" / "selected.hiplc"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"handoff")
            store.create("ideas", "idea-shot-a", {"id": "idea-shot-a", "track": "cinematography", "state": "proposed"})
            store.create("proposals", "proposal-shot-a", {"id": "proposal-shot-a", "idea_id": "idea-shot-a", "track": "cinematography", "state": "approved"})
            store.create("experiments", "experiment-shot-a", {"id": "experiment-shot-a", "proposal_id": "proposal-shot-a", "track": "cinematography", "state": "completed"})
            store.create(
                "artifacts",
                "artifact-shot-a",
                {
                    "schema_version": 1,
                    "id": "artifact-shot-a",
                    "experiment_id": "experiment-shot-a",
                    "track": "cinematography",
                    "state": "verified",
                    "path": "work/studio/handoffs/shot-a/selected.hiplc",
                    "sha256": "sha256:" + hashlib.sha256(b"handoff").hexdigest(),
                    "verified": True,
                    "visibility": "private",
                },
            )

            component = promote_artifact(store, root, "artifact-shot-a", "shot", "KC selected the shot family")

            self.assertEqual(component["component_kind"], "shot")
            self.assertEqual(component["track"], "cinematography")


if __name__ == "__main__":
    unittest.main()
