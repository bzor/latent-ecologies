"""Idempotent command execution shared by Discord, CLI, and local adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .activity_log import activity_id_for, read_activity, timestamp, validate_activity
from .studio_schema import validate_record
from .studio_store import StudioStore


@dataclass(frozen=True)
class CommandContext:
    actor: str
    origin: str
    source_ref: str
    idempotency_key: str
    study_id: str | None = None
    seed_id: str | None = None


def _target(context: CommandContext) -> tuple[str, str, str]:
    values = [("study_id", "studies", context.study_id), ("seed_id", "ideas", context.seed_id)]
    selected = [(field, collection, value) for field, collection, value in values if value is not None]
    if len(selected) != 1:
        raise ValueError("command context requires exactly one study_id or seed_id")
    field, collection, value = selected[0]
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must not be empty")
    return field, collection, value


def _assert_same_command(activity: dict[str, Any], context: CommandContext, action: str) -> None:
    target_field, _, target_id = _target(context)
    expected = {
        target_field: target_id,
        "actor": context.actor,
        "origin": context.origin,
        "source_ref": context.source_ref,
        "idempotency_key": context.idempotency_key,
        "action": action,
    }
    mismatches = [key for key, value in expected.items() if activity.get(key) != value]
    if mismatches:
        raise ValueError("idempotency key is already reserved for a different command")


def execute_idempotent(
    store: StudioStore,
    context: CommandContext,
    action: str,
    operation: Callable[[], dict[str, object]],
    *,
    summary: str,
) -> dict[str, Any]:
    target_field, collection, target_id = _target(context)
    target = store.read(collection, target_id)
    target_kind = "study" if target_field == "study_id" else "idea"
    target_errors = validate_record(target_kind, target)
    if target_errors:
        raise ValueError("; ".join(target_errors))

    activity_id = activity_id_for(context.idempotency_key)
    try:
        existing = read_activity(store, context.idempotency_key)
    except FileNotFoundError:
        existing = None
    if existing is not None:
        _assert_same_command(existing, context, action)
        if existing["state"] == "completed":
            return {"activity": existing, "result": existing["result"], "replayed": True}
        raise ValueError(f"idempotent activity is {existing['state']}; recover it before retrying")

    now = timestamp()
    activity: dict[str, Any] = {
        "schema_version": 1,
        "id": activity_id,
        target_field: target_id,
        "action": action,
        "actor": context.actor,
        "origin": context.origin,
        "idempotency_key": context.idempotency_key,
        "source_ref": context.source_ref,
        "state": "pending",
        "result_refs": [],
        "summary": summary,
        "created_at": now,
        "updated_at": now,
        "visibility": "private",
    }
    validate_activity(activity)
    try:
        store.create("activities", activity_id, activity)
    except FileExistsError:
        raced = read_activity(store, context.idempotency_key)
        _assert_same_command(raced, context, action)
        if raced["state"] == "completed":
            return {"activity": raced, "result": raced["result"], "replayed": True}
        raise ValueError(f"idempotent activity is {raced['state']}; recover it before retrying")

    try:
        result = operation()
        if not isinstance(result, dict):
            raise ValueError("command operation must return an object")
        result_id = result.get("id")
        if not isinstance(result_id, str) or not result_id:
            raise ValueError("command result must contain a record id")
        completed = {
            **activity,
            "state": "completed",
            "result_refs": [result_id],
            "result": result,
            "updated_at": timestamp(),
        }
        validate_activity(completed)
        store.update("activities", activity_id, completed)
        return {"activity": completed, "result": result, "replayed": False}
    except Exception as error:
        failed = {
            **activity,
            "state": "failed",
            "error": f"{type(error).__name__}: {error}"[:2000],
            "updated_at": timestamp(),
        }
        validate_activity(failed)
        store.update("activities", activity_id, failed)
        raise
