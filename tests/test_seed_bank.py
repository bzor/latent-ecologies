import tempfile
import unittest
from pathlib import Path

from houdini_ai.seed_bank import create_seed, promote_seed_to_study, transition_seed, update_seed
from houdini_ai.studio_schema import validate_record
from houdini_ai.studio_store import StudioStore


class SeedBankTests(unittest.TestCase):
    def test_seed_rejects_ai_style_display_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            with self.assertRaisesRegex(ValueError, "short_summary contains an em dash"):
                create_seed(
                    store,
                    {
                        "title": "Refractory field",
                        "short_summary": "The field stores route history — later agents sample it.",
                        "long_summary": "Agents deposit and sample a scalar field.",
                    },
                )

    def test_brainstorm_updates_are_bounded_and_preserve_seed_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            seed = create_seed(
                store,
                {
                    "title": "Reciprocal Weather",
                    "short_summary": "First summary.",
                    "long_summary": "First long summary.",
                    "reference_links": [],
                    "tags": [],
                },
            )
            updated = update_seed(
                store,
                seed["id"],
                {
                    "title": "Reciprocal Weather Systems",
                    "short_summary": "Agents leave weather that alters affinity.",
                    "long_summary": "A developed account of field memory and nonlocal relationship feedback.",
                    "reference_links": [
                        {"title": "Field memory", "url": "https://example.com/field", "kind": "article"}
                    ],
                    "questions": ["How slowly should the field decay?"],
                    "constraints": ["Preserve realtime behavior."],
                    "tags": ["agents", "field-memory"],
                },
            )
            self.assertEqual(updated["id"], seed["id"])
            self.assertEqual(updated["state"], "inbox")
            self.assertEqual(updated["source_urls"], ["https://example.com/field"])
            with self.assertRaisesRegex(ValueError, "unsupported Seed update fields"):
                update_seed(store, seed["id"], {"state": "promoted"})

    def test_complete_private_seed_promotes_idempotently_to_linked_study(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            seed = create_seed(
                store,
                {
                    "title": "Reciprocal Weather",
                    "short_summary": "Agents create weather that later changes their affinities.",
                    "long_summary": (
                        "A field-driven particle system in which collective motion deposits a slowly evolving atmosphere. "
                        "The atmosphere feeds back into friend and enemy relationships at nonlocal scales."
                    ),
                    "reference_links": [
                        {
                            "title": "Reaction-diffusion systems",
                            "url": "https://example.com/paper",
                            "kind": "paper",
                            "note": "Possible atmosphere model.",
                        }
                    ],
                    "tags": ["agents", "feedback", "weather"],
                    "questions": ["Can the field retain legible memory?"],
                    "constraints": ["Behavior must work in realtime before Look development."],
                },
            )

            self.assertEqual(seed["state"], "inbox")
            self.assertEqual(seed["visibility"], "private")
            self.assertNotIn("track", seed)
            self.assertEqual(validate_record("idea", seed), [])
            transition_seed(store, seed["id"], "incubating")
            ready = transition_seed(store, seed["id"], "ready")
            self.assertEqual(ready["state"], "ready")

            first = promote_seed_to_study(
                store,
                seed["id"],
                study_id="study-004-reciprocal-weather",
                study_title="Study 004 — Reciprocal Weather",
                primary_track="behavior",
                recommended_next_action="Define the smallest realtime Behavior probe.",
            )
            replay = promote_seed_to_study(
                store,
                seed["id"],
                study_id="study-004-reciprocal-weather",
                study_title="Study 004 — Reciprocal Weather",
                primary_track="behavior",
                recommended_next_action="Define the smallest realtime Behavior probe.",
            )

            promoted = store.read("ideas", seed["id"])
            study = store.read("studies", "study-004-reciprocal-weather")
            self.assertEqual(first, replay)
            self.assertEqual(promoted["state"], "promoted")
            self.assertEqual(promoted["promoted_study_id"], study["id"])
            self.assertEqual(promoted["track"], "behavior")
            self.assertEqual(study["idea_id"], seed["id"])
            self.assertEqual(study["intent"], seed["long_summary"])
            self.assertEqual(validate_record("study", study), [])


if __name__ == "__main__":
    unittest.main()
