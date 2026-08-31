import tempfile
import unittest
from pathlib import Path

from houdini_ai.studies import (
    PHASES,
    create_study,
    focus_study,
    focused_study,
    list_studies,
)
from houdini_ai.studio_schema import validate_record
from houdini_ai.studio_store import StudioStore


class StudyTests(unittest.TestCase):
    def test_phases_skip_from_artist_led_look_to_specimen(self) -> None:
        self.assertEqual(PHASES, ("seed", "directions", "behavior", "look", "specimen", "delivery"))

    def payload(self, study_id: str, title: str) -> dict[str, object]:
        return {
            "id": study_id,
            "title": title,
            "state": "active",
            "current_phase": "behavior",
            "intent": "Find a behavior worth developing.",
            "approved_selection_ids": [],
            "unresolved_questions": ["Which branch preserves the strongest morphology?"],
            "blockers": [],
            "recommended_next_action": "Compare the verified branches.",
        }

    def test_multiple_studies_can_be_active_while_focus_is_one_atomic_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            first = create_study(
                store,
                self.payload("study-003-nonlocal-affinity-dance", "Study 003 — Nonlocal Affinity Dance"),
                focus=True,
            )
            second = create_study(
                store,
                self.payload("study-004-field-memory", "Study 004 — Field Memory"),
            )

            self.assertEqual(validate_record("study", first), [])
            self.assertEqual(validate_record("study", second), [])
            self.assertEqual(first["state"], "active")
            self.assertEqual(second["state"], "active")
            self.assertEqual(focused_study(store)["id"], first["id"])

            focus_study(store, second["id"])

            records = list_studies(store)
            self.assertEqual([item["id"] for item in records if item["is_focused"]], [second["id"]])
            self.assertEqual({item["state"] for item in records}, {"active"})
            self.assertTrue((Path(directory) / "studio" / "study-state" / "focused.json").is_file())


if __name__ == "__main__":
    unittest.main()
