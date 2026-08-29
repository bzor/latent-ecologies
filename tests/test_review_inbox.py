import json
import tempfile
import unittest
from pathlib import Path

from houdini_ai.review_inbox import build_review_inbox
from houdini_ai.studio_sessions import create_session
from houdini_ai.studio_store import StudioStore


class ReviewInboxTests(unittest.TestCase):
    def test_inbox_aggregates_only_open_actionable_work_across_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StudioStore(root)
            session = create_session(
                store,
                {
                    "title": "Pilot",
                    "project_slug": "pilot",
                    "current_phase": "directions",
                    "intent": "Find distinct mechanisms.",
                    "approved_selection_ids": [],
                    "unresolved_questions": ["Which mechanisms are genuinely different?"],
                    "blockers": ["No direction board yet."],
                    "recommended_next_action": "Draft three directions.",
                },
                activate=True,
            )
            store.create("proposals", "proposal-open", {"id": "proposal-open", "state": "proposed", "track": "behavior", "question": "Does it turn over?"})
            store.create("proposals", "proposal-approved", {"id": "proposal-approved", "state": "approved", "track": "behavior", "question": "Already decided"})
            store.create(
                "notes",
                "note-question",
                {"id": "note-question", "created_at": "2026-08-15T10:00:00Z", "category": "question", "stage": "look", "track": "look", "text": "Should color wait for motion?", "visibility": "private"},
            )
            store.create(
                "notes",
                "note-working",
                {"id": "note-working", "created_at": "2026-08-15T09:00:00Z", "category": "working", "stage": "look", "track": "look", "text": "This is working.", "visibility": "private"},
            )
            reviews = root / "work" / "reviews"
            reviews.mkdir(parents=True)
            (reviews / "legacy-study.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "study_id": "legacy-study",
                        "items": [
                            {"id": "comment-open", "created_at": "2026-08-15T11:00:00Z", "kind": "comment", "status": "open", "text": "Inspect the transition.", "job_id": "job-a", "artifact_path": "review/a.mp4"},
                            {"id": "decision-open", "created_at": "2099-08-15T12:00:00Z", "kind": "decision", "decision": "iterate", "status": "acknowledged", "text": "Open the crossing.", "job_id": "job-a", "artifact_path": "review/a.mp4"},
                            {"id": "resolved", "created_at": "2026-08-15T13:00:00Z", "kind": "comment", "status": "resolved", "text": "Done."},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            inbox = build_review_inbox(root)

            self.assertEqual(inbox["session_id"], session["id"])
            self.assertEqual(inbox["total"], 6)
            self.assertEqual(
                set(inbox["counts"]),
                {"artifact-note", "artifact-decision", "proposal", "process-question", "session-question", "session-blocker"},
            )
            self.assertEqual({item["source_type"] for item in inbox["items"]}, set(inbox["counts"]))
            self.assertFalse(any(item["id"] in {"proposal-approved", "note-working", "resolved"} for item in inbox["items"]))
            self.assertTrue(all(item["visibility"] == "private" for item in inbox["items"]))
            self.assertEqual(inbox["items"][0]["id"], "decision-open")


if __name__ == "__main__":
    unittest.main()
