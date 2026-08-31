"""Render final-quality gate frames for A1, C, and A2."""
import json
import time
from pathlib import Path

import hou

ROOT = Path(__file__).resolve().parents[1]
HIP = ROOT / "work/studio/handoffs/scar-tissue-abc-a-v1/scar-tissue-abc-a-handoff.hiplc"
OUTPUT = HIP.parent / "main-render-gate"
OUTPUT.mkdir(parents=True, exist_ok=True)
FRAMES = (158, 788, 1103)
MINIMUM_COMPLETE_BYTES = 1_000_000


def frame_path(frame: int) -> Path:
    return OUTPUT / f"scar-tissue-portrait-{frame:04d}.exr"


def complete(frame: int) -> bool:
    target = frame_path(frame)
    return target.is_file() and target.stat().st_size >= MINIMUM_COMPLETE_BYTES

hou.hipFile.load(str(HIP), suppress_save_prompt=True)
settings = hou.node("/stage/portrait_9x16_settings")
render = hou.node("/stage/portrait_9x16_render")
if settings is None or render is None:
    raise RuntimeError("missing final portrait branch")
records = []
for frame in FRAMES:
    target = frame_path(frame)
    if complete(frame):
        record = {
            "frame": frame,
            "output": str(target),
            "bytes": target.stat().st_size,
            "reused": True,
        }
        records.append(record)
        print(json.dumps(record), flush=True)
        continue
    settings.parm("picture").set(str(target))
    hou.setFrame(frame)
    started = time.perf_counter()
    render.render(frame_range=(frame, frame, 1))
    elapsed = time.perf_counter() - started
    if not target.is_file() or target.stat().st_size == 0:
        raise RuntimeError(f"gate frame was not created: {frame}")
    record = {
        "frame": frame,
        "output": str(target),
        "bytes": target.stat().st_size,
        "elapsed_seconds": elapsed,
    }
    records.append(record)
    print(json.dumps(record), flush=True)
    partial_receipt = {
        "hip": str(HIP),
        "frames": records,
        "complete": False,
    }
    (OUTPUT / "receipt.json").write_text(
        json.dumps(partial_receipt, indent=2) + "\n", encoding="utf-8"
    )
receipt = {
    "hip": str(HIP),
    "frames": records,
    "resolution": [settings.parm("resolutionx").eval(), settings.parm("resolutiony").eval()],
    "primary_samples": settings.parm("samplesperpixel").eval(),
    "path_traced_samples": settings.parm("pathtracedsamples").eval(),
    "denoiser": settings.parm("denoiser").evalAsString(),
    "renderer": render.parm("renderer").evalAsString(),
    "complete": True,
}
(OUTPUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
