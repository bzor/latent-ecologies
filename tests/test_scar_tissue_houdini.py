import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from houdini_ai.doctor import discover_tools


ROOT = Path(__file__).resolve().parents[1]


class ScarTissueHoudiniTests(unittest.TestCase):
    def run_probe(self, mutation: str, engine: str | None = None, frame_end: int = 8) -> dict:
        hython = next(tool.path for tool in discover_tools() if tool.name == "hython")
        if hython is None:
            self.skipTest("Houdini is unavailable")
        experiment = json.loads((ROOT / "studio/experiments/behavior/scar-tissue/base.json").read_text(encoding="utf-8"))
        experiment["parameters"].update(
            {"frame_end": frame_end, "agent_count": 8, "grid_width": 8, "grid_height": 12, "mutation": mutation}
        )
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        config = output / "experiment.json"
        config.write_text(json.dumps(experiment), encoding="utf-8")
        command = [str(hython), str(ROOT / "houdini/simulate_scar_tissue.py"), str(config), str(output)]
        if engine:
            command.extend(["--engine", engine])
        result = subprocess.run(
            command,
            capture_output=True, text=True, timeout=180, check=False,
            env={**os.environ, "HOUDINI_TEMP_DIR": str(output / "temp")},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads((output / "metrics.json").read_text(encoding="utf-8"))

    def test_vex_authoritative_state_persists_and_metrics_come_from_geometry(self) -> None:
        metrics = self.run_probe("saturation-repulsion", "vex-authoritative")
        self.assertEqual(metrics["engine"], "houdini-vex-authoritative")
        self.assertEqual(metrics["state_authority"], "vex-geometry")
        self.assertEqual(metrics["reference_comparison"], "not-run")
        self.assertEqual(metrics["vex_cook_count"], 8)
        self.assertEqual(metrics["agent_count"], 8)
        self.assertEqual(metrics["field_point_count"], 8 * 12)
        self.assertGreater(metrics["deposited_cells"], 0)
        self.assertGreater(metrics["oriented_cells"], 0)
        self.assertGreater(metrics["idle_cells"], 0)
        self.assertGreater(metrics["decayed_cells"], 0)
        self.assertEqual(metrics["vex_errors"], [])
        self.assertNotIn("reference_state_sha256", metrics)
        self.assertEqual(len(metrics["state_sha256"]), 64)
        self.assertEqual(metrics["state_digest_source"], "reloaded-display-cache")
        self.assertEqual(metrics["final_frame_agent_updates"], 8)
        self.assertEqual(metrics["cumulative_agent_updates"], 8 * 8)
        self.assertEqual(metrics["cumulative_decayed_cell_updates"], metrics["decayed_cells"])
        self.assertIn("abandoned_cells", metrics)
        self.assertIn("returned_cells", metrics)
        self.assertGreaterEqual(len(metrics["review"]), 2)
        self.assertEqual(len(metrics["review"][-1]["agents"]), 8)
        self.assertEqual(len(metrics["review"][-1]["field"]), 8 * 12)

    def test_vex_authoritative_same_seed_is_deterministic(self) -> None:
        first = self.run_probe("saturation-repulsion", "vex-authoritative")
        second = self.run_probe("saturation-repulsion", "vex-authoritative")
        self.assertEqual(first["state_sha256"], second["state_sha256"])
        self.assertEqual(first["checkpoints"], second["checkpoints"])

    def test_vex_continuation_matches_fresh_authoritative_run(self) -> None:
        hython = next(tool.path for tool in discover_tools() if tool.name == "hython")
        if hython is None:
            self.skipTest("Houdini is unavailable")
        experiment = json.loads((ROOT / "studio/experiments/behavior/scar-tissue/base.json").read_text(encoding="utf-8"))
        experiment["parameters"].update(
            {"frame_end": 10, "agent_count": 8, "grid_width": 8, "grid_height": 12, "mutation": "directional-refractory"}
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "experiment.json"
            config.write_text(json.dumps(experiment), encoding="utf-8")
            fresh = root / "fresh"
            result = subprocess.run(
                [str(hython), str(ROOT / "houdini/simulate_scar_tissue.py"), str(config), str(fresh), "--engine", "vex-authoritative"],
                capture_output=True, text=True, timeout=180, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            resumed = root / "resumed"
            resumed.mkdir()
            shutil.copytree(fresh / "cache", resumed / "cache")
            for path in (resumed / "cache").glob("vex-state.*.bgeo.sc"):
                if int(path.stem.split(".")[-2]) > 8:
                    path.unlink()
            result = subprocess.run(
                [str(hython), str(ROOT / "houdini/extend_scar_tissue.py"), str(config), str(resumed), "--start-frame", "9", "--end-frame", "10"],
                capture_output=True, text=True, timeout=180, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            continuation = json.loads((resumed / "continuation-metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(continuation["source_frame"], 8)
            self.assertEqual(continuation["frame_start"], 9)
            self.assertEqual(continuation["frame_end"], 10)
            self.assertEqual(continuation["vex_cook_count"], 2)
            self.assertEqual(continuation["state_sha256"], json.loads((fresh / "metrics.json").read_text())["state_sha256"])

    def test_vex_authoritative_three_mutations_execute_distinct_branches(self) -> None:
        results = {
            mutation: self.run_probe(mutation, "vex-authoritative")
            for mutation in ("saturation-repulsion", "directional-scar", "refractory-healing")
        }
        self.assertEqual({item["mutation_branch"] for item in results.values()}, {0, 1, 2})
        self.assertEqual(len({item["state_sha256"] for item in results.values()}), 3)
        self.assertTrue(all(item["branch_agent_updates"] > 0 for item in results.values()))

    def test_vex_authoritative_directional_refractory_executes_combined_branch(self) -> None:
        combined = self.run_probe("directional-refractory", "vex-authoritative", frame_end=60)
        self.assertEqual(combined["mutation_branch"], 3)
        self.assertGreater(combined["directional_alignment_samples"], 0)
        self.assertGreater(combined["cumulative_decayed_cell_updates"], 0)
        self.assertGreater(combined["agent_mean_turn_spread"], 0.01)
        self.assertLess(combined["tight_turning_agent_fraction"], 0.75)
        self.assertLess(combined["looping_agent_fraction"], 0.5)

    def test_vex_authoritative_fibrotic_remodeling_matures_persistent_collagen(self) -> None:
        fibrotic = self.run_probe("fibrotic-remodeling", "vex-authoritative", frame_end=60)
        self.assertEqual(fibrotic["mutation_branch"], 4)
        self.assertGreater(fibrotic["provisional_matrix_cells"], 0)
        self.assertGreater(fibrotic["mature_collagen_cells"], 0)
        self.assertGreater(fibrotic["mature_collagen_total"], 0.0)
        self.assertGreater(fibrotic["checkpoints"][-1]["mature_collagen_total"], fibrotic["checkpoints"][19]["mature_collagen_total"])
        self.assertGreater(fibrotic["collagen_retention_ratio"], 0.9)
        self.assertEqual(
            fibrotic["state_digest_fields"],
            [
                "P", "heading", "scar_value", "scar_direction", "scar_idle",
                "provisional_matrix", "mature_collagen", "wound_signal",
                "tension_direction", "scar_contraction", "crosslink_density",
                "fibrotic_signal",
            ],
        )
        self.assertGreater(fibrotic["directional_alignment_samples"], 0)
        self.assertLess(fibrotic["tight_turning_agent_fraction"], 0.75)

    def test_vex_authoritative_wound_contractile_branch_concentrates_aligned_relief(self) -> None:
        wound = self.run_probe("wound-contractile-remodeling", "vex-authoritative", frame_end=90)
        self.assertEqual(wound["mutation_branch"], 5)
        self.assertGreater(wound["wound_cells"], 0)
        self.assertGreater(wound["wound_collagen_concentration_ratio"], wound["wound_cell_fraction"])
        self.assertGreater(wound["tension_aligned_cells"], 0)
        self.assertGreater(wound["contraction_cells"], 0)
        self.assertGreater(wound["contraction_total"], 0.0)
        self.assertGreater(wound["relief_potential_max"], wound["mature_collagen_max"])
        self.assertEqual(
            wound["state_digest_fields"],
            [
                "P", "heading", "scar_value", "scar_direction", "scar_idle",
                "provisional_matrix", "mature_collagen", "wound_signal",
                "tension_direction", "scar_contraction", "crosslink_density",
                "fibrotic_signal",
            ],
        )
        self.assertGreater(wound["directional_alignment_samples"], 0)
        self.assertLess(wound["tight_turning_agent_fraction"], 0.75)
        self.assertLess(wound["looping_agent_fraction"], 0.5)

    def test_purse_string_branch_builds_contractile_edges_and_collagen_bridges(self) -> None:
        closure = self.run_probe("purse-string-closure", "vex-authoritative", frame_end=90)
        self.assertEqual(closure["mutation_branch"], 6)
        self.assertGreater(closure["wound_edge_cells"], 0)
        self.assertGreater(closure["edge_collagen_concentration_ratio"], closure["wound_edge_fraction"])
        self.assertGreater(closure["bridge_cells"], 0)
        self.assertGreater(closure["contraction_total"], 0.0)
        self.assertGreater(closure["relief_potential_max"], closure["mature_collagen_max"])
        self.assertLess(closure["tight_turning_agent_fraction"], 0.75)
        self.assertLess(closure["looping_agent_fraction"], 0.5)

    def test_crosslink_weave_branch_builds_interlocking_collagen_junctions(self) -> None:
        weave = self.run_probe("collagen-crosslink-weave", "vex-authoritative", frame_end=90)
        self.assertEqual(weave["mutation_branch"], 7)
        self.assertGreater(weave["crosslink_cells"], 0)
        self.assertGreater(weave["crosslink_total"], 0.0)
        self.assertGreater(weave["crosslink_max"], 0.0)
        self.assertGreater(weave["crosslinked_relief_max"], weave["mature_collagen_max"])
        self.assertLess(weave["tight_turning_agent_fraction"], 0.75)
        self.assertLess(weave["looping_agent_fraction"], 0.5)

    def test_keloid_signal_branch_forms_local_self_sustaining_fibrotic_foci(self) -> None:
        bloom = self.run_probe("keloid-signal-bloom", "vex-authoritative", frame_end=90)
        self.assertEqual(bloom["mutation_branch"], 8)
        self.assertGreater(bloom["fibrotic_signal_cells"], 0)
        self.assertGreater(bloom["fibrotic_signal_total"], 0.0)
        self.assertGreater(bloom["fibrotic_signal_max"], 0.10)
        self.assertGreater(bloom["fibrotic_foci"], 0)
        self.assertGreater(bloom["signal_weighted_collagen"], 0.0)
        self.assertLess(bloom["fibrotic_signal_cells"], bloom["field_point_count"])
        self.assertLess(bloom["tight_turning_agent_fraction"], 0.75)
        self.assertLess(bloom["looping_agent_fraction"], 0.5)

    def test_directional_and_refractory_vex_receive_required_state(self) -> None:
        directional = self.run_probe("directional-scar")
        refractory = self.run_probe("refractory-healing")
        self.assertGreater(directional["vex_directional_points"], 0)
        self.assertGreater(refractory["vex_idle_samples"], 0)
        self.assertEqual(refractory["vex_idle_source"], "reference-agent-cell")

    def test_hython_smoke_probe_writes_metrics_cache_and_hip(self) -> None:
        hython = next(tool.path for tool in discover_tools() if tool.name == "hython")
        if hython is None:
            self.skipTest("Houdini is unavailable")
        experiment = json.loads((ROOT / "studio/experiments/behavior/scar-tissue/base.json").read_text(encoding="utf-8"))
        experiment["parameters"].update({"frame_end": 8, "agent_count": 48, "grid_width": 24, "grid_height": 36})
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            config = output / "experiment.json"
            config.write_text(json.dumps(experiment), encoding="utf-8")
            result = subprocess.run(
                [str(hython), str(ROOT / "houdini/simulate_scar_tissue.py"), str(config), str(output)],
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
                env={**os.environ, "HOUDINI_TEMP_DIR": str(output / "temp")},
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            metrics = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["agent_count"], 48)
            self.assertEqual(metrics["frame_end"], 8)
            self.assertEqual(metrics["engine"], "houdini-vex-hybrid")
            self.assertEqual(len(metrics["vex_sha256"]), 64)
            self.assertGreater(metrics["vex_cook_count"], 0)
            self.assertEqual(metrics["vex_errors"], [])
            self.assertGreater(metrics["vex_displaced_points"], 0)
            self.assertEqual(metrics["reference_state_sha256"], metrics["state_sha256"])
            self.assertTrue(metrics["verification_scope"].startswith("base mutation checkpoint"))
            self.assertTrue((output / "scar-tissue.hiplc").is_file())
            self.assertTrue((output / "cache/state.0008.bgeo.sc").is_file())
            self.assertTrue(metrics["state_sha256"])
            self.assertTrue(metrics["display_cache_sha256"])

    def test_grid_hair_agent_look_builds_from_authoritative_cache(self) -> None:
        hython = next(tool.path for tool in discover_tools() if tool.name == "hython")
        if hython is None:
            self.skipTest("Houdini is unavailable")
        source = ROOT / "work/studio/probes/scar-tissue/directional-refractory-v3"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = subprocess.run(
                [
                    str(hython), str(ROOT / "houdini/render_scar_tissue_grid_look.py"),
                    str(source / "cache"), str(source / "metrics.json"), str(output),
                    "--frames", "1,30", "--width", "720", "--samples", "8",
                    "--palette", "mineral-wound", "--camera", "low-grazing", "--build-only",
                ],
                capture_output=True, text=True, timeout=180, check=False,
                env={**os.environ, "HOUDINI_TEMP_DIR": str(output / "temp")},
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["look"], "memory-grid-hairs-chrome-agents")
            self.assertEqual(receipt["frames"], [1, 30])
            self.assertEqual(receipt["field_instances_per_frame"], 72 * 108)
            self.assertGreater(receipt["hair_curves_per_frame"]["30"], 0)
            self.assertEqual(receipt["agent_instances_per_frame"], 256)
            self.assertEqual(receipt["trail_start_instances_per_frame"]["30"], 256)
            self.assertGreater(receipt["trail_curves_per_frame"]["30"], 0)
            self.assertEqual(receipt["trail_radius"], 0.004)
            self.assertEqual(receipt["trail_material"], "chrome")
            self.assertEqual(receipt["trail_endpoint_scale"], receipt["agent_scale"])
            self.assertEqual(receipt["agent_scale"], 0.015)
            self.assertEqual(receipt["agent_layer_height"], receipt["trail_layer_height"])
            self.assertEqual(receipt["agent_system_material"], "shared-chrome")
            self.assertGreater(receipt["maximum_hair_tip_height"]["30"], 0.72)
            self.assertEqual(receipt["hair_temporal_easing"], "exponential-history")
            self.assertGreater(receipt["hair_history_frames"], 1)
            self.assertEqual(receipt["hair_bend_profile"], "power-toward-tip")
            self.assertEqual(receipt["hair_bend_exponent"], 2.2)
            self.assertEqual(receipt["hair_maximum_lean"], 0.58)
            self.assertEqual(receipt["hair_radius_profile"], "linear-root-to-point")
            self.assertEqual(receipt["hair_root_scale"], 1.0)
            self.assertEqual(receipt["hair_tip_scale"], 0.0)
            self.assertEqual(receipt["cube_height_mapping"], "smoothstep")
            self.assertEqual(receipt["cube_bevel_divisions"], 1)
            self.assertEqual(receipt["cube_bevel_width"], 0.006)
            self.assertEqual(receipt["cube_bevel_space"], "fixed-world-after-instance-scale")
            self.assertTrue(receipt["overscan_ground"])
            self.assertEqual(receipt["render_width"], 720)
            self.assertEqual(receipt["samples_per_pixel"], 8)
            self.assertEqual(receipt["camera_preset"], "low-grazing")
            self.assertEqual(set(receipt["camera_parameters"]), {"tx", "ty", "tz", "rx", "ry", "focal_length"})
            self.assertEqual(receipt["camera_parameters"]["ty"], 3.8)
            self.assertEqual(receipt["camera_parameters"]["tz"], 15.8)
            self.assertEqual(receipt["camera_parameters"]["rx"], -15.0)
            self.assertEqual(receipt["camera_parameters"]["focal_length"], 64.0)
            self.assertEqual(receipt["palette"], "mineral-wound")
            self.assertEqual(set(receipt["palette_roles"]), {"ground", "grid", "hairs", "chrome"})
            self.assertEqual(receipt["cube_color_mapping"], "scar-value-plus-idle-and-state")
            self.assertEqual(receipt["cube_color_attributes"], ["scar_value", "scar_idle", "scar_state"])
            self.assertEqual(receipt["cube_vertical_color_profile"], "floor-to-state-tip-power")
            self.assertEqual(receipt["cube_vertical_color_exponent"], 2.0)
            self.assertEqual(receipt["cube_state_color_roles"]["1"], "electric-blue")
            self.assertEqual(receipt["cube_state_color_roles"]["2"], "teal")
            self.assertGreater(receipt["cube_color_ranges"]["30"]["scar_value_max"], 0.0)
            self.assertGreater(receipt["cube_color_ranges"]["30"]["scar_idle_max"], 0)
            self.assertEqual(receipt["cube_color_ranges"]["30"]["scar_state_max"], 2)
            self.assertLessEqual(receipt["cube_color_ranges"]["30"]["display_color_max"], 0.95)
            self.assertTrue((output / "scar-tissue-grid-look.hiplc").is_file())

    def test_fast_motion_check_uses_opengl_and_authoritative_caches(self) -> None:
        hython = next(tool.path for tool in discover_tools() if tool.name == "hython")
        if hython is None:
            self.skipTest("Houdini is unavailable")
        source = ROOT / "work/studio/probes/scar-tissue/directional-refractory-v3"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = subprocess.run(
                [
                    str(hython), str(ROOT / "houdini/render_scar_tissue_motion_check.py"),
                    str(source / "cache"), str(source / "metrics.json"), str(output),
                    "--frames", "1,30", "--camera", "tight-isometric", "--build-only",
                ],
                capture_output=True, text=True, timeout=180, check=False,
                env={**os.environ, "HOUDINI_TEMP_DIR": str(output / "temp")},
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["operation"], "motion-check")
            self.assertEqual(receipt["render_engine"], "software-flat-proxy")
            self.assertEqual(receipt["opengl_status"], "unavailable-headless-vulkan-crash")
            self.assertEqual(receipt["source_authority"], "vex-geometry-cache")
            self.assertEqual(receipt["frames"], [1, 30])
            self.assertEqual(receipt["camera"], "tight-isometric")
            self.assertFalse(receipt["karma_invoked"])
            self.assertTrue((output / "scar-tissue-motion-check.hiplc").is_file())

    def test_abc_a_handoff_builds_contiguous_animated_edit(self) -> None:
        hython = next(tool.path for tool in discover_tools() if tool.name == "hython")
        if hython is None:
            self.skipTest("Houdini is unavailable")
        source = ROOT / "work/studio/probes/scar-tissue/directional-refractory-v3"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = subprocess.run(
                [
                    str(hython), str(ROOT / "houdini/build_scar_tissue_handoff.py"),
                    str(source / "cache"), str(source / "metrics.json"), str(output),
                    "--build-only",
                ],
                capture_output=True, text=True, timeout=180, check=False,
                env={**os.environ, "HOUDINI_TEMP_DIR": str(output / "temp")},
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["timeline_fps"], 45)
            self.assertEqual(receipt["frame_range"], [1, 1260])
            self.assertEqual([shot["frames"] for shot in receipt["shots"]], [[1, 315], [316, 630], [631, 945], [946, 1260]])
            self.assertEqual([shot["camera"] for shot in receipt["shots"]], ["A", "B", "C", "A"])
            self.assertTrue(all(shot["camera_motion"] == "subtle" for shot in receipt["shots"]))
            self.assertTrue(receipt["editable_controls"]["materials"])
            self.assertTrue(receipt["editable_controls"]["depth_of_field"])
            self.assertTrue(receipt["editable_controls"]["lighting"])
            self.assertEqual(receipt["cube_bevel_divisions"], 1)
            self.assertEqual(receipt["cube_bevel_width"], 0.006)
            self.assertEqual(receipt["state_palette_ramp_positions"], [0.0, 0.5, 1.0])
            self.assertEqual(receipt["state_palette_primvar"], "state_index")
            self.assertEqual(receipt["state_mix_primvar"], "state_mix")
            self.assertEqual(receipt["lighting_rig"], ["dome_fill", "grazing_area_key", "cool_rim"])
            self.assertTrue((output / "scar-tissue-abc-a-handoff.hiplc").is_file())

    def test_abc_a_camera_evaluation_is_contiguous_at_cuts(self) -> None:
        from houdini_ai.scar_tissue_edit import camera_at_frame

        expected = {1: "A1", 315: "A1", 316: "B", 630: "B", 631: "C", 945: "C", 946: "A2", 1260: "A2"}
        for frame, label in expected.items():
            camera = camera_at_frame(frame)
            self.assertEqual(camera["shot"], label)
            self.assertEqual(set(camera), {"shot", "tx", "ty", "tz", "rx", "ry", "focal_length"})

    def test_portrait_edit_preserves_shots_with_portrait_framing(self) -> None:
        from houdini_ai.scar_tissue_edit import camera_at_frame, portrait_camera_at_frame

        expected = {
            1: ("A1", 125.0), 315: ("A1", 125.0),
            316: ("B", 140.0), 630: ("B", 140.0),
            631: ("C", 150.0), 945: ("C", 150.0),
            946: ("A2", 125.0), 1260: ("A2", 125.0),
        }
        for frame, (shot, focal_length) in expected.items():
            camera = portrait_camera_at_frame(frame)
            self.assertEqual(camera["shot"], shot)
            self.assertEqual(camera["aspect_ratio"], [9, 16])
            self.assertAlmostEqual(camera["focal_length"], focal_length)
        self.assertLess(portrait_camera_at_frame(316)["ty"], camera_at_frame(316)["ty"])
        self.assertAlmostEqual(portrait_camera_at_frame(316)["ty"], 3.60)
        self.assertAlmostEqual(portrait_camera_at_frame(630)["ty"], 3.40)

    def test_portrait_motion_check_uses_nine_by_sixteen_frame(self) -> None:
        from houdini_ai.scar_tissue_edit import frame_dimensions

        self.assertEqual(frame_dimensions(480, portrait=True), (480, 853))
        self.assertEqual(frame_dimensions(480, portrait=False), (480, 270))

    def test_portrait_view_controls_reconstruct_animated_camera(self) -> None:
        from houdini_ai.scar_tissue_edit import (
            portrait_camera_at_frame,
            portrait_control_at_frame,
            portrait_controlled_camera_at_frame,
            portrait_stage_control_path,
        )

        expected_controls = {1: "A", 315: "A", 316: "B", 630: "B", 631: "C", 945: "C", 946: "A", 1260: "A"}
        for frame, control in expected_controls.items():
            self.assertEqual(portrait_control_at_frame(frame), control)
            direct = portrait_camera_at_frame(frame)
            controlled = portrait_controlled_camera_at_frame(frame)
            for name in ("tx", "ty", "tz", "rx", "ry"):
                self.assertAlmostEqual(controlled[name], direct[name])
        self.assertEqual(portrait_stage_control_path("A"), "/stage/PORTRAIT_VIEW_A_CTRL")
        self.assertEqual(portrait_stage_control_path("B"), "/stage/PORTRAIT_VIEW_B_CTRL")
        self.assertEqual(portrait_stage_control_path("C"), "/stage/PORTRAIT_VIEW_C_CTRL")


if __name__ == "__main__":
    unittest.main()
