"""Build a complete social post kit from a render and a study card.

Phase 1 of docs/SOCIAL_PUBLISHING.md: at a pipeline gate the system prepares
everything a post needs — the two platform derivatives (feed 4:5 and vertical
9:16), per-platform caption drafts generated from the study card, alt text, a
Discord-postable summary, and a receipt with content hashes and per-platform
constraint checks. Nothing is uploaded; KC approves and posts from the kit.
Captions follow docs/TECHNICAL_VOICE.md and must pass the display-text
validator; generation fails loudly on a violation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from .behavior_postable import POSTABLE_CRF, POSTABLE_FPS, _frame_pattern, _VIDEO_SUFFIXES
from .display_text import validate_display_text
from .study_card import STUDY_CARD_NAME, load_study_card

# The two encodes that cover all five destinations (docs/SOCIAL_PUBLISHING.md).
DERIVATIVES: dict[str, tuple[int, int]] = {
    "feed": (1080, 1350),
    "vertical": (1080, 1920),
}

# Per-platform routing and the constraints the receipt checks. Duration limits
# are the platform caps worth verifying at this volume: X standard accounts stop
# at 2:20, Bluesky and Reels/Shorts at 3:00; TikTok's cap is far above any
# specimen and is recorded for completeness.
PLATFORMS: dict[str, dict[str, Any]] = {
    "x": {"derivative": "feed", "max_seconds": 140, "caption_limit": 280},
    "bluesky": {"derivative": "feed", "max_seconds": 180, "caption_limit": 300},
    "instagram": {"derivative": "vertical", "max_seconds": 180, "caption_limit": 2200},
    "shorts": {"derivative": "vertical", "max_seconds": 180, "caption_limit": 5000},
    "tiktok": {"derivative": "vertical", "max_seconds": 600, "caption_limit": 2200},
}

STAGES = ("behavior", "delivery", "recap")

HASHTAGS = ("#houdini", "#generativeart", "#simulation", "#creativecoding")


def _discover_tool(name: str) -> Path:
    from .detail_promote import _discover_ffmpeg as discover

    return discover(name)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _first_sentence(text: str) -> str:
    head, separator, _ = text.partition(". ")
    return head + ("." if separator else "")


def _study_line(card: Mapping[str, Any]) -> str:
    return f"STUDY {int(card['number']):03d} · {card['title']}"


def _stage_line(card: Mapping[str, Any], stage: str) -> str | None:
    if stage == "behavior":
        return "Behavior-stage diagnostic render."
    if stage == "recap":
        return f"Study {int(card['number']):03d} is complete."
    return None


def _compose(blocks: Sequence[tuple[str, bool]], limit: int, separator: str = "\n") -> str:
    """Join blocks in order, keeping optional ones only while the limit holds."""

    kept: list[str] = []
    for text, required in blocks:
        if not text:
            continue
        candidate = kept + [text]
        if len(separator.join(candidate)) <= limit:
            kept = candidate
        elif required:
            raise ValueError(f"required caption block does not fit in {limit} characters: {text!r}")
    return separator.join(kept)


def build_captions(card: Mapping[str, Any], stage: str) -> dict[str, str]:
    """Generate per-platform caption drafts from the study card."""

    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    study = _study_line(card)
    subtitle = str(card.get("subtitle", ""))
    summary = str(card.get("summary", ""))
    sentence = str(card.get("short_summary", "")) or _first_sentence(summary)
    stage_line = _stage_line(card, stage)
    bullets = "\n".join(f"- {item}" for item in card.get("bullets", []))
    params = " · ".join(f"{label} {value}" for label, value in card.get("params", []))
    hashtags = " ".join(HASHTAGS)

    short_blocks: list[tuple[str, bool]] = [
        (study, True),
        (subtitle, False),
        (stage_line or "", False),
        (sentence, False),
    ]
    captions = {
        "x": _compose(short_blocks, PLATFORMS["x"]["caption_limit"]),
        "bluesky": _compose(short_blocks, PLATFORMS["bluesky"]["caption_limit"]),
        "instagram": _compose(
            [
                (f"{study}\n{subtitle}" if subtitle else study, True),
                (stage_line or "", False),
                (summary, True),
                (bullets, False),
                (params, False),
                (hashtags, False),
            ],
            PLATFORMS["instagram"]["caption_limit"],
            separator="\n\n",
        ),
        "shorts": _compose(short_blocks, PLATFORMS["shorts"]["caption_limit"]),
        "tiktok": _compose(
            [(study, True), (stage_line or "", False), (sentence, False), (hashtags, False)],
            PLATFORMS["tiktok"]["caption_limit"],
        ),
    }
    errors: list[str] = []
    for platform, caption in captions.items():
        errors.extend(validate_display_text(caption, f"caption.{platform}"))
    if errors:
        raise ValueError("; ".join(errors))
    return captions


def build_alt_text(card: Mapping[str, Any]) -> str:
    parts = [f"{_study_line(card)}."]
    if card.get("subtitle"):
        parts.append(f"{card['subtitle']}.")
    if card.get("summary"):
        parts.append(str(card["summary"]))
    alt = " ".join(parts)
    errors = validate_display_text(alt, "alt-text")
    if errors:
        raise ValueError("; ".join(errors))
    return alt


def _probe_duration(video: Path) -> float | None:
    try:
        ffprobe = _discover_tool("ffprobe")
    except FileNotFoundError:
        return None
    result = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def encode_derivative(
    source: Path,
    output: Path,
    size: tuple[int, int],
    *,
    source_fps: float | None = None,
    monochrome: bool = False,
    ffmpeg: Path | None = None,
) -> dict[str, Any]:
    """Encode a video or frame directory into one derivative of the postable contract."""

    source = source.resolve()
    ffmpeg = ffmpeg or _discover_tool("ffmpeg")
    output.parent.mkdir(parents=True, exist_ok=True)

    command: list[str] = [str(ffmpeg), "-y", "-loglevel", "error"]
    duration: float | None = None
    if source.is_dir():
        pattern, start, frame_count = _frame_pattern(source)
        rate = source_fps or POSTABLE_FPS
        command.extend(["-framerate", str(rate), "-start_number", str(start), "-i", pattern])
        duration = frame_count / rate
    elif source.suffix.lower() in _VIDEO_SUFFIXES:
        if source_fps is not None:
            raise ValueError("source_fps applies to frame sequences; videos keep their own timing")
        command.extend(["-i", str(source)])
    else:
        raise ValueError(f"source must be a video or a frame directory: {source}")

    width, height = size
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
        raise RuntimeError(f"ffmpeg did not create {output.name}")
    if duration is None:
        duration = _probe_duration(output)

    return {
        "path": str(output),
        "bytes": output.stat().st_size,
        "sha256": _sha256(output),
        "size": [width, height],
        "fps": POSTABLE_FPS,
        "duration_seconds": round(duration, 3) if duration is not None else None,
    }


def platform_checks(
    derivatives: Mapping[str, Mapping[str, Any]], captions: Mapping[str, str]
) -> dict[str, dict[str, Any]]:
    checks: dict[str, dict[str, Any]] = {}
    for platform, spec in PLATFORMS.items():
        derivative = derivatives.get(spec["derivative"])
        duration = derivative.get("duration_seconds") if derivative else None
        caption = captions.get(platform, "")
        checks[platform] = {
            "derivative": spec["derivative"],
            "derivative_built": derivative is not None,
            "duration_seconds": duration,
            "duration_ok": None if duration is None else duration <= spec["max_seconds"],
            "caption_chars": len(caption),
            "caption_ok": 0 < len(caption) <= spec["caption_limit"],
        }
    return checks


def _kit_summary(
    card: Mapping[str, Any],
    stage: str,
    derivatives: Mapping[str, Mapping[str, Any]],
    checks: Mapping[str, Mapping[str, Any]],
    captions: Mapping[str, str],
    alt_text: str,
) -> str:
    lines = [
        f"## Post kit · {_study_line(card)}",
        "",
        f"Stage: {stage}. Captions and alt text are drafts; approve or edit the exact text before posting.",
        "",
    ]
    for name, derivative in derivatives.items():
        duration = derivative.get("duration_seconds")
        shown = f"{duration:.1f}s" if duration is not None else "duration unknown"
        lines.append(
            f"- `{Path(derivative['path']).name}` {derivative['size'][0]}x{derivative['size'][1]} · {shown}"
        )
    lines.append("")
    for platform, check in checks.items():
        flags = []
        if check["duration_ok"] is False:
            flags.append("OVER DURATION CAP")
        if not check["caption_ok"]:
            flags.append("CAPTION OVER LIMIT")
        status = " · ".join(flags) if flags else "ok"
        lines.append(f"- {platform}: {check['derivative']} · {check['caption_chars']} chars · {status}")
    for platform, caption in captions.items():
        lines.extend(["", f"### {platform}", "```", caption, "```"])
    lines.extend(["", "### alt text", "```", alt_text, "```", ""])
    return "\n".join(lines)


def build_post_kit(
    study_dir: Path,
    source: Path,
    out_dir: Path,
    *,
    stage: str,
    source_fps: float | None = None,
    monochrome: bool = False,
    only: Sequence[str] | None = None,
    ffmpeg: Path | None = None,
) -> dict[str, Any]:
    """Build derivatives, caption drafts, alt text, summary, and receipt into out_dir."""

    card = load_study_card(study_dir / "00_study" / STUDY_CARD_NAME)
    names = tuple(only) if only else tuple(DERIVATIVES)
    unknown = [name for name in names if name not in DERIVATIVES]
    if unknown:
        raise ValueError(f"unknown derivatives: {unknown}; choose from {tuple(DERIVATIVES)}")

    captions = build_captions(card, stage)
    alt_text = build_alt_text(card)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = card["variation_file_stem"]

    derivatives = {
        name: encode_derivative(
            source,
            out_dir / f"{stem}.{name}.mp4",
            DERIVATIVES[name],
            source_fps=source_fps,
            monochrome=monochrome,
            ffmpeg=ffmpeg,
        )
        for name in names
    }
    checks = platform_checks(derivatives, captions)

    for platform, caption in captions.items():
        (out_dir / f"caption.{platform}.txt").write_text(caption + "\n", encoding="utf-8")
    (out_dir / "alt-text.txt").write_text(alt_text + "\n", encoding="utf-8")
    summary_path = out_dir / "post-kit.md"
    summary_path.write_text(
        _kit_summary(card, stage, derivatives, checks, captions, alt_text), encoding="utf-8"
    )

    receipt: dict[str, Any] = {
        "schema_version": 1,
        "kind": "post-kit",
        "study_id": card["study_id"],
        "variation_id": card["variation_id"],
        "stem": stem,
        "stage": stage,
        "source": {
            "path": str(source.resolve()),
            "sha256": _sha256(source) if source.is_file() else None,
        },
        "derivatives": derivatives,
        "platforms": checks,
        "captions": {platform: f"caption.{platform}.txt" for platform in captions},
        "alt_text": "alt-text.txt",
        "summary": summary_path.name,
    }
    receipt_path = out_dir / "post-kit.receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt["receipt_path"] = str(receipt_path)
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m houdini_ai.post_kit",
        description="Build a social post kit (derivatives, caption drafts, alt text, receipt) from a render.",
    )
    parser.add_argument("--study", required=True, type=Path, help="study vault directory (holds 00_study/study-card.json)")
    parser.add_argument("--source", required=True, type=Path, help="source video or frame directory")
    parser.add_argument("--out", required=True, type=Path, help="output directory for the kit")
    parser.add_argument("--stage", required=True, choices=STAGES, help="pipeline stage the material comes from")
    parser.add_argument("--source-fps", type=float, default=None, help="playback rate of an input frame sequence")
    parser.add_argument("--monochrome", action="store_true", help="desaturate a legacy colored render")
    parser.add_argument(
        "--only",
        action="append",
        choices=tuple(DERIVATIVES),
        help="build only this derivative (repeatable); default builds all",
    )
    args = parser.parse_args(argv)

    receipt = build_post_kit(
        args.study,
        args.source,
        args.out,
        stage=args.stage,
        source_fps=args.source_fps,
        monochrome=args.monochrome,
        only=args.only,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
