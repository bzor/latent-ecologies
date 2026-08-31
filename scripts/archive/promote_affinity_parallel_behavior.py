"""Package and idempotently promote Study 003 shallow-3D Parallel Behavior."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from houdini_ai.promotions import promote_artifact
from houdini_ai.studio_commands import CommandContext, execute_idempotent
from houdini_ai.studio_schema import validate_record
from houdini_ai.studio_store import StudioStore

STUDY_ID = "study-003-nonlocal-affinity-dance"
IDEA_ID = "idea-study-003-affinity-parallel-behavior-v1"
PROPOSAL_ID = "proposal-study-003-affinity-parallel-endurance-v1"
EXPERIMENT_ID = "experiment-study-003-affinity-parallel-endurance-v1"
ARTIFACT_ID = "artifact-study-003-affinity-parallel-endurance-v1"
APPROVAL_MESSAGE_ID = "1538666235619704842"
ENDURANCE_APPROVAL_MESSAGE_ID = "1538663472307642562"


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(kind: str, value: dict[str, Any]) -> None:
    errors = validate_record(kind, value)
    if errors:
        raise ValueError(f"invalid {kind}: " + "; ".join(errors))


def create_or_match(store: StudioStore, collection: str, kind: str, record_id: str, value: dict[str, Any]) -> None:
    validate(kind, value)
    try:
        existing = store.read(collection, record_id)
    except FileNotFoundError:
        store.create(collection, record_id, value)
        return
    if existing != value:
        raise ValueError(f"existing {record_id} conflicts with canonical promotion record")


def package_handoff(root: Path) -> tuple[Path, dict[str, Any]]:
    endurance = root / "work/studies/study-003-nonlocal-affinity-dance/20-behavior/endurance/parallel-cohort-100k-960-v1"
    handoff = root / "work/studio/handoffs/study-003-affinity-shallow3d-parallel-v1"
    sources = {
        "behavior-review-straight-on.mp4": endurance / "review-straight-on/parallel-cohort-100k-960-endurance-straight-on.mp4",
        "behavior-review-isometric.mp4": endurance / "review/parallel-cohort-100k-960-endurance.mp4",
        "endurance-receipt.json": endurance / "endurance-receipt.json",
        "metrics.json": endurance / "simulation/metrics.json",
        "review-sample.json": endurance / "simulation/review.json",
        "final-state.0960.bgeo.sc": endurance / "simulation/cache/state.0960.bgeo.sc",
        "nonlocal-affinity-3d.hiplc": endurance / "simulation/nonlocal-affinity-3d.hiplc",
        "prepared-parallel-cohort.json": root / "work/studies/study-003-nonlocal-affinity-dance/20-behavior/comparisons/affinity-cohort-100k-v1/receipts/tight-swirls-parallel-cohort-100k.json",
    }
    missing = [str(path) for path in sources.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing promotion source: " + ", ".join(missing))
    handoff.mkdir(parents=True, exist_ok=True)
    files: dict[str, dict[str, Any]] = {}
    for name, source in sources.items():
        target = handoff / name
        if target.exists() and sha(target) != sha(source):
            raise ValueError(f"existing handoff file conflicts: {target}")
        if not target.exists():
            shutil.copy2(source, target)
        files[name] = {"sha256": sha(target), "bytes": target.stat().st_size}
    manifest = {
        "schema_version": 1,
        "study_id": STUDY_ID,
        "component_kind": "behavior",
        "canonical_branch": "shallow-3D Parallel cohorts",
        "population_count": 100000,
        "genuine_steps": 960,
        "state_authority": "vex-geometry",
        "review_projection": "straight-on XY",
        "approval_message_id": APPROVAL_MESSAGE_ID,
        "endurance_approval_message_id": ENDURANCE_APPROVAL_MESSAGE_ID,
        "held_siblings": ["Mixed cohorts", "Neighbor braid"],
        "look_status": "not-started",
        "publication_status": "not-authorized",
        "files": files,
    }
    manifest_path = handoff / "manifest.json"
    encoded = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if manifest_path.exists() and manifest_path.read_text(encoding="utf-8") != encoded:
        raise ValueError("existing handoff manifest conflicts")
    manifest_path.write_text(encoded, encoding="utf-8")
    return handoff, manifest


def run(root: Path) -> dict[str, Any]:
    root = root.resolve()
    store = StudioStore(root)
    handoff, manifest = package_handoff(root)
    video = handoff / "behavior-review-straight-on.mp4"
    receipt = json.loads((handoff / "endurance-receipt.json").read_text(encoding="utf-8"))
    if receipt.get("topology_retained") is not True or receipt.get("vex_errors") != [] or receipt.get("vex_cook_count") != 960:
        raise ValueError("endurance receipt does not pass the Behavior promotion gate")
    now = timestamp()
    idea = {
        "schema_version": 1,
        "id": IDEA_ID,
        "title": "Shallow-3D Parallel cohorts",
        "raw_text": "Promote the identity-preserving 100k shallow-3D Parallel cohort lift as Study 003's canonical Behavior while retaining Mixed and Neighbor as siblings.",
        "short_summary": "Canonical Study 003 Behavior candidate selected after a verified 960-step endurance check.",
        "track": "behavior",
        "state": "proposed",
        "visibility": "private",
        "created_at": now,
        "updated_at": now,
        "tags": ["nonlocal-affinity", "parallel-cohorts", "shallow-3d"],
        "constraints": ["Preserve the exact Canvas anchor identity and ordered events.", "Do not alter Behavior during Look Development."],
        "extensions": {"studio/parent-study": STUDY_ID},
    }
    proposal = {
        "schema_version": 1,
        "id": PROPOSAL_ID,
        "idea_id": IDEA_ID,
        "direction_ids": ["direction-fbe9c254e174"],
        "track": "behavior",
        "state": "approved",
        "question": "Does shallow-3D Parallel retain topology and continue reorganizing through a 960-step endurance horizon?",
        "hypothesis": "Parallel routing will retain the lifted graph while surviving collapse and re-expansion without settling into a static point mass.",
        "mechanism": "Run the exact 100k shallow-3D Parallel prepared receipt for 960 VEX-authoritative synchronous steps and review a 20k stratified XY sample.",
        "outputs": ["960-step VEX-authoritative cache", "straight-on XY motion review", "verified topology and endurance receipt"],
        "stop_conditions": ["relationship digest mismatch", "VEX error", "non-finite geometry", "late motion convergence"],
        "runner": "behavior.nonlocal_affinity_3d",
        "cost_tier": "study",
        "visibility": "private",
        "extensions": {"studio/approval-message-id": ENDURANCE_APPROVAL_MESSAGE_ID},
    }
    experiment = {
        "schema_version": 1,
        "id": EXPERIMENT_ID,
        "proposal_id": PROPOSAL_ID,
        "track": "behavior",
        "state": "completed",
        "runner": "behavior.nonlocal_affinity_3d",
        "parameters": {
            "branch": "parallel",
            "dimensions": 3,
            "depth": "shallow",
            "agent_count": 100000,
            "steps": 960,
            "review_count": 20000,
            "review_interval": 4,
        },
        "visibility": "private",
        "extensions": {
            "studio/endurance-receipt": "work/studio/handoffs/study-003-affinity-shallow3d-parallel-v1/endurance-receipt.json",
            "studio/topology-retained": True,
        },
    }
    artifact = {
        "schema_version": 1,
        "id": ARTIFACT_ID,
        "experiment_id": EXPERIMENT_ID,
        "track": "behavior",
        "state": "verified",
        "path": "work/studio/handoffs/study-003-affinity-shallow3d-parallel-v1/behavior-review-straight-on.mp4",
        "sha256": "sha256:" + sha(video),
        "verified": True,
        "visibility": "private",
        "decision": "promote",
        "decision_note": "KC approved promotion of shallow-3D Parallel after straight-on review.",
        "extensions": {
            "studio/manifest": "work/studio/handoffs/study-003-affinity-shallow3d-parallel-v1/manifest.json",
            "studio/state-authority": "vex-geometry",
            "studio/topology-retained": manifest["state_authority"] == "vex-geometry" and receipt["topology_retained"],
            "studio/approval-message-id": APPROVAL_MESSAGE_ID,
        },
    }
    for kind, value in (("idea", idea), ("proposal", proposal), ("experiment", experiment), ("artifact", artifact)):
        validate(kind, value)
    study = store.read("studies", STUDY_ID)

    def operation() -> dict[str, object]:
        create_or_match(store, "ideas", "idea", IDEA_ID, idea)
        create_or_match(store, "proposals", "proposal", PROPOSAL_ID, proposal)
        create_or_match(store, "experiments", "experiment", EXPERIMENT_ID, experiment)
        create_or_match(store, "artifacts", "artifact", ARTIFACT_ID, artifact)
        component = promote_artifact(
            store,
            root,
            ARTIFACT_ID,
            "behavior",
            "KC approved shallow-3D Parallel cohorts as Study 003's canonical Behavior after the straight-on 960-step endurance review; Mixed remains an exploratory sibling and Neighbor remains held evidence.",
        )
        extensions = dict(study.get("extensions", {}))
        extensions.update({
            "studio/canonical-behavior-component": component["id"],
            "studio/canonical-behavior-branch": "shallow-3D Parallel cohorts",
            "studio/behavior-promotion-message-id": APPROVAL_MESSAGE_ID,
            "studio/held-behavior-siblings": "Mixed cohorts; Neighbor braid",
        })
        approved = list(study.get("approved_selection_ids", []))
        if component["id"] not in approved:
            approved.append(component["id"])
        updated_study = {
            **study,
            "current_phase": "look",
            "approved_selection_ids": approved,
            "unresolved_questions": [],
            "recommended_next_action": "Run a Look Direction Workshop against the frozen shallow-3D Parallel Behavior component.",
            "updated_at": timestamp(),
            "extensions": extensions,
        }
        validate("study", updated_study)
        store.update("studies", STUDY_ID, updated_study)
        return component

    context = CommandContext(
        actor="kc",
        origin="discord",
        source_ref=f"discord-message:{APPROVAL_MESSAGE_ID}",
        idempotency_key=f"discord:{APPROVAL_MESSAGE_ID}:study.promote-behavior",
        study_id=STUDY_ID,
    )
    result = execute_idempotent(
        store,
        context,
        "study.promote-behavior",
        operation,
        summary="Promote shallow-3D Parallel cohorts as Study 003 canonical Behavior.",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    run(Path.cwd())
