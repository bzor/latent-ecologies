"""Assemble one postable review packet from a round's candidate artifacts.

A review packet is the mandatory closing artifact of a work round: a labelled
contact sheet, a labelled side-by-side comparison video (when candidates have
video evidence), and a caption ready to post in the Study's Discord thread so
KC can decide by replying with a letter. Candidates keep identical cell size,
frame rate, and letter ordering across the sheet, the video, and the caption.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import string
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw, ImageFont

CELL_SIZE = (960, 540)
LABEL_BAR_HEIGHT = 40
BACKGROUND = (17, 19, 18)
TEXT = (220, 224, 216)
MAX_CANDIDATES = 8

_VIDEO_SUFFIXES = (".mp4", ".mov", ".webm")
_STILL_SUFFIXES = (".png", ".jpg", ".jpeg")
_PREFERRED_VIDEO_STEMS = ("motion", "review", "comparison", "timelapse")
_PREFERRED_STILLS = ("late.png", "middle.png", "early.png", "contact-sheet.png")


@dataclass(frozen=True)
class Candidate:
    letter: str
    name: str
    source: Path
    video: Path | None
    still: Path | None


def _discover_ffmpeg() -> Path:
    from .detail_promote import _discover_ffmpeg as discover

    return discover("ffmpeg")


def _find_video(directory: Path) -> Path | None:
    videos = sorted(path for path in directory.rglob("*") if path.suffix.lower() in _VIDEO_SUFFIXES)
    if not videos:
        return None
    for stem in _PREFERRED_VIDEO_STEMS:
        for path in videos:
            if stem in path.stem.lower():
                return path
    return videos[0]


def _find_still(directory: Path) -> Path | None:
    for name in _PREFERRED_STILLS:
        matches = sorted(directory.rglob(name))
        if matches:
            return matches[0]
    frames = sorted(directory.rglob("frame-*.png"))
    if frames:
        return frames[-1]
    stills = sorted(path for path in directory.rglob("*") if path.suffix.lower() in _STILL_SUFFIXES)
    return stills[0] if stills else None


def resolve_candidate(letter: str, name: str, source: Path) -> Candidate:
    """Locate a candidate's video and still evidence beneath its source path."""

    source = source.resolve()
    if not source.exists():
        raise FileNotFoundError(f"candidate {name}: {source} does not exist")
    if source.is_file():
        suffix = source.suffix.lower()
        if suffix in _VIDEO_SUFFIXES:
            return Candidate(letter, name, source, video=source, still=None)
        if suffix in _STILL_SUFFIXES:
            return Candidate(letter, name, source, video=None, still=source)
        raise ValueError(f"candidate {name}: unsupported file type {source.suffix}")
    video = _find_video(source)
    still = _find_still(source)
    if video is None and still is None:
        raise FileNotFoundError(f"candidate {name}: no video or still evidence under {source}")
    return Candidate(letter, name, source, video=video, still=still)


def _extract_still(ffmpeg: Path, video: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(ffmpeg), "-y", "-loglevel", "error", "-sseof", "-1", "-i", str(video), "-frames:v", "1", str(destination)],
        check=True,
    )
    if not destination.exists() or destination.stat().st_size == 0:
        raise RuntimeError(f"ffmpeg did not extract a still from {video}")
    return destination


def _font() -> ImageFont.ImageFont:
    return ImageFont.load_default()


