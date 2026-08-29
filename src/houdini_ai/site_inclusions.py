"""Explicit local allowlist records for living public Studies."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from .activity_log import activity_id_for, timestamp
from .artifact_catalog import build_artifact_catalog
from .studio_commands import CommandContext, execute_idempotent
from .studio_schema import validate_record
from .studio_store import StudioStore


_WINDOWS_ABSOLUTE = re.compile(r"[A-Za-z]:[\\\\/]")
_POSIX_ABSOLUTE = re.compile(r"(?:^|\s)/(?:Users|home|tmp|var|etc)(?:/|\b)")


def _validate(record: dict[str, Any]) -> None:
    errors = validate_record("site-inclusion", record)
    if errors:
        raise ValueError("; ".join(errors))


def _public_text(value: object, label: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} must contain 1 to {maximum} characters")
    if _WINDOWS_ABSOLUTE.search(value) or _POSIX_ABSOLUTE.search(value):
        raise ValueError(f"{label} must not contain a local absolute path")
    return value.strip()


def _verified_catalog_entry(root: Path, artifact_id: str, study_id: str) -> dict[str, Any]:
    matches = [entry for entry in build_artifact_catalog(root) if entry.get("artifact_id") == artifact_id]
    if len(matches) != 1:
        raise ValueError("site inclusion requires one cataloged verified artifact")
    entry = matches[0]
    if entry.get("validation") != "verified":
        raise ValueError("site inclusion requires a verified artifact")
    if entry.get("project_id") != study_id:
        raise ValueError("artifact belongs to a different Study")
    return entry


def create_site_draft(
    store: StudioStore,
    root: Path,
    context: CommandContext,
    *,
    artifact_id: str,
    public_title: str,
    public_caption: str,
    role: str,
    section: str,
    order: int,
    alt_text: str,
) -> dict[str, Any]:
    root = Path(root).resolve()
    artifact = store.read("artifacts", artifact_id)
    artifact_errors = validate_record("artifact", artifact)
    if artifact_errors:
        raise ValueError("; ".join(artifact_errors))
    _verified_catalog_entry(root, artifact_id, context.study_id)

    title = _public_text(public_title, "public_title", 200)
    caption = _public_text(public_caption, "public_caption", 4000)
    accessible = _public_text(alt_text, "alt_text", 1000)
    inclusion_digest = hashlib.sha256(f"{context.study_id}\0{artifact_id}".encode("utf-8")).hexdigest()[:20]
    inclusion_id = f"site-inclusion-{inclusion_digest}"

    def operation() -> dict[str, object]:
        now = timestamp()
        record: dict[str, Any] = {
            "schema_version": 1,
            "id": inclusion_id,
            "study_id": context.study_id,
            "artifact_id": artifact_id,
            "source_sha256": artifact["sha256"],
            "state": "site-draft",
            "rights_status": "pending",
            "rights_rationale": "Publication rights review has not been recorded.",
            "public_title": title,
            "public_caption": caption,
            "role": role,
            "section": section,
            "order": order,
            "alt_text": accessible,
            "included_by_activity_id": activity_id_for(context.idempotency_key),
            "ever_public": False,
            "created_at": now,
            "updated_at": now,
            "visibility": "private",
        }
        _validate(record)
        return store.create("site-inclusions", inclusion_id, record)

    return execute_idempotent(
        store,
        context,
        "site.include",
        operation,
        summary=f"Prepare {artifact_id} for the public Study as site-draft.",
    )


def set_site_rights(
    store: StudioStore,
    context: CommandContext,
    inclusion_id: str,
    status: str,
    rationale: str,
) -> dict[str, Any]:
    if status not in {"pending", "cleared", "blocked"}:
        raise ValueError("unsupported site rights status")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("rights rationale must not be empty")

    def operation() -> dict[str, object]:
        latest = store.read("site-inclusions", inclusion_id)
        _validate(latest)
        if latest.get("study_id") != context.study_id:
            raise ValueError("site inclusion belongs to a different Study")
        updated = {
            **latest,
            "rights_status": status,
            "rights_rationale": rationale.strip(),
            "updated_at": timestamp(),
        }
        _validate(updated)
        return store.update("site-inclusions", inclusion_id, updated)

    return execute_idempotent(
        store,
        context,
        f"site.rights-{status}",
        operation,
        summary=f"Record {status} publication rights for {inclusion_id}.",
    )


_TRANSITIONS = {
    "private": frozenset(("site-draft",)),
    "site-draft": frozenset(("private", "site-live")),
    "site-live": frozenset(("archive-keep", "retired")),
    "archive-keep": frozenset(("retired",)),
    "retired": frozenset(),
}


def transition_site_inclusion(
    store: StudioStore,
    context: CommandContext,
    inclusion_id: str,
    state: str,
) -> dict[str, Any]:
    current = store.read("site-inclusions", inclusion_id)
    _validate(current)
    if current.get("study_id") != context.study_id:
        raise ValueError("site inclusion belongs to a different Study")

    def operation() -> dict[str, object]:
        latest = store.read("site-inclusions", inclusion_id)
        _validate(latest)
        source_state = str(latest["state"])
        if state not in _TRANSITIONS.get(source_state, frozenset()):
            raise ValueError(f"cannot transition site inclusion from {source_state} to {state}")
        if state in {"site-live", "archive-keep"}:
            if latest["rights_status"] != "cleared":
                raise ValueError("site-live requires recorded rights clearance")
            if context.actor != "kc":
                raise ValueError("site-live requires explicit KC confirmation")
        now = timestamp()
        updated: dict[str, Any] = {**latest, "state": state, "updated_at": now}
        if state == "site-live":
            updated["ever_public"] = True
            updated.setdefault("first_published_at", now)
        _validate(updated)
        return store.update("site-inclusions", inclusion_id, updated)

    return execute_idempotent(
        store,
        context,
        f"site.{state}",
        operation,
        summary=f"Transition {inclusion_id} to {state}.",
    )
