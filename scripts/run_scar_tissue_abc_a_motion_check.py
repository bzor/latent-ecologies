from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HYTHON = Path("C:/Program Files/Side Effects Software/Houdini 22.0.368/bin/hython.exe")
SOURCE = ROOT / "work/studio/probes/scar-tissue/directional-refractory-v3"
OUTPUT = ROOT / "work/studio/handoffs/scar-tissue-abc-a-v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    frames = list(range(1, 1261, 3))
    command = [
        str(HYTHON), str(ROOT / "houdini/render_scar_tissue_motion_check.py"),
        str(SOURCE / "cache"), str(SOURCE / "metrics.json"), str(OUTPUT),
        "--frames", ",".join(str(frame) for frame in frames), "--edit-camera", "--reuse-derived", "--width", "480",
    ]
    result = subprocess.run(command, check=False)
    if result.returncode:
        return result.returncode
    encode = OUTPUT / "encode-motion"
    shutil.rmtree(encode, ignore_errors=True)
    encode.mkdir()
    for index, frame in enumerate(frames):
        source = OUTPUT / "frames" / f"motion.{frame:04d}.png"
        if not source.is_file():
            raise FileNotFoundError(f"missing motion frame: {source}")
        shutil.copy2(source, encode / f"motion.{index:04d}.png")
    media = OUTPUT / "scar-tissue-abc-a-motion-check.mp4"
    result = subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", "15", "-i",
        str(encode / "motion.%04d.png"), "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(media),
    ], check=False)
    if result.returncode:
        return result.returncode
    receipt_path = OUTPUT / "motion-check-receipt.json"
    receipt = {
        "schema_version": 1, "operation": "motion-check", "render_engine": "software-flat-proxy",
        "source_authority": "vex-geometry-cache", "source_frame_range": [1, 1260], "source_fps": 30,
        "sample_interval": 3, "sampled_frames": frames, "frame_count": len(frames),
        "output_fps": 15, "speed_multiplier": 1.5, "duration_seconds": 28.0,
        "camera_edit": "A-B-C-A", "cuts": [1, 316, 631, 946], "karma_invoked": False,
        "media": {"path": media.name, "bytes": media.stat().st_size, "sha256": sha(media)},
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(media.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
