import hou

HIP = r"E:/Projects/houdini-ai/work/studio/handoffs/scar-tissue-abc-a-v1/scar-tissue-abc-a-handoff.hiplc"
OUT = r"E:/Projects/houdini-ai/work/studio/handoffs/scar-tissue-abc-a-v1"
FRAMES = {158: 100.0, 473: 105.0, 788: 130.0, 1103: 100.0}

hou.hipFile.load(HIP, suppress_save_prompt=True)
stage = hou.node("/stage")
source = stage.node("CAM_EDIT_ABC_A")
camera = hou.copyNodesTo((source,), stage)[0]
camera.setName("PORTRAIT_FOCAL_PROBE", unique_name=True)
camera.parm("primpath").set("/cameras/portrait_focal_probe")
camera.parm("aspectratiox").set(9)
camera.parm("aspectratioy").set(16)
camera.parm("focalLength").deleteAllKeyframes()
settings = stage.createNode("karmarendersettings", "portrait_focal_probe_settings")
settings.setInput(0, camera)
settings.parm("camera").set("/cameras/portrait_focal_probe")
settings.parm("res_mode").set("autoheight")
settings.parm("resolutionx").set(720)
settings.parm("samplesperpixel").set(8)
rop = stage.createNode("usdrender_rop", "portrait_focal_probe_render")
rop.setInput(0, settings)
rop.parm("renderer").set("Karma XPU")
rop.parm("soho_foreground").set(True)
rop.parm("mkpath").set(True)
for frame, focal in FRAMES.items():
    hou.setFrame(frame)
    camera.parm("focalLength").set(focal)
    settings.parm("picture").set(f"{OUT}/portrait-focal-probe-{frame:04d}.png")
    rop.render(frame_range=(frame, frame, 1))
