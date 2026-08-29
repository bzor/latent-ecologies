"""Render a design-overlay PNG sequence (alpha) headlessly from a study.json
sidecar and an exported overlay config. Resumable: valid existing frames are
kept. See docs/DETAIL_PASS_PROMOTE.md.

    python scripts/render_overlay_sequence.py --study study.json \
        --config overlay-config.json --out work/overlay_frames [--frames 60]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from houdini_ai.detail_promote import render_overlay_sequence  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--frames", type=int, help="override frame count (defaults to study.json frames)")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    result = render_overlay_sequence(
        json.loads(args.study.read_text(encoding="utf-8")),
        json.loads(args.config.read_text(encoding="utf-8")),
        args.out,
        jobs=args.jobs,
        frame_count=args.frames,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
