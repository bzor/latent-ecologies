import unittest

from houdini_ai.costs import ApprovalRequired, CostGate, CostTier


class CostGateTests(unittest.TestCase):
    def test_tiny_cost_can_run_without_separate_approval(self) -> None:
        CostGate().require(CostTier.TINY, approved=False)

    def test_probe_cost_can_run_without_separate_approval(self) -> None:
        gate = CostGate()
        gate.require(CostTier.PROBE, approved=False)

    def test_study_specimen_and_external_costs_require_explicit_approval(self) -> None:
        gate = CostGate()
        for tier in (CostTier.STUDY, CostTier.SPECIMEN, CostTier.EXTERNAL):
            with self.subTest(tier=tier):
                with self.assertRaises(ApprovalRequired):
                    gate.require(tier, approved=False)

    def test_explicit_approval_allows_gated_costs(self) -> None:
        gate = CostGate()
        for tier in (CostTier.STUDY, CostTier.SPECIMEN, CostTier.EXTERNAL):
            with self.subTest(tier=tier):
                gate.require(tier, approved=True)

    def test_truthy_non_boolean_is_not_explicit_approval(self) -> None:
        gate = CostGate()
        with self.assertRaises(ApprovalRequired):
            gate.require(CostTier.STUDY, approved="yes")

    def test_unknown_cost_tier_is_rejected(self) -> None:
        gate = CostGate()
        with self.assertRaises(ValueError):
            gate.require("expensive", approved=True)


if __name__ == "__main__":
    unittest.main()
