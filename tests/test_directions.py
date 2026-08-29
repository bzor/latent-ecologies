import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from houdini_ai.directions import (
    create_direction,
    decide_direction,
    derive_probe_proposal,
    merge_directions,
    mutate_direction,
)
from houdini_ai.studio_store import StudioStore


def direction(title: str, mechanism: str, outcome: str) -> dict:
    return {
        "title": title,
        "premise": f"{title} asks whether local interactions can organize the whole field.",
        "mechanism": mechanism,
        "expected_emergent_behavior": outcome,
        "cheapest_informative_probe": "Run 120 low-resolution steps and inspect occupancy, flow coherence, and state transitions.",
        "risks": ["The local rule may collapse into a static attractor."],
        "conceptual_distinction": "This changes the causal interaction rule, not merely speeds, thresholds, seeds, or presentation values.",
        "sibling_relations": [],
    }


class DirectionTests(unittest.TestCase):
    def test_multiple_conceptual_directions_can_be_selected_while_siblings_remain_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            store.create("ideas", "idea-pilot", {"id": "idea-pilot", "track": "behavior", "state": "scoped"})
            with patch("houdini_ai.runners.RunnerRegistry.dispatch") as dispatch:
                field = create_direction(store, "idea-pilot", direction(
                    "Reciprocal Scar Field",
                    "Agents deposit a signed memory field; neighboring agents read its gradient and invert their response after repeated exposure.",
                    "Migrating fronts should repeatedly attract, scar, and then repel later populations.",
                ))
                exchange = create_direction(store, "idea-pilot", direction(
                    "Contact Exchange",
                    "Agents exchange discrete internal states only at contact, changing future affinity and producing contagious local alliances.",
                    "Transient coalitions should form, split, and recombine without a global field.",
                ))
                boundary = create_direction(store, "idea-pilot", direction(
                    "Living Boundary",
                    "The occupied region grows and erodes its own boundary; agents move by curvature and local boundary age rather than flocking.",
                    "The population should behave like a breathing membrane with pinches and healing ruptures.",
                ))
                field = decide_direction(store, field["id"], "select")
                exchange = decide_direction(store, exchange["id"], "select")
                boundary = decide_direction(store, boundary["id"], "reject")
                self.assertEqual((field["state"], exchange["state"], boundary["state"]), ("selected", "selected", "rejected"))

                mutant = mutate_direction(store, field["id"], direction(
                    "Delayed Scar Echo",
                    "Agents read an earlier time slice of the signed field, so their response follows delayed evidence rather than the present gradient.",
                    "Delayed feedback should produce traveling echoes and overshoot instead of immediate front reversal.",
                ))
                merged = merge_directions(store, [field["id"], exchange["id"]], direction(
                    "Scar-Borne Exchange",
                    "Contact swaps internal state while the deposited field stores that exchange, coupling direct contagion to persistent spatial memory.",
                    "Coalitions should leave durable territories that alter later contact dynamics.",
                ))
                self.assertEqual(mutant["parent_direction_ids"], [field["id"]])
                self.assertEqual(mutant["relation_kind"], "mutation")
                self.assertEqual(set(merged["parent_direction_ids"]), {field["id"], exchange["id"]})
                self.assertEqual(merged["relation_kind"], "conceptual-merge")
                mutant = decide_direction(store, mutant["id"], "hold")
                self.assertEqual(mutant["state"], "held")
                boundary = decide_direction(store, boundary["id"], "select")
                self.assertEqual(boundary["state"], "selected")
                boundary = decide_direction(store, boundary["id"], "reject")
                self.assertEqual(store.read("directions", field["id"])["state"], "selected")
                self.assertEqual(store.read("directions", boundary["id"])["state"], "rejected")
                dispatch.assert_not_called()

    def test_only_selected_direction_derives_a_separately_approved_probe_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            store.create("ideas", "idea-pilot", {"id": "idea-pilot", "track": "behavior", "state": "scoped"})
            selected = create_direction(store, "idea-pilot", direction(
                "Reciprocal Scar Field",
                "Agents deposit a signed memory field; neighboring agents read its gradient and invert their response after repeated exposure.",
                "Migrating fronts should repeatedly attract, scar, and then repel later populations.",
            ))
            with self.assertRaises(ValueError):
                derive_probe_proposal(store, selected["id"], {
                    "outputs": ["motion-check.mp4", "metrics.json"], "stop_conditions": ["120 steps"],
                    "runner": "behavior.probe", "cost_tier": "probe",
                }, registered_runners={"behavior.probe"})
            decide_direction(store, selected["id"], "select")
            proposal = derive_probe_proposal(store, selected["id"], {
                "outputs": ["motion-check.mp4", "metrics.json"], "stop_conditions": ["120 steps"],
                "runner": "behavior.probe", "cost_tier": "probe",
            }, registered_runners={"behavior.probe"})
            self.assertEqual(proposal["state"], "proposed")
            self.assertEqual(proposal["direction_ids"], [selected["id"]])
            self.assertEqual(proposal["mechanism"], selected["mechanism"])
            self.assertEqual(proposal["hypothesis"], selected["expected_emergent_behavior"])
            self.assertNotIn("approved_at", proposal)

            parameter_only = direction("Faster Variant", "Increase speed from 1.0 to 2.0.", "The agents move faster.")
            parameter_only.pop("conceptual_distinction")
            with self.assertRaises(ValueError):
                create_direction(store, "idea-pilot", parameter_only)


if __name__ == "__main__":
    unittest.main()
