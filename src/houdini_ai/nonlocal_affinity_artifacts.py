"""Neutral diagnostic media packaging for VEX-authoritative affinity trajectories."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_motion_check(
    trajectory_path: Path,
    output_dir: Path,
    *,
    fps: int = 20,
    size: tuple[int, int] = (550, 550),
    ffmpeg: str = "ffmpeg",
) -> dict[str, object]:
    """Render a source-neutral fixed camera diagnostic and encode it."""

    trajectory = json.loads(Path(trajectory_path).read_text(encoding="utf-8"))
    if trajectory.get("state_authority") != "vex-geometry":
        raise ValueError("motion checks require a VEX-authoritative trajectory")
    frames = trajectory.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError("trajectory requires at least one frame")
    if fps < 1 or size[0] < 16 or size[1] < 16:
        raise ValueError("invalid motion-check fps or dimensions")

    output_dir = Path(output_dir)
    frame_dir = output_dir / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    for stale in frame_dir.glob("frame-*.png"):
        stale.unlink()

    width, height = size
    for frame_index, frame in enumerate(frames):
        image = Image.new("RGB", size, (244, 244, 240))
        draw = ImageDraw.Draw(image)
        for position in frame["positions"]:
            px = round((float(position[0]) + 2.0) / 4.0 * (width - 1))
            py = round((2.0 - float(position[1])) / 4.0 * (height - 1))
            if -2 <= px <= width + 1 and -2 <= py <= height + 1:
                draw.ellipse((px - 1, py - 1, px + 1, py + 1), fill=(12, 12, 11))
        image.save(frame_dir / f"frame-{frame_index:04d}.png")

    motion_path = output_dir / "motion-check.mp4"
    result = subprocess.run(
        [
            ffmpeg, "-y", "-v", "error", "-framerate", str(fps),
            "-i", str(frame_dir / "frame-%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(motion_path),
        ],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if result.returncode != 0 or not motion_path.is_file():
        raise RuntimeError(f"FFmpeg motion-check encoding failed: {result.stdout}{result.stderr}")

    checksummed = [motion_path, frame_dir / "frame-0000.png", frame_dir / f"frame-{len(frames) - 1:04d}.png"]
    receipt: dict[str, object] = {
        "schema_version": 1,
        "operation": "nonlocal-affinity-motion-check",
        "state_authority": "vex-geometry",
        "render_style": "neutral-fixed-range-points",
        "plot_range": [-2.0, 2.0],
        "frame_count": len(frames),
        "fps": fps,
        "dimensions": [width, height],
        "motion_check": motion_path.name,
        "sha256": {
            str(path.relative_to(output_dir)).replace("\\", "/"): _sha256(path)
            for path in checksummed
        },
    }
    (output_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt
