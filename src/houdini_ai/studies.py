"""Canonical project workspaces independent from conversation sessions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .studio_schema import validate_record
from .studio_store import StudioStore


PHASES = ("seed", "directions", "behavior", "look", "specimen", "delivery")
STUDY_STATES = ("active", "closing", "archived")

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
