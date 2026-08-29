"""Unified read-only Review Inbox projection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .studio_sessions import active_session
from .studio_store import StudioStore


def _item(
    source_type: str,
    record_id: str,
    text: str,
    *,
    created_at: str = "",
    stage: str = "workflow",
    track: str | None = None,
    status: str = "open",
    reference_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": record_id,
        "source_type": source_type,
        "created_at": created_at,
        "stage": stage,
        "track": track,
        "status": status,
        "text": text,
        "visibility": "private",
    }
    if reference_id:
        result["reference_id"] = reference_id
    if metadata:
        result["metadata"] = metadata
    return result


def _review_items(root: Path, errors: list[dict[str, str]]) -> list[dict[str, Any]]:
    directory = root / "work" / "reviews"
    result: list[dict[str, Any]] = []
    if not directory.is_dir():
        return result
    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            records = payload.get("items", []) if isinstance(payload, dict) else []
            if not isinstance(records, list):
                raise ValueError("review items must be a list")
            for record in records:
                if not isinstance(record, dict) or record.get("status") == "resolved":
                    continue
                kind = "artifact-decision" if record.get("kind") == "decision" else "artifact-note"
                result.append(
                    _item(
                        kind,
                        str(record.get("id", "")),
                        str(record.get("text", "")),
                        created_at=str(record.get("created_at", "")),
                        stage="review",
                        status=str(record.get("status", "open")),
                        reference_id=str(record.get("artifact_path", "")) or None,
                        metadata={
                            "study_id": payload.get("study_id"),
                            "job_id": record.get("job_id"),
                            "decision": record.get("decision"),
                            "timecode": record.get("timecode"),
                        },
                    )
                )
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append({"path": str(path), "error": str(error)})
    return result


def build_review_inbox(root: Path) -> dict[str, Any]:
    """Aggregate unresolved local review work without mutating source records."""

    root = Path(root).resolve()
    store = StudioStore(root)
    errors: list[dict[str, str]] = []
    items = _review_items(root, errors)

    proposals, proposal_errors = store.list("proposals")
    errors.extend(proposal_errors)
    for record in proposals:
        if record.get("state") != "proposed":
            continue
        items.append(
            _item(
                "proposal",
                str(record.get("id", "")),
                str(record.get("question", record.get("mechanism", "Proposal needs review"))),
                created_at=str(record.get("created_at", "")),
                stage="directions",
                track=str(record.get("track")) if record.get("track") else None,
                reference_id=str(record.get("idea_id", "")) or None,
            )
        )

    notes, note_errors = store.list("notes")
    errors.extend(note_errors)
    for record in notes:
        if record.get("category") != "question":
            continue
        items.append(
            _item(
                "process-question",
                str(record.get("id", "")),
                str(record.get("text", "")),
                created_at=str(record.get("created_at", "")),
                stage=str(record.get("stage", "workflow")),
                track=str(record.get("track")) if record.get("track") else None,
                reference_id=str(record.get("reference_id", "")) or None,
            )
        )

    session = active_session(store)
    if session:
        created_at = str(session.get("updated_at", ""))
        stage = str(session.get("current_phase", "workflow"))
        for index, question in enumerate(session.get("unresolved_questions", [])):
            items.append(
                _item(
                    "session-question",
                    f"{session['id']}-question-{index + 1}",
                    str(question),
                    created_at=created_at,
                    stage=stage,
                    reference_id=str(session["id"]),
                )
            )
        for index, blocker in enumerate(session.get("blockers", [])):
            items.append(
                _item(
                    "session-blocker",
                    f"{session['id']}-blocker-{index + 1}",
                    str(blocker),
                    created_at=created_at,
                    stage=stage,
                    reference_id=str(session["id"]),
                )
            )

    items.sort(key=lambda item: (str(item.get("created_at", "")), str(item.get("id", ""))), reverse=True)
    counts: dict[str, int] = {}
    for item in items:
        source_type = str(item["source_type"])
        counts[source_type] = counts.get(source_type, 0) + 1
    return {
        "session_id": session.get("id") if session else None,
        "total": len(items),
        "counts": counts,
        "items": items,
        "errors": errors,
        "visibility": "private",
    }
