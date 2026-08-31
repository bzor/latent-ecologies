"""Sequential, isolated Look-direction execution rounds."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import shutil
import signal
import subprocess
import threading
import uuid
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from PIL import Image

from .doctor import discover_tools
from .studio_schema import validate_record
from .studio_store import StudioStore
from .study_vault import study_directory_name


_DIRECTION_ID = re.compile(r"look-direction-[a-z0-9]+(?:-[a-z0-9]+)*")
_STAGE_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_ROUND_ID = re.compile(r"look-round-[0-9]{3}")
_CACHE_FRAME = re.compile(r"(\d{3,6})(?=\.(?:bgeo|vdb)(?:\.sc)?$)", re.IGNORECASE)
_REQUIRED_DIRECTION_FIELDS = (
    "id",
    "title",
    "thesis",
    "state_to_form_mappings",
    "primary_hierarchy",
    "representation_system",
    "lighting_assumptions",
    "cost_tier",
    "motion_proposition",
    "exclusions",
    "risks",
    "cheapest_decisive_probe",
    "stop_conditions",
    "implementation_stages",
    "visual_target",
)
_REQUIRED_VISUAL_TARGET_FIELDS = (
    "references",
    "final_image_thesis",
    "required_reads",
    "prohibited_reads",
    "material_intent",
    "framing_intent",
    "lighting_intent",
    "temporal_signature",
)
_REQUIRED_MAPPING_FIELDS = (
    "source_attribute",
    "visible_response",
    "houdini_mechanism",
    "acceptance_observable",
)
_REQUIRED_STAGE_FIELDS = (
    "id",
    "title",
    "intent",
    "data_inputs",
    "houdini_strategy",
    "output",
    "acceptance_observable",
)
_PROCESS_OUTPUT_LIMIT = 1_000_000
_PARENT_OWNED_WORKER_ARTIFACTS = {
    "agent-stdout.log", "agent-stderr.log", "agent-process.json", "agent-usage.json",
}
Worker = Callable[[Path, Path], None]
HipVerifier = Callable[[Path, Path], Mapping[str, Any]]
PlaygroundBuilder = Callable[[Path, Path], None]
ScaffoldBuilder = Callable[[Path, Path], None]


class LookBudgetExceeded(RuntimeError):
    """Raised when a bounded creative worker exceeds its declared resource budget."""


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(dict(value), handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_exclusive_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(dict(value), handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _round_anchor_path(root: Path, study_id: str, round_id: str) -> Path:
    return (
        root / "work" / "studio" / "look-round-anchors" /
        study_directory_name(study_id) / f"{round_id}.json"
    )


def _contained_path(root: Path, value: object, label: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError(f"{label} must be a project-relative path")
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label} escapes project root") from error
    return path


def _require_regular_contained_file(root: Path, path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular non-symlink file")
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError) as error:
        raise ValueError(f"{label} resolves outside the project root") from error


def _nonempty_strings(value: object, label: str) -> None:
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{label} must be a non-empty list of non-empty strings")


_IMMUTABLE_ITEM_FIELDS = (
    "sequence_index", "direction_id", "title", "context_id", "brief_path", "brief_sha256",
    "packet_path", "packet_sha256", "prompt_path", "prompt_sha256", "output_path",
)


def _immutable_item(item: Mapping[str, Any]) -> dict[str, Any]:
    return {field: item.get(field) for field in _IMMUTABLE_ITEM_FIELDS}


_IMMUTABLE_PLAYGROUND_FIELDS = (
    "packet_path", "packet_sha256", "readme_path", "readme_sha256", "output_path",
)


def _immutable_playground(item: Mapping[str, Any]) -> dict[str, Any]:
    return {field: item.get(field) for field in _IMMUTABLE_PLAYGROUND_FIELDS}


def _validate_source(root: Path, study_id: str, source: Mapping[str, Any]) -> list[dict[str, Any]]:
    component_id = source.get("id")
    if not isinstance(component_id, str) or not component_id.startswith("component-behavior-"):
        raise ValueError("source Behavior requires a canonical component id")
    if source.get("component_kind") != "behavior" or source.get("state") != "promoted":
        raise ValueError("Look execution requires a promoted Behavior component")
    content_hash = source.get("content_hash")
    if not isinstance(content_hash, str) or not re.fullmatch(r"sha256:[a-f0-9]{64}", content_hash):
        raise ValueError("source Behavior requires a sha256 content_hash")
    try:
        canonical = StudioStore(root).read("components", component_id)
    except FileNotFoundError as error:
        raise ValueError("Look execution requires a canonical promoted Behavior record") from error
    canonical_errors = validate_record("component", canonical)
    expected = {
        "id": component_id,
        "component_kind": "behavior",
        "state": "promoted",
        "content_hash": content_hash,
    }
    if canonical_errors or any(canonical.get(key) != value for key, value in expected.items()):
        raise ValueError("source claim does not match the canonical promoted Behavior record")
    _nonempty_strings(source.get("cache_paths"), "source cache_paths")
    selected_root = (
        root / "studies" / study_directory_name(study_id) / "01_behavior" / "03_selected"
    ).resolve()
    cache_receipt: list[dict[str, Any]] = []
    for raw_path in source["cache_paths"]:
        cache_path = _contained_path(root, raw_path, "source cache_path")
        try:
            cache_path.relative_to(selected_root)
        except ValueError as error:
            raise ValueError("source cache_paths must be canonical selected Behavior inputs") from error
        if not cache_path.is_file():
            raise ValueError(f"canonical selected Behavior cache does not exist: {raw_path}")
        cache_receipt.append({"path": raw_path, "bytes": cache_path.stat().st_size, "sha256": _sha256(cache_path)})
    return cache_receipt


def _validate_direction(value: Mapping[str, Any]) -> None:
    missing = [field for field in _REQUIRED_DIRECTION_FIELDS if field not in value]
    if missing:
        raise ValueError(f"missing Look direction fields: {', '.join(missing)}")
    if not isinstance(value["id"], str) or _DIRECTION_ID.fullmatch(value["id"]) is None:
        raise ValueError("Look direction id must match look-direction-lowercase-slug")
    for field in (
        "title", "thesis", "representation_system", "lighting_assumptions", "motion_proposition",
        "cheapest_decisive_probe",
    ):
        if not isinstance(value[field], str) or not value[field].strip():
            raise ValueError(f"{field} must be a non-empty string")
    if value["cost_tier"] not in {"tiny", "probe", "study", "specimen", "external"}:
        raise ValueError("cost_tier must be tiny, probe, study, specimen, or external")
    for field in ("primary_hierarchy", "exclusions", "risks", "stop_conditions"):
        _nonempty_strings(value[field], field)
    excluded_text = " ".join(value["exclusions"]).lower()
    if any(term in excluded_text for term in ("palette", "material", "cinematography", "framing", "lighting")):
        raise ValueError(
            "Look Development must resolve materials, framing, and lighting; they cannot be deferred"
        )
    visual_target = value["visual_target"]
    if not isinstance(visual_target, Mapping):
        raise ValueError("visual_target must be an object")
    missing_target = [field for field in _REQUIRED_VISUAL_TARGET_FIELDS if field not in visual_target]
    if missing_target:
        raise ValueError(f"missing visual_target fields: {', '.join(missing_target)}")
    for field in ("references", "required_reads", "prohibited_reads"):
        _nonempty_strings(visual_target.get(field), f"visual_target {field}")
    for field in (
        "final_image_thesis", "material_intent", "framing_intent", "lighting_intent",
        "temporal_signature",
    ):
        if not isinstance(visual_target.get(field), str) or not visual_target[field].strip():
            raise ValueError(f"visual_target {field} must be a non-empty string")
    mappings = value["state_to_form_mappings"]
    if not isinstance(mappings, list) or not mappings:
        raise ValueError("state_to_form_mappings must not be empty")
    observables: list[str] = []
    for mapping in mappings:
        if not isinstance(mapping, Mapping):
            raise ValueError("each state-to-form mapping must be an object")
        missing_mapping = [
            field for field in _REQUIRED_MAPPING_FIELDS
            if not isinstance(mapping.get(field), str) or not mapping[field].strip()
        ]
        if missing_mapping:
            raise ValueError(f"invalid state-to-form mapping fields: {', '.join(missing_mapping)}")
        observables.append(mapping["acceptance_observable"])
    if len(set(observables)) != len(observables):
        raise ValueError("acceptance observables must be unique within a Look direction")

    stages = value["implementation_stages"]
    if not isinstance(stages, list) or len(stages) < 4:
        raise ValueError("a Look direction requires at least four implementation stages")
    stage_ids: list[str] = []
    for stage in stages:
        if not isinstance(stage, Mapping):
            raise ValueError("each implementation stage must be an object")
        missing_stage = [field for field in _REQUIRED_STAGE_FIELDS if field not in stage]
        if missing_stage:
            raise ValueError(f"missing implementation stage fields: {', '.join(missing_stage)}")
        stage_id = stage.get("id")
        if not isinstance(stage_id, str) or _STAGE_ID.fullmatch(stage_id) is None:
            raise ValueError("implementation stage id must be a lowercase slug")
        stage_ids.append(stage_id)
        for field in ("title", "intent", "houdini_strategy", "output", "acceptance_observable"):
            if not isinstance(stage.get(field), str) or not stage[field].strip():
                raise ValueError(f"implementation stage {field} must be a non-empty string")
        _nonempty_strings(stage.get("data_inputs"), "implementation stage data_inputs")
    if len(set(stage_ids)) != len(stage_ids):
        raise ValueError("implementation stage ids must be unique within a Look direction")


def _workspace_layout(index: int, direction_slug: str) -> dict[str, str]:
    return {
        "design_directory": "00_design",
        "implementation_plan": "00_design/IMPLEMENTATION_PLAN.json",
        "scene_directory": "01_scene",
        "scene_stem": f"01_scene/{index:02d}_{direction_slug}",
        "probe_directory": "02_probes",
        "motion_directory": "03_motion",
        "evidence_directory": "04_evidence",
        "graph_audit": "04_evidence/graph-audit.json",
    }


def _review_contract(cache_receipt: Sequence[Mapping[str, Any]], direction_slug: str) -> dict[str, Any]:
    frames = [
        int(match.group(1))
        for record in cache_receipt
        if (match := _CACHE_FRAME.search(str(record["path"]))) is not None
    ]
    frames = sorted(set(frames))
    if len(frames) < 8:
        raise ValueError("final-image Look review requires at least eight distinct cache frames")
    neutral_frames = {
        "early": frames[0],
        "middle": frames[len(frames) // 2],
        "late": frames[-1],
    }
    motion_windows = [
        frames[index:index + 8]
        for index in range(len(frames) - 7)
        if all(
            right == left + 1
            for left, right in zip(frames[index:index + 8], frames[index + 1:index + 8])
        )
    ]
    if not motion_windows:
        raise ValueError("final-image Look review requires eight contiguous cache frames")
    midpoint = frames[len(frames) // 2]
    motion_frames = min(
        motion_windows, key=lambda window: abs(window[len(window) // 2] - midpoint)
    )
    return {
        "contract_version": 2,
        "renderer": "karma",
        "color_pipeline": "ACEScg-OCIO",
        "neutral_rig_id": "bzor-neutral-lookdev-v1",
        "resolution": [640, 360],
        "samples_per_pixel": 4,
        "path_traced_samples": 16,
        "neutral_camera_parameters": {
            "tx": 0.0, "ty": 0.0, "tz": 8.0,
            "rx": 0.0, "ry": 0.0, "rz": 0.0,
            "focalLength": 50.0,
        },
        "neutral_dome_parameters": {
            "xn__inputsintensity_i0a": 1.0,
            "xn__inputscolor_ztar": 1.0,
            "xn__inputscolor_ztag": 1.0,
            "xn__inputscolor_ztab": 1.0,
        },
        "neutral_render_parameters": {
            "enabledof": 0,
            "enablemblur": 0,
            "res_mode": "manual",
        },
        "neutral_frames": neutral_frames,
        "motion_frames": motion_frames,
        "neutral_render_paths": {
            role: f"02_probes/neutral-{role}.{frame:04d}.png"
            for role, frame in neutral_frames.items()
        },
        "hero_render_path": "02_probes/hero.png",
        "motion_preview_path": f"03_motion/{direction_slug}-motion.gif",
        "annotated_claim_sheet_path": "04_evidence/annotated-claim-sheet.png",
        "required_scene_nodes": {
            "look_import": "/stage/IMPORT_LOOK",
            "material_library": "/stage/MATERIALS_LOOK",
            "material_assignment": "/stage/ASSIGN_LOOK_MATERIALS",
            "neutral_camera": "/stage/CAM_NEUTRAL",
            "hero_camera": "/stage/CAM_HERO",
            "neutral_dome": "/stage/LIGHT_NEUTRAL_DOME",
            "hero_key": "/stage/KEY",
            "hero_fill": "/stage/FILL",
            "hero_rim": "/stage/RIM",
            "lighting_selector": "/stage/SELECT_LIGHTING_MODE",
            "render_settings": "/stage/RENDER_KARMA_SETTINGS",
            "render_output": "/stage/OUT_KARMA",
        },
    }


def _hip_files_beneath(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".hip", ".hiplc", ".hipnc"}
    }


def _allocate_round(work_dir: Path) -> tuple[str, Path]:
    work_dir.mkdir(parents=True, exist_ok=True)
    for number in range(1, 1000):
        round_id = f"look-round-{number:03d}"
        round_dir = work_dir / round_id
        try:
            round_dir.mkdir()
            return round_id, round_dir
        except FileExistsError:
            continue
    raise RuntimeError("no Look round identifiers remain")


def _worker_prompt(packet: Mapping[str, Any]) -> str:
    direction = packet["direction"]
    claims = "\n".join(
        f"- {mapping['acceptance_observable']}" for mapping in direction["state_to_form_mappings"]
    )
    claim_contract = [
        {
            "claim": mapping["acceptance_observable"],
            "mechanical_status": "demonstrated | partial | failed",
            "visual_status": "demonstrated | partial | failed",
            "technical_evidence_paths": ["04_evidence/a-listed-technical-artifact.json"],
            "render_evidence_paths": [packet["review_contract"]["annotated_claim_sheet_path"]],
        }
        for mapping in direction["state_to_form_mappings"]
    ]
    plan_stages: list[dict[str, Any]] = []
    for index, stage in enumerate(direction["implementation_stages"], start=1):
        source_path = f"/obj/LOOK/STAGE_{index:02d}_SOURCE"
        output_path = f"/obj/LOOK/STAGE_{index:02d}_OUT"
        plan_stages.append({
            **stage,
            "network_section": f"LOOK_STAGE_{index:02d}",
            "node_families": ["file", "null"],
            "nodes": [
                {
                    "path": source_path,
                    "type": "file",
                    "role": "illustrative stage source",
                    "inputs": [],
                },
                {
                    "path": output_path,
                    "type": "null",
                    "role": "illustrative stage output",
                    "inputs": [source_path],
                },
            ],
            "output_node": output_path,
            "artist_controls": [{"node_path": source_path, "parm": "file"}],
            "status": "implemented",
            "evidence_paths": [f"04_evidence/stage-{index:02d}-{stage['id']}.json"],
        })
    review_contract = packet["review_contract"]
    plan_contract = {
        "direction_id": direction["id"],
        "project_root": packet["project_root"],
        "source_behavior_content_hash": packet["source_behavior"]["content_hash"],
        "source_cache_receipt": packet["source_cache_receipt"],
        "stages": plan_stages,
        "render_setup": {
            "renderer": review_contract["renderer"],
            "color_pipeline": review_contract["color_pipeline"],
            "neutral_rig_id": review_contract["neutral_rig_id"],
            "resolution": review_contract["resolution"],
            "samples_per_pixel": review_contract["samples_per_pixel"],
            "path_traced_samples": review_contract["path_traced_samples"],
            "neutral_camera_parameters": review_contract["neutral_camera_parameters"],
            "neutral_dome_parameters": review_contract["neutral_dome_parameters"],
            "neutral_render_parameters": review_contract["neutral_render_parameters"],
            "neutral_frames": review_contract["neutral_frames"],
            "motion_frames": review_contract["motion_frames"],
            "nodes": review_contract["required_scene_nodes"],
        },
    }
    identity_contract = {
        "schema_version": 2,
        "direction_id": direction["id"],
        "context_id": packet["context_id"],
        "attempt_id": "COPY execution-packet.json attempt_id EXACTLY",
        "source_behavior_content_hash": packet["source_behavior"]["content_hash"],
        "state": "visual-review-ready",
        "claims": claim_contract,
        "review_media": {
            "renderer": review_contract["renderer"],
            "color_pipeline": review_contract["color_pipeline"],
            "neutral_rig_id": review_contract["neutral_rig_id"],
            "neutral_renders": [
                {"role": role, "frame": frame, "path": review_contract["neutral_render_paths"][role]}
                for role, frame in review_contract["neutral_frames"].items()
            ],
            "hero_render": {
                "path": review_contract["hero_render_path"],
                "camera": review_contract["required_scene_nodes"]["hero_camera"],
            },
            "motion_preview": {
                "path": review_contract["motion_preview_path"],
                "frame_start": review_contract["motion_frames"][0],
                "frame_end": review_contract["motion_frames"][-1],
            },
            "annotated_claim_sheet": {
                "path": review_contract["annotated_claim_sheet_path"],
                "claims": [mapping["acceptance_observable"] for mapping in direction["state_to_form_mappings"]],
            },
            "scene_nodes": review_contract["required_scene_nodes"],
        },
        "artifacts": [{
            "path": "attempt-relative/artifact.ext",
            "bytes": 123,
            "sha256": "exact lowercase SHA-256 without a prefix",
        }],
        "node_errors": [],
        "deviations": [],
    }
    return f"""# Look Execution Agent — {direction['title']}

