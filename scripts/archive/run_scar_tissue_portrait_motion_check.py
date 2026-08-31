from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HYTHON = Path("C:/Program Files/Side Effects Software/Houdini 22.0.368/bin/hython.exe")
HANDOFF = ROOT / "work/studio/handoffs/scar-tissue-abc-a-v1"
OUTPUT = HANDOFF / "portrait-motion-check"
CACHE = ROOT / "work/studio/probes/scar-tissue/directional-refractory-v3/cache"
METRICS = ROOT / "work/studio/probes/scar-tissue/directional-refractory-v3/metrics.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    shutil.rmtree(OUTPUT, ignore_errors=True)
    OUTPUT.mkdir(parents=True)
    frames = list(range(1, 1261, 3))
    command = [
        str(HYTHON), str(ROOT / "houdini/render_scar_tissue_motion_check.py"),
        str(CACHE), str(METRICS), str(OUTPUT),
        "--frames", ",".join(str(frame) for frame in frames),
        "--portrait-edit", "--reuse-derived", "--derived-dir", str(HANDOFF), "--width", "360",
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    encode = OUTPUT / "encode"
    encode.mkdir()
    for index, frame in enumerate(frames, 1):
        shutil.copy2(OUTPUT / "frames" / f"motion.{frame:04d}.png", encode / f"frame-{index:04d}.png")
    media = OUTPUT / "scar-tissue-abc-a-portrait-motion-check.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", "15", "-i", str(encode / "frame-%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(media),
    ], cwd=ROOT, check=True)
    receipt = json.loads((OUTPUT / "receipt.json").read_text(encoding="utf-8"))
    receipt.update({
        "source_frame_range": [1, 1260], "sample_stride": 3, "sampled_frame_count": len(frames),
        "source_fps": 45, "output_fps": 15, "duration_seconds": 28.0,
        "media": {"path": media.name, "bytes": media.stat().st_size, "sha256": sha(media)},
    })
    (OUTPUT / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(media.resolve())


if __name__ == "__main__": main()
