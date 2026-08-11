#!/usr/bin/env python3
"""Append a validated assistant response to a Review Studio field note."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study_id")
    parser.add_argument("note_id")
    parser.add_argument("text")
    parser.add_argument("--status", default="acknowledged", choices=("acknowledged", "implemented", "resolved", "open"))
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="project root (default: current directory)")
    parser.add_argument("--result-json", help="optional result object with commit, job_id, and artifact_paths")
    args = parser.parse_args()
    root = args.root.resolve()
    sys.path.insert(0, str(root / "src"))
    from houdini_ai.review_studio import ReviewStore  # pylint: disable=import-outside-toplevel

    value = {"text": args.text, "status": args.status}
    if args.result_json is not None:
        value["result"] = json.loads(args.result_json)
    response = ReviewStore(root).respond(args.study_id, args.note_id, value)
    print(json.dumps(response, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
