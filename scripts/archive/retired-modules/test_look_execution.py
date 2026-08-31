import hashlib
import json
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from houdini_ai.look_execution import (
    build_aggregate_review,
    make_hermes_worker,
    make_hython_direction_scaffold_builder,
    prepare_look_round,
    run_look_round as _run_look_round,
)
from houdini_ai.studio_store import StudioStore


STUDY_ID = "study-003-test"


def direction(direction_id: str, title: str, attribute: str, response: str) -> dict:
    return {
        "id": direction_id,
        "title": title,
        "thesis": f"{title} makes the simulation state physically legible.",
        "visual_target": {
            "references": ["reference://approved-look-01", "reference://approved-look-02"],
            "final_image_thesis": f"A resolved final image where {response} is the dominant read.",
            "required_reads": [response, "clear simulation-to-form causality"],
            "prohibited_reads": ["raw diagnostic viewport", "unshaded geometry test"],
            "material_intent": "A deliberate MaterialX surface response with authored roughness and scale cues.",
            "framing_intent": "One neutral coverage camera and one art-directed hero camera.",
            "lighting_intent": "A locked neutral rig plus an authored hero key, fill, and rim treatment.",
            "temporal_signature": "The final-image hierarchy remains legible across early, middle, and late frames.",
        },
        "state_to_form_mappings": [
            {
                "source_attribute": attribute,
                "visible_response": response,
                "houdini_mechanism": f"Drive {response} from {attribute} in SOPs.",
                "acceptance_observable": f"High and low {attribute} samples produce visibly different {response}.",
            }
        ],
        "primary_hierarchy": ["field structure", "agents", "diagnostics"],
        "representation_system": "Houdini SOP geometry with neutral diagnostic materials.",
        "lighting_assumptions": "One fixed neutral technical rig reveals form without becoming an aesthetic commitment.",
        "cost_tier": "probe",
        "motion_proposition": "Persistent state changes form across early, middle, and late frames.",
        "exclusions": ["behavior changes", "publication finishing"],
        "risks": ["The mapping may become decorative instead of explanatory."],
        "cheapest_decisive_probe": "Render fixed early, middle, and late technical frames.",
        "stop_conditions": ["Stop if the source attribute is absent from the authoritative cache."],
        "implementation_stages": [
            {
                "id": "inspect-source",
                "title": "Inspect authoritative source data",
                "intent": "Measure the real cache attributes and choose robust working ranges.",
                "data_inputs": [attribute],
                "houdini_strategy": "Load and inspect the frozen caches without changing Behavior.",
                "output": "A reusable, normalized source-data branch.",
                "acceptance_observable": f"The graph records the measured range of {attribute}.",
            },
            {
                "id": "build-primary-form",
                "title": "Build the primary state-driven form",
                "intent": f"Make {attribute} legible through {response}.",
                "data_inputs": [attribute],
                "houdini_strategy": f"Construct the main SOP branch driving {response} from {attribute}.",
                "output": "Primary look geometry with stable controls.",
                "acceptance_observable": f"Primary {response} responds across the measured {attribute} range.",
            },
            {
                "id": "build-secondary-hierarchy",
                "title": "Build supporting visual hierarchy",
                "intent": "Separate persistent field structure, agents, and diagnostics.",
                "data_inputs": [attribute],
                "houdini_strategy": "Build adjacent, independently switchable SOP branches and merge them explicitly.",
                "output": "A readable multi-layer look assembly.",
                "acceptance_observable": "Primary and secondary layers remain independently legible.",
            },
            {
                "id": "temporal-proof-and-handoff",
                "title": "Prove motion and package the graph",
                "intent": "Verify the direction across time and leave an artist-readable HIP.",
                "data_inputs": [attribute],
                "houdini_strategy": "Cook early, middle, and late probes, organize the graph, save, reopen, and recook.",
                "output": "Canonical HIP, temporal probes, and graph audit.",
                "acceptance_observable": "The reopened HIP cooks the intended output and temporal probes show the mapping evolving.",
            },
        ],
    }


def behavior_source(root: Path, marker: str) -> dict:
    relatives = [
        f"studies/study_003_test/01_behavior/03_selected/selection_001/cache.{frame:04d}.bgeo.sc"
        for frame in range(1, 9)
    ]
    for relative in relatives:
        cache = root / relative
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(f"cache-{marker}-{relative}".encode())
    content_hash = "sha256:" + marker * 64
    component = {
        "schema_version": 1,
        "id": "component-behavior-a",
        "track": "behavior",
        "state": "promoted",
        "component_kind": "behavior",
        "source_experiment_id": "experiment-behavior-a",
        "source_artifact_ref": relatives[0],
        "rationale": "KC selected and locked this Behavior.",
        "content_hash": content_hash,
        "visibility": "private",
    }
    store = StudioStore(root)
    try:
        store.create("components", "component-behavior-a", component)
    except FileExistsError:
        store.update("components", "component-behavior-a", component)
    return {
        "id": "component-behavior-a",
        "component_kind": "behavior",
        "state": "promoted",
        "content_hash": content_hash,
        "cache_paths": relatives,
    }


