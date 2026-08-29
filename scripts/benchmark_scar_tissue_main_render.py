"""Benchmark one full-quality frame through the final portrait branch."""
import json
import time
from pathlib import Path

import hou

ROOT = Path(__file__).resolve().parents[1]
HIP = ROOT / "work/studio/handoffs/scar-tissue-abc-a-v1/scar-tissue-abc-a-handoff.hiplc"
OUTPUT = HIP.parent / "main-render-benchmark" / "scar-tissue-portrait-0473.exr"
RECEIPT = HIP.parent / "main-render-benchmark" / "receipt.json"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

hou.hipFile.load(str(HIP), suppress_save_prompt=True)
settings = hou.node("/stage/portrait_9x16_settings")
render = hou.node("/stage/portrait_9x16_render")
if settings is None or render is None:
    raise RuntimeError("missing final portrait branch")
settings.parm("picture").set(str(OUTPUT))
hou.setFrame(473)
started = time.perf_counter()
render.render(frame_range=(473, 473, 1))
elapsed = time.perf_counter() - started
if not OUTPUT.is_file() or OUTPUT.stat().st_size == 0:
    raise RuntimeError("benchmark EXR was not created")
report = {
    "hip": str(HIP),
    "frame": 473,
    "output": str(OUTPUT),
    "output_bytes": OUTPUT.stat().st_size,
    "elapsed_seconds": elapsed,
    "resolution": [settings.parm("resolutionx").eval(), settings.parm("resolutiony").eval()],
    "primary_samples": settings.parm("samplesperpixel").eval(),
    "path_traced_samples": settings.parm("pathtracedsamples").eval(),
    "denoiser": settings.parm("denoiser").evalAsString(),
    "renderer": render.parm("renderer").evalAsString(),
}
RECEIPT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