You are a fresh leaf execution context for exactly one structural Look direction.

## Authority

- Read `execution-packet.json` beside this file before acting.
- Behavior is frozen and read-only. Consume the named authoritative caches; do not alter simulation mechanics.
- Implement only `{direction['id']}`. Do not search for, imitate, or discuss sibling Look directions.
- Geometry translation, materials, animation treatment, framing, lighting, rendering, and outputs are all in scope.
- Technical probes are intermediate evidence only; they never complete Look Development.

## Required sequence

1. Inspect the real cache attributes and record their ranges.
2. Before creating the scene, expand the selected implementation stages into `00_design/IMPLEMENTATION_PLAN.json` using the exact top-level `stages` contract below—not `implementation_stages`. Preserve every selected stage field and value exactly, in the selected order, then add: `network_section`; `node_families`; `nodes` (never `ordered_nodes`) as absolute `path`/exact Houdini `type` token/`role`/`inputs` records; final `output_node`; artist controls as `node_path`/`parm` records; `status: implemented`; and distinct `evidence_paths`. Each `inputs` array must list the exact direct upstream planned node paths in Houdini input-index order; use an empty array for a source node. List nodes in topological order: every input path must appear in an earlier stage or earlier in the same stage’s `nodes` list. This is a DAG contract: parallel sources and probes belong in separate branches and must not be falsely serialized. `node_families` must equal the de-duplicated `nodes[].type` tokens in first-occurrence order. Every artist control must name a node path present in that same stage’s `nodes` list. Node paths must be unique across stages, and `output_node` must equal the final item in that stage’s `nodes` list.
3. Implement the plan one stage at a time. Finish and cook each stage before starting the next; do not collapse the direction into one opaque wrangle or a token handful of nodes.
4. Translate every state-to-form mapping into a cooked Houdini mechanism and keep Behavior read-only.
5. Build the cheapest decisive live-Houdini probe as an engineering checkpoint, then continue into deliberate final-image geometry, MaterialX materials, animation treatment, framing, and lighting. Do not stop at the probe.
6. Build the exact `render_setup` recorded in the plan. Every required `/stage` node must exist in this direction's HIP, use its semantic Houdini node family, be connected into the rendered USD stream, and remain editable. A shared playground is not a substitute.
7. Render the exact neutral early/middle/late frames and paths in `review_contract`, through the locked neutral rig, with matching resolution, renderer, and color pipeline. Also render the hero still, a continuous motion preview, and an annotated claim sheet that points each acceptance observable to visible image features. SVGs, viewport captures, graph audits, clay topology, and software projections may support debugging but cannot occupy these required render slots.
8. Organize connected networks top-to-bottom, parallel systems in adjacent columns, descriptive SOURCE_/LOOK_/MAT_/OUT_ sections, and notes or network boxes for major systems. Set display/render flags on the final direction output; intermediate stage outputs must cook cleanly but are not required to hold mutually exclusive flags.
9. Save exactly one canonical scene as `01_scene/{packet['sequence_index']:02d}_{direction['id'].removeprefix('look-direction-')}.hip`, `.hiplc`, or `.hipnc`. The parent will reopen it in a separate Hython process, reconcile planned nodes, controls, and render infrastructure against the real graph, and write `04_evidence/graph-audit.json`.
10. Write `receipt.json` using the exact machine contract below. Copy identity values from `execution-packet.json`; do not nest `context_id` or `source_behavior_content_hash` under another object. Include exactly one claim per state-to-form acceptance observable, using the exact observable string as `claim`; record mechanical and visual status separately. Every technical and render evidence path must name an artifact listed in `artifacts`. For every artifact, `bytes` must be the exact JSON integer returned by the file size—not a quoted string—and `sha256` must be recomputed only after the artifact is final and will no longer be edited. Never repair a failed claim with prose.
11. Stop only after the complete rendered package is visually review-ready. Do not ask KC for review; the parent withholds comparison until every direction passes equivalent gates.

## Acceptance observables

{claims}

## Exact `IMPLEMENTATION_PLAN.json` machine contract

The node paths/types/roles below are illustrative schema values: replace them with the real implemented graph while preserving every selected stage field and all structural keys exactly.

```json
{json.dumps(plan_contract, indent=2, ensure_ascii=False)}
```

## Exact `receipt.json` machine contract

```json
{json.dumps(identity_contract, indent=2, ensure_ascii=False)}
```

The parent creates `04_evidence/graph-audit.json` and the verification seal after your process exits. Do not claim or fabricate those parent-owned outputs.

No adjective without an observable. No implementation claim without a cooked artifact.
"""


def _playground_readme(round_id: str) -> str:
    return f"""# 00 Look playground — {round_id}

This is KC's non-competing personal Look sandbox. It is built before the selected directions and
is never included as a candidate in comparative review.

