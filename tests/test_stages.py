import unittest

from houdini_ai.stages import (
    BEHAVIOR_GRAPH,
    CAMERA_GRAPH,
    LEGACY_GRAPH,
    LOOK_GRAPH,
    StageGraph,
)


class StageGraphTests(unittest.TestCase):
    def test_legacy_graph_preserves_existing_stage_order(self) -> None:
        self.assertEqual(
            LEGACY_GRAPH.stages,
            ("validate", "build", "simulate", "probe", "render", "composite", "encode", "package"),
        )

    def test_behavior_graph_has_foundational_stages(self) -> None:
        self.assertEqual(BEHAVIOR_GRAPH.stages, ("validate", "build", "simulate", "instrument", "package"))

    def test_look_and_camera_graphs_are_declarable(self) -> None:
        self.assertIsInstance(LOOK_GRAPH, StageGraph)
        self.assertIsInstance(CAMERA_GRAPH, StageGraph)
        self.assertTrue(LOOK_GRAPH.stages)
        self.assertTrue(CAMERA_GRAPH.stages)

    def test_graph_rejects_empty_or_duplicate_stage_ids(self) -> None:
        with self.assertRaises(ValueError):
            StageGraph("empty", ())
        with self.assertRaises(ValueError):
            StageGraph("duplicate", ("validate", "validate"))


if __name__ == "__main__":
    unittest.main()
