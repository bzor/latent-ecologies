"""Render the Mass Flow lookdev at the six-fps review cadence and encode an MP4."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("cache_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--hdri", type=Path, required=True)
    parser.add_argument("--renderer", choices=("cpu", "xpu"), default="xpu")
    parser.add_argument("--frame-start", type=int, default=1)
    parser.add_argument("--frame-end", type=int, default=600)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output_dir = args.output_dir.resolve()
    frames_dir = output_dir / "frames"
    hip_dir = output_dir / "hips"
    frames_dir.mkdir(parents=True, exist_ok=True)
    hip_dir.mkdir(parents=True, exist_ok=True)
    frame_numbers = range(args.frame_start, args.frame_end + 1)
    renderer = root / "houdini" / "render_mass_flow_trails.py"
    for index, frame in enumerate(frame_numbers, 1):
        image = frames_dir / f"mass-flow-lookdev.{index:04d}.png"
        hip = hip_dir / f"mass-flow-lookdev.{index:04d}.hip"
        command = [
            sys.executable, str(renderer), str(args.config.resolve()), str(args.cache_dir.resolve()), str(hip), str(image),
            "--hdri", str(args.hdri.resolve()), "--renderer", args.renderer, "--end-frame", str(frame), "--skip-existing",
        ]
        print(f"[{index:03d}/{len(frame_numbers):03d}] frame {frame:04d}", flush=True)
        result = subprocess.run(command, env=os.environ.copy(), check=False)
        if result.returncode:
            raise SystemExit(result.returncode)

    ffmpeg = os.environ.get("HDAI_FFMPEG", "ffmpeg")
    output = output_dir / "mass-flow-20s-lookdev.mp4"
    if args.frame_start != 1 or args.frame_end != 600:
        return
    command = [
        ffmpeg, "-y", "-framerate", "30", "-i", str(frames_dir / "mass-flow-lookdev.%04d.png"),
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
    ]
    subprocess.run(command, check=True)
    print(f"video: {output}")


if __name__ == "__main__":
    main()
