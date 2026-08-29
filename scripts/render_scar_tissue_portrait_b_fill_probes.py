import hou
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HIP = ROOT / "work/studio/handoffs/scar-tissue-abc-a-v1/scar-tissue-abc-a-handoff.hiplc"
OUT = HIP.parent
hou.hipFile.load(str(HIP), suppress_save_prompt=True)
stage = hou.node("/stage")
source = stage.node("CAM_EDIT_ABC_A_PORTRAIT")
camera = hou.copyNodesTo((source,), stage)[0]
camera.setName("PORTRAIT_B_FILL_PROBE", unique_name=True); camera.parm("primpath").set("/cameras/portrait_b_fill_probe")
for name in ("ty", "rx", "focalLength"):
    camera.parm(name).deleteAllKeyframes()
for frame, ty in ((316, 4.75), (630, 4.55)):
    for parm, value in (("ty", ty), ("rx", -24.0), ("focalLength", 115.0)):
        key=hou.Keyframe(); key.setFrame(frame); key.setValue(value); key.setExpression("linear()", hou.exprLanguage.Hscript); camera.parm(parm).setKeyframe(key)
settings=hou.copyNodesTo((stage.node("portrait_9x16_settings"),),stage)[0]; settings.setName("portrait_b_fill_probe_settings"); settings.setInput(0,camera); settings.parm("camera").set("/cameras/portrait_b_fill_probe"); settings.parm("resolutionx").set(720); settings.parm("samplesperpixel").set(10)
rop=hou.copyNodesTo((stage.node("portrait_9x16_render"),),stage)[0]; rop.setName("portrait_b_fill_probe_render"); rop.setInput(0,settings)
for frame in (316,473,630):
    hou.setFrame(frame); settings.parm("picture").set(str(OUT/f"portrait-b-fill-probe-{frame:04d}.png")); rop.render(frame_range=(frame,frame,1))
