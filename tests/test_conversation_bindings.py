import tempfile
import unittest
from pathlib import Path

from houdini_ai.conversation_bindings import bind_discord_thread, deactivate_binding, resolve_discord_thread
from houdini_ai.seed_bank import create_seed
from houdini_ai.studies import create_study
from houdini_ai.studio_schema import validate_record
from houdini_ai.studio_store import StudioStore


class ConversationBindingTests(unittest.TestCase):
    def make_study(self, store: StudioStore, study_id: str) -> None:
        create_study(
            store,
            {
                "id": study_id,
                "title": study_id,
                "intent": "Develop the study.",
                "recommended_next_action": "Review evidence.",
            },
        )

    def make_seed(self, store: StudioStore) -> dict:
        return create_seed(
            store,
            {
                "title": "Fieldwriting Ants",
                "short_summary": "Agents write a shared field.",
                "long_summary": "Deterministic agents read and rewrite one shared spatial field.",
            },
        )

    def test_discord_thread_resolves_to_one_seed_without_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            seed = self.make_seed(store)

            binding = bind_discord_thread(
                store,
                seed_id=seed["id"],
                guild_id="123456789012345678",
                parent_channel_id="223456789012345678",
                thread_id="323456789012345678",
            )

            self.assertEqual(validate_record("conversation-binding", binding), [])
            self.assertEqual(resolve_discord_thread(store, binding["thread_id"])["seed_id"], seed["id"])
            self.assertNotIn("token", " ".join(binding).lower())
            self.assertEqual(
                bind_discord_thread(
                    store,
                    seed_id=seed["id"],
                    guild_id=binding["guild_id"],
                    parent_channel_id=binding["parent_channel_id"],
                    thread_id=binding["thread_id"],
                ),
                binding,
            )

    def test_discord_thread_resolves_to_one_study_without_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            self.make_study(store, "study-003-nonlocal-affinity-dance")

            binding = bind_discord_thread(
                store,
                study_id="study-003-nonlocal-affinity-dance",
                guild_id="123456789012345678",
                parent_channel_id="223456789012345678",
                thread_id="323456789012345678",
            )

            self.assertEqual(validate_record("conversation-binding", binding), [])
            self.assertEqual(resolve_discord_thread(store, "323456789012345678")["study_id"], binding["study_id"])
            self.assertNotIn("token", " ".join(binding).lower())
            self.assertEqual(
                bind_discord_thread(
                    store,
                    study_id=binding["study_id"],
                    guild_id=binding["guild_id"],
                    parent_channel_id=binding["parent_channel_id"],
                    thread_id=binding["thread_id"],
                ),
                binding,
            )

            deactivated = deactivate_binding(store, binding["id"])
            self.assertEqual(deactivated["state"], "inactive")
            with self.assertRaisesRegex(FileNotFoundError, "active Discord binding"):
                resolve_discord_thread(store, binding["thread_id"])

    def test_one_active_thread_cannot_bind_to_two_studies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            self.make_study(store, "study-a")
            self.make_study(store, "study-b")
            bind_discord_thread(
                store,
                study_id="study-a",
                guild_id="123456789012345678",
                parent_channel_id="223456789012345678",
                thread_id="323456789012345678",
            )

            with self.assertRaisesRegex(ValueError, "already bound"):
                bind_discord_thread(
                    store,
                    study_id="study-b",
                    guild_id="123456789012345678",
                    parent_channel_id="223456789012345678",
                    thread_id="323456789012345678",
                )

    def test_one_seed_cannot_bind_to_two_active_threads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            seed = self.make_seed(store)
            bind_discord_thread(
                store,
                seed_id=seed["id"],
                guild_id="123456789012345678",
                parent_channel_id="223456789012345678",
                thread_id="323456789012345678",
            )

            with self.assertRaisesRegex(ValueError, "already bound"):
                bind_discord_thread(
                    store,
                    seed_id=seed["id"],
                    guild_id="123456789012345678",
                    parent_channel_id="223456789012345678",
                    thread_id="423456789012345678",
                )


if __name__ == "__main__":
    unittest.main()