def write_receipt(
    packet_path: Path,
    output_dir: Path,
    *,
    evidence: str = "probe.txt",
    claims: list[str] | None = None,
    include_review_media: bool = True,
    legacy_claims: bool = False,
    evidence_content: str | None = None,
) -> None:
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    artifact = output_dir / evidence
    artifact.write_text(evidence_content or packet["direction"]["title"], encoding="utf-8")
    observables = claims or [
        mapping["acceptance_observable"] for mapping in packet["direction"]["state_to_form_mappings"]
    ]
    plan_path = output_dir / packet["workspace_layout"]["implementation_plan"]
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    stage_evidence = []
    for index, stage in enumerate(packet["direction"]["implementation_stages"], start=1):
        path = output_dir / f"04_evidence/stage-{index:02d}-{stage['id']}.txt"
        path.write_text(stage["acceptance_observable"], encoding="utf-8")
        stage_evidence.append(path)
    plan_path.write_text(json.dumps({
        "direction_id": packet["direction"]["id"],
        "project_root": packet["project_root"],
        "source_behavior_content_hash": packet["source_behavior"]["content_hash"],
        "source_cache_receipt": packet["source_cache_receipt"],
        "stages": [
            {
                **stage,
                "network_section": f"LOOK_{index:02d}_{stage['id'].upper().replace('-', '_')}",
                "node_families": ["file", "attribwrangle", "null"],
                "nodes": [
                    {
                        "path": f"/obj/LOOK_{index:02d}/SOURCE", "type": "file", "role": "source",
                        "inputs": [],
                    },
                    {
                        "path": f"/obj/LOOK_{index:02d}/PROCESS", "type": "attribwrangle", "role": "process",
                        "inputs": [f"/obj/LOOK_{index:02d}/SOURCE"],
                    },
                    {
                        "path": f"/obj/LOOK_{index:02d}/OUT", "type": "null", "role": "output",
                        "inputs": [f"/obj/LOOK_{index:02d}/PROCESS"],
                    },
                ],
                "output_node": f"/obj/LOOK_{index:02d}/OUT",
                "artist_controls": [
                    {"node_path": f"/obj/LOOK_{index:02d}/PROCESS", "parm": "range_min"},
                ],
                "status": "implemented",
                "evidence_paths": [stage_evidence[index - 1].relative_to(output_dir).as_posix()],
            }
            for index, stage in enumerate(packet["direction"]["implementation_stages"], start=1)
        ],
        "render_setup": {
            "renderer": packet["review_contract"]["renderer"],
            "color_pipeline": packet["review_contract"]["color_pipeline"],
            "neutral_rig_id": packet["review_contract"]["neutral_rig_id"],
            "resolution": packet["review_contract"]["resolution"],
            "samples_per_pixel": packet["review_contract"]["samples_per_pixel"],
            "path_traced_samples": packet["review_contract"]["path_traced_samples"],
            "neutral_camera_parameters": packet["review_contract"]["neutral_camera_parameters"],
            "neutral_dome_parameters": packet["review_contract"]["neutral_dome_parameters"],
            "neutral_render_parameters": packet["review_contract"]["neutral_render_parameters"],
            "neutral_frames": packet["review_contract"]["neutral_frames"],
            "motion_frames": packet["review_contract"]["motion_frames"],
            "nodes": packet["review_contract"]["required_scene_nodes"],
        },
    }), encoding="utf-8")
    hip_path = output_dir / packet["workspace_layout"]["scene_stem"]
    hip_path = hip_path.with_suffix(".hiplc")
    hip_path.parent.mkdir(parents=True, exist_ok=True)
    hip_path.write_bytes(b"test hip")

    review = packet["review_contract"]
    media_paths = [
        *(output_dir / path for path in review["neutral_render_paths"].values()),
        output_dir / review["hero_render_path"],
        output_dir / review["motion_preview_path"],
        output_dir / review["annotated_claim_sheet_path"],
    ]
    for index, path in enumerate(media_paths[:4], start=1):
        path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGB", (320, 180), (12 + index * 20, 24, 45))
        draw = ImageDraw.Draw(image)
        draw.rectangle((30 + index * 5, 35, 200, 145), fill=(80, 60 + index * 25, 180))
        image.save(path)
    motion_frames = []
    for index in range(8):
        frame = Image.new("RGB", (320, 180), (15, 20 + index * 30, 35))
        ImageDraw.Draw(frame).ellipse((40 + index * 35, 55, 130 + index * 35, 145), fill=(180, 100, 60))
        motion_frames.append(frame)
    media_paths[4].parent.mkdir(parents=True, exist_ok=True)
    motion_frames[0].save(media_paths[4], save_all=True, append_images=motion_frames[1:], duration=80, loop=0)
    media_paths[5].parent.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGB", (640, 360), (18, 22, 30))
    draw = ImageDraw.Draw(sheet)
    draw.rectangle((20, 20, 620, 250), fill=(65, 85, 115))
    draw.line((70, 300, 300, 130), fill=(255, 180, 60), width=4)
    sheet.save(media_paths[5])

    required = [plan_path, hip_path, *stage_evidence, *media_paths]
    claim_records = [
        ({"claim": observable, "status": "demonstrated", "evidence_paths": [evidence]}
         if legacy_claims else {
             "claim": observable,
             "mechanical_status": "demonstrated",
             "visual_status": "demonstrated",
             "technical_evidence_paths": [stage_evidence[0].relative_to(output_dir).as_posix()],
             "render_evidence_paths": [
                 review["annotated_claim_sheet_path"],
                 review["motion_preview_path"],
             ],
         })
        for observable in observables
    ]
    receipt = {
        "schema_version": 2,
        "direction_id": packet["direction"]["id"],
        "context_id": packet["context_id"],
        "attempt_id": packet["attempt_id"],
        "source_behavior_content_hash": packet["source_behavior"]["content_hash"],
        "state": "visual-review-ready",
        "claims": claim_records,
        "artifacts": [{
            "path": evidence,
            "bytes": artifact.stat().st_size,
            "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        }] + [{
            "path": path.relative_to(output_dir).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        } for path in required],
        "node_errors": [],
        "deviations": [],
    }
    if include_review_media:
        receipt["review_media"] = {
            "renderer": review["renderer"],
            "color_pipeline": review["color_pipeline"],
            "neutral_rig_id": review["neutral_rig_id"],
            "neutral_renders": [
                {
                    "role": role,
                    "frame": review["neutral_frames"][role],
                    "path": review["neutral_render_paths"][role],
                }
                for role in ("early", "middle", "late")
            ],
            "hero_render": {
                "path": review["hero_render_path"],
                "camera": review["required_scene_nodes"]["hero_camera"],
            },
            "motion_preview": {
                "path": review["motion_preview_path"],
                "frame_start": review["motion_frames"][0],
                "frame_end": review["motion_frames"][-1],
            },
            "annotated_claim_sheet": {
                "path": review["annotated_claim_sheet_path"],
                "claims": observables,
            },
            "scene_nodes": review["required_scene_nodes"],
        }
    (output_dir / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")


def fake_hip_verifier(hip_path: Path, plan_path: Path) -> dict:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    receipt_by_frame = {
        int(Path(record["path"]).name.split(".")[-3]): record
        for record in plan["source_cache_receipt"]
    }
    source_frames = sorted(set([
        *plan["render_setup"]["neutral_frames"].values(),
        *plan["render_setup"]["motion_frames"],
    ]))
    project_root = next(
        ancestor for ancestor in plan_path.resolve().parents
        if all((ancestor / record["path"]).is_file() for record in plan["source_cache_receipt"])
    )
    file_nodes = [
        node["path"] for stage in plan["stages"] for node in stage["nodes"]
        if node["type"] == "file"
    ]
    proof_dir = hip_path.parent.parent / "04_evidence" / "parent-renders"
    proof_dir.mkdir(parents=True, exist_ok=True)
    proof_specs = [
        *((f"neutral-{role}", plan["render_setup"]["neutral_frames"][role]) for role in ("early", "middle", "late")),
        ("hero", plan["render_setup"]["neutral_frames"]["middle"]),
        *((f"motion-{index:03d}", frame) for index, frame in enumerate(plan["render_setup"]["motion_frames"])),
    ]
    parent_renders = []
    camera_prims = {
        "neutral_camera": "/World/Cameras/Neutral",
        "hero_camera": "/World/Cameras/Hero",
    }
    for index, (role, frame) in enumerate(proof_specs, start=1):
        path = proof_dir / f"{role}.{frame:04d}.png"
        image = Image.new("RGB", tuple(plan["render_setup"]["resolution"]), (20 * index % 255, 30, 45))
        ImageDraw.Draw(image).rectangle(
            (40, 50, 240 + 20 * index, 250), fill=(80, 35 * index % 255, 160)
        )
        image.save(path)
        parent_renders.append({
            "role": role,
            "frame": frame,
            "camera": camera_prims["hero_camera" if role == "hero" else "neutral_camera"],
            "lighting_mode": 1 if role == "hero" else 0,
            "path": str(path.resolve()),
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    stages = [{
        "stage_id": stage["id"],
        "network_section": stage["network_section"],
        "nodes": stage["nodes"],
        "output_node": stage["output_node"],
        "display_flag": True,
        "render_flag": True,
        "output_flag_required": index == len(plan["stages"]) - 1,
        "errors": [],
    } for index, stage in enumerate(plan["stages"])]
    scaffold_path = hip_path.parent.parent / "00_design" / "PARENT_SCAFFOLD.json"
    scaffold_identities = {}
    if scaffold_path.is_file():
        scaffold = json.loads(scaffold_path.read_text(encoding="utf-8"))
        scaffold_identities = {
            record["path"]: {"type": record["type"], "scaffold_id": record["scaffold_id"]}
            for record in scaffold["protected_nodes"].values()
        }
    return {
        "schema_version": 1,
        "verification_engine": "fresh-hython-reopen",
        "hip_path": str(hip_path.resolve()),
        "hip_sha256": hashlib.sha256(hip_path.read_bytes()).hexdigest(),
        "plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        "passed": True,
        "node_count": sum(len(stage["nodes"]) for stage in plan["stages"]),
        "network_sections": [stage["network_section"] for stage in plan["stages"]],
        "stages": stages,
        "upward_edges": [],
        "duplicate_node_positions": [],
        "node_errors": [],
        "scaffold_identities": scaffold_identities,
        "source_cache": {
            "passed": True,
            "records": [{
                "frame": frame,
                "path": str((project_root / receipt_by_frame[frame]["path"]).resolve()),
                "bytes": receipt_by_frame[frame]["bytes"],
                "sha256": receipt_by_frame[frame]["sha256"],
                "file_nodes": file_nodes,
                "active_cook_only": True,
                "sop_import_path": plan["stages"][-1]["output_node"],
                "sop_import_bound": True,
            } for frame in source_frames],
            "errors": [],
        },
        "render_setup": {
            "passed": True,
            "renderer": plan["render_setup"]["renderer"],
            "color_pipeline": plan["render_setup"]["color_pipeline"],
            "neutral_rig_id": plan["render_setup"]["neutral_rig_id"],
            "camera_prims": camera_prims,
            "ocio_config": "test-fixture-aces.ocio",
            "neutral_signature": {
                "samples": [{
                    "frame": frame,
                    "camera": {"primpath": "/World/Cameras/Neutral", "tz": 5.0},
                    "dome": {"primpath": "/World/Lights/NeutralDome", "xn__inputsintensity_i0a": 1.0},
                    "render_settings": {"resolutionx": 640, "resolutiony": 360, "samplesperpixel": 4},
                } for frame in source_frames],
                "camera": {"primpath": "/World/Cameras/Neutral", "tz": 5.0},
                "dome": {"primpath": "/World/Lights/NeutralDome", "xn__inputsintensity_i0a": 1.0},
                "render_settings": {"resolutionx": 640, "resolutiony": 360, "samplesperpixel": 4},
                "resolution": plan["render_setup"]["resolution"],
                "samples_per_pixel": plan["render_setup"]["samples_per_pixel"],
                "path_traced_samples": plan["render_setup"]["path_traced_samples"],
                "neutral_selector_input": 0,
                "locked_contract": {
                    "camera": plan["render_setup"]["neutral_camera_parameters"],
                    "dome": plan["render_setup"]["neutral_dome_parameters"],
                    "render_settings": plan["render_setup"]["neutral_render_parameters"],
                },
                "ocio_sha256": "a" * 64,
            },
            "parent_renders": parent_renders,
            "material_bindings": [{
                "role": record["role"],
                "frame": record["frame"],
                "prim_pattern": "/World/Look/**",
                "material_path": "/materials/LOOK_MATERIAL",
                "target_paths": ["/World/Look/mesh"],
                "passed": True,
            } for record in parent_renders],
            "nodes": [
                {
                    "role": role,
                    "path": path,
                    "type": {
                        "look_import": "sopimport",
                        "material_library": "materiallibrary",
                        "material_assignment": "assignmaterial",
                        "neutral_camera": "camera",
                        "hero_camera": "camera",
                        "neutral_dome": "domelight::3.0",
                        "hero_key": "distantlight::2.0",
                        "hero_fill": "distantlight::2.0",
                        "hero_rim": "distantlight::2.0",
                        "lighting_selector": "switch",
                        "render_settings": "karmarendersettings",
                        "render_output": "usdrender_rop",
                    }[role],
                    "connected_to_render_output": True,
                }
                for role, path in plan["render_setup"]["nodes"].items()
            ],
            "errors": [],
        },
    }


def write_playground(packet_path: Path, output_dir: Path) -> None:
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    cache_entries = []
    for frame, cache_record in enumerate(packet["source_cache_receipt"], start=1):
        cache_path = next(
            candidate
            for ancestor in output_dir.resolve().parents
            if (candidate := ancestor / cache_record["path"]).is_file()
        )
        cache_entries.append((frame, cache_record, cache_path))
    cache_record, cache_path = cache_entries[0][1:]
    hip_path = output_dir / packet["workspace_layout"]["hip_path"]
    hip_path.write_bytes(b"test playground hip")
    audit_path = output_dir / packet["workspace_layout"]["audit_path"]
    audit = {
        "schema_version": 1,
        "verification_engine": "fresh-hython-reopen",
        "hip_path": str(hip_path.resolve()),
        "hip_sha256": hashlib.sha256(hip_path.read_bytes()).hexdigest(),
        "passed": True,
        "source_file": "/obj/PLAYGROUND_SIM/SOURCE_PROMOTED_SIMULATION",
        "source_node": "/obj/PLAYGROUND_SIM/OUT_SIMULATION",
        "visibility_node": "/obj/PLAYGROUND_SIM/ENSURE_POINT_VISIBILITY",
        "floor_node": "/obj/PLAYGROUND_ENVIRONMENT/NEUTRAL_FLOOR",
        "floor_placement": "/obj/PLAYGROUND_ENVIRONMENT/PLACE_FLOOR",
        "environment_node": "/obj/PLAYGROUND_ENVIRONMENT/OUT_ENVIRONMENT",
        "simulation_import": "/stage/IMPORT_SIMULATION",
        "environment_import": "/stage/IMPORT_ENVIRONMENT",
        "scene_merge": "/stage/MERGE_SCENE",
        "material_library": "/stage/MATERIALS_STARTER",
        "material_assignment": "/stage/ASSIGN_STARTER_MATERIALS",
        "camera_node": "/stage/CAM_PLAYGROUND",
        "dome_light": "/stage/LIGHT_DOME",
        "key_light": "/stage/KEY",
        "fill_light": "/stage/FILL",
        "rim_light": "/stage/RIM",
        "lighting_selector": "/stage/SELECT_LIGHTING_MODE",
        "lighting_modes": ["dome", "photographer"],
        "photographer_lights": ["KEY", "FILL", "RIM"],
        "karma_settings": "/stage/RENDER_KARMA_SETTINGS",
        "render_output": "/stage/OUT_KARMA",
        "node_errors": [],
        "source_cache_path": str(cache_path.resolve()),
        "source_cache_sha256": cache_record["sha256"],
        "source_cache_bytes": cache_record["bytes"],
        "cache_sequence": [{
            "path": str(path.resolve()),
            "frame": frame,
            "bytes": record["bytes"],
            "sha256": record["sha256"],
            "errors": [],
        } for frame, record, path in cache_entries],
        "frame_range": [1, len(cache_entries)],
        "camera_framing": {"auto_framed": True},
        "render_configuration": {
            "camera": "/World/Cameras/Playground",
            "picture": str((output_dir / "renders/playground.$F4.exr").resolve()),
            "resolution_x": 768,
            "point_style": "Spheres",
            "renderer": "BRAY_HdKarma",
        },
    }
    audit_path.write_text(json.dumps(audit), encoding="utf-8")
    receipt_path = output_dir / packet["workspace_layout"]["receipt_path"]
    receipt_path.write_text(json.dumps({
        "schema_version": 1,
        "round_id": packet["round_id"],
        "source_behavior_content_hash": packet["source_behavior"]["content_hash"],
        "state": "internally-verified",
        "hip_path": packet["workspace_layout"]["hip_path"],
        "hip_bytes": hip_path.stat().st_size,
        "hip_sha256": hashlib.sha256(hip_path.read_bytes()).hexdigest(),
        "audit_path": packet["workspace_layout"]["audit_path"],
        "audit_sha256": hashlib.sha256(audit_path.read_bytes()).hexdigest(),
        "lighting_modes": ["dome", "photographer"],
    }), encoding="utf-8")


def run_look_round(root: Path, manifest_path: Path, worker, **kwargs):
    return _run_look_round(
        root, manifest_path, worker, fake_hip_verifier, write_playground, **kwargs
    )


class LookExecutionTests(unittest.TestCase):
    def test_direction_scaffold_builder_rejects_nonpositive_timeout(self) -> None:
        with self.assertRaisesRegex(ValueError, "timeout must be positive"):
            make_hython_direction_scaffold_builder(
                Path(__file__).resolve().parents[1],
                Path("C:/not-invoked/hython.exe"),
                timeout=0,
            )

    def test_final_image_review_requires_eight_distinct_cache_frames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = behavior_source(root, "a")
            source["cache_paths"] = source["cache_paths"][:7]
            with self.assertRaisesRegex(ValueError, "eight distinct cache frames"):
                prepare_look_round(root, STUDY_ID, source, [
                    direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
                ])

    def test_direction_requires_a_final_image_visual_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = direction("look-direction-weave", "Affinity Weave", "affinity", "strand density")
            candidate.pop("visual_target")
            with self.assertRaisesRegex(ValueError, "visual_target"):
                prepare_look_round(root, STUDY_ID, behavior_source(root, "a"), [candidate])

    def test_direction_cannot_defer_materials_framing_or_lighting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = direction("look-direction-weave", "Affinity Weave", "affinity", "strand density")
            candidate["exclusions"] = ["palette development", "final cinematography"]
            with self.assertRaisesRegex(ValueError, "materials, framing, and lighting"):
                prepare_look_round(root, STUDY_ID, behavior_source(root, "a"), [candidate])

    def test_worker_prompt_freezes_exact_plan_and_receipt_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "0"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            prompt = (root / manifest["directions"][0]["prompt_path"]).read_text(encoding="utf-8")
            self.assertIn('"context_id"', prompt)
            self.assertIn('"source_behavior_content_hash"', prompt)
            self.assertIn('"claim": "High and low affinity samples produce visibly different strand density."', prompt)
            self.assertIn('"mechanical_status"', prompt)
            self.assertIn('"visual_status"', prompt)
            self.assertIn('"technical_evidence_paths"', prompt)
            self.assertIn('"render_evidence_paths"', prompt)
            self.assertIn('"review_media"', prompt)
            self.assertIn('"render_setup"', prompt)
            self.assertIn('"hero_camera": "/stage/CAM_HERO"', prompt)
            self.assertIn('"bytes": 123', prompt)
            self.assertIn('"stages": [', prompt)
            self.assertIn('"inputs": []', prompt)
            self.assertIn('must name a node path present in that same stage’s `nodes` list', prompt)
            self.assertIn('`nodes` (never `ordered_nodes`)', prompt)
            self.assertIn('exactly one claim per state-to-form acceptance observable', prompt)
            self.assertIn('Do not stop at the probe', prompt)

    def test_prepares_and_builds_a_non_competing_00_look_playground_first(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "0"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            playground = manifest["playground"]
            self.assertTrue(playground["output_path"].endswith("/look-round-001/00_look"))
            packet = json.loads((root / playground["packet_path"]).read_text(encoding="utf-8"))
            self.assertEqual(packet["workspace_layout"]["hip_path"], "00_look.hiplc")
            self.assertEqual(packet["features"]["lighting_modes"], ["dome", "photographer"])
            self.assertEqual(packet["features"]["photographer_lights"], ["key", "fill", "rim"])
            self.assertTrue((root / playground["readme_path"]).is_file())
            calls = []

            def playground_builder(packet_path: Path, output_dir: Path) -> None:
                calls.append("playground")
                write_playground(packet_path, output_dir)

            def worker(packet_path: Path, output_dir: Path) -> None:
                calls.append("direction")
                write_receipt(packet_path, output_dir)

            _run_look_round(
                root, manifest_path, worker, fake_hip_verifier, playground_builder
            )
            self.assertEqual(calls, ["playground", "direction"])
            completed = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(completed["playground"]["state"], "internally-verified")
            self.assertTrue((root / completed["playground"]["hip_path"]).is_file())
            review_path = build_aggregate_review(root, manifest_path)
            review = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertEqual(review["playground_hip_path"], completed["playground"]["hip_path"])
            self.assertEqual([item["direction_id"] for item in review["directions"]], ["look-direction-weave"])

    def test_rejects_playground_audit_not_bound_to_the_frozen_cache_and_frame_range(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "0"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])

            def inconsistent_playground(packet_path: Path, output_dir: Path) -> None:
                write_playground(packet_path, output_dir)
                packet = json.loads(packet_path.read_text(encoding="utf-8"))
                audit_path = output_dir / packet["workspace_layout"]["audit_path"]
                audit = json.loads(audit_path.read_text(encoding="utf-8"))
                audit["source_cache_path"] = str((root / "different-cache.bgeo.sc").resolve())
                audit["frame_range"] = [99, 101]
                audit_path.write_text(json.dumps(audit), encoding="utf-8")
                receipt_path = output_dir / packet["workspace_layout"]["receipt_path"]
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                receipt["audit_sha256"] = hashlib.sha256(audit_path.read_bytes()).hexdigest()
                receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "did not prove the required setup"):
                _run_look_round(
                    root,
                    manifest_path,
                    write_receipt,
                    fake_hip_verifier,
                    inconsistent_playground,
                )

    def test_prepares_consistently_named_direction_and_attempt_workspaces(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "0"), [
                direction("look-direction-affinity-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            item = manifest["directions"][0]
            self.assertTrue(item["output_path"].endswith("/01_affinity-weave"))
            packet = json.loads((root / item["packet_path"]).read_text(encoding="utf-8"))
            self.assertEqual(packet["workspace_layout"], {
                "design_directory": "00_design",
                "implementation_plan": "00_design/IMPLEMENTATION_PLAN.json",
                "scene_directory": "01_scene",
                "scene_stem": "01_scene/01_affinity-weave",
                "probe_directory": "02_probes",
                "motion_directory": "03_motion",
                "evidence_directory": "04_evidence",
                "graph_audit": "04_evidence/graph-audit.json",
            })

            def worker(packet_path: Path, output_dir: Path) -> None:
                for name in ("00_design", "01_scene", "02_probes", "03_motion", "04_evidence"):
                    self.assertTrue((output_dir / name).is_dir())
                write_receipt(packet_path, output_dir)

            run_look_round(root, manifest_path, worker)
            completed = json.loads(manifest_path.read_text(encoding="utf-8"))
            audit_path = root / completed["directions"][0]["graph_audit_path"]
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            self.assertEqual(audit["verification_engine"], "fresh-hython-reopen")
            self.assertTrue(audit["passed"])

    def test_rejects_a_shallow_direction_without_four_implementation_stages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            brief = direction("look-direction-weave", "Affinity Weave", "affinity", "strand density")
            brief["implementation_stages"] = brief["implementation_stages"][:3]
            with self.assertRaisesRegex(ValueError, "at least four implementation stages"):
                prepare_look_round(root, STUDY_ID, behavior_source(root, "0"), [brief])

    def test_rejects_an_unexpanded_stage_plan_without_node_level_design(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "0"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])

            def shallow_worker(packet_path: Path, output_dir: Path) -> None:
                write_receipt(packet_path, output_dir)
                packet = json.loads(packet_path.read_text(encoding="utf-8"))
                plan_path = output_dir / packet["workspace_layout"]["implementation_plan"]
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                plan["stages"][0].pop("node_families")
                plan_path.write_text(json.dumps(plan), encoding="utf-8")
                receipt_path = output_dir / "receipt.json"
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                plan_artifact = next(item for item in receipt["artifacts"] if item["path"] == packet["workspace_layout"]["implementation_plan"])
                plan_artifact["bytes"] = plan_path.stat().st_size
                plan_artifact["sha256"] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
                receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "node_families"):
                run_look_round(root, manifest_path, shallow_worker)

    def test_rejects_any_undeclared_hip_anywhere_in_the_attempt_workspace(self) -> None:
        for relative in (
            "01_scene/01_weave.hip",
            "02_probes/undeclared.hip",
            "01_scene/nested/undeclared.hiplc",
            "undeclared.hipnc",
        ):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "0"), [
                    direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
                ])

                def ambiguous_worker(packet_path: Path, output_dir: Path) -> None:
                    write_receipt(packet_path, output_dir)
                    undeclared = output_dir / relative
                    undeclared.parent.mkdir(parents=True, exist_ok=True)
                    undeclared.write_bytes(b"second hip")

                with self.assertRaisesRegex(ValueError, "exactly one consistently named canonical HIP"):
                    run_look_round(root, manifest_path, ambiguous_worker)

    def test_parent_audit_must_reconcile_planned_nodes_with_fresh_hython_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "0"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])

            def inconsistent_verifier(hip_path: Path, plan_path: Path) -> dict:
                audit = fake_hip_verifier(hip_path, plan_path)
                audit["stages"][0]["nodes"][0]["type"] = "fabricated"
                return audit

            with self.assertRaisesRegex(ValueError, "did not prove implementation stage"):
                _run_look_round(
                    root, manifest_path, write_receipt, inconsistent_verifier, write_playground
                )

    def test_parent_audit_rejects_byte_identical_noncanonical_cache_copies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "0"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])

            def copied_cache_verifier(hip_path: Path, plan_path: Path) -> dict:
                audit = fake_hip_verifier(hip_path, plan_path)
                copied_root = root / "noncanonical-cache-copy"
                copied_root.mkdir()
                for record in audit["source_cache"]["records"]:
                    source = Path(record["path"])
                    copied = copied_root / source.name
                    copied.write_bytes(source.read_bytes())
                    record["path"] = str(copied.resolve())
                return audit

            with self.assertRaisesRegex(ValueError, "frozen source-cache binding metadata mismatch"):
                _run_look_round(
                    root, manifest_path, write_receipt, copied_cache_verifier, write_playground
                )

    def test_final_review_rechecks_recursive_hip_uniqueness(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "0"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            run_look_round(root, manifest_path, write_receipt)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            attempt_dir = root / manifest["directions"][0]["current_attempt_path"]
            (attempt_dir / "02_probes/late-undeclared.hip").write_bytes(b"late hip")

            with self.assertRaisesRegex(ValueError, "exactly one consistently named canonical HIP"):
                build_aggregate_review(root, manifest_path)

    def test_final_review_rechecks_00_look_scene_uniqueness(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "0"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            run_look_round(root, manifest_path, write_receipt)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            playground = root / manifest["playground"]["output_path"]
            (playground / "tangent.hipnc").write_bytes(b"undeclared personal tangent")

            with self.assertRaisesRegex(ValueError, "exactly one canonical playground HIP"):
                build_aggregate_review(root, manifest_path)

    def test_final_review_rejects_a_symlinked_00_look_scene(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "0"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            run_look_round(root, manifest_path, write_receipt)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            hip_path = root / manifest["playground"]["hip_path"]
            outside = root / "substituted-playground.hiplc"
            outside.write_bytes(hip_path.read_bytes())
            hip_path.unlink()
            try:
                hip_path.symlink_to(outside)
            except OSError as error:
                self.skipTest(f"file symlinks are unavailable: {error}")

            with self.assertRaisesRegex(ValueError, "regular non-symlink file"):
                build_aggregate_review(root, manifest_path)

    def test_prepares_isolated_sequential_packets_without_exposing_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = behavior_source(root, "a")
            directions = [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
                direction("look-direction-membrane", "Tension Membrane", "tension", "surface displacement"),
            ]

            manifest_path = prepare_look_round(root, STUDY_ID, source, directions)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["state"], "prepared")
            self.assertEqual(manifest["execution_mode"], "sequential-fresh-context")
            self.assertEqual(manifest["review_policy"], "withhold-until-all-complete")
            self.assertEqual(manifest["execution_policy"], {
                "max_attempts_per_direction": 2,
                "worker_timeout_seconds": 1800,
                "max_total_tokens_per_attempt": 200000,
                "max_estimated_cost_usd_per_attempt": 10.0,
                "repair_mode": "targeted-from-parent-diagnostics",
            })
            self.assertEqual([item["direction_id"] for item in manifest["directions"]], [
                "look-direction-weave", "look-direction-membrane",
            ])
            self.assertFalse((manifest_path.parents[2] / "02_review").exists())
            packets = []
            for item in manifest["directions"]:
                packet_path = root / item["packet_path"]
                brief_path = root / item["brief_path"]
                packet = json.loads(packet_path.read_text(encoding="utf-8"))
                brief = json.loads(brief_path.read_text(encoding="utf-8"))
                packets.append(packet)
                self.assertEqual(hashlib.sha256(brief_path.read_bytes()).hexdigest(), item["brief_sha256"])
                self.assertEqual(brief["state"], "selected")
                self.assertEqual(brief["direction"], packet["direction"])
                self.assertEqual(packet["source_behavior"]["content_hash"], source["content_hash"])
                self.assertEqual(packet["constraints"]["behavior"], "read-only")
                self.assertEqual(packet["constraints"]["materials"], "required")
                self.assertEqual(packet["constraints"]["framing"], "required")
                self.assertEqual(packet["constraints"]["lighting"], "required")
                self.assertEqual(packet["output_contract"]["receipt_state"], "visual-review-ready")
                self.assertEqual(packet["review_contract"]["renderer"], "karma")
                self.assertEqual(packet["review_contract"]["neutral_rig_id"], "bzor-neutral-lookdev-v1")
                self.assertEqual(set(packet["review_contract"]["neutral_frames"]), {"early", "middle", "late"})
                self.assertTrue((packet_path.parent / "WORKER_PROMPT.md").is_file())
            self.assertNotEqual(packets[0]["context_id"], packets[1]["context_id"])
            self.assertNotIn("Tension Membrane", (root / manifest["directions"][0]["prompt_path"]).read_text())

    def test_attempt_budget_stops_blind_rebuilds_before_worker_launch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "a"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["state"] = "failed"
            manifest["directions"][0]["attempt_count"] = 2
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            launched = False

            def worker(packet: Path, output: Path) -> None:
                nonlocal launched
                launched = True

            with self.assertRaisesRegex(RuntimeError, "attempt budget exhausted"):
                run_look_round(root, manifest_path, worker)
            self.assertFalse(launched)

    def test_frozen_failed_round_cannot_be_executed_again(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "a"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["state"] = "failed"
            manifest["frozen"] = True
            manifest["frozen_disposition"] = "failed-research-provenance"
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            launched = False

            def worker(packet: Path, output: Path) -> None:
                nonlocal launched
                launched = True

            with self.assertRaisesRegex(RuntimeError, "frozen failed research provenance"):
                run_look_round(root, manifest_path, worker)
            self.assertFalse(launched)

    def test_parent_scaffold_exists_before_creative_worker_launch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "a"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            calls: list[str] = []

            def scaffold(packet_path: Path, output: Path) -> None:
                packet = json.loads(packet_path.read_text(encoding="utf-8"))
                scene = output / packet["workspace_layout"]["scene_stem"]
                scene = scene.with_suffix(".hiplc")
                scene.parent.mkdir(parents=True, exist_ok=True)
                scene.write_bytes(b"parent-owned scaffold")
                scaffold_id = "a" * 64
                (output / "00_design" / "PARENT_SCAFFOLD.json").write_text(json.dumps({
                    "schema_version": 1,
                    "protected_nodes": {
                        "final_output": {
                            "path": "/obj/LOOK_DIRECTION/OUT_FINAL",
                            "type": "null",
                            "scaffold_id": scaffold_id,
                        },
                    },
                }), encoding="utf-8")
                calls.append("scaffold")

            def worker(packet_path: Path, output: Path) -> None:
                self.assertEqual(calls, ["scaffold"])
                self.assertEqual(len(list((output / "01_scene").glob("*.hip*"))), 1)
                calls.append("worker")
                write_receipt(packet_path, output)

            run_look_round(root, manifest_path, worker, scaffold_builder=scaffold)
            self.assertEqual(calls, ["scaffold", "worker"])

    def test_parent_failure_creates_one_targeted_repair_from_prior_scene(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "a"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            verifier_calls = 0

            def verifier(hip_path: Path, plan_path: Path):
                nonlocal verifier_calls
                verifier_calls += 1
                if verifier_calls == 1:
                    raise RuntimeError("parent preflight: missing protected material binding")
                return fake_hip_verifier(hip_path, plan_path)

            def first_worker(packet_path: Path, output: Path) -> None:
                write_receipt(packet_path, output)
                (output / "00_design" / "creative-state.txt").write_text("keep me", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "missing protected material binding"):
                _run_look_round(root, manifest_path, first_worker, verifier, write_playground)
            failed = json.loads(manifest_path.read_text(encoding="utf-8"))
            item = failed["directions"][0]
            self.assertEqual(item["state"], "repair-required")
            self.assertTrue((root / item["failure_diagnostic_path"]).is_file())

            def repair_worker(packet_path: Path, output: Path) -> None:
                packet = json.loads(packet_path.read_text(encoding="utf-8"))
                self.assertEqual(packet["repair_context"]["mode"], "targeted-from-parent-diagnostics")
                self.assertEqual((output / "00_design" / "creative-state.txt").read_text(), "keep me")
                write_receipt(packet_path, output)

            _run_look_round(root, manifest_path, repair_worker, verifier, write_playground)
            repaired = json.loads(manifest_path.read_text(encoding="utf-8"))["directions"][0]
            self.assertEqual(repaired["attempt_count"], 2)
            self.assertTrue(repaired["receipt_verified"])

    def test_claims_separate_mechanical_and_visual_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(
                root,
                STUDY_ID,
                behavior_source(root, "a"),
                [direction("look-direction-weave", "Affinity Weave", "affinity", "strand density")],
            )
            with self.assertRaisesRegex(ValueError, "mechanical_status"):
                run_look_round(
                    root,
                    manifest_path,
                    lambda packet, output: write_receipt(
                        packet, output, include_review_media=False, legacy_claims=True
                    ),
                )

    def test_direction_receipt_without_rendered_review_media_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(
                root,
                STUDY_ID,
                behavior_source(root, "a"),
                [direction("look-direction-weave", "Affinity Weave", "affinity", "strand density")],
            )
            with self.assertRaisesRegex(ValueError, "review_media"):
                run_look_round(
                    root,
                    manifest_path,
                    lambda packet, output: write_receipt(packet, output, include_review_media=False),
                )

    def test_parent_hython_audit_must_prove_direction_render_setup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(
                root,
                STUDY_ID,
                behavior_source(root, "a"),
                [direction("look-direction-weave", "Affinity Weave", "affinity", "strand density")],
            )
            def verifier_without_render_setup(hip_path: Path, plan_path: Path) -> dict:
                audit = fake_hip_verifier(hip_path, plan_path)
                audit.pop("render_setup")
                return audit

            with self.assertRaisesRegex(ValueError, "render setup"):
                _run_look_round(
                    root,
                    manifest_path,
                    write_receipt,
                    verifier_without_render_setup,
                    write_playground,
                )

    def test_parent_hython_audit_must_produce_bound_render_proofs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "a"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])

            def incomplete_verifier(hip_path: Path, plan_path: Path) -> dict:
                audit = fake_hip_verifier(hip_path, plan_path)
                audit["render_setup"]["parent_renders"] = []
                return audit

            with self.assertRaisesRegex(ValueError, "motion render proofs"):
                _run_look_round(
                    root, manifest_path, write_receipt, incomplete_verifier, write_playground,
                )

    def test_parent_motion_proof_must_show_temporal_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "a"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])

            def static_motion_verifier(hip_path: Path, plan_path: Path) -> dict:
                audit = fake_hip_verifier(hip_path, plan_path)
                records = [
                    record for record in audit["render_setup"]["parent_renders"]
                    if record["role"].startswith("motion-")
                ]
                source = Path(records[0]["path"]).read_bytes()
                for record in records[1:]:
                    path = Path(record["path"])
                    path.write_bytes(source)
                    record["bytes"] = path.stat().st_size
                    record["sha256"] = hashlib.sha256(source).hexdigest()
                return audit

            with self.assertRaisesRegex(ValueError, "temporal change"):
                _run_look_round(
                    root, manifest_path, write_receipt, static_motion_verifier, write_playground,
                )

    def test_receipt_node_errors_block_decision_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "a"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])

            def worker(packet_path: Path, output_dir: Path) -> None:
                write_receipt(packet_path, output_dir)
                receipt_path = output_dir / "receipt.json"
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                receipt["node_errors"] = ["material assignment failed"]
                receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "node_errors"):
                run_look_round(root, manifest_path, worker)

    def test_runs_workers_sequentially_verifies_receipts_then_builds_one_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = behavior_source(root, "b")
            directions = [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
                direction("look-direction-membrane", "Tension Membrane", "tension", "surface displacement"),
            ]
            manifest_path = prepare_look_round(root, STUDY_ID, source, directions)
            calls = []

            def worker(packet_path: Path, output_dir: Path) -> None:
                packet = json.loads(packet_path.read_text(encoding="utf-8"))
                calls.append((packet["direction"]["id"], packet["context_id"], packet["attempt_id"], output_dir))
                write_receipt(packet_path, output_dir)

            completed_path = run_look_round(root, manifest_path, worker)

            self.assertEqual([call[0] for call in calls], ["look-direction-weave", "look-direction-membrane"])
            self.assertEqual(len({call[1] for call in calls}), 2)
            self.assertEqual(len({call[2] for call in calls}), 2)
            completed = json.loads(completed_path.read_text(encoding="utf-8"))
            self.assertEqual(completed["state"], "decision-ready-awaiting-comparative-review")
            self.assertTrue(all(item["receipt_verified"] for item in completed["directions"]))
            self.assertTrue(all(item["status"]["decision_ready"] for item in completed["directions"]))
            review_path = build_aggregate_review(root, completed_path)
            review = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertEqual(review["state"], "ready-for-kc-review")
            self.assertEqual(len(review["directions"]), 2)
            self.assertTrue(review["directions"][0]["canonical_hip_path"].endswith("/01_scene/01_weave.hiplc"))
            comparison = review_path.with_name("COMPARISON.md").read_text(encoding="utf-8")
            self.assertIn("Affinity Weave", comparison)
            self.assertIn("Tension Membrane", comparison)
            self.assertIn("Canonical editable HIP:", comparison)
            self.assertIn("Matched neutral frames", comparison)

    def test_aggregate_review_requires_measured_neutral_scene_equivalence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "b"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
                direction("look-direction-membrane", "Tension Membrane", "tension", "surface displacement"),
            ])

            def differing_verifier(hip_path: Path, plan_path: Path) -> dict:
                audit = fake_hip_verifier(hip_path, plan_path)
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                if plan["direction_id"] == "look-direction-membrane":
                    audit["render_setup"]["neutral_signature"]["locked_contract"]["camera"]["tz"] = 6.0
                return audit

            with self.assertRaisesRegex(ValueError, "equivalent neutral review conditions"):
                _run_look_round(root, manifest_path, write_receipt, differing_verifier, write_playground)

    def test_hermes_worker_uses_a_new_process_for_each_direction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_agent = root / "fake_agent.py"
            repo_root = Path(__file__).resolve().parents[1]
            fake_agent.write_text(
                f"import sys; sys.path[:0] = [{str(repo_root)!r}, {str(repo_root / 'src')!r}]\n"
                "import json, os, re, sys\n"
                "from pathlib import Path\n"
                "from tests.test_look_execution import write_receipt\n"
                "prompt = sys.argv[-1]\n"
                "packet_path = Path(re.search(r'PACKET: (.+)', prompt).group(1).strip())\n"
                "output_dir = Path(re.search(r'OUTPUT: (.+)', prompt).group(1).strip())\n"
                "packet = json.loads(packet_path.read_text(encoding='utf-8'))\n"
                "write_receipt(packet_path, output_dir, evidence_content=str(os.getpid()))\n"
                "print(packet['context_id'])\n",
                encoding="utf-8",
            )
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "c"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
                direction("look-direction-membrane", "Tension Membrane", "tension", "surface displacement"),
            ])

            run_look_round(root, manifest_path, make_hermes_worker(root, [sys.executable, str(fake_agent)]))

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            pids = [(root / item["receipt_path"]).parent.joinpath("probe.txt").read_text() for item in manifest["directions"]]
            self.assertEqual(len(set(pids)), 2)
            for item in manifest["directions"]:
                process_receipt = json.loads((root / item["receipt_path"]).parent.joinpath("agent-process.json").read_text())
                self.assertEqual(process_receipt["returncode"], 0)
                self.assertIn(item["context_id"], process_receipt["stdout"])

    def test_hermes_worker_keeps_large_prompt_content_out_of_the_windows_command_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "attempt"
            output.mkdir()
            packet = output / "execution-packet.json"
            packet.write_text("{}", encoding="utf-8")
            prompt = output / "WORKER_PROMPT.md"
            prompt.write_text("contract\n" + "x" * 200_000, encoding="utf-8")
            fake_agent = root / "record_query.py"
            fake_agent.write_text(
                "import sys\n"
                "from pathlib import Path\n"
                "query = sys.argv[-1]\n"
                "Path('query.txt').write_text(query, encoding='utf-8')\n",
                encoding="utf-8",
            )

            make_hermes_worker(root, [sys.executable, str(fake_agent)])(packet, output)

            query = (output / "query.txt").read_text(encoding="utf-8")
            self.assertLess(len(query), 4096)
            self.assertIn(f"PROMPT: {prompt.resolve()}", query)
            self.assertIn("OUTPUT/receipt.json", query)
            self.assertIn("OUTPUT/00_design/IMPLEMENTATION_PLAN.json", query)
            self.assertIn("exact planned canonical per-frame File SOP", query)
            self.assertIn("bind Karma settings to CAM_HERO", query)
            self.assertIn("actual distantlight", query)
            self.assertIn("configure OUT_KARMA's renderer parameter", query)
            self.assertIn("direction.state_to_form_mappings[*].acceptance_observable", query)
            self.assertIn("byte-for-byte and in order", query)
            self.assertIn("Each claim's render_evidence_paths may use", query)
            self.assertIn("auxiliary overlays, charts, contact sheets", query)
            self.assertIn("actual independently measured and emitted values", query)
            self.assertIn("both the relationship axis and measured disturbance axis", query)
            self.assertIn("Reject and relight a hero that is near-black", query)
            self.assertIn("PARENT_SCAFFOLD.json", query)
            self.assertIn("Open and extend the existing canonical HIP", query)
            self.assertIn("last output_node exactly", query)
            self.assertIn("/obj/LOOK_DIRECTION/OUT_FINAL", query)
            self.assertIn("repair_context", query)
            self.assertIn("PARENT_FAILURE_DIAGNOSTIC.json", query)
            self.assertNotIn("x" * 100, query)

    def test_worker_usage_report_enforces_token_and_cost_budgets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "attempt"
            output.mkdir()
            packet = output / "execution-packet.json"
            packet.write_text("{}", encoding="utf-8")
            (output / "WORKER_PROMPT.md").write_text("contract", encoding="utf-8")
            fake_agent = root / "fake_usage_agent.py"
            fake_agent.write_text(
                "import json,sys\n"
                "from pathlib import Path\n"
                "p=Path(sys.argv[sys.argv.index('--usage-file')+1])\n"
                "p.write_text(json.dumps({'total_tokens': 201, 'estimated_cost_usd': 1.25}))\n",
                encoding="utf-8",
            )
            worker = make_hermes_worker(
                root,
                [sys.executable, str(fake_agent)],
                max_total_tokens=200,
                max_estimated_cost_usd=2.0,
                capture_usage=True,
            )
            with self.assertRaisesRegex(RuntimeError, "token budget exceeded"):
                worker(packet, output)
            process_receipt = json.loads((output / "agent-process.json").read_text())
            self.assertEqual(process_receipt["usage"]["total_tokens"], 201)

    def test_tampered_manifest_cannot_redirect_worker_inside_or_outside_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "d"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["directions"][0]["output_path"] = "docs"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            calls = []

            with self.assertRaisesRegex(ValueError, "immutable round descriptor"):
                run_look_round(root, manifest_path, lambda packet, output: calls.append((packet, output)))

            self.assertEqual(calls, [])

    def test_promoted_behavior_caches_must_be_canonical_existing_study_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = behavior_source(root, "e")
            source["cache_paths"] = ["docs/private.txt"]
            with self.assertRaisesRegex(ValueError, "canonical selected Behavior"):
                prepare_look_round(root, STUDY_ID, source, [
                    direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
                ])

    def test_receipt_rejects_claim_evidence_that_is_not_a_verified_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "f"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])

            def worker(packet_path: Path, output_dir: Path) -> None:
                write_receipt(packet_path, output_dir, evidence="unrelated.txt", claims=["missing claim evidence"])

            with self.assertRaisesRegex(ValueError, "claim coverage mismatch"):
                run_look_round(root, manifest_path, worker)

    def test_retry_cannot_reuse_a_stale_receipt_from_failed_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "1"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])

            def failed_worker(packet_path: Path, output_dir: Path) -> None:
                write_receipt(packet_path, output_dir)
                raise RuntimeError("worker failed after writing stale receipt")

            with self.assertRaisesRegex(RuntimeError, "stale receipt"):
                run_look_round(root, manifest_path, failed_worker)
            with self.assertRaisesRegex(ValueError, "regular non-symlink file"):
                run_look_round(root, manifest_path, lambda packet, output: None)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["state"], "failed")
            self.assertEqual(manifest["directions"][0]["attempt_count"], 2)

    def test_aggregate_review_revalidates_artifact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "2"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            run_look_round(root, manifest_path, write_receipt)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            receipt_path = root / manifest["directions"][0]["receipt_path"]
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            (receipt_path.parent / receipt["artifacts"][0]["path"]).write_text("tampered", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "artifact metadata mismatch"):
                build_aggregate_review(root, manifest_path)

    def test_receipt_must_cover_every_acceptance_observable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            brief = direction("look-direction-weave", "Affinity Weave", "affinity", "strand density")
            brief["state_to_form_mappings"].append({
                "source_attribute": "tension",
                "visible_response": "bend",
                "houdini_mechanism": "Drive bend from tension.",
                "acceptance_observable": "High tension produces more bend than low tension.",
            })
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "3"), [brief])

            def incomplete_worker(packet_path: Path, output_dir: Path) -> None:
                packet = json.loads(packet_path.read_text(encoding="utf-8"))
                first = packet["direction"]["state_to_form_mappings"][0]["acceptance_observable"]
                write_receipt(packet_path, output_dir, claims=[first])

            with self.assertRaisesRegex(ValueError, "claim coverage mismatch"):
                run_look_round(root, manifest_path, incomplete_worker)

    def test_round_lock_prevents_concurrent_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "4"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            lock = manifest_path.with_name(".run.lock")
            lock.write_text("other runner", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "already running"):
                run_look_round(root, manifest_path, write_receipt)

    def test_worker_cannot_rewrite_the_frozen_attempt_packet(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "5"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])

            def tampering_worker(packet_path: Path, output_dir: Path) -> None:
                packet = json.loads(packet_path.read_text(encoding="utf-8"))
                packet["direction"]["state_to_form_mappings"][0]["acceptance_observable"] = "Easier fake claim."
                packet_path.write_text(json.dumps(packet), encoding="utf-8")
                write_receipt(packet_path, output_dir)

            with self.assertRaisesRegex(ValueError, "attempt packet changed"):
                run_look_round(root, manifest_path, tampering_worker)

    def test_execution_rejects_behavior_cache_changed_after_preparation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = behavior_source(root, "6")
            manifest_path = prepare_look_round(root, STUDY_ID, source, [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            (root / source["cache_paths"][0]).write_bytes(b"changed after freeze")

            with self.assertRaisesRegex(ValueError, "Behavior cache changed"):
                run_look_round(root, manifest_path, write_receipt)
    def test_brief_requires_lighting_assumptions_and_cost_tier(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            brief = direction("look-direction-weave", "Affinity Weave", "affinity", "strand density")
            brief.pop("lighting_assumptions")
            with self.assertRaisesRegex(ValueError, "lighting_assumptions"):
                prepare_look_round(root, STUDY_ID, behavior_source(root, "7"), [brief])
            brief["lighting_assumptions"] = "Neutral technical rig."
            brief["cost_tier"] = "unknown"
            with self.assertRaisesRegex(ValueError, "cost_tier"):
                prepare_look_round(root, STUDY_ID, behavior_source(root, "8"), [brief])
    def test_gated_cost_round_requires_explicit_execution_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            brief = direction("look-direction-weave", "Affinity Weave", "affinity", "strand density")
            brief["cost_tier"] = "study"
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "9"), [brief])
            calls = []
            with self.assertRaisesRegex(ValueError, "explicit cost approval"):
                run_look_round(root, manifest_path, lambda packet, output: calls.append((packet, output)))
            self.assertEqual(calls, [])
            run_look_round(root, manifest_path, write_receipt, cost_approved=True)
    def test_source_claim_must_match_the_canonical_promoted_component(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = behavior_source(root, "a")
            source["content_hash"] = "sha256:" + "b" * 64
            with self.assertRaisesRegex(ValueError, "canonical promoted Behavior"):
                prepare_look_round(root, STUDY_ID, source, [
                    direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
                ])
    def test_execution_rejects_canonical_behavior_record_changed_after_preparation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "b"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            store = StudioStore(root)
            component = store.read("components", "component-behavior-a")
            component["content_hash"] = "sha256:" + "c" * 64
            store.update("components", "component-behavior-a", component)
            with self.assertRaisesRegex(ValueError, "canonical promoted Behavior changed"):
                run_look_round(root, manifest_path, write_receipt)
    def test_manifest_cannot_remove_a_selected_direction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "c"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
                direction("look-direction-membrane", "Tension Membrane", "tension", "surface displacement"),
            ])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["directions"].pop()
            descriptor_path = manifest_path.with_name("round-descriptor.json")
            descriptor_path.chmod(0o644)
            descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
            descriptor["directions"].pop()
            descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")
            manifest["round_descriptor_sha256"] = hashlib.sha256(descriptor_path.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "round anchor"):
                run_look_round(root, manifest_path, write_receipt)

    def test_manifest_cannot_replace_frozen_source_cache_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "d"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            substitute = root / "docs" / "substitute.bin"
            substitute.parent.mkdir()
            substitute.write_bytes(b"substitute")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["source_cache_receipt"] = [{
                "path": "docs/substitute.bin",
                "bytes": substitute.stat().st_size,
                "sha256": hashlib.sha256(substitute.read_bytes()).hexdigest(),
            }]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "immutable round descriptor"):
                run_look_round(root, manifest_path, write_receipt)

    def test_final_review_requires_the_exact_canonical_attempt_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "e"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            run_look_round(root, manifest_path, write_receipt)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            item = manifest["directions"][0]
            actual_attempt = root / item["current_attempt_path"]
            redirected = actual_attempt.parent / "shadow" / actual_attempt.name
            shutil.copytree(actual_attempt, redirected)
            item["current_attempt_path"] = redirected.relative_to(root).as_posix()
            item["attempt_packet_path"] = (redirected / "execution-packet.json").relative_to(root).as_posix()
            item["receipt_path"] = (redirected / "receipt.json").relative_to(root).as_posix()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "canonical attempt workspace"):
                build_aggregate_review(root, manifest_path)

    def test_final_review_binds_attempt_packet_to_frozen_base_packet(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "f"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            run_look_round(root, manifest_path, write_receipt)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            item = manifest["directions"][0]
            attempt_packet_path = root / item["attempt_packet_path"]
            packet = json.loads(attempt_packet_path.read_text(encoding="utf-8"))
            packet["direction"]["thesis"] = "Weakened after execution."
            attempt_packet_path.write_text(json.dumps(packet), encoding="utf-8")
            item["attempt_packet_sha256"] = hashlib.sha256(attempt_packet_path.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "frozen base packet"):
                build_aggregate_review(root, manifest_path)

    def test_legacy_technical_complete_state_cannot_release_comparative_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "1"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            run_look_round(root, manifest_path, write_receipt)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["state"] = "complete-awaiting-comparative-review"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "decision-ready"):
                build_aggregate_review(root, manifest_path)

    def test_aggregate_recomputes_claim_summary_from_verified_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "1"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            run_look_round(root, manifest_path, write_receipt)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["directions"][0]["claim_summary"] = {"demonstrated": 0, "partial": 0, "failed": 999}
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            review_path = build_aggregate_review(root, manifest_path)
            review = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertEqual(review["directions"][0]["claim_summary"], {
                "mechanical": {"demonstrated": 1, "partial": 0, "failed": 0},
                "visual": {"demonstrated": 1, "partial": 0, "failed": 0},
            })

    def test_worker_process_logs_are_bounded_on_disk(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            noisy_agent = root / "noisy_agent.py"
            noisy_agent.write_text(
                "import sys, time\n"
                "sys.stdout.write('x' * 2000000)\n"
                "sys.stdout.flush()\n"
                "time.sleep(10)\n",
                encoding="utf-8",
            )
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "2"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            with self.assertRaisesRegex(RuntimeError, "output limit"):
                run_look_round(root, manifest_path, make_hermes_worker(
                    root, [sys.executable, str(noisy_agent)], timeout=20,
                ))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            log_path = root / manifest["directions"][0]["current_attempt_path"] / "agent-stdout.log"
            self.assertLessEqual(log_path.stat().st_size, 1_000_000)
    def test_final_review_cannot_substitute_an_older_valid_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "3"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])

            def first_attempt(packet_path: Path, output_dir: Path) -> None:
                write_receipt(packet_path, output_dir)
                raise RuntimeError("force retry after a complete but unaccepted attempt")

            with self.assertRaisesRegex(RuntimeError, "force retry"):
                run_look_round(root, manifest_path, first_attempt)
            run_look_round(root, manifest_path, write_receipt)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            item = manifest["directions"][0]
            direction_dir = root / item["output_path"]
            older_dir = direction_dir / "attempt-001"
            older_packet = older_dir / "execution-packet.json"
            item.update({
                "attempt_count": 1,
                "current_attempt_id": f"{item['context_id']}-attempt-001",
                "current_attempt_path": older_dir.relative_to(root).as_posix(),
                "attempt_packet_path": older_packet.relative_to(root).as_posix(),
                "attempt_packet_sha256": hashlib.sha256(older_packet.read_bytes()).hexdigest(),
                "receipt_path": (older_dir / "receipt.json").relative_to(root).as_posix(),
            })
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "latest canonical attempt"):
                build_aggregate_review(root, manifest_path)
    def test_mutable_flags_cannot_selectively_rerun_a_verified_direction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "4"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
                direction("look-direction-membrane", "Tension Membrane", "tension", "surface displacement"),
            ])
            run_look_round(root, manifest_path, write_receipt)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["state"] = "failed"
            manifest["directions"][0]["receipt_verified"] = False
            manifest["directions"][0]["state"] = "failed"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            calls = []
            run_look_round(root, manifest_path, lambda packet, output: calls.append((packet, output)))
            self.assertEqual(calls, [])
            recovered = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual([item["attempt_count"] for item in recovered["directions"]], [1, 1])

    def test_released_review_is_hash_bound_and_revalidated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "5"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            run_look_round(root, manifest_path, write_receipt)
            review_path = build_aggregate_review(root, manifest_path)
            comparison_path = review_path.with_name("COMPARISON.md")
            comparison_path.write_text("tampered after release", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "released review integrity"):
                build_aggregate_review(root, manifest_path)
    @unittest.skipUnless(sys.platform == "win32", "Windows Job-tree termination regression")
    def test_output_overflow_terminates_worker_descendants(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "surviving-child.txt"
            child = root / "child.py"
            child.write_text(
                "import pathlib, sys, time\n"
                "time.sleep(2)\n"
                "pathlib.Path(sys.argv[1]).write_text('survived', encoding='utf-8')\n",
                encoding="utf-8",
            )
            parent = root / "parent.py"
            parent.write_text(
                "import subprocess, sys, time\n"
                "subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2]])\n"
                "sys.stdout.write('x' * 2000000)\n"
                "sys.stdout.flush()\n"
                "time.sleep(10)\n",
                encoding="utf-8",
            )
            manifest_path = prepare_look_round(root, STUDY_ID, behavior_source(root, "6"), [
                direction("look-direction-weave", "Affinity Weave", "affinity", "strand density"),
            ])
            with self.assertRaisesRegex(RuntimeError, "output limit"):
                run_look_round(root, manifest_path, make_hermes_worker(
                    root, [sys.executable, str(parent), str(child), str(marker)], timeout=20,
                ))
            time.sleep(3)
            self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
