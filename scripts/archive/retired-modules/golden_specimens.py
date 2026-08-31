"""Registration of completed real projects as Studio golden specimens."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from .lineage import stable_content_hash
from .studio_schema import validate_record
from .studio_sessions import ensure_scar_tissue_session, scar_tissue_behavior_reset_active
from .studio_store import StudioStore


SCAR_TISSUE_COMPONENTS = (
    "component-behavior-b3bcc837c3e2",
    "component-look-6013004ba32c",
    "component-palette-a52433fdb147",
)
SCAR_TISSUE_SHOT_COMPONENT = "component-shot-scar-tissue-abc-a-v1"
SCAR_TISSUE_SPECIMEN = "specimen-scar-tissue-v1"
_FRAME_PATTERN = re.compile(r"scar-tissue-portrait-(\d{4})\.png")


class GoldenSpecimenError(ValueError):
    pass


def _validated(kind: str, record: dict[str, Any]) -> dict[str, Any]:
    errors = validate_record(kind, record)
    if errors:
        raise GoldenSpecimenError(f"invalid {kind} record: {'; '.join(errors)}")
    return record


def _create_or_confirm(store: StudioStore, collection: str, record: dict[str, Any]) -> None:
    record_id = str(record["id"])
    try:
        existing = store.read(collection, record_id)
    except FileNotFoundError:
        store.create(collection, record_id, record)
        return
    if existing != record:
        raise GoldenSpecimenError(f"conflicting existing golden record: {record_id}")


def _write_current_specimen(store: StudioStore, record: dict[str, Any]) -> None:
    record_id = str(record["id"])
    try:
        existing = store.read("specimens", record_id)
    except FileNotFoundError:
        store.create("specimens", record_id, record)
        return
    immutable_keys = ("schema_version", "id", "component_ids", "creative_reason", "deliverables", "cost_tier", "visibility")
    if any(existing.get(key) != record.get(key) for key in immutable_keys):
        raise GoldenSpecimenError(f"conflicting existing golden record: {record_id}")
    store.update("specimens", record_id, record)


def _frame_progress(frames_directory: Path, expected_frames: int = 1260) -> dict[str, Any]:
    frames: set[int] = set()
    if frames_directory.is_dir():
        for path in frames_directory.iterdir():
            match = _FRAME_PATTERN.fullmatch(path.name)
            if path.is_file() and path.stat().st_size > 0 and match:
                number = int(match.group(1))
                if 1 <= number <= expected_frames:
                    frames.add(number)
    next_frame = next((number for number in range(1, expected_frames + 1) if number not in frames), None)
    contiguous_frames = expected_frames if next_frame is None else next_frame - 1
    return {
        "completed_frames": len(frames),
        "contiguous_frames": contiguous_frames,
        "expected_frames": expected_frames,
        "highest_complete_frame": max(frames, default=0),
        "next_frame": next_frame,
        "complete": len(frames) == expected_frames,
    }


def register_scar_tissue(root: Path) -> dict[str, Any]:
    """Register the real Scar Tissue selection and current delivery state locally."""

    root = Path(root).resolve()
    store = StudioStore(root)
    if scar_tissue_behavior_reset_active(store):
        raise GoldenSpecimenError("Scar Tissue is reset to Behavior; legacy golden registration is retired")
    selected: list[dict[str, Any]] = []
    expected = (
        (SCAR_TISSUE_COMPONENTS[0], "behavior", "behavior"),
        (SCAR_TISSUE_COMPONENTS[1], "look", "look"),
        (SCAR_TISSUE_COMPONENTS[2], "chromatic", "palette"),
    )
    for component_id, track, kind in expected:
        try:
            component = store.read("components", component_id)
        except FileNotFoundError as error:
            raise GoldenSpecimenError(f"missing selected Scar Tissue component: {component_id}") from error
        _validated("component", component)
        if component.get("track") != track or component.get("component_kind") != kind:
            raise GoldenSpecimenError(f"selected Scar Tissue component has the wrong role: {component_id}")
        selected.append(component)

    handoff_relative = "work/studio/handoffs/scar-tissue-abc-a-v1/scar-tissue-abc-a-handoff.hiplc"
    handoff = root / Path(handoff_relative)
    if not handoff.is_file() or handoff.stat().st_size == 0:
        raise GoldenSpecimenError("Scar Tissue editable handoff is missing or empty")
    digest = "sha256:" + hashlib.sha256(handoff.read_bytes()).hexdigest()

    idea = _validated("idea", {
        "schema_version": 1,
        "id": "idea-scar-tissue-cinematography-abc-a-v1",
        "title": "Scar Tissue A-B-C-A cinematography",
        "raw_text": "Interpret the system at holistic, environmental, and intimate scales, then return to the establishing view.",
        "track": "cinematography",
        "state": "proposed",
        "visibility": "private",
    })
    proposal = _validated("proposal", {
        "schema_version": 1,
        "id": "proposal-scar-tissue-cinematography-abc-a-v1",
        "idea_id": idea["id"],
        "track": "cinematography",
        "state": "approved",
        "question": "Can A-B-C-A coverage explain the whole field, enter it, inspect local activity, and return coherently?",
        "mechanism": "Use a continuous 45 fps timeline with tight-isometric, low-grazing, and intimate-tracking camera families.",
        "outputs": ["editable-handoff", "motion-check", "portrait-frame-sequence"],
        "stop_conditions": ["coverage loses system legibility", "camera transitions break timeline continuity"],
        "runner": "cinematography.scar_tissue_handoff",
        "cost_tier": "specimen",
        "visibility": "private",
    })
    experiment = _validated("experiment", {
        "schema_version": 1,
        "id": "experiment-scar-tissue-cinematography-abc-a-v1",
        "proposal_id": proposal["id"],
        "track": "cinematography",
        "state": "completed",
        "runner": "cinematography.scar_tissue_handoff",
        "parameters": {"frame_start": 1, "frame_end": 1260, "fps": 45, "shot_order": ["A1", "B", "C", "A2"]},
        "visibility": "private",
    })
    artifact = _validated("artifact", {
        "schema_version": 1,
        "id": "artifact-scar-tissue-cinematography-abc-a-v1",
        "experiment_id": experiment["id"],
        "track": "cinematography",
        "state": "verified",
        "path": handoff_relative,
        "sha256": digest,
        "verified": True,
        "visibility": "private",
        "decision": "promote",
        "decision_note": "KC approved the A1-B-C-A2 continuous portrait handoff as the selected cinematography.",
    })
    shot_rationale = "KC selected the A1-B-C-A2 continuous portrait handoff with per-view stage camera controls."
    shot = _validated("component", {
        "schema_version": 1,
        "id": SCAR_TISSUE_SHOT_COMPONENT,
        "track": "cinematography",
        "state": "promoted",
        "component_kind": "shot",
        "source_experiment_id": experiment["id"],
        "source_artifact_ref": handoff_relative,
        "rationale": shot_rationale,
        "content_hash": stable_content_hash({"source_sha256": digest, "rationale": shot_rationale}),
        "visibility": "private",
    })
    for collection, record in (("ideas", idea), ("proposals", proposal), ("experiments", experiment), ("artifacts", artifact), ("components", shot)):
        _create_or_confirm(store, collection, record)

    progress = _frame_progress(handoff.parent / "portrait-frames")
    specimen = _validated("specimen", {
        "schema_version": 1,
        "id": SCAR_TISSUE_SPECIMEN,
        "state": "rendering" if not progress["complete"] else "approved",
        "component_ids": [*SCAR_TISSUE_COMPONENTS, SCAR_TISSUE_SHOT_COMPONENT],
        "creative_reason": "First complete end-to-end proving run of the Computational Studio, preserving Scar Tissue's selected behavior, structural look, semantic palette, and A-B-C-A cinematography.",
        "deliverables": ["portrait-png-sequence-1080x1920", "28-second-portrait-video", "private-field-note"],
        "cost_tier": "specimen",
        "approved": bool(progress["complete"]),
        "visibility": "private",
        "extensions": {
            "studio/project-slug": "scar-tissue",
            "studio/lineage-role": "golden-reference",
            "studio/render-progress": progress,
            "studio/handoff-path": handoff_relative,
            "studio/shot-order": ["A1", "B", "C", "A2"],
            "studio/sound-decision": "undecided",
        },
    })
    _write_current_specimen(store, specimen)
    ensure_scar_tissue_session(store, specimen)
    return specimen
