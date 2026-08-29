"""Explicit publication lifecycle for public Seed Bank entries."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from .studio_schema import validate_record
from .studio_store import StudioStore


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _validate(kind: str, record: dict[str, Any]) -> None:
    errors = validate_record(kind, record)
    if errors:
        raise ValueError("; ".join(errors))


def _complete_seed(store: StudioStore, seed_id: str) -> dict[str, Any]:
    seed = store.read("ideas", seed_id)
    _validate("idea", seed)
    missing = [field for field in ("short_summary", "long_summary", "reference_links", "tags") if field not in seed]
    if missing:
        raise ValueError(f"Seed is incomplete for publication: {', '.join(missing)}")
    return seed


def create_seed_site_draft(store: StudioStore, seed_id: str, *, source_ref: str) -> dict[str, Any]:
    _complete_seed(store, seed_id)
    digest = hashlib.sha256(seed_id.encode("utf-8")).hexdigest()[:20]
    inclusion_id = f"seed-inclusion-{digest}"
    try:
        existing = store.read("seed-inclusions", inclusion_id)
    except FileNotFoundError:
        existing = None
    if existing is not None:
        _validate("seed-inclusion", existing)
        if existing["seed_id"] != seed_id:
            raise ValueError("Seed inclusion identity collision")
        return existing
    now = _timestamp()
    record = {
        "schema_version": 1,
        "id": inclusion_id,
        "seed_id": seed_id,
        "state": "site-draft",
        "rights_status": "pending",
        "rights_rationale": "Publication rights review has not been recorded.",
        "source_ref": source_ref,
        "ever_public": False,
        "created_at": now,
        "updated_at": now,
        "visibility": "private",
    }
    _validate("seed-inclusion", record)
    return store.create("seed-inclusions", inclusion_id, record)


def set_seed_rights(store: StudioStore, inclusion_id: str, status: str, rationale: str) -> dict[str, Any]:
    if status not in {"pending", "cleared", "blocked"}:
        raise ValueError("unsupported Seed rights status")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("rights rationale must not be empty")
    record = store.read("seed-inclusions", inclusion_id)
    _validate("seed-inclusion", record)
    updated = {**record, "rights_status": status, "rights_rationale": rationale.strip(), "updated_at": _timestamp()}
    _validate("seed-inclusion", updated)
    return store.update("seed-inclusions", inclusion_id, updated)


_TRANSITIONS = {
    "private": frozenset(("site-draft",)),
    "site-draft": frozenset(("private", "site-live")),
    "site-live": frozenset(("retired",)),
    "retired": frozenset(),
}


def transition_seed_publication(
    store: StudioStore,
    inclusion_id: str,
    target: str,
    *,
    actor: str,
    source_ref: str,
) -> dict[str, Any]:
    record = store.read("seed-inclusions", inclusion_id)
    _validate("seed-inclusion", record)
    source = str(record["state"])
    if target not in _TRANSITIONS.get(source, frozenset()):
        raise ValueError(f"cannot transition Seed inclusion from {source} to {target}")
    if target == "site-live":
        if record["rights_status"] != "cleared":
            raise ValueError("site-live requires recorded rights clearance")
        if actor != "kc":
            raise ValueError("site-live requires explicit KC confirmation")
    now = _timestamp()
    updated = {**record, "state": target, "updated_at": now, "live_source_ref": source_ref}
    if target == "site-live":
        updated["ever_public"] = True
        updated.setdefault("first_published_at", now)
    _validate("seed-inclusion", updated)
    return store.update("seed-inclusions", inclusion_id, updated)
