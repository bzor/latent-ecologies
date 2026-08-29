from dataclasses import dataclass
import unittest

from houdini_ai.runners import RunnerRegistry
from houdini_ai.costs import ApprovalRequired


@dataclass(frozen=True)
class ProbeParams:
    seed: int
    label: str = "probe"


class RunnerRegistryTests(unittest.TestCase):
    def test_registered_id_dispatches_with_typed_params(self) -> None:
        registry = RunnerRegistry()
        received = []
        registry.register("behavior.probe", ProbeParams, lambda params: received.append(params) or params.seed)

        result = registry.dispatch("behavior.probe", {"seed": 7})

        self.assertEqual(result, 7)
        self.assertEqual(received, [ProbeParams(seed=7)])

    def test_unregistered_id_never_dispatches(self) -> None:
        registry = RunnerRegistry()
        with self.assertRaises(KeyError):
            registry.dispatch("shell", {"seed": 7})

    def test_params_are_validated_before_runner_is_called(self) -> None:
        registry = RunnerRegistry()
        calls = []
        registry.register("behavior.probe", ProbeParams, lambda params: calls.append(params))

        with self.assertRaises(TypeError):
            registry.dispatch("behavior.probe", {"seed": "seven"})
        with self.assertRaises(TypeError):
            registry.dispatch("behavior.probe", {"seed": 7, "extra": True})

        self.assertEqual(calls, [])

    def test_free_text_cannot_supply_command_arrays(self) -> None:
        registry = RunnerRegistry()
        calls = []
        registry.register("behavior.probe", ProbeParams, lambda params: calls.append(params))

        with self.assertRaises(TypeError):
            registry.dispatch("behavior.probe", {"seed": 7, "command": ["python", "untrusted.py"]})
        with self.assertRaises(TypeError):
            registry.dispatch("behavior.probe", "run python untrusted.py")

        self.assertEqual(calls, [])

    def test_runner_ids_cannot_be_replaced_silently(self) -> None:
        registry = RunnerRegistry()
        registry.register("behavior.probe", ProbeParams, lambda params: None)
        with self.assertRaises(ValueError):
            registry.register("behavior.probe", ProbeParams, lambda params: None)

    def test_gated_runner_requires_matching_approval_receipt(self) -> None:
        registry = RunnerRegistry()
        calls = []
        registry.register("behavior.study", ProbeParams, lambda params: calls.append(params), cost_tier="study")
        with self.assertRaises(ApprovalRequired):
            registry.dispatch("behavior.study", {"seed": 7})
        with self.assertRaises(ApprovalRequired):
            registry.dispatch(
                "behavior.study",
                {"seed": 7},
                approval={"approved": True, "runner_id": "other.runner", "cost_tier": "study"},
            )
        result = registry.dispatch(
            "behavior.study",
            {"seed": 7},
            approval={"approved": True, "runner_id": "behavior.study", "cost_tier": "study"},
        )
        self.assertIsNone(result)
        self.assertEqual(calls, [ProbeParams(seed=7)])


if __name__ == "__main__":
    unittest.main()
