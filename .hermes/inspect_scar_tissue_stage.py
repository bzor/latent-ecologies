import json
import sys
from pathlib import Path

import hou
from pxr import UsdLux

hip = Path(sys.argv[1]).resolve()
hou.hipFile.load(str(hip), suppress_save_prompt=True)
stage = hou.node("/stage")
selected = [
    "dome_fill",
    "grazing_area_key",
    "cool_rim",
    "assign_neutral_materials",
    "PORTRAIT_VIEW_A_CTRL",
    "PORTRAIT_VIEW_B_CTRL",
    "PORTRAIT_VIEW_C_CTRL",
    "CAM_EDIT_ABC_A",
    "grid_look_settings",
    "grid_look_render",
    "CAM_EDIT_ABC_A_PORTRAIT",
    "portrait_9x16_settings",
    "portrait_9x16_render",
]
frames = (158, 473, 788, 1103)
controls = {}
for view in "ABC":
    node = stage.node(f"PORTRAIT_VIEW_{view}_CTRL")
    controls[view] = {
        name: node.parm(name).eval()
        for name in ("tx", "ty", "tz", "rx", "ry", "rz")
    }

def light_paths(node):
    if node is None:
        return []
    usd_stage = node.stage()
    return sorted(
        str(prim.GetPath())
        for prim in usd_stage.Traverse()
        if prim.IsA(UsdLux.Light)
    )

nodes = {}
for name in selected:
    node = stage.node(name)
    nodes[name] = None if node is None else {
        "type": node.type().name(),
        "inputs": [item.path() if item else None for item in node.inputs()],
        "outputs": [item.path() for item in node.outputs()],
        "errors": list(node.errors()),
        "light_prims": light_paths(node),
    }

render_info = {}
for settings_name in ("grid_look_settings", "portrait_9x16_settings"):
    node = stage.node(settings_name)
    usd_stage = node.stage()
    render_info[settings_name] = {
        "camera_parm": node.parm("camera").eval() if node.parm("camera") else None,
        "render_settings_prims": sorted(
            str(prim.GetPath())
            for prim in usd_stage.Traverse()
            if prim.GetTypeName() == "RenderSettings"
        ),
        "light_prims": light_paths(node),
    }

print(json.dumps({
    "hip": str(hip),
    "controls": controls,
    "nodes": nodes,
    "render_info": render_info,
}, indent=2))
