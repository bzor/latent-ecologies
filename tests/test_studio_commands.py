import tempfile
import unittest
from pathlib import Path

from houdini_ai.studies import create_study
from houdini_ai.studio_commands import CommandContext, execute_idempotent
from houdini_ai.studio_schema import validate_record
from houdini_ai.studio_store import StudioStore


class StudioCommandTests(unittest.TestCase):
    def test_seed_targeted_command_receives_a_private_idempotent_activity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            seed = {
                "schema_version": 1,
                "id": "idea-seed-a",
                "title": "Seed A",
                "raw_text": "Private seed context.",
                "state": "inbox",
                "visibility": "private",
            }
            store.create("ideas", seed["id"], seed)
            context = CommandContext(
                seed_id=seed["id"],
                actor="kc",
                origin="discord",
                source_ref="discord:seed-thread:message-1",
                idempotency_key="discord:message-1:seed.promote",
            )

            def operation() -> dict[str, object]:
                return {"id": "study-004-seed-a", "state": "active"}

            first = execute_idempotent(store, context, "seed.promote", operation, summary="Promote Seed A.")
            replay = execute_idempotent(store, context, "seed.promote", operation, summary="Promote Seed A.")
            self.assertEqual(first["activity"]["seed_id"], seed["id"])
            self.assertNotIn("study_id", first["activity"])
            self.assertFalse(first["replayed"])
            self.assertTrue(replay["replayed"])
            self.assertEqual(validate_record("activity", first["activity"]), [])

    def test_replayed_discord_command_returns_original_receipt_without_mutating_twice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            create_study(
                store,
                {
                    "id": "study-003-nonlocal-affinity-dance",
                    "title": "Study 003",
                    "intent": "Preserve exact behavior identity.",
                    "recommended_next_action": "Review the comparison.",
                },
            )
            context = CommandContext(
                study_id="study-003-nonlocal-affinity-dance",
                actor="kc",
                origin="discord",
                source_ref="discord:123456789012345678:323456789012345678:423456789012345678",
                idempotency_key="discord:423456789012345678:site.include:artifact-a",
            )
            calls = 0

            def operation() -> dict[str, object]:
                nonlocal calls
                calls += 1
                store.create("test-results", "result-a", {"id": "result-a"})
                return {"id": "result-a", "state": "created"}

            first = execute_idempotent(store, context, "site.include", operation, summary="Include the comparison.")
            second = execute_idempotent(store, context, "site.include", operation, summary="Include the comparison.")

            self.assertEqual(calls, 1)
            self.assertFalse(first["replayed"])
            self.assertTrue(second["replayed"])
            self.assertEqual(first["result"], second["result"])
            self.assertEqual(first["activity"]["id"], second["activity"]["id"])
            self.assertEqual(first["activity"]["result_refs"], ["result-a"])
            self.assertEqual(validate_record("activity", first["activity"]), [])

            with self.assertRaisesRegex(ValueError, "idempotency key"):
                execute_idempotent(store, context, "artifact.decide", operation, summary="Different action.")


if __name__ == "__main__":
    unittest.main()
