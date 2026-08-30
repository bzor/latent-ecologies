"""Verify a rendered PNG sequence before it enters the detail pass.

Frame-level checks (numbering, decode, dimensions, blank and stuck frames) catch a
missing or broken frame. They do not catch the failure mode that actually reached a
delivery in this project: a frame whose simulation state disagrees with its
neighbours, which reads as a one-frame pop in motion while every per-frame check
passes.

The temporal residual catches it. For each interior frame the mean absolute
difference between the frame and the average of its neighbours is measured:

    residual(n) = mean(|f(n) - (f(n-1) + f(n+1)) / 2|)

Within a continuous run this is dominated by render noise and inter-frame motion and
stays close to the sequence median. A frame rendered from a different solver
trajectory disagrees with both neighbours, so its residual spikes, and both
neighbours rise with it because they are measured against it. See
`docs/RENDER_INTEGRITY.md` for the measured baselines.

    python scripts/verify_render_sequence.py studies/001-memory-field/02_look/renders
    python scripts/verify_render_sequence.py <dir> --pattern "look.*.png" --json out.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

FRAME_NUMBER = re.compile(r"\.(\d+)\.png$", re.IGNORECASE)

# A frame this far above the sequence median is treated as a discontinuity. Measured
# clean sequences sit within 1.2x of the median; a reused isolated frame reached 3.8x
# and an ordinary run seam 2.3x.
DEFAULT_RESIDUAL_RATIO = 1.8

# Minimum spread between the darkest and lightest channel value before a frame is
# considered to carry visible content.
MIN_CONTENT_SPREAD = 12


def frame_number(path: Path) -> int | None:
    match = FRAME_NUMBER.search(path.name)
    return int(match.group(1)) if match else None


def load_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        image.load()
        return np.asarray(image.convert("RGB"), dtype=np.float64)


def check_frames(paths: list[Path]) -> dict[str, Any]:
    """Per-frame integrity: decode, uniform format, blank frames, duplicate frames."""
    sizes: set[tuple[tuple[int, int], str]] = set()
    blanks: list[str] = []
    signatures: dict[str, str] = {}

    for path in paths:
        with Image.open(path) as image:
            image.load()
            sizes.add((image.size, image.mode))
            rgb = image.convert("RGB")
            if max(high - low for low, high in rgb.getextrema()) < MIN_CONTENT_SPREAD:
                blanks.append(path.name)
            thumbnail = rgb.resize((48, 60), Image.BILINEAR)
        signatures[path.name] = hashlib.sha256(thumbnail.tobytes()).hexdigest()

    names = sorted(signatures)
    duplicates = [
        [names[index - 1], names[index]]
        for index in range(1, len(names))
        if signatures[names[index]] == signatures[names[index - 1]]
    ]
    return {
        "uniform_format": len(sizes) == 1,
        "formats": sorted(f"{size[0]}x{size[1]} {mode}" for size, mode in sizes),
        "blank_frames": blanks,
        "identical_consecutive_frames": duplicates,
        "unique_signatures": len(set(signatures.values())),
    }


def temporal_residuals(paths: list[Path]) -> dict[int, float]:
    """Mean absolute difference between each interior frame and its neighbours' average."""
    residuals: dict[int, float] = {}
    if len(paths) < 3:
        return residuals

    previous = load_rgb(paths[0])
    current = load_rgb(paths[1])
    for index in range(1, len(paths) - 1):
        following = load_rgb(paths[index + 1])
        number = frame_number(paths[index])
        if number is not None:
            residuals[number] = float(np.abs(current - (previous + following) / 2).mean())
        previous, current = current, following
    return residuals


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="directory holding the rendered frames")
    parser.add_argument("--pattern", default="*.png", help="glob for the frame files")
    parser.add_argument("--start", type=int, help="expected first frame number")
    parser.add_argument("--end", type=int, help="expected last frame number")
    parser.add_argument(
        "--residual-ratio",
        type=float,
        default=DEFAULT_RESIDUAL_RATIO,
        help=f"flag frames above this multiple of the median residual (default {DEFAULT_RESIDUAL_RATIO})",
    )
    parser.add_argument("--skip-residual", action="store_true", help="run per-frame checks only")
    parser.add_argument("--json", type=Path, help="write the full report here")
    args = parser.parse_args()

    paths = sorted(
        (path for path in args.directory.glob(args.pattern) if frame_number(path) is not None),
        key=lambda path: frame_number(path) or 0,
    )
    if not paths:
        print(f"VERIFY-FAILED no frames matching {args.pattern} in {args.directory}")
        return 1

    numbers = [frame_number(path) for path in paths]
    start = args.start if args.start is not None else min(numbers)
    end = args.end if args.end is not None else max(numbers)
    missing = sorted(set(range(start, end + 1)) - set(numbers))

    report: dict[str, Any] = {
        "kind": "render-sequence-verification",
        "directory": str(args.directory),
        "frames_found": len(paths),
        "frame_range": [start, end],
        "missing_frames": missing,
    }
    report.update(check_frames(paths))

    failures: list[str] = []
    if missing:
        failures.append(f"{len(missing)} missing frames (first {missing[0]})")
    if not report["uniform_format"]:
        failures.append(f"mixed frame formats: {report['formats']}")
    if report["blank_frames"]:
        failures.append(f"{len(report['blank_frames'])} blank frames")
    if report["identical_consecutive_frames"]:
        failures.append(f"{len(report['identical_consecutive_frames'])} identical consecutive frames")

    if not args.skip_residual:
        residuals = temporal_residuals(paths)
        if residuals:
            values = list(residuals.values())
            median = statistics.median(values)
            threshold = median * args.residual_ratio
            anomalies = sorted(
                ({"frame": frame, "residual": round(value, 4), "ratio": round(value / median, 3)}
                 for frame, value in residuals.items() if value > threshold),
                key=lambda item: item["frame"],
            )
            report["temporal_residual"] = {
                "frames_analysed": len(values),
                "median": round(median, 4),
                "min": round(min(values), 4),
                "max": round(max(values), 4),
                "max_ratio": round(max(values) / median, 3),
                "threshold_ratio": args.residual_ratio,
                "anomalies": anomalies,
            }
            if anomalies:
                failures.append(
                    f"{len(anomalies)} temporal discontinuities (frames "
                    f"{', '.join(str(item['frame']) for item in anomalies[:8])})"
                )

    report["passed"] = not failures
    report["failures"] = failures

    print(f"frames: {report['frames_found']}  range: {start}..{end}  missing: {len(missing)}")
    print(f"format: {', '.join(report['formats'])}")
    residual = report.get("temporal_residual")
    if residual:
        print(
            f"temporal residual: median {residual['median']}  max {residual['max']} "
            f"({residual['max_ratio']}x)  anomalies {len(residual['anomalies'])}"
        )
        for item in residual["anomalies"]:
            print(f"   frame {item['frame']}: {item['residual']} ({item['ratio']}x)")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if failures:
        print("VERIFY-FAILED " + "; ".join(failures))
        return 1
    print("VERIFY-OK sequence is continuous and complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
