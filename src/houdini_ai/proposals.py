"""Creation and approval of bounded, non-executable proposals."""

from __future__ import annotations

import uuid
from collections.abc import Collection, Mapping
from typing import Any

from .studio_schema import validate_record
from .studio_store import StudioStore

_REQUIRED = ("question", "mechanism", "outputs", "stop_conditions", "runner", "cost_tier")
_OPTIONAL = ("hypothesis", "direction_ids", "extensions")


def create_proposal(
    store: StudioStore,
    idea_id: str,
    value: Mapping[str, Any],
    *,
    registered_runners: Collection[str],
) -> dict[str, Any]:
    idea = store.read("ideas", idea_id)
    missing = [field for field in _REQUIRED if field not in value]
    if missing:
        raise ValueError(f"missing proposal fields: {', '.join(missing)}")
    unknown = set(value) - set(_REQUIRED) - set(_OPTIONAL)
    if unknown:
        raise ValueError(f"unsupported proposal fields: {', '.join(sorted(unknown))}")
    if value["runner"] not in registered_runners:
        raise ValueError(f"unregistered runner: {value['runner']}")
    record = {
        "schema_version": 1,
        "id": f"proposal-{uuid.uuid4().hex[:12]}",
        "idea_id": idea_id,
        "track": idea["track"],
        "state": "proposed",
        **{field: value[field] for field in (*_REQUIRED, *_OPTIONAL) if field in value},
        "visibility": "private",
    }
    errors = validate_record("proposal", record)
    if errors:
        raise ValueError("; ".join(errors))
    store.create("proposals", record["id"], record)
    proposed_idea = {**idea, "state": "proposed"}
    store.update("ideas", idea_id, proposed_idea)
    return record


def approve_proposal(store: StudioStore, proposal_id: str) -> dict[str, Any]:
    record = store.read("proposals", proposal_id)
    if record.get("state") != "proposed":
        raise ValueError("only proposed proposals can be approved")
    approved = {**record, "state": "approved"}
    errors = validate_record("proposal", approved)
    if errors:
        raise ValueError("; ".join(errors))
    store.update("proposals", proposal_id, approved)
    return approved
