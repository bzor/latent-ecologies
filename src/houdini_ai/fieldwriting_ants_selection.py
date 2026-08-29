from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Mapping

from houdini_ai.fieldwriting_ants import DirectionResult, summarize_direction
from houdini_ai.promotions import promote_artifact
from houdini_ai.studio_store import StudioStore

STUDY_ID = "study-004-three-dimensional-fieldwriting-ants"
VAULT_NAME = "study_004_three-dimensional-fieldwriting-ants"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot_payload(result: DirectionResult) -> dict[str, object]:
    summary = summarize_direction(result)
    return {
        "schema_version": 1,
        "kind": "fieldwriting-ants-behavior-cache",
        "system": result.system,
        "steps": result.steps,
        "state_sha256": summary["state_sha256"],
        "semantic_state_contract": "Scalar field states are behavioral indices independent of palette or material.",
        "metrics": result.metrics,
        "summary": summary,
        "trajectories": result.trajectories,
        "final_field": result.field,
        "snapshots": [
            {
                "step": snapshot.step,
                "agent_positions": snapshot.agent_positions,
                "agent_frames": snapshot.agent_frames,
                "field": snapshot.field,
                "event_positions": snapshot.event_positions,
            }
            for snapshot in result.snapshots
        ],
    }


def freeze_fieldwriting_behavior(
    root: Path,
    *,
    selection_id: str,
    branch_id: str,
    result: DirectionResult,
    source_media: Mapping[str, Path],
    rationale: str,
    authorization_message_id: str,
) -> dict[str, object]:
    root = Path(root).resolve()
    slug = selection_id.removeprefix("selection-")
    handoff_directory = root / "work" / "studio" / "handoffs" / f"study-004-{slug}"
    selected_directory = (
        root
        / "studies"
        / VAULT_NAME
        / "01_behavior"
        / "03_selected"
        / selection_id
    )
    if handoff_directory.exists() or selected_directory.exists():
        raise FileExistsError(f"selection already exists: {selection_id}")
    for name, source in source_media.items():
        if Path(name).name != name or not Path(source).is_file():
            raise ValueError(f"invalid source media: {name}")

    handoff_directory.mkdir(parents=True)
    cache_payload = _snapshot_payload(result)
    handoff_path = handoff_directory / "behavior-handoff.json"
    handoff_path.write_text(json.dumps(cache_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    idea_id = f"idea-{slug}"
    proposal_id = f"proposal-{slug}"
    experiment_id = f"experiment-{slug}"
    artifact_id = f"artifact-{slug}"
    relative_handoff = handoff_path.relative_to(root).as_posix()
    store = StudioStore(root)
    store.create(
        "ideas",
        idea_id,
        {
            "schema_version": 1,
            "id": idea_id,
            "track": "behavior",
            "state": "proposed",
            "title": branch_id,
            "parent_idea_id": "idea-three-dimensional-fieldwriting-ants-617e0720",
            "visibility": "private",
        },
    )
    store.create(
        "proposals",
        proposal_id,
        {
            "schema_version": 1,
            "id": proposal_id,
            "idea_id": idea_id,
            "track": "behavior",
            "state": "approved",
            "mechanism": branch_id,
            "visibility": "private",
        },
    )
    store.create(
        "experiments",
        experiment_id,
        {
            "schema_version": 1,
            "id": experiment_id,
            "proposal_id": proposal_id,
            "track": "behavior",
            "state": "completed",
            "parameters": result.metrics,
            "visibility": "private",
        },
    )
    artifact = {
        "schema_version": 1,
        "id": artifact_id,
        "experiment_id": experiment_id,
        "track": "behavior",
        "state": "verified",
        "path": relative_handoff,
        "sha256": "sha256:" + _sha256(handoff_path),
        "verified": True,
        "visibility": "private",
    }
    store.create("artifacts", artifact_id, artifact)
    component = promote_artifact(store, root, artifact_id, "behavior", rationale)

    selected_directory.mkdir(parents=True)
    selected_cache = selected_directory / "behavior-cache.json"
    shutil.copy2(handoff_path, selected_cache)
    copied_media: dict[str, Path] = {}
    for name, source in source_media.items():
        destination = selected_directory / name
        shutil.copy2(source, destination)
        copied_media[name] = destination

    component_path = selected_directory / "component.json"
    component_path.write_text(json.dumps(component, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifact_path = selected_directory / "artifact.json"
    artifact_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    proposal = store.read("proposals", proposal_id)
    experiment = store.read("experiments", experiment_id)
    (selected_directory / "proposal.json").write_text(
        json.dumps(proposal, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (selected_directory / "experiment.json").write_text(
        json.dumps(experiment, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    selected_cache_relative = selected_cache.relative_to(root).as_posix()
    look_source = {
        "schema_version": 1,
        "id": component["id"],
        "component_kind": "behavior",
        "state": "promoted",
        "content_hash": component["content_hash"],
        "cache_paths": [selected_cache_relative],
        "extensions": {
            "studio/source-selection": selected_directory.relative_to(root).as_posix(),
            "studio/branch": branch_id,
            "studio/state-sha256": cache_payload["state_sha256"],
            "studio/cache-format": "fieldwriting-ants-behavior-cache-json-v1",
        },
    }
    (selected_directory / "look-source.json").write_text(
        json.dumps(look_source, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    selection = {
        "schema_version": 1,
        "selection_id": selection_id,
        "study_id": STUDY_ID,
        "phase": "behavior",
        "branch_id": branch_id,
        "state": "promoted-behavior",
        "component_id": component["id"],
        "source_artifact_id": artifact_id,
        "artifact": relative_handoff,
        "sha256": artifact["sha256"],
        "rationale": rationale,
        "authorization_message_id": authorization_message_id,
    }
    (selected_directory / "selection.json").write_text(
        json.dumps(selection, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    receipt_files = [
        selected_cache,
        component_path,
        artifact_path,
        selected_directory / "proposal.json",
        selected_directory / "experiment.json",
        selected_directory / "look-source.json",
        selected_directory / "selection.json",
        *copied_media.values(),
    ]
    receipt = {
        "schema_version": 1,
        "selection_id": selection_id,
        "files": {
            path.name: {
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in receipt_files
        },
    }
    receipt_path = selected_directory / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "selection_directory": selected_directory,
        "selection": selection,
        "component": component,
        "artifact": artifact,
        "receipt": receipt_path,
    }
