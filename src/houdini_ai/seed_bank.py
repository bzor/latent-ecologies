"""Canonical Seed Bank built on the existing idea lineage."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from .display_text import validate_display_text
from .studies import create_study
from .studio_commands import CommandContext, execute_idempotent
from .studio_schema import validate_record
from .studio_store import StudioStore
from .studio_types import TRACKS


_SEED_TRANSITIONS = {
    "inbox": frozenset(("incubating", "ready", "archived")),
    "incubating": frozenset(("ready", "archived")),
    "ready": frozenset(("incubating", "promoted", "archived")),
    "promoted": frozenset(("archived",)),
    "archived": frozenset(),
}


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _text(value: dict[str, Any], key: str, limit: int) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"{key} must not be empty")
    text = item.strip()
    if len(text) > limit:
        raise ValueError(f"{key} exceeds {limit} characters")
    return text


def _validate(record: dict[str, Any]) -> None:
    errors = validate_record("idea", record)
    if errors:
        raise ValueError("; ".join(errors))


def _validate_display_fields(value: dict[str, Any]) -> None:
    errors: list[str] = []
    for key in ("title", "short_summary", "long_summary"):
        item = value.get(key)
        if isinstance(item, str):
            errors.extend(validate_display_text(item, key))
    if errors:
        raise ValueError("; ".join(errors))


def create_seed(store: StudioStore, value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("seed must be an object")
    title = _text(value, "title", 300)
    short_summary = _text(value, "short_summary", 500)
    long_summary = _text(value, "long_summary", 20_000)
    _validate_display_fields({"title": title, "short_summary": short_summary, "long_summary": long_summary})
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48] or "untitled"
    now = _timestamp()
    links = list(value.get("reference_links", []))
    record: dict[str, Any] = {
        "schema_version": 1,
        "id": f"idea-{slug}-{uuid.uuid4().hex[:8]}",
        "title": title,
        "raw_text": str(value.get("raw_text", long_summary)).strip(),
        "short_summary": short_summary,
        "long_summary": long_summary,
        "reference_links": links,
        "source_urls": list(dict.fromkeys(link.get("url") for link in links if isinstance(link, dict) and isinstance(link.get("url"), str))),
        "questions": list(value.get("questions", [])),
        "constraints": list(value.get("constraints", [])),
        "tags": list(value.get("tags", [])),
        "state": "inbox",
        "visibility": "private",
        "created_at": now,
        "updated_at": now,
    }
    if "track" in value:
        record["track"] = value["track"]
    _validate(record)
    return store.create("ideas", record["id"], record)


_UPDATABLE_FIELDS = frozenset(
    ("title", "short_summary", "long_summary", "raw_text", "reference_links", "questions", "constraints", "tags")
)


def update_seed(store: StudioStore, seed_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(changes, dict) or not changes:
        raise ValueError("Seed changes must be a non-empty object")
    unsupported = sorted(set(changes) - _UPDATABLE_FIELDS)
    if unsupported:
        raise ValueError(f"unsupported Seed update fields: {', '.join(unsupported)}")
    record = store.read("ideas", seed_id)
    _validate(record)
    updated = {**record, **changes, "updated_at": _timestamp()}
    for key, limit in (("title", 300), ("short_summary", 500), ("long_summary", 20_000), ("raw_text", 20_000)):
        if key in changes:
            updated[key] = _text(updated, key, limit)
    _validate_display_fields(updated)
    if "reference_links" in changes:
        links = changes["reference_links"]
        if not isinstance(links, list):
            raise ValueError("reference_links must be an array")
        updated["source_urls"] = list(
            dict.fromkeys(
                link.get("url")
                for link in links
                if isinstance(link, dict) and isinstance(link.get("url"), str)
            )
        )
    _validate(updated)
    return store.update("ideas", seed_id, updated)


def transition_seed(store: StudioStore, seed_id: str, target: str) -> dict[str, Any]:
    record = store.read("ideas", seed_id)
    _validate(record)
    source = str(record["state"])
    if target not in _SEED_TRANSITIONS.get(source, frozenset()):
        raise ValueError(f"cannot transition Seed from {source} to {target}")
    updated = {**record, "state": target, "updated_at": _timestamp()}
    _validate(updated)
    return store.update("ideas", seed_id, updated)


def promote_seed_to_study(
    store: StudioStore,
    seed_id: str,
    *,
    study_id: str,
    study_title: str,
    primary_track: str,
    recommended_next_action: str,
) -> dict[str, Any]:
    seed = store.read("ideas", seed_id)
    _validate(seed)
    if seed.get("state") == "promoted":
        if seed.get("promoted_study_id") != study_id:
            raise ValueError("Seed was already promoted to a different Study")
        return store.read("studies", study_id)
    if seed.get("state") != "ready":
        raise ValueError("Seed must be ready before promotion")
    if primary_track not in TRACKS:
        raise ValueError("primary_track must be a canonical Studio track")
    study = create_study(
        store,
        {
            "id": study_id,
            "title": study_title,
            "current_phase": "seed",
            "intent": seed["long_summary"],
            "recommended_next_action": recommended_next_action,
            "idea_id": seed_id,
        },
    )
    updated = {
        **seed,
        "state": "promoted",
        "track": primary_track,
        "promoted_study_id": study_id,
        "updated_at": _timestamp(),
    }
    _validate(updated)
    store.update("ideas", seed_id, updated)
    return study


def promote_seed_to_study_command(
    store: StudioStore,
    context: CommandContext,
    *,
    study_id: str,
    study_title: str,
    primary_track: str,
    recommended_next_action: str,
) -> dict[str, Any]:
    if context.seed_id is None:
        raise ValueError("Seed promotion command requires a seed_id context")
    return execute_idempotent(
        store,
        context,
        "seed.promote",
        lambda: promote_seed_to_study(
            store,
            context.seed_id,
            study_id=study_id,
            study_title=study_title,
            primary_track=primary_track,
            recommended_next_action=recommended_next_action,
        ),
        summary=f"Promote Seed {context.seed_id} into Study {study_id}.",
    )

_DIGEST_ORDER = ("inbox", "incubating", "proposed", "ready", "promoted", "archived")
_DIGEST_HEADINGS = {
    "inbox": "Inbox — not yet incubated",
    "incubating": "Incubating",
    "proposed": "Proposed — probe contracts drafted",
    "ready": "Ready — awaiting a promotion decision",
    "promoted": "Promoted into Studies",
    "archived": "Archived",
}


def build_seed_digest(store: StudioStore, *, today: str) -> str:
    """Render the private Seed Bank digest as Discord-postable markdown.

    A ritual artifact: posted to keep the front of the pipeline warm during
    production weeks. Groups seeds by lifecycle state, oldest first within each
    group so long-waiting seeds surface. Archived seeds appear as a count only.
    """
    records, errors = store.list("ideas")
    if errors:
        raise ValueError("; ".join(error["error"] for error in errors))
    by_state: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_state.setdefault(str(record.get("state", "inbox")), []).append(record)

    lines = [f"**Seed Bank digest · {today}**", ""]
    for state in _DIGEST_ORDER:
        seeds = sorted(by_state.pop(state, []), key=lambda r: str(r.get("updated_at") or r.get("created_at") or ""))
        if not seeds:
            continue
        if state == "archived":
            lines.extend((f"_{len(seeds)} archived seed(s) held as evidence._", ""))
            continue
        lines.append(f"**{_DIGEST_HEADINGS[state]}** ({len(seeds)})")
        for record in seeds:
            title = str(record.get("title") or record.get("raw_text") or record.get("id", "")).strip()
            if len(title) > 90:
                title = title[:87] + "..."
            touched = str(record.get("updated_at") or record.get("created_at") or "")[:10]
            questions = record.get("questions") or []
            question_note = f" · {len(questions)} open question(s)" if questions else ""
            study = record.get("promoted_study_id")
            study_note = f" · -> {study}" if study else ""
            lines.append(f"- {title} · `{record.get('id', '')}` · {record.get('track', '?')} · touched {touched}{question_note}{study_note}")
        lines.append("")
    for state, seeds in sorted(by_state.items()):
        lines.append(f"**{state}** ({len(seeds)}) — unrecognized lifecycle state; records need review")
        lines.append("")
    lines.append("_Reply with a seed id to incubate, promote, or archive it._")
    return "\n".join(lines).rstrip() + "\n"
