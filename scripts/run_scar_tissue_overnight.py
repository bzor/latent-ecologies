from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "work/studio/lookdev/scar-tissue-grid-hairs-full-v1"
FRAMES = OUTPUT / "frames"
HYTHON = Path("C:/Program Files/Side Effects Software/Houdini 22.0.368/bin/hython.exe")


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    FRAMES.mkdir(exist_ok=True)
    frames = list(range(1, 301))
    command = [
        str(HYTHON),
        str(ROOT / "houdini/render_scar_tissue_grid_look.py"),
        str(ROOT / "work/studio/probes/scar-tissue/directional-refractory-v3/cache"),
        str(ROOT / "work/studio/probes/scar-tissue/directional-refractory-v3/metrics.json"),
        str(OUTPUT),
        "--frames",
        ",".join(str(frame) for frame in frames),
        "--width",
        "720",
        "--samples",
        "8",
    ]
    env = {**os.environ, "HOUDINI_TEMP_DIR": str(OUTPUT / "temp")}
    result = subprocess.run(command, env=env, check=False)
    if result.returncode:
        return result.returncode

    encode = OUTPUT / "encode-frames"
    encode.mkdir(exist_ok=True)
    for index, path in enumerate(sorted(FRAMES.glob("frame-*.png"))):
        shutil.copy2(path, encode / f"frame-{index:04d}.png")
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-framerate", "30",
            "-i", str(encode / "frame-%04d.png"), "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(OUTPUT / "scar-tissue-grid-hairs-full.mp4"),
        ],
        check=False,
    )
    if result.returncode:
        return result.returncode
    receipt_path = OUTPUT / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    files = [OUTPUT / "scar-tissue-grid-hairs-full.mp4", OUTPUT / "scar-tissue-grid-look.hiplc", *sorted(FRAMES.glob("*.png"))]
    receipt["rendered_artifacts"] = {
        path.relative_to(OUTPUT).as_posix(): {
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in files
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
