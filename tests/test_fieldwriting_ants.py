import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from houdini_ai.fieldwriting_ants import (
    detect_tail_period,
    enumerate_near_rules,
    hamann_direction_result,
    package_direction,
    render_direction_frames,
    simulate_collision_colony,
    simulate_chiral_highway_pair,
    simulate_hamann,
    simulate_langton_2d,
    simulate_shared_2d_colony,
    simulate_ring_excavator,
    simulate_wound_healing_colony,
    summarize_direction,
)
from houdini_ai.fieldwriting_ants_robustness import (
    run_a3_robustness_matrix,
    run_c2_robustness_matrix,
    serializable_robustness_report,
)
from scripts.build_fieldwriting_ant_robustness import checksum as robustness_checksum
from scripts.freeze_fieldwriting_ant_c2_radius2_selection import build_c2_radius2_selection_result
from houdini_ai.fieldwriting_ants_selection import freeze_fieldwriting_behavior
from houdini_ai.fieldwriting_ants_offshoots import (
    analyze_offshoot_candidate,
    detect_translating_tail,
    simulate_rul_bridge_feedback_variant,
    simulate_rul_bridge_variant,
)
from houdini_ai.fieldwriting_ants_c2_options import (
    c2_compact_configurations,
    c2_prewarmed_configurations,
    prewarmed_snapshot_window,
)


