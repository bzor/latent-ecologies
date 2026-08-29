"""Canonical project workspaces independent from conversation sessions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .studio_schema import validate_record
from .studio_store import StudioStore


PHASES = ("seed", "directions", "behavior", "look", "specimen", "delivery")
STUDY_STATES = ("active", "closing", "archived")
PROJECT_ID_ALIASES = {
    "pilot-study-003": "study-003-nonlocal-affinity-dance",
}


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _validate(record: dict[str, Any]) -> None:
    errors = validate_record("study", record)
    if errors:
        raise ValueError("; ".join(errors))


def create_study(store: StudioStore, value: dict[str, Any], *, focus: bool = False) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("study must be an object")
    now = _timestamp()
    record: dict[str, Any] = {
        "schema_version": 1,
        "id": value.get("id"),
        "title": value.get("title"),
        "state": value.get("state", "active"),
        "current_phase": value.get("current_phase", "seed"),
        "intent": value.get("intent"),
        "approved_selection_ids": list(value.get("approved_selection_ids", [])),
        "unresolved_questions": list(value.get("unresolved_questions", [])),
        "blockers": list(value.get("blockers", [])),
        "recommended_next_action": value.get("recommended_next_action"),
        "created_at": now,
        "updated_at": now,
        "visibility": "private",
    }
    for optional in ("selected_branch_id", "idea_id", "specimen_id", "extensions"):
        if optional in value:
            record[optional] = value[optional]
    _validate(record)
    store.create("studies", str(record["id"]), record)
    if focus:
        focus_study(store, str(record["id"]))
    return record


def focus_study(store: StudioStore, study_id: str) -> dict[str, Any]:
    record = store.read("studies", study_id)
    _validate(record)
    pointer = {"study_id": study_id}
    try:
        store.update("study-state", "focused", pointer)
    except FileNotFoundError:
        store.create("study-state", "focused", pointer)
    return {**record, "is_focused": True}


def focused_study(store: StudioStore) -> dict[str, Any] | None:
    try:
        pointer = store.read("study-state", "focused")
    except FileNotFoundError:
        return None
    study_id = pointer.get("study_id")
    if not isinstance(study_id, str):
        raise ValueError("focused Study pointer is invalid")
    try:
        record = store.read("studies", study_id)
    except FileNotFoundError as error:
        raise ValueError("focused Study pointer references a missing Study") from error
    _validate(record)
    return {**record, "is_focused": True}


def list_studies(store: StudioStore) -> list[dict[str, Any]]:
    records, errors = store.list("studies")
    if errors:
        raise ValueError("; ".join(error["error"] for error in errors))
    focused = focused_study(store)
    focused_id = focused.get("id") if focused else None
    result: list[dict[str, Any]] = []
    for record in records:
        _validate(record)
        result.append({**record, "is_focused": record.get("id") == focused_id})
    return sorted(result, key=lambda item: (not item["is_focused"], str(item.get("updated_at", "")), str(item["id"])))


def _study_from_session(session: dict[str, Any]) -> dict[str, Any]:
    project_slug = session.get("project_slug")
    if not isinstance(project_slug, str) or not project_slug:
        raise ValueError("session project_slug is required for Study migration")
    state = {"open": "active", "completed": "archived", "archived": "archived"}.get(session.get("state"))
    if state is None:
        raise ValueError(f"unsupported session state for Study migration: {session.get('state')}")
    extensions = dict(session.get("extensions", {}))
    extensions["studio/migrated-from-session"] = session.get("id")
    record: dict[str, Any] = {
        "schema_version": 1,
        "id": PROJECT_ID_ALIASES.get(project_slug, project_slug),
        "title": session.get("title"),
        "state": state,
        "current_phase": session.get("current_phase"),
        "intent": session.get("intent"),
        "approved_selection_ids": list(session.get("approved_selection_ids", [])),
        "unresolved_questions": list(session.get("unresolved_questions", [])),
        "blockers": list(session.get("blockers", [])),
        "recommended_next_action": session.get("recommended_next_action"),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
        "visibility": "private",
        "extensions": extensions,
    }
    for optional in ("selected_branch_id", "idea_id", "specimen_id"):
        if optional in session:
            record[optional] = session[optional]
    _validate(record)
    return record


def migrate_sessions_to_studies(store: StudioStore, *, apply: bool = False) -> dict[str, Any]:
    """Project legacy sessions into Studies without modifying source records."""

    sessions, errors = store.list("sessions")
    if errors:
        raise ValueError("; ".join(error["error"] for error in errors))
    try:
        active_session_id = store.read("session-state", "active").get("session_id")
    except FileNotFoundError:
        active_session_id = None

    items: list[dict[str, Any]] = []
    focus_target: str | None = None
    for session in sessions:
        candidate = _study_from_session(session)
        study_id = str(candidate["id"])
        try:
            existing = store.read("studies", study_id)
        except FileNotFoundError:
            action = "create"
            if apply:
                store.create("studies", study_id, candidate)
        else:
            action = "exists" if existing == candidate else "conflict"
        items.append({
            "source_session_id": session.get("id"),
            "study_id": study_id,
            "action": action,
        })
        if session.get("id") == active_session_id and action != "conflict":
            focus_target = study_id

    if apply and focus_target is not None:
        focus_study(store, focus_target)
    return {
        "applied": apply,
        "items": items,
        "conflicts": [item for item in items if item["action"] == "conflict"],
    }
