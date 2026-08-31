"""Register the corrected continuous-rewire Behavior as a superseding component."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from houdini_ai.promotions import promote_artifact
from houdini_ai.studio_schema import validate_record
from houdini_ai.studio_store import StudioStore

IDEA_ID = "idea-study-003-affinity-continuous-rewire-correction-v2"
PROPOSAL_ID = "proposal-study-003-affinity-continuous-rewire-v2"
EXPERIMENT_ID = "experiment-study-003-affinity-continuous-rewire-v2"
ARTIFACT_ID = "artifact-study-003-affinity-continuous-rewire-v2"
OLD_COMPONENT_ID = "component-behavior-2e6832d7d826"
MESSAGE_ID = "1539259275254169642"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def checked(kind: str, record: dict[str, Any]) -> dict[str, Any]:
    errors = validate_record(kind, record)
    if errors:
        raise RuntimeError(f"invalid {kind}: {'; '.join(errors)}")
    return record


def run(root: Path) -> dict[str, Any]:
    root = root.resolve()
    selection = root / "studies/study_003_nonlocal-affinity-dance/01_behavior/03_selected/selection_002"
    old_selection = selection.parent / "selection_001"
    receipt_path = selection / "cache_sequence/receipt.json"
    audit_path = selection / "cache_sequence/fresh-hython-audit.json"
    cache_source_path = selection / "cache-source.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    cache_source = json.loads(cache_source_path.read_text(encoding="utf-8"))
    if audit.get("errors") or audit.get("checked_frame_count") != 450:
        raise RuntimeError("fresh Hython audit is incomplete")
    if audit.get("last_relationship_change_frame") != 650:
        raise RuntimeError("corrected relationship graph does not change through frame 650")
    if not receipt.get("original_240_step_schedule_is_exact_prefix"):
        raise RuntimeError("corrected schedule does not preserve the accepted prefix")
    if receipt.get("last_visible_scheduled_rewire_frame") != 650:
        raise RuntimeError("corrected schedule does not reach the visible endpoint")

    receipt["fresh_hython_audit"] = {
        "path": selection.joinpath("cache_sequence/fresh-hython-audit.json").relative_to(root).as_posix(),
        "bytes": audit_path.stat().st_size,
        "sha256": sha256(audit_path),
        "checked_frame_count": audit["checked_frame_count"],
        "last_relationship_change_frame": audit["last_relationship_change_frame"],
        "total_friend_changes": audit["total_friend_changes"],
        "total_enemy_changes": audit["total_enemy_changes"],
        "errors": audit["errors"],
    }
    write_json(receipt_path, receipt)

    handoff = root / "work/studio/handoffs/study-003-affinity-continuous-rewire-v2"
    if handoff.exists():
        raise RuntimeError(f"immutable handoff already exists: {handoff}")
    handoff.mkdir(parents=True)
    shutil.copy2(receipt_path, handoff / "behavior-correction-receipt.json")
    shutil.copy2(audit_path, handoff / "fresh-hython-audit.json")
    manifest = {
        "schema_version": 1,
        "study_id": "study-003-nonlocal-affinity-dance",
        "correction_authorization_message_id": MESSAGE_ID,
        "supersedes_component_id": OLD_COMPONENT_ID,
        "selection": selection.relative_to(root).as_posix(),
        "files": {},
        "source_code": {},
    }
    tracked = {
        "behavior-correction-receipt.json": handoff / "behavior-correction-receipt.json",
        "fresh-hython-audit.json": handoff / "fresh-hython-audit.json",
        "prepared-parallel-cohort-960.json": selection / "prepared-parallel-cohort-960.json",
        "final-state.0960.bgeo.sc": selection / "final-state.0960.bgeo.sc",
    }
    for name, path in tracked.items():
        manifest["files"][name] = {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
    for relative_path in (
        "houdini/stage_affinity_continuous_rewire_cache.py",
        "houdini/verify_affinity_behavior_cache.py",
        "tests/test_affinity_continuous_rewire_cache.py",
    ):
        path = root / relative_path
        manifest["source_code"][relative_path] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    write_json(handoff / "manifest.json", manifest)

    store = StudioStore(root)
    idea = checked("idea", {
        "schema_version": 1,
        "id": IDEA_ID,
        "title": "Study 003 continuous-rewire correction",
        "raw_text": "Correct the selected Behavior so its deterministic relationship rewiring continues throughout the complete animation instead of ending with the original 240-step preparation horizon.",
        "track": "behavior",
        "state": "proposed",
        "visibility": "private",
        "short_summary": "Preserve the accepted Study 003 prefix and continue its exact stochastic stream through the full horizon.",
        "tags": ["graph-dynamics", "nonlocal-affinity", "correction"],
        "questions": ["Can the accepted prefix remain bit-identical while its event stream is extended deterministically?"],
        "constraints": ["Do not alter initialization, routing, force parameters, or historical events."],
        "extensions": {
            "studio/parent-study": "study-003-nonlocal-affinity-dance",
            "studio/approval-message-id": MESSAGE_ID,
        },
    })
    proposal = checked("proposal", {
        "schema_version": 1,
        "id": PROPOSAL_ID,
        "idea_id": IDEA_ID,
        "direction_ids": ["direction-fbe9c254e174"],
        "track": "behavior",
        "state": "approved",
        "question": "Can the promoted shallow-3D Parallel Behavior be corrected so deterministic rewiring remains active throughout its complete 960-step horizon?",
        "hypothesis": "Extending the original Mulberry32 draw stream while preserving its exact 240-step prefix will retain the accepted early Behavior and continue graph rewiring through the visible endpoint.",
        "mechanism": "Replay the same 5k Canvas initialization, shallow-Z lift, 20-member Parallel cohort routing, and exact historical event prefix, then continue the same deterministic RNG stream through step 960 before VEX-authoritative evolution.",
        "outputs": ["corrected 960-step prepared schedule", "450 consecutive 100k-point caches for frames 201-650", "all-frame relationship-change audit"],
        "stop_conditions": ["historical prefix mismatch", "missing late rewires", "VEX error", "point-count drift", "non-finite geometry", "invalid friend or enemy index"],
        "runner": "behavior.nonlocal_affinity_3d",
        "cost_tier": "study",
        "visibility": "private",
        "extensions": {"studio/approval-message-id": MESSAGE_ID},
    })
    experiment = checked("experiment", {
        "schema_version": 1,
        "id": EXPERIMENT_ID,
        "proposal_id": PROPOSAL_ID,
        "track": "behavior",
        "state": "completed",
        "runner": "behavior.nonlocal_affinity_3d",
        "parameters": {
            "agent_count": 100000,
            "anchor_count": 5000,
            "cohort_size": 20,
            "routing": "parallel",
            "steps": 960,
            "cache_frame_start": 201,
            "cache_frame_end": 650,
            "rewiring": "same deterministic stream active through complete horizon",
        },
        "visibility": "private",
        "extensions": {
            "studio/handoff": handoff.relative_to(root).as_posix(),
            "studio/state-authority": "vex-geometry",
        },
    })
    artifact_relative = (handoff / "behavior-correction-receipt.json").relative_to(root).as_posix()
    artifact = checked("artifact", {
        "schema_version": 1,
        "id": ARTIFACT_ID,
        "experiment_id": EXPERIMENT_ID,
        "track": "behavior",
        "state": "verified",
        "path": artifact_relative,
        "sha256": "sha256:" + sha256(handoff / "behavior-correction-receipt.json"),
        "verified": True,
        "visibility": "private",
        "decision": "promote",
        "decision_note": "KC corrected the intended mechanism: rewiring must continue throughout the whole animation.",
        "extensions": {
            "studio/approval-message-id": MESSAGE_ID,
            "studio/manifest": (handoff / "manifest.json").relative_to(root).as_posix(),
            "studio/state-authority": "vex-geometry",
            "studio/last-visible-rewire-frame": 650,
        },
    })
    store.create("ideas", IDEA_ID, idea)
    store.create("proposals", PROPOSAL_ID, proposal)
    store.create("experiments", EXPERIMENT_ID, experiment)
    store.create("artifacts", ARTIFACT_ID, artifact)
    component = promote_artifact(
        store,
        root,
        ARTIFACT_ID,
        "behavior",
        "Corrects the truncated prepared schedule while preserving the accepted initialization and exact historical event/state prefix; rewiring now continues through the complete animation horizon.",
        supersedes_id=OLD_COMPONENT_ID,
    )
    old_component = store.read("components", OLD_COMPONENT_ID)
    store.update("components", OLD_COMPONENT_ID, {**old_component, "state": "superseded"})

    write_json(selection / "component.json", component)
    selection_record = {
        "selection_id": "selection_002",
        "study_id": "study-003-nonlocal-affinity-dance",
        "phase": "behavior",
        "state": "current",
        "component_id": component["id"],
        "supersedes_component_id": OLD_COMPONENT_ID,
        "artifact": artifact_relative,
        "sha256": artifact["sha256"],
        "correction_authorization_message_id": MESSAGE_ID,
    }
    write_json(selection / "selection.json", selection_record)
    old_selection_record = json.loads((old_selection / "selection.json").read_text(encoding="utf-8"))
    old_selection_record["state"] = "superseded"
    old_selection_record["superseded_by"] = "selection_002"
    write_json(old_selection / "selection.json", old_selection_record)

    look_source = {
        "id": component["id"],
        "component_kind": "behavior",
        "state": "promoted",
        "content_hash": component["content_hash"],
        "cache_paths": cache_source["cache_paths"],
        "extensions": {
            "studio/cache-receipt": selection.joinpath("cache_sequence/receipt.json").relative_to(root).as_posix(),
            "studio/source-selection": selection.relative_to(root).as_posix(),
            "studio/frame-start": 201,
            "studio/frame-end": 650,
            "studio/frame-count": 450,
            "studio/point-count": 100000,
            "studio/required-point-attributes": "P,friend,enemy",
            "studio/stable-identity": "point-number",
            "studio/rewiring": "active deterministic schedule through the complete 960-step horizon; visible last change frame 650",
            "studio/supersedes-component": OLD_COMPONENT_ID,
        },
    }
    write_json(selection / "look-source.json", look_source)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    study_paths = (
        root / "studies/study_003_nonlocal-affinity-dance/00_study/study.json",
        root / "work/studio/studies/study-003-nonlocal-affinity-dance.json",
    )
    for study_path in study_paths:
        study = json.loads(study_path.read_text(encoding="utf-8"))
        study["approved_selection_ids"] = [
            component["id"] if value == OLD_COMPONENT_ID else value
            for value in study["approved_selection_ids"]
        ]
        extensions = dict(study["extensions"])
        extensions["studio/canonical-behavior-component"] = component["id"]
        extensions["studio/behavior-correction-message-id"] = MESSAGE_ID
        extensions["studio/look-cache-receipt"] = selection.joinpath("cache_sequence/receipt.json").relative_to(root).as_posix()
        extensions["studio/look-source"] = selection.joinpath("look-source.json").relative_to(root).as_posix()
        extensions["studio/look-cache-rewiring"] = "deterministic rewiring continues through frame 650 and complete 960-step horizon"
        study["extensions"] = extensions
        study["updated_at"] = now
        errors = validate_record("study", study)
        if errors:
            raise RuntimeError(f"invalid updated Study record: {'; '.join(errors)}")
        write_json(study_path, study)

    result = {
        "component_id": component["id"],
        "supersedes_id": OLD_COMPONENT_ID,
        "selection": selection.relative_to(root).as_posix(),
        "look_source": selection.joinpath("look-source.json").relative_to(root).as_posix(),
        "handoff": handoff.relative_to(root).as_posix(),
        "last_relationship_change_frame": audit["last_relationship_change_frame"],
    }
    print(json.dumps(result, sort_keys=True))
    return result


if __name__ == "__main__":
    run(Path.cwd())
