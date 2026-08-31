import tempfile
import unittest
from pathlib import Path

from houdini_ai.seed_bank import build_seed_digest
from houdini_ai.studio_store import StudioStore


def seed(store: StudioStore, seed_id: str, **fields) -> None:
    record = {"schema_version": 1, "id": seed_id, "state": "inbox", "track": "behavior", "visibility": "private"}
    record.update(fields)
    store.create("ideas", seed_id, record)


class SeedDigestTests(unittest.TestCase):
    def test_digest_groups_by_lifecycle_oldest_first_and_counts_archived(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            seed(store, "idea-young", title="Young Seed", created_at="2026-08-30T10:00:00Z")
            seed(store, "idea-old", title="Old Seed", created_at="2026-08-01T10:00:00Z", questions=["q1", "q2"])
            seed(
                store, "idea-done", title="Done Seed", state="promoted",
                created_at="2026-08-10T10:00:00Z", promoted_study_id="study-009-example",
            )
            seed(store, "idea-gone", title="Gone", state="archived", created_at="2026-08-02T10:00:00Z")
            digest = build_seed_digest(store, today="2026-08-31")
            self.assertIn("Seed Bank digest · 2026-08-31", digest)
            self.assertLess(digest.index("Old Seed"), digest.index("Young Seed"))
            self.assertIn("2 open question(s)", digest)
            self.assertIn("-> study-009-example", digest)
            self.assertIn("_1 archived seed(s) held as evidence._", digest)
            self.assertNotIn("Gone", digest)

    def test_digest_truncates_titles_and_flags_unknown_states(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            seed(store, "idea-long", title="x" * 120, created_at="2026-08-20T10:00:00Z")
            seed(store, "idea-odd", title="Odd", state="mystery", created_at="2026-08-20T10:00:00Z")
            digest = build_seed_digest(store, today="2026-08-31")
            self.assertIn("x" * 87 + "...", digest)
            self.assertNotIn("x" * 91, digest)
            self.assertIn("unrecognized lifecycle state", digest)


if __name__ == "__main__":
    unittest.main()
