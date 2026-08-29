"""Render neutral, fixed-camera review media for 3D Nonlocal Affinity caches."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


BRANCHES = (
    ("tight-swirls", "Tight Swirls"),
    ("wide-swirls-outliers", "Wide Swirls w/ Outliers"),
    ("cohesive-swirl", "Cohesive Swirl"),
)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    try:
        return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)
    except OSError:
        return ImageFont.load_default()


def _project(point: list[float], projection: str) -> tuple[float, float]:
    x, y, z = point
    if projection == "xy":
        return x, y
    if projection != "fixed-isometric":
        raise ValueError(f"unsupported projection: {projection}")
    return ((x - z) / math.sqrt(2.0), (x + z - 2.0 * y) / math.sqrt(6.0))


def _load_reviews(
    root: Path, branches: tuple[tuple[str, str], ...],
) -> tuple[list[int], dict[str, list[dict[str, Any]]]]:
    reviews: dict[str, list[dict[str, Any]]] = {}
    steps: list[int] | None = None
    for slug, _title in branches:
        payload = json.loads((root / slug / "review.json").read_text(encoding="utf-8"))
        frames = payload["frames"]
        branch_steps = [int(frame["step"]) for frame in frames]
        if steps is None:
            steps = branch_steps
        elif branch_steps != steps:
            raise RuntimeError("review branches do not share a checkpoint schedule")
        reviews[slug] = frames
    return steps or [], reviews


def _bounds(reviews: dict[str, list[dict[str, Any]]], projection: str) -> tuple[float, float, float, float]:
    projected = [
        _project(point, projection)
        for frames in reviews.values()
        for frame in frames
        for point in frame["points"]
    ]
    us = [point[0] for point in projected]
    vs = [point[1] for point in projected]
    return min(us), min(vs), max(us), max(vs)


def render_comparison(
    root: Path,
    output: Path,
    *,
    hold_frames: int = 4,
    fps: int = 12,
    heading: str = "Study 003 | 100k point-agent comparison",
    label_suffix: str = "",
    point_size: int = 1,
    trail_alpha: float = 1.0,
    projection: str = "fixed-isometric",
    population_count: int = 100000,
    branches: tuple[tuple[str, str], ...] = BRANCHES,
    video_name: str = "affinity-3d-100k-neutral-comparison.mp4",
) -> dict[str, Any]:
    if len(branches) != 3:
        raise ValueError("comparison renderer requires exactly three branches")
    if Path(video_name).name != video_name or not video_name.endswith(".mp4"):
        raise ValueError("video_name must be a local .mp4 filename")
    steps, reviews = _load_reviews(root, branches)
    if not steps:
        raise RuntimeError("no review checkpoints found")
    output.mkdir(parents=True, exist_ok=True)
    frame_dir = output / "frames"
    frame_dir.mkdir(exist_ok=True)
    panel_width, panel_height = 480, 480
    header_height, footer_height, gap, margin = 72, 38, 12, 16
    width = margin * 2 + panel_width * 3 + gap * 2
    height = header_height + panel_height + footer_height
    u_min, v_min, u_max, v_max = _bounds(reviews, projection)
    span = max(u_max - u_min, v_max - v_min, 1e-9)
    scale = panel_width * 0.88 / span
    u_center, v_center = (u_min + u_max) * 0.5, (v_min + v_max) * 0.5
    sample_count = len(reviews[branches[0][0]][0]["points"])
    sample_note = (
        f"all {population_count} points"
        if sample_count == population_count
        else f"{sample_count} deterministic sample of {population_count}"
    )
    title_font, label_font, meta_font = _font(24, True), _font(18, True), _font(14)
    panel_background = Image.new("RGB", (panel_width, panel_height), (12, 17, 24))
    panel_histories = [panel_background.copy() for _branch in branches]
    rendered = 0
    last_image: Image.Image | None = None
    for frame_index, step in enumerate(steps):
        image = Image.new("RGB", (width, height), (8, 11, 16))
        draw = ImageDraw.Draw(image)
        display_note = "no trails" if trail_alpha >= 0.999 else f"persistence α {trail_alpha:.2f}"
        projection_note = "Canvas XY" if projection == "xy" else "fixed isometric"
        draw.text((margin, 14), heading, font=title_font, fill=(236, 241, 247))
        draw.text(
            (margin, 45),
            f"step {step:03d}/{steps[-1]} · {projection_note} · {sample_note} · {display_note} · no interpolation",
            font=meta_font,
            fill=(139, 153, 171),
        )
        for branch_index, (slug, title) in enumerate(branches):
            left = margin + branch_index * (panel_width + gap)
            top = header_height
            if trail_alpha >= 0.999:
                panel = panel_background.copy()
            else:
                panel = Image.blend(panel_histories[branch_index], panel_background, trail_alpha)
            panel_draw = ImageDraw.Draw(panel)
            points = reviews[slug][frame_index]["points"]
            pixels = []
            for point in points:
                u, v = _project(point, projection)
                px = int(panel_width * 0.5 + (u - u_center) * scale)
                py = int(panel_height * 0.5 - (v - v_center) * scale)
                if 0 <= px < panel_width and 0 <= py < panel_height:
                    pixels.append((px, py))
            if point_size <= 1:
                panel_draw.point(pixels, fill=(226, 232, 240))
            else:
                radius = point_size // 2
                for px, py in pixels:
                    panel_draw.rectangle((px - radius, py - radius, px - radius + point_size - 1, py - radius + point_size - 1), fill=(226, 232, 240))
            panel_histories[branch_index] = panel
            image.paste(panel, (left, top))
            draw.rectangle((left, top, left + panel_width - 1, top + panel_height - 1), outline=(42, 50, 61))
            draw.text((left + 10, top + 10), title + label_suffix, font=label_font, fill=(236, 241, 247))
        draw.text(
            (margin, header_height + panel_height + 10),
            "Behavior evidence only. Particle geometry, size, trails, lighting, and camera remain unselected Look parameters.",
            font=meta_font,
            fill=(139, 153, 171),
        )
        last_image = image
        for _ in range(hold_frames):
            image.save(frame_dir / f"frame-{rendered:04d}.png")
            rendered += 1
    if last_image is None:
        raise RuntimeError("review renderer produced no frames")
    contact_sheet = output / "final-checkpoint.png"
    last_image.save(contact_sheet)
    video = output / video_name
    completed = subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-framerate", str(fps), "-i", str(frame_dir / "frame-%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(video),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(f"ffmpeg failed: {completed.stderr}")
    receipt = {
        "schema_version": 1,
        "source": f"three VEX-authoritative {population_count}-point simulations",
        "population_count_per_branch": population_count,
        "review_sample_count_per_branch": sample_count,
        "branches": [{"slug": slug, "title": title} for slug, title in branches],
        "checkpoint_steps": steps,
        "projection": projection,
        "interpolation": "none",
        "trails": "none" if trail_alpha >= 0.999 else f"framebuffer persistence alpha {trail_alpha}",
        "point_size": point_size,
        "fps": fps,
        "hold_frames_per_checkpoint": hold_frames,
        "heading": heading,
        "label_suffix": label_suffix,
        "video": video.name,
        "contact_sheet": contact_sheet.name,
    }
    (output / "review-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def render_single_review(
    source: Path,
    output: Path,
    *,
    title: str,
    hold_frames: int = 1,
    fps: int = 24,
    heading: str = "Study 003 | Parallel cohort endurance check",
    point_size: int = 1,
    trail_alpha: float = 0.18,
    projection: str = "fixed-isometric",
    population_count: int = 100000,
    video_name: str = "parallel-cohort-endurance.mp4",
) -> dict[str, Any]:
    if Path(video_name).name != video_name or not video_name.endswith(".mp4"):
        raise ValueError("video_name must be a local .mp4 filename")
    payload = json.loads((source / "review.json").read_text(encoding="utf-8"))
    frames = payload["frames"]
    if not frames:
        raise RuntimeError("no review checkpoints found")
    steps = [int(frame["step"]) for frame in frames]
    if steps != sorted(set(steps)):
        raise RuntimeError("review checkpoints must be unique and ordered")
    output.mkdir(parents=True, exist_ok=True)
    frame_dir = output / "frames"
    frame_dir.mkdir(exist_ok=True)
    projected = [_project(point, projection) for frame in frames for point in frame["points"]]
    us = [point[0] for point in projected]
    vs = [point[1] for point in projected]
    span = max(max(us) - min(us), max(vs) - min(vs), 1e-9)
    u_center = (min(us) + max(us)) * 0.5
    v_center = (min(vs) + max(vs)) * 0.5
    panel_width, panel_height = 960, 720
    header_height, footer_height, margin = 78, 40, 18
    width, height = panel_width + margin * 2, panel_height + header_height + footer_height
    scale = min(panel_width, panel_height) * 0.88 / span
    background = Image.new("RGB", (panel_width, panel_height), (12, 17, 24))
    history = background.copy()
    title_font, label_font, meta_font = _font(24, True), _font(18, True), _font(14)
    rendered = 0
    last_image: Image.Image | None = None
    for frame in frames:
        step = int(frame["step"])
        panel = background.copy() if trail_alpha >= 0.999 else Image.blend(history, background, trail_alpha)
        panel_draw = ImageDraw.Draw(panel)
        pixels = []
        for point in frame["points"]:
            u, v = _project(point, projection)
            px = int(panel_width * 0.5 + (u - u_center) * scale)
            py = int(panel_height * 0.5 - (v - v_center) * scale)
            if 0 <= px < panel_width and 0 <= py < panel_height:
                pixels.append((px, py))
        if point_size <= 1:
            panel_draw.point(pixels, fill=(226, 232, 240))
        else:
            radius = point_size // 2
            for px, py in pixels:
                panel_draw.rectangle((px - radius, py - radius, px + radius, py + radius), fill=(226, 232, 240))
        history = panel
        image = Image.new("RGB", (width, height), (8, 11, 16))
        draw = ImageDraw.Draw(image)
        draw.text((margin, 14), heading, font=title_font, fill=(236, 241, 247))
        draw.text(
            (margin, 47),
            f"{title} · genuine step {step:03d}/{steps[-1]} · {len(frame['points'])} stratified points of {population_count} · no interpolation",
            font=meta_font,
            fill=(139, 153, 171),
        )
        image.paste(panel, (margin, header_height))
        draw.rectangle((margin, header_height, margin + panel_width - 1, header_height + panel_height - 1), outline=(42, 50, 61))
        draw.text(
            (margin, header_height + panel_height + 10),
            "Behavior endurance evidence only. The run uses shallow-3D VEX state. Look, palette, lighting, and camera remain deferred.",
            font=meta_font,
            fill=(139, 153, 171),
        )
        last_image = image
        for _ in range(hold_frames):
            image.save(frame_dir / f"frame-{rendered:04d}.png")
            rendered += 1
    if last_image is None:
        raise RuntimeError("review renderer produced no frames")
    contact_sheet = output / "final-checkpoint.png"
    last_image.save(contact_sheet)
    video = output / video_name
    completed = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-framerate", str(fps),
         "-i", str(frame_dir / "frame-%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", str(video)],
        capture_output=True, text=True, check=False,
    )
    if completed.returncode:
        raise RuntimeError(f"ffmpeg failed: {completed.stderr}")
    receipt = {
        "schema_version": 1,
        "source": "one VEX-authoritative endurance simulation",
        "title": title,
        "population_count": population_count,
        "review_sample_count": len(frames[0]["points"]),
        "checkpoint_steps": steps,
        "total_steps": steps[-1],
        "projection": projection,
        "interpolation": "none",
        "trails": "none" if trail_alpha >= 0.999 else f"framebuffer persistence alpha {trail_alpha}",
        "point_size": point_size,
        "fps": fps,
        "hold_frames_per_checkpoint": hold_frames,
        "video": video.name,
        "contact_sheet": contact_sheet.name,
    }
    (output / "review-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--hold-frames", type=int, default=4)
    parser.add_argument("--heading", default="Study 003 | 100k point-agent comparison")
    parser.add_argument("--label-suffix", default="")
    parser.add_argument("--point-size", type=int, default=1)
    parser.add_argument("--trail-alpha", type=float, default=1.0)
    parser.add_argument("--projection", choices=("fixed-isometric", "xy"), default="fixed-isometric")
    parser.add_argument("--population-count", type=int, default=100000)
    args = parser.parse_args()
    print(json.dumps(render_comparison(
        args.root,
        args.output,
        fps=args.fps,
        hold_frames=args.hold_frames,
        heading=args.heading,
        label_suffix=args.label_suffix,
        point_size=args.point_size,
        trail_alpha=args.trail_alpha,
        projection=args.projection,
        population_count=args.population_count,
    ), sort_keys=True))


if __name__ == "__main__":
    main()
