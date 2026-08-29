"""Composite a rendered overlay PNG sequence over a verified render with FFmpeg.
See docs/DETAIL_PASS_PROMOTE.md.

    python scripts/composite_overlay.py --render render.mp4 \
        --overlay work/overlay_frames --fps 24 --frames 600 --out post.mp4
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from houdini_ai.detail_promote import composite_overlay  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", type=Path, required=True, help="video file or printf-style PNG pattern")
    parser.add_argument("--render-start-number", type=int, help="start number when --render is a PNG pattern")
    parser.add_argument("--overlay", type=Path, required=True, help="directory of overlay-%%06d.png frames")
    parser.add_argument("--fps", type=float, required=True)
    parser.add_argument("--frames", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = composite_overlay(
        args.render,
        args.overlay,
        args.out,
        fps=args.fps,
        frames=args.frames,
        render_start_number=args.render_start_number,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
