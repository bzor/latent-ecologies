import hashlib
import json
import sys
from pathlib import Path

import hou

hip = Path(sys.argv[1]).resolve()
backup = Path(sys.argv[2]).resolve()


def snapshot(path: Path) -> dict:
    hou.hipFile.load(str(path), suppress_save_prompt=True)
    camera = hou.node("/stage/CAM_EDIT_ABC_A")
    settings = hou.node("/stage/grid_look_settings")
    return {
        "camera": {name: (camera.parm(name).rawValue(), [key.asCode() for key in camera.parm(name).keyframes()]) for name in ("tx", "ty", "tz", "rx", "ry", "focalLength", "aspectratiox", "aspectratioy")},
        "settings": {name: settings.parm(name).rawValue() for name in ("camera", "res_mode", "resolutionx", "resolutiony", "samplesperpixel", "picture")},
    }

before = snapshot(backup)
after = snapshot(hip)
portrait = hou.node("/stage/CAM_EDIT_ABC_A_PORTRAIT")
settings = hou.node("/stage/portrait_9x16_settings")
rop = hou.node("/stage/portrait_9x16_render")
frames = (1, 315, 316, 630, 631, 945, 946, 1260)
report = {
    "landscape_unchanged": before == after,
    "portrait_camera": {str(frame): {name: portrait.parm(name).evalAtFrame(frame) for name in ("tx", "ty", "tz", "rx", "ry", "focalLength")} for frame in frames},
    "aspect_ratio": [portrait.parm("aspectratiox").eval(), portrait.parm("aspectratioy").eval()],
    "settings": {name: settings.parm(name).eval() for name in ("camera", "res_mode", "resolutionx", "resolutiony", "samplesperpixel", "picture")},
    "portrait_errors": {node.path(): list(node.errors()) for node in (portrait, settings, rop)},
    "vertical_edges": {
        "camera_to_settings": settings.position().y() < portrait.position().y(),
        "settings_to_render": rop.position().y() < settings.position().y(),
    },
}
print(json.dumps(report, indent=2))