- Open `00_look.hiplc`.
- The promoted simulation is read-only under `/obj/PLAYGROUND_SIM`.
- Use `/stage/lighting_mode` to switch between `Dome` and `Photographer` lighting.
- Photographer mode provides independently editable Key, Fill, and Rim lights.
- Camera, neutral floor, MaterialX starter material, Karma settings, and render output are ready.
- Save tangents or experiments as new files outside this generated directory if you want to keep them.
"""


def _prepare_playground(
    root: Path,
    round_dir: Path,
    round_id: str,
    study_id: str,
    source_behavior: Mapping[str, Any],
    source_cache_receipt: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    output_dir = round_dir / "00_look"
    output_dir.mkdir()
    packet_path = output_dir / "playground-packet.json"
    readme_path = output_dir / "README.md"
    packet = {
        "schema_version": 1,
        "round_id": round_id,
        "study_id": study_id,
        "source_behavior": dict(source_behavior),
        "source_cache_receipt": [dict(record) for record in source_cache_receipt],
        "purpose": "private-non-competing-artist-playground",
        "features": {
            "simulation_import": "read-only",
            "camera": "editable-lookdev-camera",
            "environment": "neutral-floor-and-background",
            "material": "editable-materialx-standard-surface",
            "lighting_modes": ["dome", "photographer"],
            "photographer_lights": ["key", "fill", "rim"],
            "renderer": "karma",
        },
        "workspace_layout": {
            "hip_path": "00_look.hiplc",
            "receipt_path": "playground-receipt.json",
            "audit_path": "playground-audit.json",
            "render_directory": "renders",
        },
    }
    _atomic_write_json(packet_path, packet)
    _write_text(readme_path, _playground_readme(round_id))
    return {
        "packet_path": _relative(root, packet_path),
        "packet_sha256": _sha256(packet_path),
        "readme_path": _relative(root, readme_path),
        "readme_sha256": _sha256(readme_path),
        "output_path": _relative(root, output_dir),
        "state": "prepared",
        "receipt_verified": False,
    }


def prepare_look_round(
    root: Path,
    study_id: str,
    source_behavior: Mapping[str, Any],
    directions: Sequence[Mapping[str, Any]],
) -> Path:
    """Freeze isolated execution packets for a sequential Look round."""

    root = Path(root).resolve()
    source_cache_receipt = _validate_source(root, study_id, source_behavior)
    if not directions:
        raise ValueError("a Look round requires at least one direction")
    for direction in directions:
        _validate_direction(direction)
    direction_ids = [str(direction["id"]) for direction in directions]
    if len(set(direction_ids)) != len(direction_ids):
        raise ValueError("Look direction ids must be unique within a round")

    look_dir = root / "studies" / study_directory_name(study_id) / "02_look"
    round_id, round_dir = _allocate_round(look_dir / "01_work")
    playground = _prepare_playground(
        root, round_dir, round_id, study_id, source_behavior, source_cache_receipt
    )
    brief_round_dir = look_dir / "00_brief" / round_id
    brief_round_dir.mkdir(parents=True)
    manifest_items: list[dict[str, Any]] = []
    for index, direction in enumerate(directions, start=1):
        direction_slug = direction["id"].removeprefix("look-direction-")
        direction_dir = round_dir / f"{index:02d}_{direction_slug}"
        direction_dir.mkdir()
        brief_path = brief_round_dir / f"{index:02d}_{direction_slug}.json"
        brief = {
            "schema_version": 1,
            "id": direction["id"],
            "study_id": study_id,
            "round_id": round_id,
            "sequence_index": index,
            "state": "selected",
            "visibility": "private",
            "source_behavior_component_id": source_behavior["id"],
            "source_behavior_content_hash": source_behavior["content_hash"],
            "source_cache_receipt": source_cache_receipt,
            "direction": dict(direction),
        }
        brief_errors = validate_record("look-direction-brief", brief)
        if brief_errors:
            raise ValueError("; ".join(brief_errors))
        _atomic_write_json(brief_path, brief)
        packet_path = direction_dir / "execution-packet.json"
        prompt_path = direction_dir / "WORKER_PROMPT.md"
        context_id = f"{round_id}-context-{index:02d}-{direction['id'].removeprefix('look-direction-')}"
        packet = {
            "schema_version": 2,
            "project_root": str(root.resolve()),
            "round_id": round_id,
            "sequence_index": index,
            "context_id": context_id,
            "study_id": study_id,
            "source_behavior": dict(source_behavior),
            "source_cache_receipt": source_cache_receipt,
            "brief_path": _relative(root, brief_path),
            "brief_sha256": _sha256(brief_path),
            "direction": dict(direction),
            "workspace_layout": _workspace_layout(index, direction_slug),
            "review_contract": _review_contract(source_cache_receipt, direction_slug),
            "constraints": {
                "behavior": "read-only",
                "materials": "required",
                "framing": "required",
                "lighting": "required",
                "final_image": "required",
                "sibling_context": "forbidden",
            },
            "output_contract": {
                "receipt_path": "receipt.json",
                "receipt_state": "visual-review-ready",
                "required_claim_statuses": ["demonstrated", "partial", "failed"],
                "required_artifact_metadata": ["path", "bytes", "sha256"],
                "review_delivery": "withheld-until-round-complete",
                "required_artifacts": [
                    "00_design/IMPLEMENTATION_PLAN.json",
                    f"01_scene/{index:02d}_{direction_slug}.hip|.hiplc|.hipnc",
                    "one distinct stage-evidence artifact per implementation stage",
                    "three matched neutral Karma renders",
                    "one art-directed hero render",
                    "one continuous motion preview",
                    "one annotated visual claim sheet",
                ],
            },
        }
        _atomic_write_json(packet_path, packet)
        _write_text(prompt_path, _worker_prompt(packet))
        manifest_items.append({
            "sequence_index": index,
            "direction_id": direction["id"],
            "title": direction["title"],
            "context_id": context_id,
            "brief_path": _relative(root, brief_path),
            "brief_sha256": _sha256(brief_path),
            "packet_path": _relative(root, packet_path),
            "packet_sha256": _sha256(packet_path),
            "prompt_path": _relative(root, prompt_path),
            "prompt_sha256": _sha256(prompt_path),
            "output_path": _relative(root, direction_dir),
            "state": "prepared",
            "attempt_count": 0,
            "receipt_verified": False,
        })

    descriptor = {
        "schema_version": 1,
        "id": round_id,
        "study_id": study_id,
        "source_behavior_component_id": source_behavior["id"],
        "source_behavior_content_hash": source_behavior["content_hash"],
        "source_cache_receipt": source_cache_receipt,
        "playground": _immutable_playground(playground),
        "directions": [_immutable_item(item) for item in manifest_items],
    }
    descriptor_path = round_dir / "round-descriptor.json"
    _atomic_write_json(descriptor_path, descriptor)
    descriptor_path.chmod(0o444)
    anchor_path = _round_anchor_path(root, study_id, round_id)
    _write_exclusive_json(anchor_path, {
        "schema_version": 1,
        "round_id": round_id,
        "study_id": study_id,
        "descriptor_path": _relative(root, descriptor_path),
        "descriptor_sha256": _sha256(descriptor_path),
    })
    anchor_path.chmod(0o444)
    manifest = {
        "schema_version": 1,
        "id": round_id,
        "study_id": study_id,
        "source_behavior_component_id": source_behavior["id"],
        "source_behavior_content_hash": source_behavior["content_hash"],
        "source_cache_receipt": source_cache_receipt,
        "round_descriptor_path": _relative(root, descriptor_path),
        "round_descriptor_sha256": _sha256(descriptor_path),
        "state": "prepared",
        "execution_mode": "sequential-fresh-context",
        "review_policy": "withhold-until-all-complete",
        "execution_policy": {
            "max_attempts_per_direction": 2,
            "worker_timeout_seconds": 1800,
            "max_total_tokens_per_attempt": 200000,
            "max_estimated_cost_usd_per_attempt": 10.0,
            "repair_mode": "targeted-from-parent-diagnostics",
        },
        "playground": playground,
        "directions": manifest_items,
    }
    manifest_path = round_dir / "round-manifest.json"
    _atomic_write_json(manifest_path, manifest)
    return manifest_path


def _load_manifest(root: Path, manifest_path: Path) -> tuple[Path, Path, dict[str, Any]]:
    root = Path(root).resolve()
    manifest_path = Path(manifest_path).resolve()
    try:
        manifest_path.relative_to(root)
    except ValueError as error:
        raise ValueError("round manifest must remain beneath the project root") from error
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("execution_mode") != "sequential-fresh-context":
        raise ValueError("invalid Look round manifest")
    study_id, round_id = value.get("study_id"), value.get("id")
    if not isinstance(study_id, str) or not isinstance(round_id, str) or _ROUND_ID.fullmatch(round_id) is None:
        raise ValueError("invalid Look round identity")
    expected = (
        root / "studies" / study_directory_name(study_id) / "02_look" / "01_work" /
        round_id / "round-manifest.json"
    ).resolve()
    if manifest_path != expected:
        raise ValueError("round manifest is not at its canonical Study path")
    descriptor_path = manifest_path.with_name("round-descriptor.json")
    anchor_path = _round_anchor_path(root, study_id, round_id)
    try:
        anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as error:
        raise ValueError("canonical round anchor is missing or invalid") from error
    expected_anchor = {
        "schema_version": 1,
        "round_id": round_id,
        "study_id": study_id,
        "descriptor_path": _relative(root, descriptor_path),
        "descriptor_sha256": _sha256(descriptor_path) if descriptor_path.is_file() else None,
    }
    if anchor != expected_anchor:
        raise ValueError("round descriptor does not match its canonical round anchor")
    if (
        value.get("round_descriptor_path") != _relative(root, descriptor_path)
        or not descriptor_path.is_file()
        or value.get("round_descriptor_sha256") != _sha256(descriptor_path)
    ):
        raise ValueError("round manifest does not match its immutable round descriptor")
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    manifest_directions = value.get("directions")
    if not isinstance(manifest_directions, list):
        raise ValueError("round manifest diverges from its immutable round descriptor")
    immutable_round = {
        "schema_version": value.get("schema_version"),
        "id": value.get("id"),
        "study_id": value.get("study_id"),
        "source_behavior_component_id": value.get("source_behavior_component_id"),
        "source_behavior_content_hash": value.get("source_behavior_content_hash"),
        "source_cache_receipt": value.get("source_cache_receipt"),
        "playground": (
            _immutable_playground(value["playground"])
            if isinstance(value.get("playground"), Mapping) else None
        ),
        "directions": [
            _immutable_item(item) if isinstance(item, Mapping) else None
            for item in manifest_directions
        ],
    }
    if descriptor != immutable_round:
        raise ValueError("round manifest diverges from its immutable round descriptor")
    return root, manifest_path, value


def _verify_source_cache_receipt(root: Path, manifest: Mapping[str, Any]) -> None:
    component_id = manifest.get("source_behavior_component_id")
    content_hash = manifest.get("source_behavior_content_hash")
    if not isinstance(component_id, str) or not isinstance(content_hash, str):
        raise ValueError("Look round has no canonical Behavior identity")
    try:
        canonical = StudioStore(root).read("components", component_id)
    except FileNotFoundError as error:
        raise ValueError("canonical promoted Behavior changed after Look preparation") from error
    expected = {
        "id": component_id,
        "component_kind": "behavior",
        "state": "promoted",
        "content_hash": content_hash,
    }
    if validate_record("component", canonical) or any(
        canonical.get(key) != value for key, value in expected.items()
    ):
        raise ValueError("canonical promoted Behavior changed after Look preparation")
    records = manifest.get("source_cache_receipt")
    if not isinstance(records, list) or not records:
        raise ValueError("Look round has no frozen Behavior cache receipt")
    study_id = manifest.get("study_id")
    if not isinstance(study_id, str):
        raise ValueError("Look round has no canonical Study identity")
    selected_root = (
        root / "studies" / study_directory_name(study_id) / "01_behavior" / "03_selected"
    ).resolve()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("invalid frozen Behavior cache receipt")
        path = _contained_path(root, record.get("path"), "source cache_path")
        try:
            path.relative_to(selected_root)
        except ValueError as error:
            raise ValueError("frozen source cache is not a canonical selected Behavior input") from error
        if not path.is_file() or path.stat().st_size != record.get("bytes") or _sha256(path) != record.get("sha256"):
            raise ValueError(f"Behavior cache changed after Look preparation: {record.get('path')}")


def _canonical_item_paths(root: Path, manifest_path: Path, item: Mapping[str, Any]) -> tuple[Path, Path, Path]:
    index = item.get("sequence_index")
    direction_id = item.get("direction_id")
    if not isinstance(index, int) or index < 1 or not isinstance(direction_id, str) or _DIRECTION_ID.fullmatch(direction_id) is None:
        raise ValueError("invalid Look direction manifest item")
    direction_dir = manifest_path.parent / f"{index:02d}_{direction_id.removeprefix('look-direction-')}"
    look_dir = manifest_path.parents[2]
    brief_path = look_dir / "00_brief" / manifest_path.parent.name / f"{index:02d}_{direction_id.removeprefix('look-direction-')}.json"
    packet_path = direction_dir / "execution-packet.json"
    prompt_path = direction_dir / "WORKER_PROMPT.md"
    expected = {
        "output_path": _relative(root, direction_dir),
        "brief_path": _relative(root, brief_path),
        "packet_path": _relative(root, packet_path),
        "prompt_path": _relative(root, prompt_path),
    }
    if any(item.get(key) != value for key, value in expected.items()):
        raise ValueError("Look manifest paths do not match the canonical direction workspace")
    if not brief_path.is_file() or _sha256(brief_path) != item.get("brief_sha256"):
        raise ValueError("selected Look Direction Brief changed after preparation")
    if not packet_path.is_file() or _sha256(packet_path) != item.get("packet_sha256"):
        raise ValueError("frozen Look execution packet changed after preparation")
    if not prompt_path.is_file() or _sha256(prompt_path) != item.get("prompt_sha256"):
        raise ValueError("frozen Look worker prompt changed after preparation")
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    if packet.get("brief_path") != item.get("brief_path") or packet.get("brief_sha256") != item.get("brief_sha256"):
        raise ValueError("frozen Look packet is not bound to its selected brief")
    if brief.get("direction") != packet.get("direction") or brief.get("state") != "selected":
        raise ValueError("selected Look Direction Brief does not match its execution packet")
    if (
        packet.get("source_cache_receipt") != brief.get("source_cache_receipt")
        or packet.get("source_behavior", {}).get("id") != brief.get("source_behavior_component_id")
        or packet.get("source_behavior", {}).get("content_hash") != brief.get("source_behavior_content_hash")
    ):
        raise ValueError("frozen Look packet and brief have inconsistent source provenance")
    expected_identity = {
        "round_id": manifest_path.parent.name,
        "sequence_index": index,
        "context_id": item.get("context_id"),
        "study_id": manifest_path.parents[3].name.replace("study_", "study-").replace("_", "-", 1),
    }
    if any(packet.get(key) != value for key, value in expected_identity.items()):
        raise ValueError("frozen Look execution packet identity does not match its manifest")
    direction = packet.get("direction")
    if not isinstance(direction, dict) or direction.get("id") != direction_id or direction.get("title") != item.get("title"):
        raise ValueError("frozen Look direction does not match its manifest")
    return direction_dir, packet_path, prompt_path


def _canonical_playground_paths(
    root: Path,
    manifest_path: Path,
    item: Mapping[str, Any],
) -> tuple[Path, Path, Path]:
    output_dir = manifest_path.parent / "00_look"
    packet_path = output_dir / "playground-packet.json"
    readme_path = output_dir / "README.md"
    expected = {
        "output_path": _relative(root, output_dir),
        "packet_path": _relative(root, packet_path),
        "readme_path": _relative(root, readme_path),
    }
    if any(item.get(key) != value for key, value in expected.items()):
        raise ValueError("Look playground paths do not match the canonical 00_look workspace")
    _require_regular_contained_file(root, packet_path, "frozen Look playground packet")
    if item.get("packet_sha256") != _sha256(packet_path):
        raise ValueError("frozen Look playground packet changed after preparation")
    _require_regular_contained_file(root, readme_path, "frozen Look playground README")
    if item.get("readme_sha256") != _sha256(readme_path):
        raise ValueError("frozen Look playground README changed after preparation")
    return output_dir, packet_path, readme_path


def _verify_playground(
    root: Path,
    manifest: Mapping[str, Any],
    item: Mapping[str, Any],
    output_dir: Path,
    packet_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    layout = packet.get("workspace_layout")
    if not isinstance(layout, dict):
        raise ValueError("Look playground packet has no workspace layout")
    hip_path = output_dir / str(layout.get("hip_path"))
    receipt_path = output_dir / str(layout.get("receipt_path"))
    audit_path = output_dir / str(layout.get("audit_path"))
    for path, label in (
        (hip_path, "00_look canonical HIP"),
        (receipt_path, "00_look receipt"),
        (audit_path, "00_look audit"),
    ):
        _require_regular_contained_file(root, path, label)
    if _hip_files_beneath(output_dir) != {str(layout.get("hip_path"))}:
        raise ValueError("00_look must contain exactly one canonical playground HIP")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("00_look playground receipt or audit is missing or invalid") from error
    expected_receipt = {
        "round_id": manifest["id"],
        "source_behavior_content_hash": manifest["source_behavior_content_hash"],
        "state": "internally-verified",
        "hip_path": layout["hip_path"],
        "hip_bytes": hip_path.stat().st_size if hip_path.is_file() else None,
        "hip_sha256": _sha256(hip_path) if hip_path.is_file() else None,
        "audit_path": layout["audit_path"],
        "audit_sha256": _sha256(audit_path) if audit_path.is_file() else None,
        "lighting_modes": ["dome", "photographer"],
    }
    if not isinstance(receipt, dict) or any(receipt.get(key) != value for key, value in expected_receipt.items()):
        raise ValueError("00_look playground receipt identity or artifact metadata mismatch")
    try:
        audited_hip = Path(str(audit.get("hip_path"))).resolve()
        audited_cache = Path(str(audit.get("source_cache_path"))).resolve()
    except (OSError, TypeError, ValueError) as error:
        raise ValueError("00_look playground audit has an invalid HIP or cache path") from error
    cache_receipt = manifest["source_cache_receipt"]
    canonical_cache = (root / cache_receipt[0]["path"]).resolve()
    cache_frames = [
        int(match.group(1))
        for record in cache_receipt
        if (match := _CACHE_FRAME.search(record["path"])) is not None
    ]
    expected_frame_range = [min(cache_frames), max(cache_frames)] if cache_frames else [1, 1]
    expected_cache_sequence = [
        {
            "path": str((root / record["path"]).resolve()),
            "frame": int(match.group(1)) if (match := _CACHE_FRAME.search(record["path"])) else None,
            "bytes": record["bytes"],
            "sha256": record["sha256"],
            "errors": [],
        }
        for record in cache_receipt
    ]
    camera_framing = audit.get("camera_framing")
    render_configuration = audit.get("render_configuration")
    if (
        audit.get("verification_engine") != "fresh-hython-reopen"
        or audit.get("passed") is not True
        or audited_hip != hip_path.resolve()
        or audit.get("hip_sha256") != _sha256(hip_path)
        or audited_cache != canonical_cache
        or audit.get("source_cache_sha256") != cache_receipt[0]["sha256"]
        or audit.get("source_cache_bytes") != cache_receipt[0]["bytes"]
        or audit.get("cache_sequence") != expected_cache_sequence
        or audit.get("frame_range") != expected_frame_range
        or not isinstance(camera_framing, Mapping)
        or camera_framing.get("auto_framed") is not True
        or not isinstance(render_configuration, Mapping)
        or render_configuration.get("camera") != "/World/Cameras/Playground"
        or not str(render_configuration.get("picture", "")).endswith("playground.$F4.exr")
        or render_configuration.get("resolution_x") != 768
        or render_configuration.get("point_style") != "Spheres"
        or render_configuration.get("renderer") != "BRAY_HdKarma"
        or audit.get("source_file") != "/obj/PLAYGROUND_SIM/SOURCE_PROMOTED_SIMULATION"
        or audit.get("source_node") != "/obj/PLAYGROUND_SIM/OUT_SIMULATION"
        or audit.get("visibility_node") != "/obj/PLAYGROUND_SIM/ENSURE_POINT_VISIBILITY"
        or audit.get("floor_node") != "/obj/PLAYGROUND_ENVIRONMENT/NEUTRAL_FLOOR"
        or audit.get("floor_placement") != "/obj/PLAYGROUND_ENVIRONMENT/PLACE_FLOOR"
        or audit.get("environment_node") != "/obj/PLAYGROUND_ENVIRONMENT/OUT_ENVIRONMENT"
        or audit.get("simulation_import") != "/stage/IMPORT_SIMULATION"
        or audit.get("environment_import") != "/stage/IMPORT_ENVIRONMENT"
        or audit.get("scene_merge") != "/stage/MERGE_SCENE"
        or audit.get("material_library") != "/stage/MATERIALS_STARTER"
        or audit.get("material_assignment") != "/stage/ASSIGN_STARTER_MATERIALS"
        or audit.get("camera_node") != "/stage/CAM_PLAYGROUND"
        or audit.get("dome_light") != "/stage/LIGHT_DOME"
        or audit.get("key_light") != "/stage/KEY"
        or audit.get("fill_light") != "/stage/FILL"
        or audit.get("rim_light") != "/stage/RIM"
        or audit.get("lighting_selector") != "/stage/SELECT_LIGHTING_MODE"
        or audit.get("lighting_modes") != ["dome", "photographer"]
        or audit.get("photographer_lights") != ["KEY", "FILL", "RIM"]
        or audit.get("karma_settings") != "/stage/RENDER_KARMA_SETTINGS"
        or audit.get("render_output") != "/stage/OUT_KARMA"
        or audit.get("node_errors") != []
    ):
        raise ValueError("00_look playground fresh-Hython audit did not prove the required setup")
    if (
        packet.get("round_id") != manifest["id"]
        or packet.get("source_behavior", {}).get("content_hash") != manifest["source_behavior_content_hash"]
        or packet.get("source_cache_receipt") != manifest["source_cache_receipt"]
    ):
        raise ValueError("00_look playground packet has inconsistent source provenance")
    return receipt, audit


def _accept_playground(
    root: Path,
    manifest: Mapping[str, Any],
    item: dict[str, Any],
    output_dir: Path,
    packet_path: Path,
) -> None:
    _verify_playground(root, manifest, item, output_dir, packet_path)
    layout = json.loads(packet_path.read_text(encoding="utf-8"))["workspace_layout"]
    seal_path = output_dir / "playground-seal.json"
    seal = {
        "schema_version": 1,
        "round_id": manifest["id"],
        "packet_sha256": _sha256(packet_path),
        "hip_sha256": _sha256(output_dir / layout["hip_path"]),
        "receipt_sha256": _sha256(output_dir / layout["receipt_path"]),
        "audit_sha256": _sha256(output_dir / layout["audit_path"]),
    }
    if seal_path.is_file():
        if json.loads(seal_path.read_text(encoding="utf-8")) != seal:
            raise ValueError("00_look playground does not match its parent seal")
    else:
        _write_exclusive_json(seal_path, seal)
        seal_path.chmod(0o444)
    item.update({
        "state": "internally-verified",
        "receipt_verified": True,
        "hip_path": _relative(root, output_dir / layout["hip_path"]),
        "receipt_path": _relative(root, output_dir / layout["receipt_path"]),
        "audit_path": _relative(root, output_dir / layout["audit_path"]),
        "seal_path": _relative(root, seal_path),
        "seal_sha256": _sha256(seal_path),
    })


def _reverify_playground(
    root: Path,
    manifest_path: Path,
    manifest: Mapping[str, Any],
) -> str:
    item = manifest.get("playground")
    if not isinstance(item, Mapping):
        raise ValueError("Look round contains no canonical 00_look playground")
    output_dir, packet_path, _ = _canonical_playground_paths(root, manifest_path, item)
    _verify_playground(root, manifest, item, output_dir, packet_path)
    layout = json.loads(packet_path.read_text(encoding="utf-8"))["workspace_layout"]
    seal_path = output_dir / "playground-seal.json"
    expected_seal = {
        "schema_version": 1,
        "round_id": manifest["id"],
        "packet_sha256": _sha256(packet_path),
        "hip_sha256": _sha256(output_dir / layout["hip_path"]),
        "receipt_sha256": _sha256(output_dir / layout["receipt_path"]),
        "audit_sha256": _sha256(output_dir / layout["audit_path"]),
    }
    expected_item = {
        "state": "internally-verified",
        "receipt_verified": True,
        "hip_path": _relative(root, output_dir / layout["hip_path"]),
        "receipt_path": _relative(root, output_dir / layout["receipt_path"]),
        "audit_path": _relative(root, output_dir / layout["audit_path"]),
        "seal_path": _relative(root, seal_path),
        "seal_sha256": _sha256(seal_path) if seal_path.is_file() else None,
    }
    if any(item.get(key) != value for key, value in expected_item.items()):
        raise ValueError("00_look playground manifest does not match its verified artifacts")
    if not seal_path.is_file() or json.loads(seal_path.read_text(encoding="utf-8")) != expected_seal:
        raise ValueError("00_look playground does not match its parent seal")
    return expected_item["hip_path"]


def _attempt_number(direction_dir: Path, recorded: object) -> int:
    numbers = []
    for path in direction_dir.glob("attempt-*"):
        if path.is_dir() and re.fullmatch(r"attempt-[0-9]{3}", path.name):
            numbers.append(int(path.name.rsplit("-", 1)[1]))
    return max([int(recorded) if isinstance(recorded, int) else 0, *numbers], default=0) + 1


def _inspect_render_image(path: Path, label: str) -> tuple[int, int]:
    try:
        with Image.open(path) as image:
            if path.suffix.lower() == ".png" and image.format != "PNG":
                raise ValueError(f"{label} must contain actual PNG data")
            image.load()
            width, height = image.size
            rgb = image.convert("RGB")
            extrema = rgb.getextrema()
            sample = rgb.copy()
            sample.thumbnail((160, 90))
            colors = sample.getcolors(maxcolors=160 * 90)
    except (OSError, ValueError) as error:
        raise ValueError(f"{label} is not a decodable render image") from error
    if width < 320 or height < 180:
        raise ValueError(f"{label} is below the 320x180 review minimum")
    if not any(high - low >= 4 for low, high in extrema):
        raise ValueError(f"{label} is blank or near-blank")
    if colors and max(count for count, _ in colors) / sum(count for count, _ in colors) > 0.995:
        raise ValueError(f"{label} is blank or near-blank")
    return width, height


def _validate_review_media(
    output_dir: Path,
    packet: Mapping[str, Any],
    review_media: Mapping[str, Any],
    artifact_paths: set[str],
) -> None:
    contract = packet["review_contract"]
    for field in ("renderer", "color_pipeline", "neutral_rig_id"):
        if review_media.get(field) != contract[field]:
            raise ValueError(f"review_media {field} does not match the locked review contract")
    if review_media.get("scene_nodes") != contract["required_scene_nodes"]:
        raise ValueError("review_media scene_nodes do not match the direction-local render contract")

    neutral = review_media.get("neutral_renders")
    expected_roles = ("early", "middle", "late")
    if not isinstance(neutral, list) or len(neutral) != 3:
        raise ValueError("review_media requires exactly three neutral_renders")
    neutral_sizes: list[tuple[int, int]] = []
    neutral_hashes: set[str] = set()
    for record, role in zip(neutral, expected_roles, strict=True):
        expected = {
            "role": role,
            "frame": contract["neutral_frames"][role],
            "path": contract["neutral_render_paths"][role],
        }
        if record != expected:
            raise ValueError(f"review_media neutral render does not match locked {role} delivery")
        relative = expected["path"]
        if relative not in artifact_paths:
            raise ValueError("review_media neutral render is not a verified artifact")
        path = output_dir / relative
        neutral_sizes.append(_inspect_render_image(path, f"neutral {role} render"))
        neutral_hashes.add(_sha256(path))
    if len(set(neutral_sizes)) != 1:
        raise ValueError("neutral renders must use matching resolution")
    if len(neutral_hashes) != 3:
        raise ValueError("neutral early, middle, and late renders must be distinct images")

    hero = review_media.get("hero_render")
    expected_hero = {
        "path": contract["hero_render_path"],
        "camera": contract["required_scene_nodes"]["hero_camera"],
    }
    if hero != expected_hero or expected_hero["path"] not in artifact_paths:
        raise ValueError("review_media requires the contracted hero render and hero camera")
    _inspect_render_image(output_dir / expected_hero["path"], "hero render")

    motion = review_media.get("motion_preview")
    expected_motion = {
        "path": contract["motion_preview_path"],
        "frame_start": contract["motion_frames"][0],
        "frame_end": contract["motion_frames"][-1],
    }
    if motion != expected_motion or expected_motion["path"] not in artifact_paths:
        raise ValueError("review_media requires the contracted continuous motion preview")
    motion_path = output_dir / expected_motion["path"]
    try:
        with Image.open(motion_path) as image:
            frame_count = getattr(image, "n_frames", 1)
            if frame_count < 8:
                raise ValueError("review_media motion preview must contain at least eight rendered frames")
            width, height = image.size
            motion_hashes: set[str] = set()
            for frame_index in range(frame_count):
                image.seek(frame_index)
                frame = image.convert("RGB")
                if frame.size != (width, height):
                    raise ValueError("review_media motion preview contains mismatched frame dimensions")
                extrema = frame.getextrema()
                if not any(high - low >= 4 for low, high in extrema):
                    raise ValueError("review_media motion preview contains a blank review frame")
                motion_hashes.add(hashlib.sha256(frame.tobytes()).hexdigest())
            if len(motion_hashes) < 2:
                raise ValueError("review_media motion preview does not show temporal change")
    except OSError as error:
        raise ValueError("review_media motion preview is not decodable") from error
    if width < 320 or height < 180:
        raise ValueError("review_media motion preview is below the 320x180 review minimum")

    sheet = review_media.get("annotated_claim_sheet")
    expected_sheet = {
        "path": contract["annotated_claim_sheet_path"],
        "claims": [
            mapping["acceptance_observable"]
            for mapping in packet["direction"]["state_to_form_mappings"]
        ],
    }
    if sheet != expected_sheet or expected_sheet["path"] not in artifact_paths:
        raise ValueError("review_media requires an annotated sheet covering every visual claim")
    _inspect_render_image(output_dir / expected_sheet["path"], "annotated claim sheet")


def _materialize_attempt(
    root: Path,
    manifest: Mapping[str, Any],
    item: dict[str, Any],
    direction_dir: Path,
    packet_path: Path,
    prompt_path: Path,
) -> tuple[Path, Path, str]:
    number = _attempt_number(direction_dir, item.get("attempt_count"))
    attempt_id = f"{item['context_id']}-attempt-{number:03d}"
    attempt_dir = direction_dir / f"attempt-{number:03d}"
    attempt_dir.mkdir()
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    attempt_packet = {**packet, "attempt_id": attempt_id}
    repair_source_relative = item.get("repair_source_path")
    if repair_source_relative is not None:
        repair_source = _contained_path(root, repair_source_relative, "repair_source_path")
        expected_source = direction_dir / f"attempt-{number - 1:03d}"
        diagnostic_relative = item.get("failure_diagnostic_path")
        expected_diagnostic = expected_source / "00_design" / "PARENT_FAILURE_DIAGNOSTIC.json"
        if (
            number < 2
            or repair_source.resolve() != expected_source.resolve()
            or repair_source.name != f"attempt-{number - 1:03d}"
            or not repair_source.is_dir()
        ):
            raise ValueError("targeted repair source must be the immediately preceding canonical attempt")
        if (
            not isinstance(diagnostic_relative, str)
            or _contained_path(root, diagnostic_relative, "failure_diagnostic_path").resolve()
            != expected_diagnostic.resolve()
            or not expected_diagnostic.is_file()
            or _sha256(expected_diagnostic) != item.get("failure_diagnostic_sha256")
        ):
            raise ValueError("targeted repair diagnostic identity or hash mismatch")
        shutil.copytree(repair_source, attempt_dir, dirs_exist_ok=True)
        attempt_packet["repair_context"] = {
            "mode": "targeted-from-parent-diagnostics",
            "source_attempt_path": repair_source_relative,
            "diagnostic_path": diagnostic_relative,
        }
    attempt_packet_path = attempt_dir / "execution-packet.json"
    _atomic_write_json(attempt_packet_path, attempt_packet)
    _write_text(attempt_dir / "WORKER_PROMPT.md", prompt_path.read_text(encoding="utf-8"))
    layout = packet["workspace_layout"]
    for key in (
        "design_directory", "scene_directory", "probe_directory", "motion_directory", "evidence_directory",
    ):
        (attempt_dir / layout[key]).mkdir(exist_ok=True)
    for stale in (
        attempt_dir / "receipt.json",
        attempt_dir / "verification-seal.json",
        attempt_dir / layout["graph_audit"],
    ):
        if stale.exists() and not stale.is_symlink():
            stale.chmod(0o666)
        stale.unlink(missing_ok=True)
    parent_renders = attempt_dir / layout["evidence_directory"] / "parent-renders"
    if parent_renders.is_dir():
        shutil.rmtree(parent_renders)
    item.update({
        "attempt_count": number,
        "current_attempt_id": attempt_id,
        "current_attempt_path": _relative(root, attempt_dir),
        "attempt_packet_path": _relative(root, attempt_packet_path),
        "attempt_packet_sha256": _sha256(attempt_packet_path),
        "state": "running",
        "receipt_verified": False,
    })
    item.pop("receipt_path", None)
    item.pop("claim_summary", None)
    item.pop("verification_seal_path", None)
    item.pop("verification_seal_sha256", None)
    item.pop("graph_audit_path", None)
    item.pop("graph_audit_sha256", None)
    return attempt_packet_path, attempt_dir, attempt_id


def _seal_parent_scaffold(
    root: Path, direction_dir: Path, attempt_dir: Path, item: dict[str, Any]
) -> None:
    receipt_path = attempt_dir / "00_design" / "PARENT_SCAFFOLD.json"
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise RuntimeError("parent direction scaffold produced no regular provenance receipt")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    protected = receipt.get("protected_nodes") if isinstance(receipt, dict) else None
    if (
        not isinstance(protected, dict)
        or not protected
        or any(
            not isinstance(record, dict)
            or not all(isinstance(record.get(key), str) and record[key] for key in ("path", "type", "scaffold_id"))
            for record in protected.values()
        )
    ):
        raise RuntimeError("parent direction scaffold provenance receipt is incomplete")
    seal_dir = direction_dir / "parent-scaffold-seals"
    seal_dir.mkdir(exist_ok=True)
    seal_path = seal_dir / f"attempt-{int(item['attempt_count']):03d}.json"
    seal = {
        "schema_version": 1,
        "attempt_id": item["current_attempt_id"],
        "receipt_path": _relative(root, receipt_path),
        "receipt_sha256": _sha256(receipt_path),
        "protected_nodes": protected,
    }
    _write_exclusive_json(seal_path, seal)
    seal_path.chmod(0o444)
    item["scaffold_seal_path"] = _relative(root, seal_path)
    item["scaffold_seal_sha256"] = _sha256(seal_path)


def _validate_parent_scaffold_seal(
    root: Path, item: Mapping[str, Any], audit: Mapping[str, Any]
) -> None:
    seal_path = _contained_path(root, item.get("scaffold_seal_path"), "scaffold_seal_path")
    if (
        seal_path.is_symlink()
        or not seal_path.is_file()
        or _sha256(seal_path) != item.get("scaffold_seal_sha256")
    ):
        raise ValueError("parent scaffold provenance seal is missing or changed")
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    receipt_path = _contained_path(root, seal.get("receipt_path"), "scaffold receipt path")
    if (
        seal.get("attempt_id") != item.get("current_attempt_id")
        or receipt_path.is_symlink()
        or not receipt_path.is_file()
        or _sha256(receipt_path) != seal.get("receipt_sha256")
    ):
        raise ValueError("worker changed the sealed parent scaffold receipt")
    expected = {
        record["path"]: {"type": record["type"], "scaffold_id": record["scaffold_id"]}
        for record in seal["protected_nodes"].values()
    }
    if audit.get("scaffold_identities") != expected:
        raise ValueError("worker replaced or removed parent-owned scaffold nodes")


def _verified_receipt(
    root: Path,
    manifest: Mapping[str, Any],
    item: Mapping[str, Any],
    base_packet_path: Path,
    packet_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    direction_dir = _contained_path(root, item.get("output_path"), "output_path")
    attempt_number = int(item.get("attempt_count", 0))
    latest_attempt_number = _attempt_number(direction_dir, 0) - 1
    if attempt_number != latest_attempt_number:
        raise ValueError("receipt does not belong to the latest canonical attempt")
    expected_attempt_dir = direction_dir / f"attempt-{attempt_number:03d}"
    expected_packet_path = expected_attempt_dir / "execution-packet.json"
    expected_receipt_path = expected_attempt_dir / "receipt.json"
    if (
        output_dir.resolve() != expected_attempt_dir.resolve()
        or packet_path.resolve() != expected_packet_path.resolve()
        or item.get("current_attempt_path") != _relative(root, expected_attempt_dir)
        or item.get("attempt_packet_path") != _relative(root, expected_packet_path)
        or (
            item.get("receipt_path") is not None
            and item.get("receipt_path") != _relative(root, expected_receipt_path)
        )
    ):
        raise ValueError("attempt paths do not match the exact canonical attempt workspace")
    expected_attempt_id = f"{item['context_id']}-attempt-{attempt_number:03d}"
    if item.get("current_attempt_id") != expected_attempt_id:
        raise ValueError("attempt identity does not match the exact canonical attempt workspace")
    if not packet_path.is_file() or _sha256(packet_path) != item.get("attempt_packet_sha256"):
        raise ValueError("frozen attempt packet changed during Look execution")
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    base_packet = json.loads(base_packet_path.read_text(encoding="utf-8"))
    expected_packet = copy.deepcopy(base_packet)
    expected_packet["attempt_id"] = expected_attempt_id
    if item.get("repair_source_path") is not None:
        expected_packet["repair_context"] = {
            "mode": "targeted-from-parent-diagnostics",
            "source_attempt_path": item["repair_source_path"],
            "diagnostic_path": item["failure_diagnostic_path"],
        }
    if packet != expected_packet:
        raise ValueError("attempt packet does not match the frozen base packet")
    receipt_path = expected_receipt_path
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise ValueError("receipt must be a regular non-symlink file")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema_version") != 2:
        raise ValueError("receipt must use the final-image Look schema_version 2 contract")
    expected_identity = {
        "direction_id": item["direction_id"],
        "context_id": item["context_id"],
        "attempt_id": item["current_attempt_id"],
        "source_behavior_content_hash": manifest["source_behavior_content_hash"],
        "state": "visual-review-ready",
    }
    mismatches = [key for key, value in expected_identity.items() if receipt.get(key) != value]
    if mismatches:
        raise ValueError(f"receipt identity mismatch: {', '.join(mismatches)}")
    claims = receipt.get("claims")
    if not isinstance(claims, list) or not claims:
        raise ValueError("receipt requires at least one claim")
    expected_claims = {
        mapping["acceptance_observable"] for mapping in packet["direction"]["state_to_form_mappings"]
    }
    actual_claims: set[str] = set()
    for claim in claims:
        if not isinstance(claim, dict) or claim.get("mechanical_status") not in {
            "demonstrated", "partial", "failed"
        }:
            raise ValueError("each receipt claim requires a valid mechanical_status")
        if claim.get("visual_status") not in {"demonstrated", "partial", "failed"}:
            raise ValueError("each receipt claim requires a valid visual_status")
        if not isinstance(claim.get("claim"), str) or not claim["claim"]:
            raise ValueError("each receipt claim requires its acceptance observable")
        _nonempty_strings(claim.get("technical_evidence_paths"), "claim technical_evidence_paths")
        _nonempty_strings(claim.get("render_evidence_paths"), "claim render_evidence_paths")
        actual_claims.add(claim["claim"])
    if actual_claims != expected_claims or len(claims) != len(expected_claims):
        raise ValueError("claim coverage mismatch for Look direction acceptance observables")
    if any(claim["mechanical_status"] != "demonstrated" for claim in claims):
        raise ValueError("mechanically_verified requires every mechanical claim to be demonstrated")
    if any(claim["visual_status"] != "demonstrated" for claim in claims):
        raise ValueError("visually_demonstrated requires every visual claim to be demonstrated")

    review_media = receipt.get("review_media")
    if not isinstance(review_media, Mapping):
        raise ValueError("receipt requires a rendered review_media package")

    artifacts = receipt.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("receipt requires at least one artifact")
    verified_artifact_paths: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ValueError("receipt artifacts must be objects")
        relative_artifact = artifact.get("path")
        relative_path = Path(relative_artifact) if isinstance(relative_artifact, str) else None
        if (
            relative_path is None
            or not relative_artifact
            or relative_path.is_absolute()
            or any(part in {".", ".."} for part in relative_path.parts)
        ):
            raise ValueError("receipt artifact path must be relative")
        if relative_artifact in _PARENT_OWNED_WORKER_ARTIFACTS:
            raise ValueError(f"parent-owned accounting file cannot be receipt evidence: {relative_artifact}")
        raw_artifact_path = output_dir / relative_path
        artifact_path = raw_artifact_path.resolve()
        try:
            artifact_path.relative_to(output_dir.resolve())
        except ValueError as error:
            raise ValueError("receipt artifact escapes its attempt workspace") from error
        current = output_dir
        for part in relative_path.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError("receipt artifacts must be regular non-symlink files")
        if not artifact_path.is_file():
            raise ValueError(f"receipt artifact does not exist: {relative_artifact}")
        digest = _sha256(artifact_path)
        if artifact.get("bytes") != artifact_path.stat().st_size or artifact.get("sha256") != digest:
            raise ValueError(f"receipt artifact metadata mismatch: {relative_artifact}")
        verified_artifact_paths.add(relative_artifact)
    _validate_review_media(output_dir, packet, review_media, verified_artifact_paths)
    allowed_render_evidence = {
        *packet["review_contract"]["neutral_render_paths"].values(),
        packet["review_contract"]["hero_render_path"],
        packet["review_contract"]["motion_preview_path"],
        packet["review_contract"]["annotated_claim_sheet_path"],
    }
    for claim in claims:
        claim_evidence = [
            *claim["technical_evidence_paths"],
            *claim["render_evidence_paths"],
        ]
        if any(path not in verified_artifact_paths for path in claim_evidence):
            raise ValueError("claim evidence is not a verified artifact")
        if any(path not in allowed_render_evidence for path in claim["render_evidence_paths"]):
            raise ValueError("visual claims require rendered image-space evidence")
        if any(path in allowed_render_evidence for path in claim["technical_evidence_paths"]):
            raise ValueError("mechanical claims require technical evidence distinct from rendered evidence")
    if receipt.get("node_errors") != [] or receipt.get("deviations") != []:
        raise ValueError("receipt node_errors and deviations must both be empty for decision readiness")

    layout = packet.get("workspace_layout")
    if not isinstance(layout, dict):
        raise ValueError("Look packet requires a canonical workspace layout")
    plan_relative = layout.get("implementation_plan")
    scene_stem = layout.get("scene_stem")
    if not all(isinstance(value, str) and value for value in (plan_relative, scene_stem)):
        raise ValueError("Look packet has an invalid canonical workspace layout")
    scene_candidates = {f"{scene_stem}{suffix}" for suffix in (".hip", ".hiplc", ".hipnc")}
    scene_artifacts = scene_candidates & verified_artifact_paths
    scene_files = {
        relative for relative in scene_candidates
        if (output_dir / relative).is_file()
    }
    all_hip_files = _hip_files_beneath(output_dir)
    if plan_relative not in verified_artifact_paths:
        raise ValueError("receipt requires the canonical implementation plan artifact")
    if len(scene_artifacts) != 1 or scene_files != scene_artifacts or all_hip_files != scene_artifacts:
        raise ValueError("receipt requires exactly one consistently named canonical HIP artifact")

    plan = json.loads((output_dir / plan_relative).read_text(encoding="utf-8"))
    expected_stages = packet["direction"]["implementation_stages"]
    planned_stages = plan.get("stages") if isinstance(plan, dict) else None
    if not isinstance(plan, dict) or plan.get("direction_id") != item["direction_id"] or not isinstance(planned_stages, list):
        raise ValueError("implementation plan identity or stages are invalid")
    expected_render_setup = {
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
    }
    if (
        plan.get("source_behavior_content_hash") != packet["source_behavior"]["content_hash"]
        or plan.get("project_root") != packet["project_root"]
        or plan.get("source_cache_receipt") != packet["source_cache_receipt"]
        or plan.get("render_setup") != expected_render_setup
    ):
        raise ValueError("implementation plan must freeze the exact source cache and direction-local render_setup")
    if [stage.get("id") for stage in planned_stages if isinstance(stage, dict)] != [
        stage["id"] for stage in expected_stages
    ]:
        raise ValueError("implementation plan does not cover the selected stages in order")
    stage_evidence: list[str] = []
    planned_node_paths: set[str] = set()
    for planned, selected in zip(planned_stages, expected_stages, strict=True):
        if any(planned.get(field) != selected[field] for field in _REQUIRED_STAGE_FIELDS):
            raise ValueError(f"implementation plan changed selected stage {selected['id']}")
        if planned.get("status") != "implemented":
            raise ValueError(f"implementation stage was not completed: {selected['id']}")
        if not isinstance(planned.get("network_section"), str) or not planned["network_section"].strip():
            raise ValueError(f"implementation stage requires a network_section: {selected['id']}")
        _nonempty_strings(planned.get("node_families"), "implementation stage node_families")
        nodes = planned.get("nodes")
        if not isinstance(nodes, list) or len(nodes) < 2:
            raise ValueError(f"implementation stage requires at least two planned nodes: {selected['id']}")
        stage_paths: list[str] = []
        for node in nodes:
            if not isinstance(node, dict) or set(node) != {"path", "type", "role", "inputs"}:
                raise ValueError("each planned node requires only path, type, role, and inputs")
            if any(not isinstance(node[field], str) or not node[field].strip() for field in ("path", "type", "role")):
                raise ValueError("planned node path, type, and role must be non-empty strings")
            if not node["path"].startswith("/"):
                raise ValueError("planned node paths must be absolute Houdini paths")
            inputs = node["inputs"]
            if (
                not isinstance(inputs, list)
                or any(not isinstance(path, str) or not path.startswith("/") for path in inputs)
                or len(set(inputs)) != len(inputs)
                or node["path"] in inputs
                or any(path not in planned_node_paths and path not in stage_paths for path in inputs)
            ):
                raise ValueError(
                    "planned node inputs must be unique, absolute, topologically prior planned paths"
                )
            stage_paths.append(node["path"])
        if len(set(stage_paths)) != len(stage_paths) or planned_node_paths.intersection(stage_paths):
            raise ValueError("planned node paths must be unique across implementation stages")
        expected_families = list(dict.fromkeys(node["type"] for node in nodes))
        if planned["node_families"] != expected_families:
            raise ValueError("implementation stage node_families must match its planned node types")
        planned_node_paths.update(stage_paths)
        if planned.get("output_node") != stage_paths[-1]:
            raise ValueError("implementation stage output_node must be its final planned node")
        controls = planned.get("artist_controls")
        if not isinstance(controls, list) or not controls:
            raise ValueError("implementation stage artist_controls must not be empty")
        for control in controls:
            if (
                not isinstance(control, dict)
                or set(control) != {"node_path", "parm"}
                or control.get("node_path") not in stage_paths
                or not isinstance(control.get("parm"), str)
                or not control["parm"].strip()
            ):
                raise ValueError("artist controls must name a planned node_path and parameter")
        _nonempty_strings(planned.get("evidence_paths"), "implementation stage evidence_paths")
        if any(path not in verified_artifact_paths for path in planned["evidence_paths"]):
            raise ValueError("implementation stage evidence is not a verified artifact")
        stage_evidence.append(planned["evidence_paths"][0])
    forbidden_stage_evidence = {plan_relative, *scene_artifacts}
    if len(set(stage_evidence)) != len(stage_evidence) or any(
        path in forbidden_stage_evidence for path in stage_evidence
    ):
        raise ValueError("each implementation stage requires distinct stage-specific evidence")
    return receipt


def _claim_summary(receipt: Mapping[str, Any]) -> dict[str, Any]:
    claims = receipt["claims"]
    return {
        kind: {
            status: sum(claim[f"{kind}_status"] == status for claim in claims)
            for status in ("demonstrated", "partial", "failed")
        }
        for kind in ("mechanical", "visual")
    }


def _mark_direction_decision_ready(item: dict[str, Any], receipt: Mapping[str, Any]) -> None:
    item["state"] = "decision-ready"
    item["receipt_verified"] = True
    item["status"] = {
        "mechanically_verified": True,
        "render_setup_verified": True,
        "visually_demonstrated": True,
        "motion_verified": True,
        "decision_ready": True,
        "art_director_approved": False,
    }
    item["claim_summary"] = _claim_summary(receipt)


def _seal_verified_attempt(root: Path, item: dict[str, Any], attempt_dir: Path) -> None:
    seal_path = attempt_dir / "verification-seal.json"
    receipt_path = attempt_dir / "receipt.json"
    seal = {
        "schema_version": 1,
        "attempt_id": item["current_attempt_id"],
        "attempt_packet_sha256": item["attempt_packet_sha256"],
        "receipt_sha256": _sha256(receipt_path),
        "graph_audit_sha256": item["graph_audit_sha256"],
    }
    _write_exclusive_json(seal_path, seal)
    seal_path.chmod(0o444)
    item["verification_seal_path"] = _relative(root, seal_path)
    item["verification_seal_sha256"] = _sha256(seal_path)


def _verify_attempt_seal(root: Path, item: Mapping[str, Any], attempt_dir: Path) -> None:
    seal_path = attempt_dir / "verification-seal.json"
    expected = {
        "schema_version": 1,
        "attempt_id": item.get("current_attempt_id"),
        "attempt_packet_sha256": item.get("attempt_packet_sha256"),
        "receipt_sha256": _sha256(attempt_dir / "receipt.json"),
        "graph_audit_sha256": item.get("graph_audit_sha256"),
    }
    if (
        item.get("verification_seal_path") != _relative(root, seal_path)
        or not seal_path.is_file()
        or item.get("verification_seal_sha256") != _sha256(seal_path)
        or json.loads(seal_path.read_text(encoding="utf-8")) != expected
    ):
        raise ValueError("verified attempt does not match its parent verification seal")


def _reverify_item(
    root: Path,
    manifest_path: Path,
    manifest: Mapping[str, Any],
    item: Mapping[str, Any],
) -> dict[str, Any]:
    direction_dir, base_packet_path, _ = _canonical_item_paths(root, manifest_path, item)
    attempt_number = int(item.get("attempt_count", 0))
    attempt_dir = direction_dir / f"attempt-{attempt_number:03d}"
    packet_path = attempt_dir / "execution-packet.json"
    receipt = _verified_receipt(root, manifest, item, base_packet_path, packet_path, attempt_dir)
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    layout = packet["workspace_layout"]
    audit_path = attempt_dir / layout["graph_audit"]
    plan_path = attempt_dir / layout["implementation_plan"]
    scene_stem = layout["scene_stem"]
    scenes = [
        attempt_dir / f"{scene_stem}{suffix}"
        for suffix in (".hip", ".hiplc", ".hipnc")
        if (attempt_dir / f"{scene_stem}{suffix}").is_file()
    ]
    if (
        len(scenes) != 1
        or item.get("graph_audit_path") != _relative(root, audit_path)
        or not audit_path.is_file()
        or item.get("graph_audit_sha256") != _sha256(audit_path)
    ):
        raise ValueError("verified attempt has no intact parent graph audit")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    _validate_parent_hip_audit(audit, scenes[0], plan_path, plan)
    _verify_attempt_seal(root, item, attempt_dir)
    return receipt


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            process.kill()
    else:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except OSError:
            process.kill()


def _run_bounded_process(
    command: Sequence[str],
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    timeout: int,
) -> tuple[int | None, str | None, bool, bool]:
    """Run a process while capping each captured stream on disk."""

    stdout_path.write_bytes(b"")
    stderr_path.write_bytes(b"")
    try:
        process = subprocess.Popen(
            list(command),
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=(
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
            ),
            start_new_session=os.name != "nt",
        )
    except OSError as error:
        return None, f"{type(error).__name__}: {error}", False, False

    overflow = threading.Event()
    stream_overflow = {"stdout": False, "stderr": False}

    def drain(name: str, stream: Any, path: Path) -> None:
        written = 0
        with path.open("wb") as handle:
            while True:
                chunk = stream.read(65_536)
                if not chunk:
                    break
                remaining = _PROCESS_OUTPUT_LIMIT - written
                if remaining > 0:
                    kept = chunk[:remaining]
                    handle.write(kept)
                    written += len(kept)
                if len(chunk) > max(remaining, 0):
                    stream_overflow[name] = True
                    if not overflow.is_set():
                        overflow.set()
                        _terminate_process_tree(process)

    threads = [
        threading.Thread(target=drain, args=("stdout", process.stdout, stdout_path), daemon=True),
        threading.Thread(target=drain, args=("stderr", process.stderr, stderr_path), daemon=True),
    ]
    for thread in threads:
        thread.start()
    error_text: str | None = None
    try:
        returncode = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        _terminate_process_tree(process)
        returncode = process.wait()
        error_text = f"TimeoutExpired: worker exceeded {timeout} seconds"
    for thread in threads:
        thread.join(timeout=5)
    if process.stdout is not None:
        process.stdout.close()
    if process.stderr is not None:
        process.stderr.close()
    if overflow.is_set():
        error_text = f"ProcessOutputLimit: worker output limit is {_PROCESS_OUTPUT_LIMIT} bytes per stream"
    return returncode, error_text, stream_overflow["stdout"], stream_overflow["stderr"]


def _run_bounded_command(
    command: Sequence[str], cwd: Path, log_dir: Path, label: str, timeout: int
) -> tuple[int, str, str]:
    """Run any child with descendant-tree termination and bounded temporary logs."""

    run_id = uuid.uuid4().hex
    stdout_path = log_dir / f".{label}-{run_id}.stdout.tmp"
    stderr_path = log_dir / f".{label}-{run_id}.stderr.tmp"
    try:
        returncode, error_text, _, _ = _run_bounded_process(
            command, cwd, stdout_path, stderr_path, timeout
        )
        stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
        if error_text is not None:
            raise RuntimeError(f"{label} failed: {error_text}")
        return returncode, stdout, stderr
    finally:
        stdout_path.unlink(missing_ok=True)
        stderr_path.unlink(missing_ok=True)


def make_hermes_worker(
    root: Path,
    command_prefix: Sequence[str] = ("hermes",),
    *,
    timeout: int = 1800,
    max_total_tokens: int | None = None,
    max_estimated_cost_usd: float | None = None,
    capture_usage: bool | None = None,
) -> Worker:
    """Create a worker that launches one fresh Hermes process per packet."""

    root = Path(root).resolve()
    prefix = [str(part) for part in command_prefix]
    if not prefix or any(not part for part in prefix):
        raise ValueError("Hermes command prefix must not be empty")
    if timeout <= 0:
        raise ValueError("Hermes worker timeout must be positive")
    if max_total_tokens is not None and max_total_tokens < 1:
        raise ValueError("Hermes worker token budget must be positive")
    if max_estimated_cost_usd is not None and max_estimated_cost_usd <= 0:
        raise ValueError("Hermes worker cost budget must be positive")
    if capture_usage is None:
        capture_usage = Path(prefix[0]).stem.lower() == "hermes"

    def worker(packet_path: Path, output_dir: Path) -> None:
        packet_path = Path(packet_path).resolve()
        output_dir = Path(output_dir).resolve()
        try:
            packet_path.relative_to(root)
            output_dir.relative_to(root)
        except ValueError as error:
            raise ValueError("Hermes worker paths must remain beneath the project root") from error
        prompt_path = packet_path.with_name("WORKER_PROMPT.md")
        if prompt_path.is_symlink() or not prompt_path.is_file():
            raise ValueError("Hermes worker prompt must be a regular non-symlink file")
        runtime_prompt = (
            "Execute the complete Look Development worker contract stored in the local files below. "
            "Read PROMPT and PACKET in full with file tools before taking any action; the paths, not "
            "this launcher message, are the authoritative instructions and data.\n\n"
            f"PROMPT: {prompt_path}\n"
            f"PACKET: {packet_path}\n"
            f"OUTPUT: {output_dir}\n"
            "A parent-owned deterministic scaffold already exists at the canonical HIP path, with "
            "its protected-node manifest at OUTPUT/00_design/PARENT_SCAFFOLD.json. Open and extend "
            "the existing canonical HIP; do not clear /stage, recreate the scene from scratch, replace "
            "SOURCE_FROZEN_CACHE, or delete/rename protected nodes. Insert direction-local geometry "
            "between LOOK_INPUT and OUT_FINAL, make the implementation plan's last output_node exactly "
            "/obj/LOOK_DIRECTION/OUT_FINAL, author the creative material and hero treatment through "
            "the existing protected render graph, and preserve the exact locked neutral controls. "
            "If PACKET contains repair_context, this is a bounded targeted repair: read its referenced "
            "PARENT_FAILURE_DIAGNOSTIC.json first, preserve the cloned creative state, and change only "
            "what the parent diagnostics require rather than rebuilding the direction.\n"
            "Critical filenames are exact and case-sensitive: write the final schema-v2 receipt only "
            "as OUTPUT/receipt.json and the implementation plan only as "
            "OUTPUT/00_design/IMPLEMENTATION_PLAN.json. Do not invent an alternate receipt schema, "
            "rename either file, or add keys outside the exact machine contracts in PROMPT. "
            "Before exiting, validate those two exact files against PROMPT rather than against a "
            "worker-authored schema. Never list agent-stdout.log, agent-stderr.log, agent-process.json, "
            "or agent-usage.json as receipt artifacts; they are mutable parent-owned accounting files, "
            "not evidence. The receipt claims must copy, byte-for-byte and in order, only "
            "direction.state_to_form_mappings[*].acceptance_observable from PACKET; do not substitute "
            "implementation-stage observables, summaries, or rewritten prose. The annotated claim "
            "sheet claims must use that same exact list. Each claim's render_evidence_paths may use "
            "only the contracted neutral early/middle/late paths, hero_render_path, "
            "motion_preview_path, and annotated_claim_sheet_path from PACKET.review_contract. Do not "
            "put auxiliary overlays, charts, contact sheets, swatches, or stage images there; keep "
            "them as artifacts or technical evidence. Do not write visual-review-ready or exit while "
            "any visual_status would be partial: continue refining the rendered package instead. For "
            "count claims, print the actual independently measured and emitted values in the claim "
            "sheet and label representative visible origins. For directional-tolerance claims, show "
            "both the relationship axis and measured disturbance axis together with the measured angle "
            "and tolerance. Reject and relight a hero that is near-black or does not visibly expose the "
            "direction's primary forms.\n"
            "The parent gate is stricter than worker reopen checks: the final SOP output for the last "
            "implementation stage must hold display and render flags; the exact planned canonical "
            "per-frame File SOP must participate in that output's active cook; Solaris SOP Import must "
            "evaluate to that exact final SOP at every neutral and motion frame; record actual "
            "versioned LOP type names in the plan; hero KEY/FILL/RIM must be actual distantlight "
            "nodes rather than generic light::2.0 nodes; configure OUT_KARMA's renderer parameter to "
            "a Karma token; and bind Karma settings to CAM_HERO before exit. "
            "Run the verifier contract in PROMPT against these exact conditions, not a reduced "
            "worker-authored reopen check.\n"
            "Write every generated file beneath OUTPUT. Do not return review material to KC; "
            "the parent round withholds it until all directions are complete.\n"
        )
        stdout_path, stderr_path = output_dir / "agent-stdout.log", output_dir / "agent-stderr.log"
        usage_path = output_dir / "agent-usage.json"
        usage_path.unlink(missing_ok=True)
        command = (
            [*prefix, "--usage-file", str(usage_path), "-z", runtime_prompt]
            if capture_usage else [*prefix, "chat", "-q", runtime_prompt]
        )
        returncode, error_text, stdout_truncated, stderr_truncated = _run_bounded_process(
            command,
            output_dir,
            stdout_path,
            stderr_path,
            timeout,
        )
        stdout_value = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr_value = stderr_path.read_text(encoding="utf-8", errors="replace")
        usage: dict[str, Any] | None = None
        if usage_path.is_symlink() or (usage_path.is_file() and usage_path.stat().st_size > 65_536):
            raise RuntimeError("Look Execution Agent usage report must be a small regular non-symlink file")
        if usage_path.is_file():
            usage_value = json.loads(usage_path.read_text(encoding="utf-8"))
            if isinstance(usage_value, dict):
                usage = usage_value
        process_receipt = {
            "schema_version": 1,
            "returncode": returncode,
            "stdout": stdout_value,
            "stderr": stderr_value,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "error": error_text,
            "usage": usage,
        }
        _atomic_write_json(output_dir / "agent-process.json", process_receipt)
        if error_text is not None:
            raise RuntimeError(f"Look Execution Agent could not complete: {error_text}")
        if returncode != 0:
            raise RuntimeError(f"Look Execution Agent exited with code {returncode}: {stderr_value.strip()}")
        if capture_usage and usage is None:
            raise RuntimeError("Look Execution Agent produced no required usage accounting report")
        if usage is not None:
            total_tokens = usage.get("total_tokens")
            estimated_cost = usage.get("estimated_cost_usd")
            if max_total_tokens is not None and (
                not isinstance(total_tokens, (int, float)) or isinstance(total_tokens, bool)
            ):
                raise LookBudgetExceeded("Look worker token accounting unavailable; budget enforcement stopped")
            if max_estimated_cost_usd is not None and (
                not isinstance(estimated_cost, (int, float)) or isinstance(estimated_cost, bool)
            ):
                raise LookBudgetExceeded("Look worker cost accounting unavailable; budget enforcement stopped")
            if not math.isfinite(float(total_tokens)) or total_tokens < 0:
                raise LookBudgetExceeded("Look worker token accounting is non-finite or negative")
            if not math.isfinite(float(estimated_cost)) or estimated_cost < 0:
                raise LookBudgetExceeded("Look worker cost accounting is non-finite or negative")
            if (
                max_total_tokens is not None
                and isinstance(total_tokens, (int, float))
                and not isinstance(total_tokens, bool)
                and total_tokens > max_total_tokens
            ):
                raise LookBudgetExceeded(
                    f"Look worker token budget exceeded: {total_tokens} > {max_total_tokens}"
                )
            if (
                max_estimated_cost_usd is not None
                and isinstance(estimated_cost, (int, float))
                and not isinstance(estimated_cost, bool)
                and estimated_cost > max_estimated_cost_usd
            ):
                raise LookBudgetExceeded(
                    "Look worker estimated cost budget exceeded: "
                    f"${estimated_cost:.4f} > ${max_estimated_cost_usd:.4f}"
                )

    return worker


def make_hython_hip_verifier(
    root: Path,
    hython_path: Path | None = None,
    *,
    timeout: int = 300,
) -> HipVerifier:
    """Create the parent verifier that reopens each HIP in a fresh Hython process."""

    root = Path(root).resolve()
    if hython_path is None:
        hython_path = next((tool.path for tool in discover_tools() if tool.name == "hython"), None)
    if hython_path is None:
        raise RuntimeError("hython is required for independent Look HIP verification; run houdini-ai doctor")
    script = root / "houdini" / "verify_look_scene.py"
    if not script.is_file():
        raise RuntimeError(f"Look HIP verifier script is missing: {script}")
    if timeout <= 0:
        raise ValueError("Hython verifier timeout must be positive")

    def verify(hip_path: Path, plan_path: Path) -> Mapping[str, Any]:
        audit_path = hip_path.parent.parent / "04_evidence" / f".graph-audit-{uuid.uuid4().hex}.tmp.json"
        command = [str(hython_path), str(script), str(hip_path), str(plan_path), str(audit_path)]
        try:
            returncode, _, stderr = _run_bounded_command(
                command, hip_path.parent, audit_path.parent, "hython-look-verifier", timeout
            )
            try:
                audit = json.loads(audit_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise RuntimeError(
                    f"Hython Look verifier produced no valid audit: {stderr.strip()}"
                ) from error
            if returncode != 0:
                messages = audit.get("node_errors") if isinstance(audit, dict) else None
                raise RuntimeError(f"Hython Look verification failed: {messages or stderr.strip()}")
            if not isinstance(audit, dict):
                raise RuntimeError("Hython Look verifier audit must be an object")
            return audit
        finally:
            audit_path.unlink(missing_ok=True)

    return verify


def make_hython_playground_builder(
    root: Path,
    hython_path: Path | None = None,
    *,
    timeout: int = 300,
) -> PlaygroundBuilder:
    """Create the two-process builder/verifier for the non-competing 00_look scene."""

    root = Path(root).resolve()
    if hython_path is None:
        hython_path = next((tool.path for tool in discover_tools() if tool.name == "hython"), None)
    if hython_path is None:
        raise RuntimeError("hython is required to build the 00_look playground; run houdini-ai doctor")
    script = root / "houdini" / "build_look_playground.py"
    if not script.is_file():
        raise RuntimeError(f"00_look playground builder script is missing: {script}")
    if timeout <= 0:
        raise ValueError("00_look builder timeout must be positive")

    def run(command: Sequence[str], label: str, log_dir: Path) -> None:
        returncode, stdout, stderr = _run_bounded_command(
            command, root, log_dir, f"playground-{label}", timeout
        )
        if returncode != 0:
            detail = "\n".join(part.strip() for part in (stdout, stderr) if part.strip())
            raise RuntimeError(f"00_look {label} failed: {detail}")

    def build(packet_path: Path, output_dir: Path) -> None:
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        layout = packet["workspace_layout"]
        hip_path = output_dir / layout["hip_path"]
        audit_path = output_dir / layout["audit_path"]
        receipt_path = output_dir / layout["receipt_path"]
        quarantine_dir = output_dir / "failed-builds"
        (output_dir / layout["render_directory"]).mkdir(exist_ok=True)

        def quarantine(path: Path, label: str) -> None:
            if not path.exists() and not path.is_symlink():
                return
            quarantine_dir.mkdir(exist_ok=True)
            os.replace(path, quarantine_dir / f"{label}-{uuid.uuid4().hex}.artifact")

        if hip_path.is_symlink():
            raise RuntimeError("00_look canonical HIP must not be a symlink or reparse-point alias")
        for stale in output_dir.glob(".playground-build-*.hiplc"):
            quarantine(stale, "interrupted-hip")
        verified_existing = False
        if hip_path.is_file():
            try:
                run(
                    [str(hython_path), str(script), "verify", str(packet_path), str(hip_path), str(audit_path)],
                    "fresh-Hython verification",
                    output_dir,
                )
                verified_existing = True
            except RuntimeError:
                quarantine(hip_path, "invalid-canonical-hip")
                quarantine(audit_path, "invalid-canonical-audit")
                receipt_path.unlink(missing_ok=True)

        if not verified_existing:
            build_id = uuid.uuid4().hex
            temporary_hip = output_dir / f".playground-build-{build_id}.hiplc"
            temporary_packet = output_dir / f".playground-build-{build_id}.json"
            build_packet = copy.deepcopy(packet)
            build_packet["workspace_layout"]["hip_path"] = temporary_hip.name
            _atomic_write_json(temporary_packet, build_packet)
            try:
                run(
                    [str(hython_path), str(script), "build", str(temporary_packet), str(output_dir), str(root)],
                    "build",
                    output_dir,
                )
                run(
                    [
                        str(hython_path), str(script), "verify", str(temporary_packet),
                        str(temporary_hip), str(audit_path),
                    ],
                    "fresh-Hython verification",
                    output_dir,
                )
                os.replace(temporary_hip, hip_path)
                audit = json.loads(audit_path.read_text(encoding="utf-8"))
                audit["hip_path"] = str(hip_path.resolve())
                _atomic_write_json(audit_path, audit)
            except Exception:
                quarantine(temporary_hip, "failed-staged-hip")
                quarantine(audit_path, "failed-staged-audit")
                raise
            finally:
                temporary_packet.unlink(missing_ok=True)

        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        receipt = {
            "schema_version": 1,
            "round_id": packet["round_id"],
            "source_behavior_content_hash": packet["source_behavior"]["content_hash"],
            "state": "internally-verified",
            "hip_path": layout["hip_path"],
            "hip_bytes": hip_path.stat().st_size,
            "hip_sha256": _sha256(hip_path),
            "audit_path": layout["audit_path"],
            "audit_sha256": _sha256(audit_path),
            "lighting_modes": audit["lighting_modes"],
        }
        _atomic_write_json(receipt_path, receipt)

    return build


def make_hython_direction_scaffold_builder(
    root: Path,
    hython_path: Path | None = None,
    *,
    timeout: int = 180,
) -> ScaffoldBuilder:
    """Create the deterministic parent-owned Look direction scaffold builder."""

    root = Path(root).resolve()
    if hython_path is None:
        hython_path = next((tool.path for tool in discover_tools() if tool.name == "hython"), None)
    if hython_path is None:
        raise RuntimeError("hython is required to build the Look direction scaffold; run houdini-ai doctor")
    script = root / "houdini" / "build_look_direction_scaffold.py"
    if not script.is_file():
        raise RuntimeError(f"Look direction scaffold builder script is missing: {script}")
    if timeout <= 0:
        raise ValueError("Look direction scaffold timeout must be positive")

    def build(packet_path: Path, output_dir: Path) -> None:
        returncode, stdout, stderr = _run_bounded_command(
            [str(hython_path), str(script), str(packet_path), str(output_dir), str(root)],
            root,
            output_dir,
            "direction-scaffold",
            timeout,
        )
        if returncode != 0:
            detail = "\n".join(part.strip() for part in (stdout, stderr) if part.strip())
            raise RuntimeError(f"Look direction scaffold failed: {detail}")

    return build


def _validate_parent_hip_audit(
    audit: Mapping[str, Any],
    hip_path: Path,
    plan_path: Path,
    plan: Mapping[str, Any],
) -> None:
    if audit.get("verification_engine") != "fresh-hython-reopen" or audit.get("passed") is not True:
        raise ValueError("parent graph audit was not produced by a successful fresh Hython reopen")
    try:
        audited_hip = Path(str(audit.get("hip_path"))).resolve()
    except (OSError, TypeError, ValueError) as error:
        raise ValueError("parent graph audit has an invalid HIP path") from error
    if (
        audited_hip != hip_path.resolve()
        or audit.get("hip_sha256") != _sha256(hip_path)
        or audit.get("plan_sha256") != _sha256(plan_path)
    ):
        raise ValueError("parent graph audit is not bound to the canonical HIP and plan bytes")
    stages = plan.get("stages")
    audited_stages = audit.get("stages")
    if not isinstance(stages, list) or not isinstance(audited_stages, list) or len(stages) != len(audited_stages):
        raise ValueError("parent graph audit stage coverage mismatch")
    expected_sections: list[str] = []
    expected_node_count = 0
    for index, (stage, audited) in enumerate(zip(stages, audited_stages, strict=True)):
        expected_nodes = [
            {
                "path": node["path"],
                "type": node["type"],
                "role": node["role"],
                "inputs": node["inputs"],
            }
            for node in stage["nodes"]
        ]
        output_flag_required = index == len(stages) - 1
        if (
            not isinstance(audited, Mapping)
            or audited.get("stage_id") != stage["id"]
            or audited.get("network_section") != stage["network_section"]
            or audited.get("nodes") != expected_nodes
            or audited.get("output_node") != stage["output_node"]
            or audited.get("errors") != []
            or audited.get("output_flag_required") is not output_flag_required
            or (
                output_flag_required
                and not (audited.get("display_flag") is True or audited.get("render_flag") is True)
            )
        ):
            raise ValueError(f"parent graph audit did not prove implementation stage {stage['id']}")
        expected_sections.append(stage["network_section"])
        expected_node_count += len(expected_nodes)
    if (
        audit.get("node_count") != expected_node_count
        or audit.get("network_sections") != expected_sections
        or audit.get("upward_edges") != []
        or audit.get("duplicate_node_positions") != []
        or audit.get("node_errors") != []
    ):
        raise ValueError("parent graph audit found graph depth, layout, or cook defects")

    source_audit = audit.get("source_cache")
    source_receipt = plan.get("source_cache_receipt")
    expected_setup = plan.get("render_setup")
    expected_source_frames = sorted(set([
        *expected_setup.get("neutral_frames", {}).values(),
        *expected_setup.get("motion_frames", []),
    ])) if isinstance(expected_setup, Mapping) else []
    source_records = source_audit.get("records") if isinstance(source_audit, Mapping) else None
    if (
        not isinstance(source_receipt, list)
        or not isinstance(source_audit, Mapping)
        or source_audit.get("passed") is not True
        or source_audit.get("errors") != []
        or not isinstance(source_records, list)
        or [record.get("frame") for record in source_records] != expected_source_frames
    ):
        raise ValueError("parent graph audit did not bind the rendered HIP to frozen source caches")
    receipt_by_frame = {
        int(match.group(1)): record
        for record in source_receipt
        if (match := _CACHE_FRAME.search(str(record.get("path", "")))) is not None
    }
    planned_file_paths = {
        node["path"]
        for stage in stages
        for node in stage["nodes"]
        if str(node.get("type", "")).split("::", 1)[0] == "file"
    }
    for record in source_records:
        expected = receipt_by_frame[record["frame"]]
        reported_source_path = Path(str(record.get("path")))
        source_path = reported_source_path.resolve()
        canonical_source_path = (Path(str(plan["project_root"])) / expected["path"]).resolve()
        if (
            reported_source_path.is_symlink()
            or not source_path.is_file()
            or source_path != canonical_source_path
            or not (record.get("bytes") == expected["bytes"] == source_path.stat().st_size)
            or not (record.get("sha256") == expected["sha256"] == _sha256(source_path))
            or not isinstance(record.get("file_nodes"), list)
            or not record["file_nodes"]
            or not set(record["file_nodes"]).issubset(planned_file_paths)
            or record.get("active_cook_only") is not True
            or record.get("sop_import_bound") is not True
            or record.get("sop_import_path") != stages[-1]["output_node"]
        ):
            raise ValueError("parent frozen source-cache binding metadata mismatch")

    render_setup = audit.get("render_setup")
    expected_types = {
        "look_import": "sopimport",
        "material_library": "materiallibrary",
        "material_assignment": "assignmaterial",
        "neutral_camera": "camera",
        "hero_camera": "camera",
        "neutral_dome": "domelight",
        "hero_key": "distantlight",
        "hero_fill": "distantlight",
        "hero_rim": "distantlight",
        "lighting_selector": "switch",
        "render_settings": "karmarendersettings",
        "render_output": "usdrender_rop",
    }
    if (
        not isinstance(expected_setup, Mapping)
        or not isinstance(render_setup, Mapping)
        or render_setup.get("passed") is not True
        or render_setup.get("errors") != []
        or render_setup.get("renderer") != expected_setup.get("renderer")
        or render_setup.get("color_pipeline") != expected_setup.get("color_pipeline")
        or render_setup.get("neutral_rig_id") != expected_setup.get("neutral_rig_id")
        or not isinstance(render_setup.get("ocio_config"), str)
        or not render_setup["ocio_config"].strip()
    ):
        raise ValueError("parent graph audit did not prove the direction render setup")
    audited_nodes = render_setup.get("nodes")
    if not isinstance(audited_nodes, list) or len(audited_nodes) != len(expected_types):
        raise ValueError("parent graph audit render setup node coverage mismatch")
    by_role = {
        node.get("role"): node
        for node in audited_nodes
        if isinstance(node, Mapping) and isinstance(node.get("role"), str)
    }
    expected_paths = expected_setup.get("nodes")
    if not isinstance(expected_paths, Mapping) or set(by_role) != set(expected_types):
        raise ValueError("parent graph audit render setup roles mismatch")
    for role, expected_type in expected_types.items():
        node = by_role[role]
        if (
            node.get("path") != expected_paths.get(role)
            or str(node.get("type", "")).split("::", 1)[0] != expected_type
            or node.get("connected_to_render_output") is not True
        ):
            raise ValueError(f"parent graph audit did not prove render setup role {role}")

    signature = render_setup.get("neutral_signature")
    expected_signature_frames = sorted(set([
        *expected_setup.get("neutral_frames", {}).values(),
        *expected_setup.get("motion_frames", []),
    ]))
    signature_samples = signature.get("samples") if isinstance(signature, Mapping) else None
    if (
        not isinstance(signature, Mapping)
        or signature.get("resolution") != expected_setup.get("resolution")
        or signature.get("samples_per_pixel") != expected_setup.get("samples_per_pixel")
        or signature.get("path_traced_samples") != expected_setup.get("path_traced_samples")
        or signature.get("neutral_selector_input") != 0
        or signature.get("locked_contract") != {
            "camera": expected_setup.get("neutral_camera_parameters"),
            "dome": expected_setup.get("neutral_dome_parameters"),
            "render_settings": expected_setup.get("neutral_render_parameters"),
        }
        or not isinstance(signature.get("ocio_sha256"), str)
        or not isinstance(signature.get("camera"), Mapping)
        or not signature["camera"]
        or not isinstance(signature.get("dome"), Mapping)
        or not signature["dome"]
        or not isinstance(signature.get("render_settings"), Mapping)
        or not signature["render_settings"]
        or not isinstance(signature_samples, list)
        or any(not isinstance(sample, Mapping) for sample in signature_samples)
        or [sample.get("frame") for sample in signature_samples] != expected_signature_frames
        or any(
            not isinstance(sample.get("camera"), Mapping)
            or not sample["camera"]
            or not isinstance(sample.get("dome"), Mapping)
            or not sample["dome"]
            or not isinstance(sample.get("render_settings"), Mapping)
            or not sample["render_settings"]
            for sample in signature_samples
        )
    ):
        raise ValueError("parent graph audit did not freeze equivalent neutral review conditions")

    proofs = render_setup.get("parent_renders")
    frames = expected_setup.get("neutral_frames")
    expected_proofs = [
        *(f"neutral-{role}" for role in ("early", "middle", "late")),
        "hero",
        *(f"motion-{index:03d}" for index in range(8)),
    ]
    motion_frames = expected_setup.get("motion_frames")
    if (
        not isinstance(frames, Mapping)
        or not isinstance(motion_frames, list)
        or len(motion_frames) != 8
        or not isinstance(proofs, list)
        or len(proofs) != 12
    ):
        raise ValueError("parent graph audit did not produce all bound render proofs")
    material_bindings = render_setup.get("material_bindings")
    if not isinstance(material_bindings, list) or len(material_bindings) != len(expected_proofs):
        raise ValueError("parent graph audit did not prove MaterialX bindings at every render frame")
    proof_root = hip_path.parent.parent / "04_evidence" / "parent-renders"
    proof_hashes: set[str] = set()
    motion_hashes: set[str] = set()
    material_signatures: set[tuple[str, str]] = set()
    camera_prims = render_setup.get("camera_prims")
    if (
        not isinstance(camera_prims, Mapping)
        or set(camera_prims) != {"neutral_camera", "hero_camera"}
        or any(not isinstance(path, str) or not path.strip() for path in camera_prims.values())
        or camera_prims["neutral_camera"] == camera_prims["hero_camera"]
    ):
        raise ValueError("parent graph audit did not report distinct authored USD camera paths")
    for proof, binding, role in zip(proofs, material_bindings, expected_proofs, strict=True):
        if role.startswith("neutral-"):
            expected_frame = frames[role.removeprefix("neutral-")]
        elif role == "hero":
            expected_frame = frames["middle"]
        else:
            expected_frame = motion_frames[int(role.removeprefix("motion-"))]
        if not isinstance(proof, Mapping) or proof.get("role") != role or proof.get("frame") != expected_frame:
            raise ValueError("parent render proof role or frame mismatch")
        if (
            not isinstance(binding, Mapping)
            or binding.get("role") != role
            or binding.get("frame") != expected_frame
            or binding.get("passed") is not True
            or not binding.get("target_paths")
            or not binding.get("prim_pattern")
            or not binding.get("material_path")
        ):
            raise ValueError("parent MaterialX binding proof mismatch")
        material_signatures.add((binding["prim_pattern"], binding["material_path"]))
        try:
            proof_path = Path(str(proof.get("path"))).resolve()
            proof_path.relative_to(proof_root.resolve())
        except (OSError, TypeError, ValueError) as error:
            raise ValueError("parent render proof escaped its canonical evidence directory") from error
        if proof_path.is_symlink() or not proof_path.is_file():
            raise ValueError("parent render proof must be a regular non-symlink file")
        if proof.get("bytes") != proof_path.stat().st_size or proof.get("sha256") != _sha256(proof_path):
            raise ValueError("parent render proof metadata mismatch")
        if proof.get("camera") != camera_prims["hero_camera" if role == "hero" else "neutral_camera"]:
            raise ValueError("parent render proof camera mismatch")
        if proof.get("lighting_mode") != (1 if role == "hero" else 0):
            raise ValueError("parent render proof lighting mode mismatch")
        _inspect_render_image(proof_path, f"parent {role} render proof")
        if role.startswith("neutral-"):
            proof_hashes.add(str(proof["sha256"]))
        elif role.startswith("motion-"):
            motion_hashes.add(str(proof["sha256"]))
    if len(proof_hashes) != 3:
        raise ValueError("parent neutral render proofs must be distinct")
    if len(material_signatures) != 1:
        raise ValueError("MaterialX assignment changed across rendered evidence frames")
    if len(motion_hashes) < 2:
        raise ValueError("parent motion render proofs do not demonstrate temporal change")
    parent_motion = render_setup.get("parent_motion")
    if not isinstance(parent_motion, Mapping):
        raise ValueError("parent graph audit has no HIP-bound motion preview")
    motion_path = Path(str(parent_motion.get("path"))).resolve()
    try:
        motion_path.relative_to(proof_root.resolve())
    except ValueError as error:
        raise ValueError("parent motion preview escaped its canonical evidence directory") from error
    if (
        motion_path.is_symlink()
        or not motion_path.is_file()
        or parent_motion.get("sha256") != _sha256(motion_path)
        or parent_motion.get("bytes") != motion_path.stat().st_size
        or parent_motion.get("frame_count") != 8
        or parent_motion.get("source_frames") != motion_frames
    ):
        raise ValueError("parent HIP-bound motion preview metadata mismatch")
    with Image.open(motion_path) as image:
        if image.format != "GIF" or getattr(image, "n_frames", 1) != 8:
            raise ValueError("parent HIP-bound motion preview is not an eight-frame GIF")


def _attach_parent_motion_preview(audit: dict[str, Any], attempt_dir: Path) -> None:
    render_setup = audit.get("render_setup")
    if not isinstance(render_setup, dict):
        raise ValueError("parent graph audit has no mutable render setup record")
    motion_records = [
        record for record in render_setup.get("parent_renders", [])
        if isinstance(record, Mapping) and str(record.get("role", "")).startswith("motion-")
    ]
    if len(motion_records) != 8:
        raise ValueError("parent graph audit did not return eight motion render proofs")
    frames: list[Image.Image] = []
    for record in motion_records:
        with Image.open(Path(str(record["path"]))) as image:
            frames.append(image.convert("RGB").copy())
    motion_path = attempt_dir / "04_evidence" / "parent-renders" / "parent-motion.gif"
    if motion_path.parent.is_symlink():
        raise ValueError("parent motion directory must not be a symlink")
    motion_path.unlink(missing_ok=True)
    frames[0].save(motion_path, save_all=True, append_images=frames[1:], duration=83, loop=0)
    render_setup["parent_motion"] = {
        "path": str(motion_path.resolve()),
        "bytes": motion_path.stat().st_size,
        "sha256": _sha256(motion_path),
        "frame_count": len(frames),
        "source_frames": [record["frame"] for record in motion_records],
        "camera": motion_records[0]["camera"],
        "lighting_mode": motion_records[0]["lighting_mode"],
    }


def _create_parent_hip_audit(
    root: Path,
    item: dict[str, Any],
    attempt_dir: Path,
    packet_path: Path,
    verifier: HipVerifier,
) -> None:
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    layout = packet["workspace_layout"]
    plan_path = attempt_dir / layout["implementation_plan"]
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    scene_stem = layout["scene_stem"]
    scenes = [
        attempt_dir / f"{scene_stem}{suffix}"
        for suffix in (".hip", ".hiplc", ".hipnc")
        if (attempt_dir / f"{scene_stem}{suffix}").is_file()
    ]
    if len(scenes) != 1:
        raise ValueError("canonical attempt workspace must contain exactly one HIP scene")
    audit = verifier(scenes[0], plan_path)
    if not isinstance(audit, dict):
        raise ValueError("parent HIP verifier must return an audit object")
    if item.get("scaffold_seal_path") is not None:
        _validate_parent_scaffold_seal(root, item, audit)
    _attach_parent_motion_preview(audit, attempt_dir)
    _validate_parent_hip_audit(audit, scenes[0], plan_path, plan)
    audit_path = attempt_dir / layout["graph_audit"]
    _write_exclusive_json(audit_path, audit)
    audit_path.chmod(0o444)
    item["graph_audit_path"] = _relative(root, audit_path)
    item["graph_audit_sha256"] = _sha256(audit_path)


def _claim_lock(lock_path: Path) -> None:
    try:
        with lock_path.open("x", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
    except FileExistsError as error:
        raise RuntimeError("Look round is already running") from error


def run_look_round(
    root: Path,
    manifest_path: Path,
    worker: Worker,
    hip_verifier: HipVerifier,
    playground_builder: PlaygroundBuilder,
    *,
    cost_approved: bool = False,
    scaffold_builder: ScaffoldBuilder | None = None,
) -> Path:
    """Run one worker at a time and verify each receipt before advancing."""

    root, manifest_path, manifest = _load_manifest(root, manifest_path)
    if manifest.get("frozen") is True:
        raise RuntimeError("Look round is frozen failed research provenance and cannot be executed")
    _verify_source_cache_receipt(root, manifest)
    if manifest.get("state") not in {"prepared", "failed"}:
        raise ValueError(f"cannot execute Look round from state {manifest.get('state')}")
    items = manifest.get("directions")
    if not isinstance(items, list) or not items or any(not isinstance(item, dict) for item in items):
        raise ValueError("Look round contains invalid directions")
    canonical = [_canonical_item_paths(root, manifest_path, item) for item in items]
    playground = manifest.get("playground")
    if not isinstance(playground, dict):
        raise ValueError("Look round contains no canonical 00_look playground")
    playground_dir, playground_packet, _ = _canonical_playground_paths(
        root, manifest_path, playground
    )
    gated_costs: set[str] = set()
    for _, packet_path, _ in canonical:
        cost_tier = json.loads(packet_path.read_text(encoding="utf-8"))["direction"]["cost_tier"]
        if cost_tier in {"study", "specimen", "external"}:
            gated_costs.add(cost_tier)
    if gated_costs and not cost_approved:
        raise ValueError(f"Look round requires explicit cost approval for: {', '.join(sorted(gated_costs))}")
    lock_path = manifest_path.with_name(".run.lock")
    _claim_lock(lock_path)
    try:
        playground_seal = playground_dir / "playground-seal.json"
        if playground_seal.is_file():
            _accept_playground(root, manifest, playground, playground_dir, playground_packet)
        else:
            playground["state"] = "running"
            _atomic_write_json(manifest_path, manifest)
            playground_builder(playground_packet, playground_dir)
            _accept_playground(root, manifest, playground, playground_dir, playground_packet)
        _atomic_write_json(manifest_path, manifest)
        for item, (direction_dir, _, _) in zip(items, canonical, strict=True):
            attempt_number = int(item.get("attempt_count", 0))
            seal_path = direction_dir / f"attempt-{attempt_number:03d}" / "verification-seal.json"
            if seal_path.is_file():
                receipt = _reverify_item(root, manifest_path, manifest, item)
                _mark_direction_decision_ready(item, receipt)
            elif item.get("receipt_verified"):
                raise ValueError("manifest claims verification without a parent verification seal")
        manifest["state"] = "running"
        _atomic_write_json(manifest_path, manifest)
        policy = manifest.get("execution_policy", {
            "max_attempts_per_direction": 2,
            "worker_timeout_seconds": 1800,
            "max_total_tokens_per_attempt": 200000,
            "max_estimated_cost_usd_per_attempt": 10.0,
            "repair_mode": "targeted-from-parent-diagnostics",
        })
        max_attempts = policy.get("max_attempts_per_direction") if isinstance(policy, Mapping) else None
        if not isinstance(max_attempts, int) or max_attempts < 1:
            raise ValueError("Look round execution policy has an invalid attempt budget")
        for item, (direction_dir, packet_path, prompt_path) in zip(items, canonical, strict=True):
            if item.get("receipt_verified"):
                continue
            if item.get("state") == "budget-exhausted":
                raise RuntimeError(f"resource budget exhausted for {item['direction_id']}; redesign required")
            if int(item.get("attempt_count", 0)) >= max_attempts:
                raise RuntimeError(
                    f"attempt budget exhausted for {item['direction_id']}; diagnose or prepare a repair round"
                )
            attempt_packet, attempt_dir, _ = _materialize_attempt(
                root, manifest, item, direction_dir, packet_path, prompt_path
            )
            _atomic_write_json(manifest_path, manifest)
            try:
                attempt_packet_value = json.loads(attempt_packet.read_text(encoding="utf-8"))
                if scaffold_builder is not None and "repair_context" not in attempt_packet_value:
                    scaffold_builder(attempt_packet, attempt_dir)
                if scaffold_builder is not None:
                    _seal_parent_scaffold(root, direction_dir, attempt_dir, item)
                    _atomic_write_json(manifest_path, manifest)
                worker(attempt_packet, attempt_dir)
                receipt = _verified_receipt(root, manifest, item, packet_path, attempt_packet, attempt_dir)
                _create_parent_hip_audit(root, item, attempt_dir, attempt_packet, hip_verifier)
            except Exception as error:
                diagnostic_path = attempt_dir / "00_design" / "PARENT_FAILURE_DIAGNOSTIC.json"
                budget_exhausted = isinstance(error, LookBudgetExceeded)
                _atomic_write_json(diagnostic_path, {
                    "schema_version": 1,
                    "attempt_id": item["current_attempt_id"],
                    "phase": "worker-or-parent-verification",
                    "error_type": type(error).__name__,
                    "message": str(error),
                    "next_action": "stop-and-redesign" if budget_exhausted else "targeted-repair-only",
                })
                item.update({
                    "state": "budget-exhausted" if budget_exhausted else "repair-required",
                    "failure_diagnostic_path": _relative(root, diagnostic_path),
                    "failure_diagnostic_sha256": _sha256(diagnostic_path),
                })
                if budget_exhausted:
                    item.pop("repair_source_path", None)
                else:
                    item["repair_source_path"] = item["current_attempt_path"]
                _atomic_write_json(manifest_path, manifest)
                raise
            item["receipt_path"] = _relative(root, attempt_dir / "receipt.json")
            _seal_verified_attempt(root, item, attempt_dir)
            _mark_direction_decision_ready(item, receipt)
            for transient in ("repair_source_path", "failure_diagnostic_path", "failure_diagnostic_sha256"):
                item.pop(transient, None)
            _atomic_write_json(manifest_path, manifest)
        manifest.pop("error", None)
        manifest["state"] = "decision-ready-awaiting-comparative-review"
        _atomic_write_json(manifest_path, manifest)
    except Exception as error:
        manifest["state"] = "failed"
        manifest["error"] = f"{type(error).__name__}: {error}"
        _atomic_write_json(manifest_path, manifest)
        raise
    finally:
        lock_path.unlink(missing_ok=True)
    return manifest_path


def _review_paths(root: Path, manifest: Mapping[str, Any]) -> tuple[Path, Path, Path]:
    review_dir = (
        root / "studies" / study_directory_name(str(manifest["study_id"])) /
        "02_look" / "02_review" / str(manifest["id"])
    )
    return (
        review_dir / "review-manifest.json",
        review_dir / "COMPARISON.md",
        review_dir / "review-seal.json",
    )


def _verify_released_review(root: Path, manifest: Mapping[str, Any]) -> Path:
    review_path, comparison_path, seal_path = _review_paths(root, manifest)
    try:
        seal = json.loads(seal_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as error:
        raise ValueError("released review integrity seal is missing or invalid") from error
    expected = {
        "schema_version": 1,
        "round_id": manifest["id"],
        "review_manifest_path": _relative(root, review_path),
        "review_manifest_sha256": _sha256(review_path) if review_path.is_file() else None,
        "comparison_path": _relative(root, comparison_path),
        "comparison_sha256": _sha256(comparison_path) if comparison_path.is_file() else None,
    }
    if seal != expected:
        raise ValueError("released review integrity verification failed")
    return review_path


def build_aggregate_review(root: Path, manifest_path: Path) -> Path:
    """Expose one comparison only after every direction is freshly reverified."""

    root, manifest_path, manifest = _load_manifest(root, manifest_path)
    _verify_source_cache_receipt(root, manifest)
    round_state = manifest.get("state")
    if round_state not in {
        "decision-ready-awaiting-comparative-review", "comparative-review-ready"
    }:
        raise ValueError("aggregate review requires a decision-ready Look round")
    playground_hip_path = _reverify_playground(root, manifest_path, manifest)
    if round_state == "comparative-review-ready":
        return _verify_released_review(root, manifest)
    items = manifest.get("directions")
    if manifest.get("state") != "decision-ready-awaiting-comparative-review" or not isinstance(items, list):
        raise ValueError("aggregate review requires a decision-ready Look round")
    if not items or any(
        not isinstance(item, dict)
        or not item.get("receipt_verified")
        or not isinstance(item.get("status"), dict)
        or any(
            item["status"].get(field) is not True
            for field in (
                "mechanically_verified", "render_setup_verified", "visually_demonstrated",
                "motion_verified", "decision_ready",
            )
        )
        for item in items
    ):
        raise ValueError("aggregate review requires every direction to pass all decision-readiness gates")

    review_path, comparison_path, review_seal_path = _review_paths(root, manifest)
    review_items: list[dict[str, Any]] = []
    review_signatures: set[tuple[Any, ...]] = set()
    comparison = [
        f"# {manifest['id']} comparative Look review",
        "",
        "## Matched final-image evidence",
        "",
        "All candidates passed separate mechanical, render-setup, visual, motion, and decision-readiness gates under equivalent neutral review conditions.",
        "Direction-specific hero images follow the matched neutral renders; technical records come last.",
        "",
    ]
    for item in items:
        receipt = _reverify_item(root, manifest_path, manifest, item)
        _, base_packet_path, _ = _canonical_item_paths(root, manifest_path, item)
        packet = json.loads(base_packet_path.read_text(encoding="utf-8"))
        claim_summary = _claim_summary(receipt)
        scene_stem = packet["workspace_layout"]["scene_stem"]
        hip_artifact = next(
            artifact for artifact in receipt["artifacts"]
            if artifact["path"] in {f"{scene_stem}{suffix}" for suffix in (".hip", ".hiplc", ".hipnc")}
        )
        attempt_dir = (root / item["receipt_path"]).parent
        canonical_hip_path = _relative(root, attempt_dir / hip_artifact["path"])
        media = receipt["review_media"]
        graph_audit = json.loads((root / item["graph_audit_path"]).read_text(encoding="utf-8"))
        audited_setup = graph_audit["render_setup"]
        proof_records = audited_setup["parent_renders"]
        neutral_proofs = [record for record in proof_records if record["role"].startswith("neutral-")]
        hero_proof = next(record for record in proof_records if record["role"] == "hero")
        media_paths = {
            "neutral": [
                {
                    **record,
                    "role": record["role"].removeprefix("neutral-"),
                    "project_path": _relative(root, Path(record["path"])),
                }
                for record in neutral_proofs
            ],
            "hero": _relative(root, Path(hero_proof["path"])),
            "motion": _relative(root, Path(audited_setup["parent_motion"]["path"])),
            "annotated_claim_sheet": _relative(
                root, attempt_dir / media["annotated_claim_sheet"]["path"]
            ),
        }
        neutral_size = _inspect_render_image(
            Path(neutral_proofs[0]["path"]), "comparative neutral render"
        )
        review_signatures.add((
            media["renderer"], media["color_pipeline"], media["neutral_rig_id"],
            tuple(record["frame"] for record in neutral_proofs), neutral_size,
            tuple(audited_setup["parent_motion"]["source_frames"]),
            json.dumps(
                audited_setup["neutral_signature"]["locked_contract"],
                sort_keys=True,
                separators=(",", ":"),
            ),
        ))
        review_items.append({
            "sequence_index": item["sequence_index"],
            "direction_id": item["direction_id"],
            "title": item["title"],
            "thesis": packet["direction"]["thesis"],
            "final_image_thesis": packet["direction"]["visual_target"]["final_image_thesis"],
            "canonical_hip_path": canonical_hip_path,
            "graph_audit_path": item["graph_audit_path"],
            "receipt_path": item["receipt_path"],
            "status": item["status"],
            "claim_summary": claim_summary,
            "review_media": media_paths,
            "review_conditions": {
                "renderer": media["renderer"],
                "color_pipeline": media["color_pipeline"],
                "neutral_rig_id": media["neutral_rig_id"],
                "resolution": list(neutral_size),
                "audited_neutral_signature": audited_setup["neutral_signature"],
                "evidence_source": "parent-hython-karma-render-proof",
                "motion_source_frames": audited_setup["parent_motion"]["source_frames"],
            },
            "deviations": receipt["deviations"],
            "node_errors": receipt["node_errors"],
        })
        comparison.extend([
            f"## {item['sequence_index']}. {item['title']}",
            "",
            "### Matched neutral frames",
            "",
        ])
        for record in media_paths["neutral"]:
            image_path = Path(os.path.relpath(root / record["project_path"], comparison_path.parent)).as_posix()
            comparison.extend([
                f"**{record['role'].title()} — frame {record['frame']}**",
                "",
                f"![{item['title']} {record['role']} neutral render]({image_path})",
                "",
            ])
        hero_link = Path(os.path.relpath(root / media_paths["hero"], comparison_path.parent)).as_posix()
        sheet_link = Path(os.path.relpath(root / media_paths["annotated_claim_sheet"], comparison_path.parent)).as_posix()
        comparison.extend([
            "### Direction-specific hero image",
            "",
            f"![{item['title']} hero render]({hero_link})",
            "",
            "### Annotated visual claim sheet",
            "",
            f"![{item['title']} annotated claim sheet]({sheet_link})",
            "",
            f"- Motion preview: `{media_paths['motion']}`",
            f"- Final-image thesis: {packet['direction']['visual_target']['final_image_thesis']}",
            f"- Canonical editable HIP: `{canonical_hip_path}`",
            f"- Parent Hython scene audit: `{item['graph_audit_path']}`",
            f"- Mechanical claims demonstrated: {claim_summary['mechanical']['demonstrated']}",
            f"- Visual claims demonstrated: {claim_summary['visual']['demonstrated']}",
            "- Art-director approval: pending KC",
            "",
        ])
    if len(review_signatures) != 1:
        raise ValueError("aggregate review requires equivalent frames, resolution, renderer, color, and neutral rig")
    review = {
        "schema_version": 2,
        "round_id": manifest["id"],
        "study_id": manifest["study_id"],
        "source_behavior_component_id": manifest["source_behavior_component_id"],
        "source_behavior_content_hash": manifest["source_behavior_content_hash"],
        "state": "ready-for-kc-review",
        "review_policy": "image-first-all-directions-together",
        "art_director_approved": False,
        "playground_hip_path": playground_hip_path,
        "directions": review_items,
    }
    _atomic_write_json(review_path, review)
    _write_text(comparison_path, "\n".join(comparison))
    review_seal = {
        "schema_version": 1,
        "round_id": manifest["id"],
        "review_manifest_path": _relative(root, review_path),
        "review_manifest_sha256": _sha256(review_path),
        "comparison_path": _relative(root, comparison_path),
        "comparison_sha256": _sha256(comparison_path),
    }
    _write_exclusive_json(review_seal_path, review_seal)
    review_seal_path.chmod(0o444)
    manifest["state"] = "comparative-review-ready"
    manifest["review_manifest_path"] = _relative(root, review_path)
    manifest["review_seal_path"] = _relative(root, review_seal_path)
    manifest["review_seal_sha256"] = _sha256(review_seal_path)
    _atomic_write_json(manifest_path, manifest)
    return review_path