def _cell_image(still: Path) -> Image.Image:
    cell = Image.new("RGB", CELL_SIZE, BACKGROUND)
    with Image.open(still) as image:
        image = image.convert("RGB")
        image.thumbnail(CELL_SIZE, Image.LANCZOS)
        cell.paste(image, ((CELL_SIZE[0] - image.width) // 2, (CELL_SIZE[1] - image.height) // 2))
    return cell


def _grid_shape(count: int) -> tuple[int, int]:
    columns = count if count <= 3 else 2 if count == 4 else 3
    rows = (count + columns - 1) // columns
    return columns, rows


def build_contact_sheet(candidates: Sequence[Candidate], stills: Mapping[str, Path], destination: Path) -> Path:
    columns, rows = _grid_shape(len(candidates))
    cell_height = CELL_SIZE[1] + LABEL_BAR_HEIGHT
    sheet = Image.new("RGB", (CELL_SIZE[0] * columns, cell_height * rows), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    for index, candidate in enumerate(candidates):
        column, row = index % columns, index // columns
        origin_x, origin_y = column * CELL_SIZE[0], row * cell_height
        draw.text((origin_x + 12, origin_y + 12), f"{candidate.letter} - {candidate.name}", fill=TEXT, font=_font())
        sheet.paste(_cell_image(stills[candidate.letter]), (origin_x, origin_y + LABEL_BAR_HEIGHT))
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination)
    return destination


def _label_image(candidate: Candidate, directory: Path) -> Path:
    label = Image.new("RGB", (CELL_SIZE[0], LABEL_BAR_HEIGHT), BACKGROUND)
    ImageDraw.Draw(label).text((12, 12), f"{candidate.letter} - {candidate.name}", fill=TEXT, font=_font())
    path = directory / f"label-{candidate.letter}.png"
    label.save(path)
    return path


def build_comparison_video(
    ffmpeg: Path,
    candidates: Sequence[Candidate],
    destination: Path,
    *,
    fps: int = 30,
    crf: int = 18,
) -> Path:
    """Stack candidate videos into one labelled grid with uniform cells and frame rate."""

    with_video = [candidate for candidate in candidates if candidate.video is not None]
    if not with_video:
        raise ValueError("no candidate has video evidence")
    columns, rows = _grid_shape(len(with_video))
    destination.parent.mkdir(parents=True, exist_ok=True)
    label_dir = destination.parent / "labels"
    label_dir.mkdir(exist_ok=True)

    command: list[str] = [str(ffmpeg), "-y", "-loglevel", "error"]
    for candidate in with_video:
        command.extend(["-i", str(candidate.video)])
    labels = []
    for candidate in with_video:
        labels.append(_label_image(candidate, label_dir))
        command.extend(["-i", str(labels[-1])])

    cell_width, cell_height = CELL_SIZE[0], CELL_SIZE[1] + LABEL_BAR_HEIGHT
    filters = []
    for index in range(len(with_video)):
        filters.append(
            f"[{index}:v]scale={CELL_SIZE[0]}:{CELL_SIZE[1]}:force_original_aspect_ratio=decrease,"
            f"pad={CELL_SIZE[0]}:{CELL_SIZE[1]}:(ow-iw)/2:(oh-ih)/2:color=0x111312,"
            f"pad={cell_width}:{cell_height}:0:{LABEL_BAR_HEIGHT}:color=0x111312,"
            f"fps={fps},setsar=1[cell{index}]"
        )
    if len(with_video) == 1:
        stacked = "[cell0]"
    else:
        layout = "|".join(
            f"{(index % columns) * cell_width}_{(index // columns) * cell_height}" for index in range(len(with_video))
        )
        inputs = "".join(f"[cell{index}]" for index in range(len(with_video)))
        filters.append(f"{inputs}xstack=inputs={len(with_video)}:layout={layout}:fill=0x111312[stacked]")
        stacked = "[stacked]"
    current = stacked
    for index in range(len(with_video)):
        origin_x = (index % columns) * cell_width
        origin_y = (index // columns) * cell_height
        target = "[labelled]" if index == len(with_video) - 1 else f"[step{index}]"
        filters.append(f"{current}[{len(with_video) + index}:v]overlay={origin_x}:{origin_y}{target}")
        current = target

    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            current,
            "-c:v",
            "libx264",
            "-crf",
            str(crf),
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            str(destination),
        ]
    )
    subprocess.run(command, check=True)
    if not destination.exists() or destination.stat().st_size == 0:
        raise RuntimeError("ffmpeg did not create the comparison video")
    return destination


def build_caption(
    candidates: Sequence[Candidate],
    destination: Path,
    *,
    title: str,
    question: str,
    has_video: bool,
) -> Path:
    letters = f"{candidates[0].letter}–{candidates[-1].letter}" if len(candidates) > 1 else candidates[0].letter
    lines = [f"**{title}**", "", question, ""]
    for candidate in candidates:
        evidence = candidate.video or candidate.still
        lines.append(f"- **{candidate.letter}** — {candidate.name} (`{evidence.name}`)")
    lines.extend(
        [
            "",
            "Letters match the sheet"
            + (" and the comparison video, left to right, top to bottom." if has_video else ", left to right, top to bottom."),
            f"Reply with a letter ({letters}) and a decision — keep / iterate / mutate / hold / archive / reject — plus any notes.",
        ]
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return destination


def _record(path: Path, root: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def build_packet(
    output_dir: Path,
    candidates: Sequence[Candidate],
    *,
    title: str,
    question: str,
    fps: int = 30,
    ffmpeg: Path | None = None,
) -> dict[str, Path]:
    """Build the sheet, comparison video, caption, and receipt for one round."""

    if not candidates:
        raise ValueError("at least one candidate is required")
    output_dir.mkdir(parents=True, exist_ok=True)
    with_video = [candidate for candidate in candidates if candidate.video is not None]
    if with_video:
        ffmpeg = ffmpeg or _discover_ffmpeg()

    stills: dict[str, Path] = {}
    for candidate in candidates:
        if candidate.still is not None:
            stills[candidate.letter] = candidate.still
        else:
            stills[candidate.letter] = _extract_still(
                ffmpeg, candidate.video, output_dir / "stills" / f"{candidate.letter}.png"
            )

    outputs: dict[str, Path] = {
        "contact_sheet": build_contact_sheet(candidates, stills, output_dir / "review-packet.png"),
        "caption": build_caption(
            candidates,
            output_dir / "review-packet.md",
            title=title,
            question=question,
            has_video=bool(with_video),
        ),
    }
    if with_video:
        outputs["comparison_video"] = build_comparison_video(
            ffmpeg, candidates, output_dir / "review-packet.mp4", fps=fps
        )

    receipt = {
        "schema_version": 1,
        "title": title,
        "question": question,
        "fps": fps,
        "candidates": [
            {
                "letter": candidate.letter,
                "name": candidate.name,
                "source": str(candidate.source),
                "video": _record(candidate.video, output_dir) if candidate.video else None,
                "still": _record(stills[candidate.letter], output_dir),
            }
            for candidate in candidates
        ],
        "artifacts": {key: _record(path, output_dir) for key, path in outputs.items()},
    }
    receipt_path = output_dir / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    outputs["receipt"] = receipt_path
    return outputs


def parse_candidates(specs: Sequence[str]) -> list[Candidate]:
    if not specs:
        raise ValueError("at least one --candidate NAME=PATH is required")
    if len(specs) > MAX_CANDIDATES:
        raise ValueError(f"at most {MAX_CANDIDATES} candidates per packet; split the round instead")
    candidates = []
    for index, spec in enumerate(specs):
        name, separator, raw_path = spec.partition("=")
        if not separator or not name.strip() or not raw_path.strip():
            raise ValueError(f"candidate spec must be NAME=PATH, got {spec!r}")
        candidates.append(resolve_candidate(string.ascii_uppercase[index], name.strip(), Path(raw_path.strip())))
    return candidates


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m houdini_ai.review_packet",
        description="Assemble one postable review packet from a round's candidates.",
    )
    parser.add_argument("--out", required=True, type=Path, help="packet output directory")
    parser.add_argument("--title", required=True, help="packet title, e.g. 'Study 004 — C2 compact options'")
    parser.add_argument("--question", required=True, help="the decision being asked of KC")
    parser.add_argument(
        "--candidate",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="candidate name and its file or round directory; repeat per candidate, letters assigned in order",
    )
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args(argv)

    candidates = parse_candidates(args.candidate)
    outputs = build_packet(args.out, candidates, title=args.title, question=args.question, fps=args.fps)
    for key, path in outputs.items():
        print(f"{key}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
