import sys
from pathlib import Path

import hou

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from houdini_ai.scar_tissue_edit import SHOTS, portrait_camera_at_frame

HIP = ROOT / "work/studio/handoffs/scar-tissue-abc-a-v1/scar-tissue-abc-a-handoff.hiplc"
OUT = HIP.parent
hou.hipFile.load(str(HIP), suppress_save_prompt=True)
stage = hou.node("/stage")
source = stage.node("CAM_EDIT_ABC_A_PORTRAIT")
camera = hou.copyNodesTo((source,), stage)[0]
camera.setName("PORTRAIT_TIGHT_FILL_PROBE", unique_name=True)
camera.parm("primpath").set("/cameras/portrait_tight_fill_probe")
for name in ("tx", "ty", "tz", "rx", "ry", "focalLength"):
    camera.parm(name).deleteAllKeyframes()
for shot in SHOTS:
    for frame in shot["frames"]:
        values = portrait_camera_at_frame(frame)
        for parm_name, source_name in (("tx", "tx"), ("ty", "ty"), ("tz", "tz"), ("rx", "rx"), ("ry", "ry"), ("focalLength", "focal_length")):
            key = hou.Keyframe(); key.setFrame(frame); key.setValue(float(values[source_name])); key.setExpression("linear()", hou.exprLanguage.Hscript); camera.parm(parm_name).setKeyframe(key)
settings = hou.copyNodesTo((stage.node("portrait_9x16_settings"),), stage)[0]
settings.setName("portrait_tight_fill_probe_settings")
settings.setInput(0, camera); settings.parm("camera").set("/cameras/portrait_tight_fill_probe")
settings.parm("resolutionx").set(720); settings.parm("samplesperpixel").set(10)
rop = hou.copyNodesTo((stage.node("portrait_9x16_render"),), stage)[0]
rop.setName("portrait_tight_fill_probe_render"); rop.setInput(0, settings)
for frame in (1, 158, 315, 316, 473, 630, 631, 788, 945, 946, 1103, 1260):
    hou.setFrame(frame); settings.parm("picture").set(str(OUT / f"portrait-tight-probe-{frame:04d}.png")); rop.render(frame_range=(frame, frame, 1))
