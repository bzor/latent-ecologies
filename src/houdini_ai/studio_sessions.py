"""Active and resumable creative-session lifecycle."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from .studio_schema import validate_record
from .studio_store import StudioStore


PHASES = ("seed", "directions", "behavior", "look", "specimen", "delivery")
_SESSION_ID = re.compile(r"session-[a-z0-9]+(?:-[a-z0-9]+)*")


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _validate(record: dict[str, Any]) -> None:
    errors = validate_record("session", record)
    if errors:
        raise ValueError("; ".join(errors))


def create_session(store: StudioStore, value: dict[str, Any], *, activate: bool = False) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("session must be an object")
    title = value.get("title")
    project_slug = value.get("project_slug")
    intent = value.get("intent")
    next_action = value.get("recommended_next_action")
    if not all(isinstance(item, str) and item.strip() for item in (title, project_slug, intent, next_action)):
        raise ValueError("session title, project_slug, intent, and recommended_next_action are required")
    now = _timestamp()
    record: dict[str, Any] = {
        "schema_version": 1,
        "id": f"session-{project_slug}-{uuid.uuid4().hex[:8]}",
        "title": title.strip(),
        "project_slug": project_slug,
        "state": "open",
        "current_phase": value.get("current_phase", "seed"),
        "intent": intent,
        "approved_selection_ids": list(value.get("approved_selection_ids", [])),
        "unresolved_questions": list(value.get("unresolved_questions", [])),
        "blockers": list(value.get("blockers", [])),
        "recommended_next_action": next_action,
        "created_at": now,
        "updated_at": now,
        "visibility": "private",
    }
    for optional in ("selected_branch_id", "idea_id", "specimen_id", "extensions"):
        if optional in value:
            record[optional] = value[optional]
    _validate(record)
    store.create("sessions", str(record["id"]), record)
    if activate:
        activate_session(store, str(record["id"]))
    return record


def activate_session(store: StudioStore, session_id: str) -> dict[str, Any]:
    if not _SESSION_ID.fullmatch(session_id):
        raise ValueError("invalid session_id")
    record = store.read("sessions", session_id)
    _validate(record)
    if record.get("state") != "open":
        raise ValueError("only open sessions can be activated")
    pointer = {"session_id": session_id}
    try:
        store.update("session-state", "active", pointer)
    except FileNotFoundError:
        store.create("session-state", "active", pointer)
    return {**record, "is_active": True}


def active_session(store: StudioStore) -> dict[str, Any] | None:
    try:
        pointer = store.read("session-state", "active")
    except FileNotFoundError:
        return None
    session_id = pointer.get("session_id")
    if not isinstance(session_id, str) or not _SESSION_ID.fullmatch(session_id):
        raise ValueError("active session pointer is invalid")
    try:
        record = store.read("sessions", session_id)
    except FileNotFoundError as error:
        raise ValueError("active session pointer references a missing session") from error
    _validate(record)
    if record.get("state") != "open":
        raise ValueError("active session must remain open")
    return {**record, "is_active": True}


def list_sessions(store: StudioStore) -> list[dict[str, Any]]:
    records, errors = store.list("sessions")
    if errors:
        raise ValueError("; ".join(error["error"] for error in errors))
    active = active_session(store)
    active_id = active.get("id") if active else None
    result: list[dict[str, Any]] = []
    for record in records:
        _validate(record)
        result.append({**record, "is_active": record.get("id") == active_id})
    return sorted(result, key=lambda item: (not item["is_active"], str(item.get("updated_at", "")), str(item["id"])), reverse=False)


def update_session(store: StudioStore, session_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    if not _SESSION_ID.fullmatch(session_id):
        raise ValueError("invalid session_id")
    if not isinstance(changes, dict) or not changes:
        raise ValueError("session update must be a non-empty object")
    allowed = {
        "current_phase", "intent", "selected_branch_id", "approved_selection_ids",
        "unresolved_questions", "blockers", "recommended_next_action", "idea_id", "specimen_id",
    }
    unknown = set(changes) - allowed
    if unknown:
        raise ValueError(f"session update contains unsupported fields: {', '.join(sorted(unknown))}")
    current = store.read("sessions", session_id)
    updated = {**current, **changes, "updated_at": _timestamp()}
    _validate(updated)
    store.update("sessions", session_id, updated)
    active = active_session(store)
    return {**updated, "is_active": bool(active and active.get("id") == session_id)}


def ensure_scar_tissue_session(store: StudioStore, specimen: dict[str, Any]) -> dict[str, Any]:
    """Create or refresh the truthful golden-run session without stealing focus."""

    if scar_tissue_behavior_reset_active(store):
        raise ValueError("Scar Tissue is reset to Behavior; the archived golden-run delivery session cannot be reactivated")

    session_id = "session-scar-tissue-golden-run"
    progress = specimen.get("extensions", {}).get("studio/render-progress", {})
    next_frame = progress.get("next_frame")
    complete = progress.get("complete") is True
    now = _timestamp()
    try:
        existing = store.read("sessions", session_id)
    except FileNotFoundError:
        existing = None
    record: dict[str, Any] = {
        "schema_version": 1,
        "id": session_id,
        "title": "Directional refractory path memory | Golden run",
        "project_slug": "scar-tissue",
        "state": "open",
        "current_phase": "delivery",
        "intent": "Complete and validate the first end-to-end proving run of the Computational Studio without altering its approved creative components.",
        "approved_selection_ids": list(specimen["component_ids"]),
        "unresolved_questions": ["Should the final specimen use designed sound or intentional silence?"],
        "blockers": [] if complete else [
            f"Portrait render is incomplete: {progress.get('contiguous_frames', 0)}/{progress.get('expected_frames', 1260)} contiguous frames."
        ],
        "recommended_next_action": (
            "Validate the complete sequence, encode the 28-second portrait master, review it, and decide sound or silence."
            if complete
            else f"Resume the portrait render at frame {next_frame}, then validate the complete sequence."
        ),
        "specimen_id": str(specimen["id"]),
        "created_at": existing.get("created_at", now) if existing else now,
        "updated_at": now,
        "visibility": "private",
        "extensions": {"studio/lineage-role": "golden-reference"},
    }
    if existing:
        for field in ("intent", "unresolved_questions"):
            if field in existing:
                record[field] = existing[field]
        _validate(record)
        store.update("sessions", session_id, record)
    else:
        _validate(record)
        store.create("sessions", session_id, record)
    if active_session(store) is None:
        activate_session(store, session_id)
    return record


def scar_tissue_behavior_reset_active(store: StudioStore) -> bool:
    """Return whether the numbered Scar Tissue Study retired its old golden run."""

    try:
        study = store.read("studies", "study-002-scar-tissue")
    except FileNotFoundError:
        return False
    extensions = study.get("extensions", {})
    return (
        study.get("state") == "active"
        and study.get("current_phase") == "behavior"
        and isinstance(extensions, dict)
        and extensions.get("studio/reset-from-study-id") == "scar-tissue"
    )
