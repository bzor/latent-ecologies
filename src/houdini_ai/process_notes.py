"""Capture and summarize private observations about the Studio workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import uuid

from .studio_schema import validate_record
from .studio_store import StudioStore

NOTE_CATEGORIES = ("working", "pain-point", "missing-functionality", "idea", "question")
NOTE_STAGES = ("idea", "probe", "behavior", "look", "chromatic", "cinematography", "specimen", "field-station", "publication", "workflow")
_CATEGORY_TITLES = {
    "working": "Working",
    "pain-point": "Pain points",
    "missing-functionality": "Missing functionality",
    "idea": "Ideas",
    "question": "Questions",
}


def capture_note(
    store: StudioStore,
    text: str,
    category: str,
    stage: str,
    track: str,
    *,
    reference_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    if not text or not text.strip():
        raise ValueError("note text must not be empty")
    record: dict[str, Any] = {
        "schema_version": 1,
        "id": f"note-{uuid.uuid4().hex[:12]}",
        "created_at": created_at or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "category": category,
        "stage": stage,
        "track": track,
        "text": text,
        "visibility": "private",
    }
    if reference_id:
        record["reference_id"] = reference_id
    errors = validate_record("note", record)
    if errors:
        raise ValueError("; ".join(errors))
    store.create("notes", str(record["id"]), record)
    return record


def filtered_notes(
    store: StudioStore,
    *,
    category: str | None = None,
    stage: str | None = None,
    track: str | None = None,
) -> list[dict[str, Any]]:
    records, errors = store.list("notes")
    if errors:
        raise ValueError("; ".join(error["error"] for error in errors))
    result = [
        record for record in records
        if (category is None or record.get("category") == category)
        and (stage is None or record.get("stage") == stage)
        and (track is None or record.get("track") == track)
    ]
    return sorted(result, key=lambda item: (str(item.get("created_at", "")), str(item.get("id", ""))))


def write_digest(store: StudioStore, path: Path | None = None) -> Path:
    destination = path or store.directory / "PROCESS_NOTES.md"
    notes = filtered_notes(store)
    lines = [
        "# Studio process notes",
        "",
        "Private observations captured during real-world use. Source records under `work/studio/notes/` are canonical.",
        "",
    ]
    for category in NOTE_CATEGORIES:
        lines.extend((f"## {_CATEGORY_TITLES[category]}", ""))
        matches = [note for note in notes if note.get("category") == category]
        if not matches:
            lines.extend(("_None captured yet._", ""))
            continue
        for note in matches:
            context = f"{note['created_at']} · {note['track']} / {note['stage']}"
            if note.get("reference_id"):
                context += f" · {note['reference_id']}"
            lines.extend((f"- **{context}**", f"  {str(note['text']).strip()}", ""))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return destination
