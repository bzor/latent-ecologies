import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from houdini_ai.nonlocal_affinity import (
    AffinityConfig,
    AffinityParameters,
    AffinityState,
    RewireEvent,
    baseline_config,
    cohort_lift_prepared,
    final_prepared_relationships,
    lift_prepared_to_3d,
    prepare_canvas_run,
    prepare_reference_run,
    simulate_prepared,
    simulate_reference,
    step_state,
)
from houdini_ai.nonlocal_affinity_artifacts import package_motion_check


class NonlocalAffinityTests(unittest.TestCase):
    def test_cohort_lift_preserves_every_macro_edge_and_expands_every_rewire(self) -> None:
        prepared = {
            "initial_positions": [[-0.5, 0.25, 0.1], [0.75, -0.2, -0.05], [0.0, 0.6, 0.02]],
            "friends": [1, 2, 0],
            "enemies": [2, 0, 1],
            "rewire_events": [{"step": 2, "point": 1, "friend": 0, "enemy": 2}],
        }

        lifted = cohort_lift_prepared(
            prepared, seed=19, cohort_size=4, radius=0.02, routing="neighbor",
        )
        repeated = cohort_lift_prepared(
            prepared, seed=19, cohort_size=4, radius=0.02, routing="neighbor",
        )

        self.assertEqual(lifted, repeated)
        self.assertEqual(len(lifted["initial_positions"]), 12)
        self.assertEqual(len(lifted["rewire_events"]), 4)
        for anchor in range(3):
            self.assertEqual(lifted["initial_positions"][anchor * 4], prepared["initial_positions"][anchor])
            for member in range(4):
                point = anchor * 4 + member
                self.assertEqual(lifted["friends"][point] // 4, prepared["friends"][anchor])
                self.assertEqual(lifted["enemies"][point] // 4, prepared["enemies"][anchor])
                self.assertLessEqual(math.dist(lifted["initial_positions"][point], prepared["initial_positions"][anchor]), 0.02)
        for event in lifted["rewire_events"]:
            self.assertEqual(event["step"], 2)
            self.assertEqual(event["point"] // 4, 1)
            self.assertEqual(event["friend"] // 4, 0)
            self.assertEqual(event["enemy"] // 4, 2)
        final_friends, final_enemies = final_prepared_relationships(lifted)
        for member in range(4):
            point = 4 + member
            self.assertEqual(final_friends[point] // 4, 0)
            self.assertEqual(final_enemies[point] // 4, 2)

    def test_canvas_receipt_lift_preserves_xy_graph_and_events_while_adding_bounded_z(self) -> None:
        config = AffinityConfig(seed=7, agent_count=8, steps=3, dimensions=2)
        prepared = prepare_canvas_run(config, rewire_probability=0.5)
        lifted = lift_prepared_to_3d(prepared, seed=config.seed, depth=0.15)
        repeated = lift_prepared_to_3d(prepared, seed=config.seed, depth=0.15)

        self.assertEqual(lifted, repeated)
        self.assertEqual(lifted["friends"], prepared["friends"])
        self.assertEqual(lifted["enemies"], prepared["enemies"])
        self.assertEqual(lifted["rewire_events"], prepared["rewire_events"])
        self.assertTrue(all(position[:2] == source for position, source in zip(lifted["initial_positions"], prepared["initial_positions"])))
        self.assertTrue(all(-0.15 <= position[2] <= 0.15 for position in lifted["initial_positions"]))
        self.assertTrue(any(position[2] != 0.0 for position in lifted["initial_positions"]))

    def test_canvas_mulberry32_receipt_matches_javascript_draw_order_and_trajectory(self) -> None:
        config = AffinityConfig(
            seed=7,
            agent_count=4,
            steps=3,
            dimensions=2,
            rewires_per_event=2,
            parameters=AffinityParameters(contraction=0.9898, attraction=0.02, repulsion=0.01, softening=0.009),
        )
        prepared = prepare_canvas_run(config, rewire_probability=1.0)
        result = simulate_prepared(config, prepared)

        expected_initial = (
            (-0.9765904936939478, -0.8760834848508239),
            (0.95381526555866, 0.39805741142481565),
            (0.042890537064522505, -0.18895662389695644),
            (-0.06753473496064544, -0.5201496281661093),
        )
        expected_final = (
            (-0.912162551760891, -0.8317740923320385),
            (0.9000872913560349, 0.37019895601801045),
            (0.0769356888340302, -0.15297908023510595),
            (-0.12756541998661744, -0.5321643761572216),
        )
        self.assertEqual(tuple(tuple(item) for item in prepared["initial_positions"]), expected_initial)
        self.assertEqual(prepared["friends"], [2, 2, 1, 0])
        self.assertEqual(prepared["enemies"], [3, 2, 0, 1])
        self.assertEqual(len(prepared["rewire_events"]), 6)
        self.assertEqual(result["friends"], [1, 2, 3, 0])
        self.assertEqual(result["enemies"], [2, 2, 3, 3])
        for actual, expected in zip(result["final_positions"], expected_final):
            for actual_value, expected_value in zip(actual, expected):
                self.assertAlmostEqual(actual_value, expected_value, places=14)

    def test_one_step_matches_source_equation_with_softened_normalized_offsets(self) -> None:
        state = AffinityState(
            positions=((1.0, 0.0), (3.0, 0.0), (1.0, 4.0)),
            friends=(1, 1, 2),
            enemies=(2, 1, 2),
        )
        result = step_state(state, AffinityParameters())

        self.assertAlmostEqual(result.positions[0][0], 1.0149004975124378, places=12)
        self.assertAlmostEqual(result.positions[0][1], -0.009975062344139652, places=12)
        self.assertEqual(result.positions[1], (2.985, 0.0))
        self.assertEqual(result.positions[2], (0.995, 3.98))
        self.assertEqual(result.friends, state.friends)
        self.assertEqual(result.enemies, state.enemies)

    def test_rewire_precedes_a_synchronous_position_update(self) -> None:
        state = AffinityState(
            positions=((0.0,), (10.0,), (20.0,)),
            friends=(0, 0, 1),
            enemies=(0, 0, 1),
        )
        result = step_state(state, AffinityParameters(), RewireEvent(point=0, friend=1, enemy=2))

        self.assertAlmostEqual(result.positions[0][0], 0.009985017481269357, places=12)
        self.assertAlmostEqual(result.positions[1][0], 9.94000999000999, places=12)
        self.assertEqual(result.friends, (1, 0, 1))
        self.assertEqual(result.enemies, (2, 0, 1))

    def test_one_gate_can_apply_an_ordered_rewire_batch_before_one_synchronous_step(self) -> None:
        state = AffinityState(
            positions=((0.0,), (10.0,), (20.0,)),
            friends=(0, 0, 1),
            enemies=(0, 0, 1),
        )
        events = (
            RewireEvent(point=0, friend=1, enemy=2),
            RewireEvent(point=1, friend=2, enemy=0),
        )
        result = step_state(state, AffinityParameters(), events)

        self.assertEqual(result.friends, (1, 2, 1))
        self.assertEqual(result.enemies, (2, 0, 1))
        self.assertAlmostEqual(result.positions[0][0], 0.009985017481269357, places=12)
        self.assertAlmostEqual(result.positions[1][0], 9.97997002997003, places=12)

        config = AffinityConfig(
            seed=7,
            agent_count=8,
            steps=3,
            rewire_gate_denominator=1,
            rewire_gate_exclusive_max=2,
            rewires_per_event=4,
        )
        prepared = prepare_reference_run(config)
        self.assertEqual(len(prepared["rewire_events"]), 12)
        self.assertEqual([event["step"] for event in prepared["rewire_events"]], [1] * 4 + [2] * 4 + [3] * 4)

    def test_seeded_baseline_run_is_reproducible_seed_sensitive_and_instrumented(self) -> None:
        config = baseline_config(seed=122095, agent_count=64, steps=40)
        first = simulate_reference(config)
        second = simulate_reference(config)
        changed = simulate_reference(baseline_config(seed=122096, agent_count=64, steps=40))

        self.assertEqual(config.dimensions, 2)
        self.assertEqual(config.parameters, AffinityParameters())
        self.assertEqual(first["state_sha256"], second["state_sha256"])
        self.assertEqual(first["rewire_events"], second["rewire_events"])
        self.assertNotEqual(first["state_sha256"], changed["state_sha256"])
        self.assertEqual(first["agent_count"], 64)
        self.assertEqual(first["steps"], 40)
        self.assertEqual(first["invalid_values"], 0)
        self.assertEqual(len(first["checkpoints"]), 6)
        self.assertTrue(all(
            0 <= event[field] < 64
            for event in first["rewire_events"]
            for field in ("point", "friend", "enemy")
        ))

    def test_prepared_run_contains_only_initial_state_and_stochastic_events(self) -> None:
        config = baseline_config(seed=7, agent_count=8, steps=3)
        prepared = prepare_reference_run(config)
        metrics = simulate_reference(config)

        self.assertEqual(set(prepared), {"initial_positions", "friends", "enemies", "rewire_events"})
        self.assertEqual(len(prepared["initial_positions"]), 8)
        self.assertEqual(prepared["rewire_events"], metrics["rewire_events"])
        self.assertNotIn("final_positions", prepared)
        self.assertNotIn("state_sha256", prepared)

    def test_motion_check_packages_authoritative_trajectory_with_verified_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trajectory = root / "trajectory.json"
            trajectory.write_text(json.dumps({
                "state_authority": "vex-geometry",
                "frames": [
                    {"step": 0, "positions": [[-1.0, -1.0], [1.0, 1.0]]},
                    {"step": 1, "positions": [[-0.5, -0.5], [0.5, 0.5]]},
                ],
            }), encoding="utf-8")
            receipt = package_motion_check(trajectory, root / "motion", fps=2, size=(64, 64))

            self.assertEqual(receipt["state_authority"], "vex-geometry")
            self.assertEqual(receipt["frame_count"], 2)
            self.assertEqual(receipt["render_style"], "neutral-fixed-range-points")
            self.assertTrue((root / "motion/motion-check.mp4").is_file())
            with Image.open(root / "motion/frames/frame-0000.png") as frame:
                self.assertEqual(frame.size, (64, 64))
            for relative, digest in receipt["sha256"].items():
                self.assertEqual(hashlib.sha256((root / "motion" / relative).read_bytes()).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()
