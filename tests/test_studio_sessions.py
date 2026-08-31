import tempfile
import unittest
from pathlib import Path

from houdini_ai.studio_sessions import PHASES, activate_session, active_session, create_session, list_sessions
from houdini_ai.studio_store import StudioStore


class StudioSessionTests(unittest.TestCase):
    def payload(self, title: str, phase: str = "seed") -> dict:
        return {
            "title": title,
            "project_slug": title.lower().replace(" ", "-"),
            "current_phase": phase,
            "intent": "  Explore $(touch escaped) as creative prose, never a command.  ",
            "approved_selection_ids": [],
            "unresolved_questions": ["What is the cheapest informative probe?"],
            "blockers": [],
            "recommended_next_action": "Develop distinct behavior directions.",
        }

    def test_one_atomic_active_pointer_keeps_other_open_sessions_resumable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StudioStore(root)

            first = create_session(store, self.payload("First Study"), activate=True)
            second = create_session(store, self.payload("Second Study", "directions"))

            self.assertEqual(active_session(store)["id"], first["id"])
            activate_session(store, second["id"])

            sessions = list_sessions(store)
            self.assertEqual([item["id"] for item in sessions if item["is_active"]], [second["id"]])
            resumable = next(item for item in sessions if item["id"] == first["id"])
            self.assertEqual(resumable["state"], "open")
            self.assertFalse(resumable["is_active"])
            self.assertEqual(resumable["intent"], self.payload("First Study")["intent"])
            self.assertFalse((root / "escaped").exists())
            self.assertEqual(
                PHASES,
                ("seed", "directions", "behavior", "look", "specimen", "delivery"),
            )
            self.assertTrue((root / "studio" / "session-state" / "active.json").is_file())

    def test_activation_rejects_unknown_or_path_like_session_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            for session_id in ("session-missing", "../../outside"):
                with self.subTest(session_id=session_id), self.assertRaises((FileNotFoundError, ValueError)):
                    activate_session(store, session_id)


if __name__ == "__main__":
    unittest.main()
