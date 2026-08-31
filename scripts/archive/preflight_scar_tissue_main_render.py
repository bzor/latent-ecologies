"""Read-only preflight for the final Scar Tissue portrait sequence."""
import json
import re
import sys
from pathlib import Path

import hou
from pxr import UsdLux

hip = Path(sys.argv[1]).resolve()
hou.hipFile.load(str(hip), suppress_save_prompt=True)
stage = hou.node("/stage")
settings = stage.node("portrait_9x16_settings")
render = stage.node("portrait_9x16_render")
camera = stage.node("CAM_EDIT_ABC_A_PORTRAIT")
if None in (stage, settings, render, camera):
    raise RuntimeError("missing final portrait render branch")
hou.setFrame(473)
usd_stage = settings.stage()
lights = sorted(
    str(prim.GetPath())
    for prim in usd_stage.Traverse()
    if prim.HasAPI(UsdLux.LightAPI)
)
interesting = re.compile(r"sample|noise|denois|resolution|picture|camera|engine|device|checkpoint", re.I)
settings_parms = {
    parm.name(): {
        "label": parm.parmTemplate().label(),
        "value": parm.evalAsString(),
    }
    for parm in settings.parms()
    if interesting.search(parm.name()) or interesting.search(parm.parmTemplate().label())
}
render_parms = {
    parm.name(): {
        "label": parm.parmTemplate().label(),
        "value": parm.evalAsString(),
    }
    for parm in render.parms()
    if parm.name() in {"renderer", "trange", "f1", "f2", "f3", "soho_foreground", "mkpath"}
    or interesting.search(parm.name())
    or interesting.search(parm.parmTemplate().label())
}
report = {
    "hip": str(hip),
    "fps": hou.fps(),
    "playback_range": list(hou.playbar.playbackRange()),
    "frame_range": list(hou.playbar.frameRange()),
    "camera_prim": settings.parm("camera").eval(),
    "camera_valid": usd_stage.GetPrimAtPath(settings.parm("camera").eval()).IsValid(),
    "lights": lights,
    "settings_input": settings.input(0).path(),
    "render_input": render.input(0).path(),
    "settings_errors": list(settings.errors()),
    "render_errors": list(render.errors()),
    "settings": settings_parms,
    "render": render_parms,
}
print(json.dumps(report, indent=2))
if not report["camera_valid"] or len(lights) != 3 or report["settings_errors"] or report["render_errors"]:
    raise RuntimeError("final portrait branch failed preflight")
