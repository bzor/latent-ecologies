import tempfile
import unittest
from pathlib import Path

from houdini_ai.editorial import EditorialError, approve_editorial, editorial_summary, tag_artifact, untag_artifact
from houdini_ai.studio_store import StudioStore


class EditorialTests(unittest.TestCase):
    def test_tags_are_validated_deduplicated_and_remain_private(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            store.create("artifacts", "artifact-a", {"id": "artifact-a", "path": "work/a.mp4"})
            record = tag_artifact(store, "artifact-a", ["publish:x", "publish:x", "role:field-observation"])
            self.assertEqual(record["tags"], ["publish:x", "role:field-observation"])
            self.assertEqual(record["visibility"], "private")
            self.assertFalse(record["approved"])
            with self.assertRaises(EditorialError):
                tag_artifact(store, "artifact-a", ["role:invented"])
            updated = untag_artifact(store, "artifact-a", "publish:x")
            self.assertEqual(updated["tags"], ["role:field-observation"])

    def test_readiness_approved_requires_separate_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            store.create("artifacts", "artifact-a", {"id": "artifact-a", "path": "work/a.mp4"})
            with self.assertRaises(EditorialError):
                tag_artifact(store, "artifact-a", ["readiness:approved"])
            record = tag_artifact(store, "artifact-a", ["publish:web", "readiness:ready-for-approval"])
            approved = approve_editorial(store, record["id"])
            self.assertEqual(approved["state"], "approved")
            self.assertTrue(approved["approved"])
            self.assertIn("readiness:approved", approved["tags"])
            self.assertEqual(editorial_summary(store), [approved])

    def test_approval_requires_ready_state_and_remains_schema_valid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            store.create("artifacts", "artifact-a", {"id": "artifact-a", "path": "work/a.mp4"})
            draft = tag_artifact(store, "artifact-a", ["publish:web"])
            with self.assertRaisesRegex(EditorialError, "ready-for-approval"):
                approve_editorial(store, draft["id"])
            ready = tag_artifact(store, "artifact-a", ["readiness:ready-for-approval"])
            approved = approve_editorial(store, ready["id"])
            from houdini_ai.studio_schema import validate_record

            self.assertEqual(validate_record("editorial", approved), [])


if __name__ == "__main__":
    unittest.main()
