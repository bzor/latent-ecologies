"""Render one low-cost Karma frame to verify pointed direction hairs."""
from pathlib import Path

import hou

ROOT = Path(__file__).resolve().parents[1]
HIP = ROOT / "work/studio/handoffs/scar-tissue-abc-a-v1/scar-tissue-abc-a-handoff.hiplc"
OUTPUT = HIP.parent / "pointed-hair-verification-f0473.png"

hou.hipFile.load(str(HIP), suppress_save_prompt=True)
settings = hou.node("/stage/portrait_9x16_settings")
render = hou.node("/stage/portrait_9x16_render")
if settings is None or render is None:
    raise RuntimeError("missing portrait render branch")
settings.parm("resolutionx").set(360)
settings.parm("samplesperpixel").set(6)
settings.parm("picture").set(str(OUTPUT))
hou.setFrame(473)
render.render(frame_range=(473, 473, 1))
if not OUTPUT.is_file() or OUTPUT.stat().st_size == 0:
    raise RuntimeError("pointed-hair verification render was not created")
print(OUTPUT)
