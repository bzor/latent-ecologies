import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from houdini_ai.pilot_study_003 import bootstrap_pilot_study_003
from houdini_ai.studio_sessions import active_session
from houdini_ai.studio_store import StudioStore


SOURCE_URL = "https://community.wolfram.com/groups/-/m/t/122095"


class PilotStudy003Tests(unittest.TestCase):
    def test_bootstrap_is_idempotent_provenance_rich_and_never_dispatches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StudioStore(root)
            with patch("houdini_ai.runners.RunnerRegistry.dispatch") as dispatch:
                first = bootstrap_pilot_study_003(root)
                second = bootstrap_pilot_study_003(root)

            self.assertEqual(first, second)
            self.assertEqual(first["idea"]["title"], "Nonlocal Affinity Dance")
            self.assertEqual(first["idea"]["source_urls"], [SOURCE_URL])
            self.assertEqual(first["idea"]["questions"], [
                "How does a mutable network of attraction and aversion write itself into spatial form?"
            ])
            self.assertEqual(first["idea"]["extensions"]["studio/source-author"], "Simon Woods")
            self.assertEqual(first["idea"]["extensions"]["studio/source-role"], "faithful-launchpad")

            directions = first["directions"]
            self.assertEqual(len(directions), 3)
            self.assertEqual(
                {item["title"]: item["state"] for item in directions},
                {
                    "Faithful Nonlocal Signed Graph": "selected",
                    "Graph Choreography": "held",
                    "Encounter Memory": "held",
                },
            )
            faithful = next(item for item in directions if item["title"].startswith("Faithful"))
            self.assertIn("0.995", faithful["mechanism"])
            self.assertIn("0.02", faithful["mechanism"])
            self.assertIn("0.01", faithful["mechanism"])

            proposal = first["proposal"]
            self.assertEqual(proposal["state"], "proposed")
            self.assertEqual(proposal["direction_ids"], [faithful["id"]])
            self.assertEqual(proposal["runner"], "behavior.probe")
            self.assertEqual(proposal["cost_tier"], "probe")
            self.assertEqual(proposal["extensions"]["studio/execution-authority"], "separate-approval-required")

            session = active_session(store)
            self.assertIsNotNone(session)
            self.assertEqual(session["project_slug"], "pilot-study-003")
            self.assertEqual(session["current_phase"], "directions")
            self.assertEqual(session["idea_id"], first["idea"]["id"])
            self.assertEqual(session["selected_branch_id"], faithful["id"])
            dispatch.assert_not_called()

            for collection, expected in (("ideas", 1), ("directions", 3), ("proposals", 1), ("sessions", 1)):
                records, errors = store.list(collection)
                self.assertEqual(errors, [])
                self.assertEqual(len(records), expected)


if __name__ == "__main__":
    unittest.main()
