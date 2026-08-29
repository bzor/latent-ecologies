"""Private-by-default editorial tagging and separate approval."""

from __future__ import annotations

from collections.abc import Iterable

from .studio_store import StudioStore
from .studio_schema import validate_record
from .studio_types import EDITORIAL_TAGS


class EditorialError(ValueError):
    pass


def _editorial_id(artifact_id: str) -> str:
    return "editorial-" + artifact_id.removeprefix("artifact-")


def _derive(tags: list[str]) -> tuple[list[str], list[str]]:
    return ([tag.split(":", 1)[1] for tag in tags if tag.startswith("publish:")], [tag.split(":", 1)[1] for tag in tags if tag.startswith("role:")])


def tag_artifact(store: StudioStore, artifact_id: str, tags: Iterable[str]) -> dict[str, object]:
    artifact = store.read("artifacts", artifact_id)
    record_id = _editorial_id(artifact_id)
    try:
        current = store.read("editorial", record_id)
        exists = True
    except FileNotFoundError:
        current = {}
        exists = False
    combined = list(current.get("tags", []))
    for tag in tags:
        if tag == "readiness:approved":
            raise EditorialError("readiness:approved requires separate approval")
        if tag not in EDITORIAL_TAGS:
            raise EditorialError(f"unknown editorial tag: {tag}")
        if tag not in combined:
            combined.append(tag)
    destinations, roles = _derive(combined)
    state = current.get("state", "draft")
    if "readiness:ready-for-approval" in combined:
        state = "ready-for-approval"
    record: dict[str, object] = {
        "schema_version": 1,
        "id": record_id,
        "state": state,
        "artifact_refs": [artifact["path"]],
        "destinations": destinations,
        "roles": roles,
        "tags": combined,
        "visibility": "private",
        "approved": False,
    }
    (store.update if exists else store.create)("editorial", record_id, record)
    return record


def untag_artifact(store: StudioStore, artifact_id: str, tag: str) -> dict[str, object]:
    record_id = _editorial_id(artifact_id)
    current = store.read("editorial", record_id)
    tags = [item for item in current["tags"] if item != tag]
    destinations, roles = _derive(tags)
    updated = {**current, "tags": tags, "destinations": destinations, "roles": roles}
    store.update("editorial", record_id, updated)
    return updated


def approve_editorial(store: StudioStore, editorial_id: str) -> dict[str, object]:
    current = store.read("editorial", editorial_id)
    if current.get("state") != "ready-for-approval" or "readiness:ready-for-approval" not in current.get("tags", []):
        raise EditorialError("editorial record must be ready-for-approval")
    tags = [tag for tag in current["tags"] if not tag.startswith("readiness:")]
    tags.append("readiness:approved")
    approved = {**current, "state": "approved", "approved": True, "tags": tags}
    errors = validate_record("editorial", approved)
    if errors:
        raise EditorialError("; ".join(errors))
    store.update("editorial", editorial_id, approved)
    return approved


def editorial_summary(store: StudioStore) -> list[dict[str, object]]:
    records, errors = store.list("editorial")
    if errors:
        raise EditorialError("; ".join(error["error"] for error in errors))
    return records
