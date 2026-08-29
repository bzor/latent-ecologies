import hou

hip = r"E:/Projects/houdini-ai/work/studio/handoffs/scar-tissue-abc-a-v1/scar-tissue-abc-a-handoff.hiplc"
out = r"E:/Projects/houdini-ai/work/studio/handoffs/scar-tissue-abc-a-v1"
hou.hipFile.load(hip, suppress_save_prompt=True)
stage = hou.node("/stage")
source = stage.node("CAM_EDIT_ABC_A")
camera = hou.copyNodesTo((source,), stage)[0]
camera.setName("PORTRAIT_CROP_PROBE", unique_name=True)
camera.parm("primpath").set("/cameras/portrait_crop_probe")
camera.parm("aspectratiox").set(9)
camera.parm("aspectratioy").set(16)
for key in camera.parm("focalLength").keyframes():
    key.setValue(key.value() * 2.4363233665559245)
    camera.parm("focalLength").setKeyframe(key)
settings = stage.createNode("karmarendersettings", "portrait_crop_probe_settings")
settings.setInput(0, camera)
settings.parm("camera").set("/cameras/portrait_crop_probe")
settings.parm("res_mode").set("autoheight")
settings.parm("resolutionx").set(720)
settings.parm("samplesperpixel").set(8)
rop = stage.createNode("usdrender_rop", "portrait_crop_probe_render")
rop.setInput(0, settings)
rop.parm("renderer").set("Karma XPU")
rop.parm("soho_foreground").set(True)
rop.parm("mkpath").set(True)
for frame in (158, 473, 788, 1103):
    hou.setFrame(frame)
    settings.parm("picture").set(f"{out}/portrait-true-crop-probe-{frame:04d}.png")
    rop.render(frame_range=(frame, frame, 1))
