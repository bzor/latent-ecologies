import tempfile
import unittest
from pathlib import Path

from houdini_ai.proposals import approve_proposal, create_proposal
from houdini_ai.studio_store import StudioStore


VALID = {
    "question": "Does it turn?",
    "mechanism": "Apply a bounded field.",
    "outputs": ["metrics.json"],
    "stop_conditions": ["100 steps"],
    "runner": "behavior.probe",
    "cost_tier": "study",
}


class ProposalTests(unittest.TestCase):
    def test_create_requires_fields_existing_idea_and_registered_runner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            store.create("ideas", "idea-a", {"id": "idea-a", "track": "behavior"})
            proposal = create_proposal(store, "idea-a", VALID, registered_runners={"behavior.probe"})
            self.assertEqual(proposal["state"], "proposed")
            self.assertEqual(proposal["visibility"], "private")
            for field in VALID:
                broken = dict(VALID)
                broken.pop(field)
                with self.subTest(field=field), self.assertRaises(ValueError):
                    create_proposal(store, "idea-a", broken, registered_runners={"behavior.probe"})
            with self.assertRaises(ValueError):
                create_proposal(store, "idea-a", VALID, registered_runners=set())

    def test_approval_changes_state_without_dispatch_and_retains_cost_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            store.create("ideas", "idea-a", {"id": "idea-a", "track": "behavior"})
            proposal = create_proposal(store, "idea-a", VALID, registered_runners={"behavior.probe"})
            approved = approve_proposal(store, proposal["id"])
            self.assertEqual(approved["state"], "approved")
            self.assertEqual(approved["cost_tier"], "study")
            self.assertNotIn("executed", approved)


if __name__ == "__main__":
    unittest.main()
