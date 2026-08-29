"""Append-only identities and validation helpers for activity receipts."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from .studio_schema import validate_record
from .studio_store import StudioStore


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def activity_id_for(idempotency_key: str) -> str:
    if not isinstance(idempotency_key, str) or not idempotency_key:
        raise ValueError("idempotency key must not be empty")
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:20]
    return f"activity-{digest}"


def validate_activity(record: dict[str, Any]) -> None:
    errors = validate_record("activity", record)
    if errors:
        raise ValueError("; ".join(errors))


def read_activity(store: StudioStore, idempotency_key: str) -> dict[str, Any]:
    record = store.read("activities", activity_id_for(idempotency_key))
    validate_activity(record)
    return record
