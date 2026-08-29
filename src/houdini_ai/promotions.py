"""Immutable component promotion from verified local artifacts."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from .lineage import LineageError, promotion_chain, stable_content_hash
from .studio_schema import validate_record
from .studio_store import StudioStore


class PromotionError(ValueError):
    pass


def _verified_artifact(store: StudioStore, root: Path, artifact_id: str) -> dict[str, object]:
    try:
        artifact = store.read("artifacts", artifact_id)
    except FileNotFoundError as error:
        raise PromotionError("source artifact does not exist") from error
    relative = artifact.get("path")
    if isinstance(relative, str):
        relative_path = Path(relative.replace("\\", "/"))
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise PromotionError("source artifact path must be canonical")
    errors = validate_record("artifact", artifact)
    if errors:
        raise PromotionError("invalid source artifact: " + "; ".join(errors))
    expected = artifact.get("sha256")
    if not isinstance(relative, str) or not isinstance(expected, str):
        raise PromotionError("source artifact requires path and sha256")
    relative_path = Path(relative.replace("\\", "/"))
    parts = relative_path.parts
    job_output = len(parts) >= 5 and parts[0:2] == ("work", "jobs") and parts[3] in {"review", "render", "package", "lookdev", "publish", "cache"}
    handoff_output = len(parts) >= 5 and parts[0:3] == ("work", "studio", "handoffs")
    study_output = (
        len(parts) >= 5
        and parts[0] == "studies"
        and parts[1].startswith("study_")
        and (
            (parts[2] == "01_behavior" and parts[3] in {"02_review", "03_selected"})
            or parts[2] in {"03_specimen", "04_delivery"}
        )
    )
    if not (job_output or handoff_output or study_output):
        raise PromotionError("source artifact path must name a canonical artifact output")
    path = (Path(root).resolve() / relative).resolve()
    try:
        path.relative_to(Path(root).resolve())
    except ValueError as error:
        raise PromotionError("source artifact escapes project root") from error
    if not path.is_file():
        raise PromotionError("source artifact does not exist")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected.removeprefix("sha256:"):
        raise PromotionError("source artifact checksum mismatch")
    return artifact


def promote_artifact(
    store: StudioStore,
    root: Path,
    artifact_id: str,
    component_kind: str,
    rationale: str,
    *,
    supersedes_id: str | None = None,
) -> dict[str, object]:
    if not rationale or not rationale.strip():
        raise PromotionError("KC rationale is required")
    artifact = _verified_artifact(store, root, artifact_id)
    try:
        _, _, experiment = promotion_chain(store, artifact)
    except LineageError as error:
        raise PromotionError(str(error)) from error
    experiment_id = str(artifact["experiment_id"])
    compatible_kinds = {
        "behavior": "behavior",
        "look": "look",
        "palette": "chromatic",
        "shot": "cinematography",
    }
    if compatible_kinds.get(component_kind) != experiment.get("track"):
        raise PromotionError("component kind is incompatible with lineage track")
    if supersedes_id is not None:
        superseded = store.read("components", supersedes_id)
        if superseded.get("component_kind") != component_kind or superseded.get("track") != experiment.get("track"):
            raise PromotionError("superseded component is incompatible with promotion")
    payload = {
        "component_kind": component_kind,
        "source_experiment_id": experiment_id,
        "source_artifact_ref": artifact["path"],
        "source_sha256": artifact["sha256"],
        "rationale": rationale,
    }
    record: dict[str, object] = {
        "schema_version": 1,
        "id": f"component-{component_kind}-{uuid.uuid4().hex[:12]}",
        "track": experiment["track"],
        "state": "promoted",
        "component_kind": component_kind,
        "source_experiment_id": experiment_id,
        "source_artifact_ref": artifact["path"],
        "rationale": rationale,
        "content_hash": stable_content_hash(payload),
        "visibility": "private",
    }
    if supersedes_id is not None:
        record["supersedes_id"] = supersedes_id
    errors = validate_record("component", record)
    if errors:
        raise PromotionError("; ".join(errors))
    store.create("components", str(record["id"]), record)
    return record
