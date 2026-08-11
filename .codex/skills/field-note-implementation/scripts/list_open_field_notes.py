#!/usr/bin/env python3
"""List open Review Studio notes as deterministic serial implementation tasks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def open_tasks(root: Path) -> list[dict[str, Any]]:
    review_dir = root / "work" / "reviews"
    tasks: list[dict[str, Any]] = []
    for path in sorted(review_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        study_id = str(payload.get("study_id", path.stem))
        for item in payload.get("items", []):
            if item.get("status") != "open":
                continue
            item_id = str(item.get("id", ""))
            text = str(item.get("text", "")).strip()
            if not item_id or not text:
                raise ValueError(f"{path}: open review item requires id and text")
            tasks.append(
                {
                    "task_id": f"field-note:{study_id}:{item_id}",
                    "title": f"Implement field note for {study_id}",
                    "study_id": study_id,
                    "note_id": item_id,
                    "created_at": item.get("created_at", ""),
                    "job_id": item.get("job_id"),
                    "artifact_path": item.get("artifact_path"),
                    "timecode": item.get("timecode"),
                    "kind": item.get("kind"),
                    "decision": item.get("decision"),
                    "text": text,
                }
            )
    return sorted(tasks, key=lambda task: (task["created_at"], task["study_id"], task["note_id"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="project root (default: current directory)")
    args = parser.parse_args()
    root = args.root.resolve()
    print(json.dumps({"tasks": open_tasks(root)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
