"""Conform a behavior render into the canonical postable standard.

Behavior-stage diagnostics have drifted in size, frame rate, and palette. The
postable standard fixes one contract for anything KC may eventually post to X:
1080x1350 portrait at 30 fps, monochrome by default — the behavior is the
subject — with the CMYK accents reserved for differentiating populations,
lineages, or states when monochrome cannot. New behavior renderers should draw
with these constants directly; this module's conformer also upgrades any
existing frame sequence or video into a postable encode without re-simulating.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

POSTABLE_SIZE = (1080, 1350)
POSTABLE_FPS = 30
POSTABLE_CRF = 18

# Monochrome first: near-black ground, paper-white structure.
POSTABLE_BACKGROUND = (8, 8, 8)
POSTABLE_FOREGROUND = (236, 236, 236)
# Reserved accents, in assignment order, for when populations must be told apart.
POSTABLE_ACCENTS = {
    "cyan": (0, 174, 239),
    "magenta": (236, 0, 140),
    "yellow": (255, 242, 0),
}

# X caps standard-account videos at 2:20.
X_MAX_SECONDS = 140

_VIDEO_SUFFIXES = (".mp4", ".mov", ".webm")


def _discover_ffmpeg() -> Path:
    from .detail_promote import _discover_ffmpeg as discover

    return discover("ffmpeg")


def _frame_pattern(directory: Path) -> tuple[str, int, int]:
    """Resolve a printf-style pattern, start number, and count for a frame directory."""

    frames = sorted(directory.glob("*.png")) or sorted(directory.glob("*.jpg"))
    if not frames:
        raise FileNotFoundError(f"no PNG or JPG frames under {directory}")
    stem = frames[0].stem
    digits = len(stem) - len(stem.rstrip("0123456789"))
    if digits == 0:
        raise ValueError(f"frame names must end in a number: {frames[0].name}")
    prefix = stem[: len(stem) - digits]
    start = int(stem[len(prefix) :])
    pattern = str(directory / f"{prefix}%0{digits}d{frames[0].suffix}")
    return pattern, start, len(frames)


def conform_postable(
    source: Path,
    output: Path,
    *,
    source_fps: float | None = None,
    monochrome: bool = False,
    ffmpeg: Path | None = None,
) -> dict[str, Any]:
    """Encode a video or frame directory into the postable contract.

    ``source_fps`` sets the playback rate of an input frame sequence (and can
    re-time a video); the output is always POSTABLE_FPS. ``monochrome``
    desaturates a legacy colored render; new renders should already be drawn in
    the postable palette and leave it off.
    """

    source = source.resolve()
    ffmpeg = ffmpeg or _discover_ffmpeg()
    if output.suffix.lower() != ".mp4":
        raise ValueError("postable output must be an .mp4")
    output.parent.mkdir(parents=True, exist_ok=True)

    command: list[str] = [str(ffmpeg), "-y", "-loglevel", "error"]
    if source.is_dir():
        pattern, start, frame_count = _frame_pattern(source)
        rate = source_fps or POSTABLE_FPS
        command.extend(["-framerate", str(rate), "-start_number", str(start), "-i", pattern])
        duration = frame_count / rate
    elif source.suffix.lower() in _VIDEO_SUFFIXES:
        if source_fps is not None:
            raise ValueError("source_fps applies to frame sequences; videos keep their own timing")
        command.extend(["-i", str(source)])
        duration = None
    else:
        raise ValueError(f"source must be a video or a frame directory: {source}")

    width, height = POSTABLE_SIZE
    filters = []
    if monochrome:
        filters.append("hue=s=0")
    filters.extend(
        (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease:flags=lanczos",
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x080808",
            f"fps={POSTABLE_FPS}",
            "setsar=1",
        )
    )
    command.extend(
        [
            "-vf",
            ",".join(filters),
            "-c:v",
            "libx264",
            "-crf",
            str(POSTABLE_CRF),
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            str(output),
        ]
    )
    subprocess.run(command, check=True)
    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError("ffmpeg did not create the postable video")

    data = output.read_bytes()
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "standard": {
            "size": list(POSTABLE_SIZE),
            "fps": POSTABLE_FPS,
            "crf": POSTABLE_CRF,
            "palette": "monochrome; CMYK accents for differentiation",
        },
        "source": str(source),
        "source_fps": source_fps,
        "monochrome_conversion": monochrome,
        "output": {
            "path": str(output),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        },
        "duration_seconds": round(duration, 3) if duration is not None else None,
        "x_duration_ok": duration is None or duration <= X_MAX_SECONDS,
    }
    receipt_path = output.with_suffix(".receipt.json")
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt["receipt_path"] = str(receipt_path)
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m houdini_ai.behavior_postable",
        description="Conform a behavior render (video or frame directory) to the postable standard.",
    )
    parser.add_argument("source", type=Path, help="source video or frame directory")
    parser.add_argument("--out", required=True, type=Path, help="output .mp4 path")
    parser.add_argument("--source-fps", type=float, default=None, help="playback rate of an input frame sequence")
    parser.add_argument("--monochrome", action="store_true", help="desaturate a legacy colored render")
    args = parser.parse_args(argv)

    receipt = conform_postable(args.source, args.out, source_fps=args.source_fps, monochrome=args.monochrome)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