class FieldwritingAntTests(unittest.TestCase):
    def test_radius2_promotion_builder_reproduces_reviewed_behavior(self) -> None:
        result = build_c2_radius2_selection_result()

        self.assertEqual(result.steps, 1_200)
        self.assertEqual(result.metrics["schedule"], "synchronous-read-intent-commit")
        self.assertEqual(result.metrics["collision_policy"], "frame-exchange")
        self.assertEqual(result.metrics["initial_agents"][0][0], (2, 0, 0))
        self.assertEqual(
            summarize_direction(result)["state_sha256"],
            "992fc62e45e85eec6b383735f79357fb44be42609df9d1e5865fff35ab7d2525",
        )

    def test_c2_prewarmed_round_has_torsion_plus_two_distinct_order_invariant_options(self) -> None:
        configurations = c2_prewarmed_configurations()
        self.assertEqual(tuple(configurations), ("torsion-cage", "torsion-split", "orbital-shear"))
        hashes = set()
        for name, configuration in configurations.items():
            agents = configuration["initial_agents"]
            forward = simulate_collision_colony(
                "RLRU",
                steps=2_400,
                snapshot_interval=15,
                collision_policy="frame-exchange",
                initial_agents=agents,
            )
            reverse = simulate_collision_colony(
                "RLRU",
                steps=2_400,
                snapshot_interval=15,
                collision_policy="frame-exchange",
                initial_agents=agents,
                transaction_order=tuple(reversed(range(6))),
            )
            self.assertEqual(forward.trajectories, reverse.trajectories, name)
            self.assertEqual(forward.field, reverse.field, name)
            self.assertGreater(forward.metrics["frame_exchanges"], 0, name)
            hashes.add(summarize_direction(forward)["state_sha256"])
            window = prewarmed_snapshot_window(forward, start_step=600)
            self.assertEqual(window.snapshots[0].step, 600)
            self.assertEqual(window.snapshots[-1].step, 2_400)
            self.assertEqual(len(window.snapshots), 121)
            self.assertEqual(window.trajectories, forward.trajectories)
            self.assertEqual(window.field, forward.field)
        self.assertEqual(len(hashes), 3)

    def test_c2_compact_round_has_control_and_three_order_invariant_parameter_options(self) -> None:
        configurations = c2_compact_configurations()

        self.assertEqual(
            tuple(configurations),
            ("radius-2-control", "torsion-cage", "split-core", "orbital-cage"),
        )
        hashes = set()
        for name, configuration in configurations.items():
            agents = configuration["initial_agents"]
            self.assertEqual(len(agents), 6)
            self.assertEqual(configuration["rule"], "RLRU")
            self.assertEqual(configuration["collision_policy"], "frame-exchange")
            forward = simulate_collision_colony(
                configuration["rule"],
                steps=1_200,
                snapshot_interval=1_200,
                collision_policy=configuration["collision_policy"],
                initial_agents=agents,
                transaction_order=tuple(range(6)),
            )
            reverse = simulate_collision_colony(
                configuration["rule"],
                steps=1_200,
                snapshot_interval=1_200,
                collision_policy=configuration["collision_policy"],
                initial_agents=agents,
                transaction_order=tuple(reversed(range(6))),
            )
            self.assertEqual(forward.trajectories, reverse.trajectories, name)
            self.assertEqual(forward.field, reverse.field, name)
            self.assertGreater(forward.metrics["frame_exchanges"], 0, name)
            hashes.add(summarize_direction(forward)["state_sha256"])
        self.assertEqual(len(hashes), 4)
        self.assertEqual(
            summarize_direction(
                simulate_collision_colony(
                    "RLRU",
                    steps=1_200,
                    snapshot_interval=1_200,
                    collision_policy="frame-exchange",
                    initial_agents=configurations["radius-2-control"]["initial_agents"],
                )
            )["state_sha256"],
            "992fc62e45e85eec6b383735f79357fb44be42609df9d1e5865fff35ab7d2525",
        )

    def test_classic_2d_rl_reference_reproduces_period_104_highway(self) -> None:
        result = simulate_langton_2d("RL", steps=20_000)

        self.assertEqual(detect_tail_period(result.commands, candidates=[104]), 104)
        self.assertEqual({point[2] for point in result.trajectory}, {0})

    def test_synchronous_2d_shared_field_reference_has_explicit_collision_receipt(self) -> None:
        first = simulate_shared_2d_colony("RL", steps=500, snapshot_interval=100)
        second = simulate_shared_2d_colony("RL", steps=500, snapshot_interval=100)

        self.assertEqual(first, second)
        self.assertGreater(first.metrics["collisions"], 0)
        self.assertEqual(first.metrics["schedule"], "synchronous-read-intent-commit")
        self.assertEqual({point[2] for path in first.trajectories for point in path}, {0})

    def test_hamann_rrlu_reproduces_reported_period_32_highway(self) -> None:
        result = simulate_hamann("RRLU", steps=20_000)

        self.assertEqual(detect_tail_period(result.commands, candidates=[32]), 32)
        self.assertEqual(result.steps, 20_000)
        self.assertGreater(result.unique_cells, 1_000)

    def test_hamann_run_preserves_true_trajectory_and_sparse_snapshots(self) -> None:
        result = simulate_hamann("RUL", steps=220, snapshot_interval=55)

        self.assertEqual(len(result.trajectory), 221)
        self.assertEqual([snapshot.step for snapshot in result.snapshots], [0, 55, 110, 165, 220])
        self.assertEqual(result.trajectory[-1], result.final.position)
        self.assertTrue(result.field)

    def test_hamann_direction_adapter_preserves_frames_and_period_receipt(self) -> None:
        result = hamann_direction_result("RRLU", steps=2_000, snapshot_interval=500)

        self.assertEqual(result.system, "hamann-frame-highway")
        self.assertEqual(len(result.snapshots), 5)
        self.assertEqual(result.metrics["reported_period_candidate"], 32)
        self.assertEqual(result.trajectories[0][-1], result.snapshots[-1].agent_positions[0])
        self.assertEqual(len(result.snapshots[-1].agent_frames), 1)

    def test_ring_excavator_builds_a_shell_and_erases_its_centerline(self) -> None:
        result = simulate_ring_excavator(rule="RUL", steps=2_000, snapshot_interval=500)

        self.assertEqual(result.system, "ring-excavator")
        self.assertGreater(result.metrics["ring_writes"], 6_000)
        self.assertGreater(result.metrics["center_erases"], 0)
        self.assertGreater(result.metrics["solid_cells"], 0)
        self.assertEqual([snapshot.step for snapshot in result.snapshots], [0, 500, 1_000, 1_500, 2_000])

    def test_ring_excavator_internal_phase_can_build_a_volumetric_drifting_tube(self) -> None:
        result = simulate_ring_excavator(rule="URDL", steps=1_000, snapshot_interval=250)
        spans = summarize_direction(result)["axis_spans"]

        self.assertGreater(min(spans), 100)

    def test_ring_excavator_supports_a_visible_square_shell_radius(self) -> None:
        result = simulate_ring_excavator(rule="URDL", steps=20, snapshot_interval=20, shell_radius=3)

        self.assertEqual(result.metrics["ring_writes"], 20 * 24)
        self.assertEqual(result.metrics["shell_radius"], 3)

    def test_collision_colony_records_transactional_conflicts_and_scars(self) -> None:
        first = simulate_collision_colony(rule="RUL", steps=600, snapshot_interval=150)
        second = simulate_collision_colony(rule="RUL", steps=600, snapshot_interval=150)

        self.assertEqual(first, second)
        self.assertEqual(first.system, "collision-colony")
        self.assertGreater(first.metrics["collisions"], 0)
        self.assertGreater(first.metrics["contested_cells"], 0)
        self.assertEqual(len(first.trajectories), 6)
        self.assertTrue(any(snapshot.event_positions for snapshot in first.snapshots))

    def test_collision_colony_frame_exchange_is_a_distinct_deterministic_policy(self) -> None:
        scar = simulate_collision_colony("RLRU", steps=600, snapshot_interval=150)
        exchange = simulate_collision_colony(
            "RLRU", steps=600, snapshot_interval=150, collision_policy="frame-exchange"
        )

        self.assertEqual(exchange.metrics["collision_policy"], "frame-exchange")
        self.assertGreater(exchange.metrics["frame_exchanges"], 0)
        self.assertNotEqual(exchange.trajectories, scar.trajectories)

    def test_collision_colony_frame_exchange_is_order_invariant_under_synchronous_commit(self) -> None:
        forward = simulate_collision_colony(
            "RLRU",
            steps=300,
            snapshot_interval=300,
            collision_policy="frame-exchange",
            transaction_order=(0, 1, 2, 3, 4, 5),
        )
        reverse = simulate_collision_colony(
            "RLRU",
            steps=300,
            snapshot_interval=300,
            collision_policy="frame-exchange",
            transaction_order=(5, 4, 3, 2, 1, 0),
        )

        self.assertEqual(forward.field, reverse.field)
        self.assertEqual(forward.trajectories, reverse.trajectories)
        self.assertEqual(forward.metrics["initial_agents"], reverse.metrics["initial_agents"])
        self.assertEqual(forward.metrics["schedule"], "synchronous-read-intent-commit")

    def test_c2_robustness_matrix_proves_transaction_order_invariance(self) -> None:
        seeds = {
            "radius-2": (
                ((2, 0, 0), (-1, 0, 0), (0, 0, 1)),
                ((-2, 0, 0), (1, 0, 0), (0, 0, 1)),
                ((0, 2, 0), (0, -1, 0), (0, 0, 1)),
                ((0, -2, 0), (0, 1, 0), (0, 0, 1)),
                ((0, 0, 2), (0, 0, -1), (0, 1, 0)),
                ((0, 0, -2), (0, 0, 1), (0, 1, 0)),
            )
        }
        report = run_c2_robustness_matrix(seeds, steps=300, snapshot_interval=300)

        self.assertEqual(report["variant_count"], 1)
        self.assertTrue(report["variants"][0]["transaction_order_invariant"])
        self.assertGreater(report["variants"][0]["frame_exchanges"], 0)
        self.assertEqual(report["variants"][0]["initial_agents"], seeds["radius-2"])
        serialized = serializable_robustness_report(report)
        self.assertNotIn("result", serialized["variants"][0])
        self.assertIn("state_sha256", json.loads(json.dumps(serialized))["variants"][0])

    def test_wound_healing_colony_uses_editable_semantic_half_states(self) -> None:
        result = simulate_wound_healing_colony("RLRU", steps=800, snapshot_interval=200)
        states = {state for _, state in result.field}

        self.assertTrue(states.issubset({0.5, 1.0}))
        self.assertIn(0.5, states)
        self.assertIn(1.0, states)
        self.assertGreater(result.metrics["wounds_written"], 0)
        self.assertGreater(result.metrics["healing_transitions"], 0)
        self.assertGreater(result.metrics["erasures"], 0)

    def test_chiral_highway_pair_uses_mirrored_rules_and_shared_memory(self) -> None:
        result = simulate_chiral_highway_pair("RLRUUUL", steps=2_000, snapshot_interval=500)

        self.assertEqual(len(result.trajectories), 2)
        self.assertEqual(result.metrics["right_rule"], "RLRUUUL")
        self.assertEqual(result.metrics["left_rule"], "LRLUUUR")
        self.assertEqual(result.metrics["schedule"], "synchronous-read-intent-commit")
        self.assertGreater(result.metrics["shared_rewrites"], 0)

    def test_chiral_highway_pair_receipts_configurable_initial_frames(self) -> None:
        initial_agents = (
            ((-3, 0, 0), (0, 1, 0), (0, 0, 1)),
            ((3, 0, 0), (0, 1, 0), (0, 0, 1)),
        )
        result = simulate_chiral_highway_pair(
            "RLRUUUL", steps=100, snapshot_interval=50, initial_agents=initial_agents
        )

        self.assertEqual(result.snapshots[0].agent_positions, ((-3, 0, 0), (3, 0, 0)))
        self.assertEqual(result.snapshots[0].agent_frames[0], ((0, 1, 0), (0, 0, 1)))
        self.assertEqual(result.metrics["initial_agents"], initial_agents)
        self.assertEqual(result.metrics["initial_separation"], 6.0)

    def test_chiral_highway_pair_receipts_explicit_rule_pair_and_phases(self) -> None:
        result = simulate_chiral_highway_pair(
            "RRLU",
            steps=100,
            snapshot_interval=50,
            rules=("RRLU", "LLRU"),
            rule_phase_offsets=(0, 1),
        )

        self.assertEqual(result.metrics["right_rule"], "RRLU")
        self.assertEqual(result.metrics["left_rule"], "LLRU")
        self.assertEqual(result.metrics["rule_phase_offsets"], (0, 1))
        self.assertEqual(result.metrics["rule_pairing"], "explicit")

    def test_a3_robustness_matrix_receipts_each_initial_condition(self) -> None:
        configs = {
            "gap-2": (
                ((-1, 0, 0), (0, 1, 0), (0, 0, 1)),
                ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
            ),
            "gap-4": (
                ((-2, 0, 0), (0, 1, 0), (0, 0, 1)),
                ((2, 0, 0), (0, 1, 0), (0, 0, 1)),
            ),
        }
        report = run_a3_robustness_matrix(configs, steps=500, snapshot_interval=500)

        self.assertEqual(report["variant_count"], 2)
        self.assertEqual([row["id"] for row in report["variants"]], ["gap-2", "gap-4"])
        self.assertTrue(all(len(row["state_sha256"]) == 64 for row in report["variants"]))
        self.assertTrue(all(row["initial_agents"] == configs[row["id"]] for row in report["variants"]))

    def test_near_rule_enumerator_is_bounded_to_one_edit(self) -> None:
        variants = enumerate_near_rules("RLRUUUL")

        self.assertEqual(len(variants), 60)
        self.assertTrue(all(record["edit_distance"] == 1 for record in variants))
        self.assertNotIn("RLRUUUL", [record["rule"] for record in variants])

    def test_translating_tail_detector_finds_repeated_3d_step_unit(self) -> None:
        unit = ((1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0))
        path = [(0, 0, 0)]
        for delta in unit * 5:
            previous = path[-1]
            path.append(tuple(previous[axis] + delta[axis] for axis in range(3)))

        detected = detect_translating_tail(tuple(path), max_period=8, minimum_cycles=4)

        self.assertEqual(detected["period"], 4)
        self.assertEqual(detected["displacement"], (2, 1, 1))
        self.assertEqual(detected["active_axes"], 3)

    def test_offshoot_analysis_distinguishes_translation_from_volume(self) -> None:
        result = simulate_chiral_highway_pair("RRLU", steps=2_000, snapshot_interval=500)

        analysis = analyze_offshoot_candidate(result, max_period=128)

        self.assertEqual(len(analysis["translating_tails"]), 2)
        self.assertIn("occupied_density", analysis)
        self.assertIn("field_components", analysis)
        self.assertIn("classic_like_gate", analysis)
        self.assertEqual(analysis["gate_definition"]["minimum_cycles"], 4)

    def test_structured_rul_control_matches_unmodified_gap4_pair(self) -> None:
        expected = simulate_chiral_highway_pair(
            "RUL",
            steps=500,
            snapshot_interval=100,
            initial_agents=(((-2, 0, 0), (0, 1, 0), (0, 0, 1)), ((2, 0, 0), (0, 1, 0), (0, 0, 1))),
        )

        result = simulate_rul_bridge_variant("control", steps=500, snapshot_interval=100)

        self.assertEqual(result.trajectories, expected.trajectories)
        self.assertEqual(result.field, expected.field)
        self.assertEqual(result.metrics["variant"], "control")
        self.assertEqual(result.metrics["event_count"], 0)

    def test_structured_rul_variants_receipt_bounded_events_and_recovery(self) -> None:
        for variant in ("relay-node", "ladder-exchange", "scar-branch"):
            first = simulate_rul_bridge_variant(variant, steps=1_300, snapshot_interval=100)
            second = simulate_rul_bridge_variant(variant, steps=1_300, snapshot_interval=100)

            self.assertEqual(first, second)
            self.assertGreater(first.metrics["event_count"], 0)
            self.assertEqual(first.metrics["event_duration"], 22)
            self.assertEqual(first.metrics["base_period"], 22)
            control = simulate_rul_bridge_variant("control", steps=1_300, snapshot_interval=100)
            self.assertEqual(first.trajectories, control.trajectories)
            self.assertNotEqual(first.field, control.field)
        scar = simulate_rul_bridge_variant("scar-branch", steps=1_300, snapshot_interval=100)
        self.assertTrue({state for _, state in scar.field}.intersection({0.5, 1.0}))
        self.assertGreater(scar.metrics["healing_transitions"], 0)

    def test_feedback_rul_round_reacquires_periodic_tails_and_scar_restores_exactly(self) -> None:
        control = simulate_rul_bridge_feedback_variant("control", steps=13_000, snapshot_interval=500)
        relay = simulate_rul_bridge_feedback_variant("relay-node", steps=13_000, snapshot_interval=500)
        ladder = simulate_rul_bridge_feedback_variant("ladder-exchange", steps=15_000, snapshot_interval=500)
        scar = simulate_rul_bridge_feedback_variant("scar-branch", steps=13_000, snapshot_interval=500)

        self.assertNotEqual(relay.trajectories, control.trajectories)
        self.assertNotEqual(ladder.trajectories[:2], control.trajectories)
        for result in (control, relay, ladder, scar):
            self.assertTrue(all(detect_translating_tail(path, max_period=256)["period"] == 22 for path in result.trajectories))
        self.assertEqual(scar.trajectories, control.trajectories)
        self.assertEqual(scar.field, control.field)
        self.assertEqual(scar.metrics["restored_scar_events"], 3)
        self.assertEqual(relay.metrics["event_schedule"], (3803, 6403, 9003))
        control_with_event_frame = simulate_rul_bridge_feedback_variant(
            "control", steps=500, snapshot_interval=500, extra_snapshot_steps=(123,)
        )
        self.assertIn(123, [snapshot.step for snapshot in control_with_event_frame.snapshots])
        self.assertEqual(ladder.metrics["event_duration"], 88)

    def test_selection_freeze_creates_promoted_lineage_and_immutable_cache(self) -> None:
        result = simulate_chiral_highway_pair("RLRUUUL", steps=50, snapshot_interval=25)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            media = root / "source.mp4"
            still = root / "source.png"
            media.write_bytes(b"movie")
            still.write_bytes(b"still")

            frozen = freeze_fieldwriting_behavior(
                root,
                selection_id="selection-a3-gap-4",
                branch_id="A3-gap-4",
                result=result,
                source_media={"motion-timelapse.mp4": media, "contact-sheet.png": still},
                rationale="KC approved A3 gap-4",
                authorization_message_id="message-123",
            )

            selected = frozen["selection_directory"]
            selection = json.loads((selected / "selection.json").read_text(encoding="utf-8"))
            component = json.loads((selected / "component.json").read_text(encoding="utf-8"))
            cache = json.loads((selected / "behavior-cache.json").read_text(encoding="utf-8"))
            manifest = json.loads((selected / "receipt.json").read_text(encoding="utf-8"))

            self.assertEqual(selection["state"], "promoted-behavior")
            self.assertEqual(component["state"], "promoted")
            self.assertEqual(selection["component_id"], component["id"])
            self.assertEqual(cache["state_sha256"], summarize_direction(result)["state_sha256"])
            self.assertEqual(cache["snapshots"][-1]["step"], 50)
            self.assertEqual(selection["authorization_message_id"], "message-123")
            for record in manifest["files"].values():
                path = selected / record["path"]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record["sha256"])

    def test_robustness_checksum_preserves_artifact_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "01_A3" / "robustness.json"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("{}", encoding="utf-8")

            record = robustness_checksum(artifact, relative_to=root)

        self.assertEqual(record["path"], "01_A3/robustness.json")

    def test_direction_renderer_outputs_true_distinct_simulation_frames(self) -> None:
        result = simulate_ring_excavator(rule="RUL", steps=120, snapshot_interval=40)
        with tempfile.TemporaryDirectory() as directory:
            paths = render_direction_frames(result, Path(directory), size=(320, 320))

            self.assertEqual(len(paths), 4)
            dimensions = []
            for path in paths:
                with Image.open(path) as image:
                    dimensions.append(image.size)
            self.assertEqual(dimensions, [(320, 320)] * 4)
            self.assertGreater(len({path.read_bytes() for path in paths}), 2)
            with Image.open(paths[-1]).convert("RGB") as image:
                self.assertTrue(any(g > r + 25 and g > b + 5 for r, g, b in image.getdata()))

    def test_renderer_profiles_distinguish_anatomy_and_microcells(self) -> None:
        result = hamann_direction_result("RLRUUUL", steps=1_000, snapshot_interval=500)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            anatomy = render_direction_frames(result, root / "anatomy", size=(320, 320), profile="anatomy")
            micro = render_direction_frames(result, root / "micro", size=(320, 320), profile="microcell")

            self.assertNotEqual(anatomy[-1].read_bytes(), micro[-1].read_bytes())

    def test_direction_summary_reports_hash_bounds_and_volumetric_extent(self) -> None:
        result = simulate_ring_excavator(rule="RUL", steps=800, snapshot_interval=200)
        summary = summarize_direction(result)

        self.assertEqual(summary, summarize_direction(result))
        self.assertEqual(len(summary["state_sha256"]), 64)
        self.assertEqual(len(summary["bounds"]), 6)
        self.assertGreater(summary["axis_spans"][2], 0)
        self.assertGreater(summary["nonplanarity_ratio"], 0)
        digest = summary["state_sha256"]
        result.metrics["review_label"] = "does-not-change-state"
        self.assertEqual(summarize_direction(result)["state_sha256"], digest)


    def test_direction_summary_counts_every_semantic_state(self) -> None:
        result = hamann_direction_result("RLRUUUL", steps=5_000, snapshot_interval=5_000)
        summary = summarize_direction(result)

        self.assertEqual(sum(summary["state_counts"].values()), summary["field_cells"])
        self.assertGreater(len(summary["state_counts"]), 2)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg tools unavailable")
    def test_direction_package_encodes_and_independently_receipts_real_frames(self) -> None:
        result = simulate_ring_excavator(rule="URDL", steps=120, snapshot_interval=40)
        with tempfile.TemporaryDirectory() as directory:
            artifacts = package_direction(result, Path(directory), fps=4, size=(320, 320))
            receipt = json.loads(artifacts["receipt"].read_text(encoding="utf-8"))
            probe = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-count_frames",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=width,height,nb_read_frames",
                    "-of",
                    "json",
                    str(artifacts["video"]),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            stream = json.loads(probe.stdout)["streams"][0]

            self.assertEqual((stream["width"], stream["height"]), (320, 320))
            self.assertEqual(int(stream["nb_read_frames"]), len(result.snapshots))
            self.assertEqual(receipt["artifacts"]["video"]["sha256"], hashlib.sha256(artifacts["video"].read_bytes()).hexdigest())
            self.assertEqual(len(receipt["frames"]), len(result.snapshots))


if __name__ == "__main__":
    unittest.main()
