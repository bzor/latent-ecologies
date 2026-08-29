"""Private mappings from external conversation scopes to canonical Seeds or Studies."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .studio_schema import validate_record
from .studio_store import StudioStore


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _validate(record: dict[str, Any]) -> None:
    errors = validate_record("conversation-binding", record)
    if errors:
        raise ValueError("; ".join(errors))


def _active_bindings(store: StudioStore) -> list[dict[str, Any]]:
    records, errors = store.list("conversation-bindings")
    if errors:
        raise ValueError("; ".join(error["error"] for error in errors))
    for record in records:
        _validate(record)
    return [record for record in records if record.get("state") == "active"]


def bind_discord_thread(
    store: StudioStore,
    *,
    study_id: str | None = None,
    seed_id: str | None = None,
    guild_id: str,
    parent_channel_id: str,
    thread_id: str,
) -> dict[str, Any]:
    if (study_id is None) == (seed_id is None):
        raise ValueError("Discord binding requires exactly one of study_id or seed_id")
    if study_id is not None:
        target = store.read("studies", study_id)
        target_errors = validate_record("study", target)
        target_value = {"study_id": study_id}
    else:
        target = store.read("ideas", str(seed_id))
        target_errors = validate_record("idea", target)
        target_value = {"seed_id": seed_id}
    if target_errors:
        raise ValueError("; ".join(target_errors))

    values = {
        **target_value,
        "guild_id": guild_id,
        "parent_channel_id": parent_channel_id,
        "thread_id": thread_id,
    }
    for existing in _active_bindings(store):
        same_thread = existing.get("thread_id") == thread_id
        same_target = all(existing.get(key) == value for key, value in target_value.items())
        if same_thread and same_target and all(existing.get(key) == value for key, value in values.items()):
            return existing
        if same_thread:
            raise ValueError("Discord thread is already bound to another Seed, Study, or scope")
        if same_target:
            raise ValueError("Seed or Study is already bound to another active Discord thread")

    now = _timestamp()
    record: dict[str, Any] = {
        "schema_version": 1,
        "id": f"binding-discord-{thread_id}",
        **values,
        "platform": "discord",
        "state": "active",
        "created_at": now,
        "updated_at": now,
        "visibility": "private",
    }
    _validate(record)
    return store.create("conversation-bindings", str(record["id"]), record)


def resolve_discord_thread(store: StudioStore, thread_id: str) -> dict[str, Any]:
    matches = [record for record in _active_bindings(store) if record.get("thread_id") == thread_id]
    if not matches:
        raise FileNotFoundError(f"active Discord binding does not exist: {thread_id}")
    if len(matches) > 1:
        raise ValueError(f"multiple active Discord bindings exist: {thread_id}")
    return matches[0]


def deactivate_binding(store: StudioStore, binding_id: str) -> dict[str, Any]:
    record = store.read("conversation-bindings", binding_id)
    _validate(record)
    if record.get("state") != "active":
        raise ValueError("only an active conversation binding can be deactivated")
    updated = {**record, "state": "inactive", "updated_at": _timestamp()}
    _validate(updated)
    return store.update("conversation-bindings", binding_id, updated)
