"""Conceptual Behavior Direction Board operations."""

from __future__ import annotations

import uuid
from collections.abc import Collection, Mapping, Sequence
from typing import Any

from .proposals import create_proposal
from .studio_schema import validate_record
from .studio_store import StudioStore
from .studio_types import can_transition


DIRECTION_DECISIONS = ("select", "hold", "archive", "reject")
_DECISION_STATES = {"select": "selected", "hold": "held", "archive": "archived", "reject": "rejected"}
_REQUIRED = (
    "title", "premise", "mechanism", "expected_emergent_behavior", "cheapest_informative_probe",
    "risks", "conceptual_distinction", "sibling_relations",
)
_OPTIONAL = ("extensions",)


def _validated(record: dict[str, Any]) -> dict[str, Any]:
    errors = validate_record("direction", record)
    if errors:
        raise ValueError("; ".join(errors))
    return record


def _create(
    store: StudioStore,
    idea_id: str,
    value: Mapping[str, Any],
    *,
    parent_ids: Sequence[str] = (),
    relation_kind: str | None = None,
) -> dict[str, Any]:
    idea = store.read("ideas", idea_id)
    if idea.get("track") != "behavior":
        raise ValueError("Behavior directions require a behavior-track idea")
    missing = [field for field in _REQUIRED if field not in value]
    if missing:
        raise ValueError(f"missing direction fields: {', '.join(missing)}")
    unknown = set(value) - set(_REQUIRED) - set(_OPTIONAL)
    if unknown:
        raise ValueError(f"unsupported direction fields: {', '.join(sorted(unknown))}")
    direction_id = f"direction-{uuid.uuid4().hex[:12]}"
    for relation in value["sibling_relations"]:
        if not isinstance(relation, Mapping) or not isinstance(relation.get("direction_id"), str):
            raise ValueError("each sibling relation requires a direction_id")
        sibling = store.read("directions", relation["direction_id"])
        if sibling.get("idea_id") != idea_id:
            raise ValueError("sibling directions must belong to the same idea")
    record: dict[str, Any] = {
        "schema_version": 1,
        "id": direction_id,
        "idea_id": idea_id,
        **{field: value[field] for field in (*_REQUIRED, *_OPTIONAL) if field in value},
        "state": "candidate",
        "visibility": "private",
    }
    if parent_ids:
        record["parent_direction_ids"] = list(parent_ids)
        record["relation_kind"] = relation_kind
    _validated(record)
    store.create("directions", direction_id, record)
    return record


def create_direction(store: StudioStore, idea_id: str, value: Mapping[str, Any]) -> dict[str, Any]:
    return _create(store, idea_id, value)


def decide_direction(store: StudioStore, direction_id: str, decision: str) -> dict[str, Any]:
    if decision not in DIRECTION_DECISIONS:
        raise ValueError(f"unknown direction decision: {decision}")
    record = store.read("directions", direction_id)
    target = _DECISION_STATES[decision]
    if record.get("state") == target:
        return record
    if not can_transition("direction", str(record.get("state", "")), target):
        raise ValueError(f"cannot {decision} direction from {record.get('state')}")
    updated = _validated({**record, "state": target})
    store.update("directions", direction_id, updated)
    return updated


def mutate_direction(store: StudioStore, source_id: str, value: Mapping[str, Any]) -> dict[str, Any]:
    source = store.read("directions", source_id)
    return _create(store, str(source["idea_id"]), value, parent_ids=[source_id], relation_kind="mutation")


def merge_directions(store: StudioStore, source_ids: Sequence[str], value: Mapping[str, Any]) -> dict[str, Any]:
    unique_ids = list(dict.fromkeys(source_ids))
    if len(unique_ids) < 2:
        raise ValueError("conceptual merge requires at least two distinct directions")
    sources = [store.read("directions", direction_id) for direction_id in unique_ids]
    idea_ids = {str(source.get("idea_id")) for source in sources}
    if len(idea_ids) != 1:
        raise ValueError("merged directions must belong to the same idea")
    return _create(store, idea_ids.pop(), value, parent_ids=unique_ids, relation_kind="conceptual-merge")


def derive_probe_proposal(
    store: StudioStore,
    direction_id: str,
    value: Mapping[str, Any],
    *,
    registered_runners: Collection[str],
) -> dict[str, Any]:
    direction = store.read("directions", direction_id)
    if direction.get("state") != "selected":
        raise ValueError("only selected directions can derive probe proposals")
    allowed = {"outputs", "stop_conditions", "runner", "cost_tier", "extensions"}
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"unsupported derived-proposal fields: {', '.join(sorted(unknown))}")
    proposal_value = {
        "question": f"What does {direction['title']} reveal under its cheapest informative probe?",
        "hypothesis": direction["expected_emergent_behavior"],
        "mechanism": direction["mechanism"],
        "direction_ids": [direction_id],
        **dict(value),
    }
    return create_proposal(
        store,
        str(direction["idea_id"]),
        proposal_value,
        registered_runners=registered_runners,
    )
