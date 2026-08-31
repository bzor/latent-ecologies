"""Render one low-cost portrait lighting verification frame without saving HIP changes."""
from pathlib import Path

import hou

ROOT = Path(__file__).resolve().parents[1]
HIP = ROOT / "work/studio/handoffs/scar-tissue-abc-a-v1/scar-tissue-abc-a-handoff.hiplc"
OUTPUT = HIP.parent / "portrait-lighting-verification-f0473.png"

hou.hipFile.load(str(HIP), suppress_save_prompt=True)
settings = hou.node("/stage/portrait_9x16_settings")
render = hou.node("/stage/portrait_9x16_render")
if settings is None or render is None:
    raise RuntimeError("missing portrait render branch")
settings.parm("resolutionx").set(360)
settings.parm("samplesperpixel").set(4)
settings.parm("picture").set(str(OUTPUT))
hou.setFrame(473)
render.render(frame_range=(473, 473, 1))
if not OUTPUT.is_file() or OUTPUT.stat().st_size == 0:
    raise RuntimeError("portrait lighting verification render was not created")
print(OUTPUT)
