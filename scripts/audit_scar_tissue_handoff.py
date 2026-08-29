import json
import sys
from pathlib import Path

import hou

hip = Path(sys.argv[1]).resolve()
hou.hipFile.load(str(hip), suppress_save_prompt=True)

stage = hou.node("/stage")
obj = hou.node("/obj/scar_tissue_grid_look")
camera = stage.node("CAM_EDIT_ABC_A")
if camera is None:
    raise RuntimeError("missing edit camera")

frames = [1, 315, 316, 630, 631, 945, 946, 1260]
camera_values = {}
cook_results = {}
for frame in frames:
    hou.setFrame(frame)
    camera_values[str(frame)] = {
        name: camera.parm(name).eval() for name in ("tx", "ty", "tz", "rx", "ry", "focalLength")
    }
    output = obj.node("OUT_MEMORY_CUBES")
    geometry = output.geometry()
    cook_results[str(frame)] = {
        "errors": list(output.errors()),
        "points": len(geometry.points()) if geometry is not None else 0,
        "primitives": len(geometry.prims()) if geometry is not None else 0,
    }

major_stage = [
    "import_ground", "import_grid", "import_hairs", "import_starts", "import_agents", "import_trails",
    "neutral_look_materials", "assign_neutral_materials", "CAM_EDIT_ABC_A", "neutral_environment",
    "grid_look_settings", "grid_look_render",
]
positions = {name: list(stage.node(name).position()) for name in major_stage}
unique_positions = len({tuple(value) for value in positions.values()}) == len(positions)
bevel = obj.node("fixed_world_highlight_bevel")
copy = obj.node("memory_cubes")
gradient = obj.node("floor_to_state_tip_color")
result = {
    "fps": hou.fps(),
    "frame_range": list(hou.playbar.frameRange()),
    "playback_range": list(hou.playbar.playbackRange()),
    "camera_values": camera_values,
    "camera_keyframes": {name: [key.frame() for key in camera.parm(name).keyframes()] for name in ("tx", "ty", "tz", "rx", "ry", "focalLength")},
    "cook_results": cook_results,
    "major_stage_positions": positions,
    "major_stage_positions_unique": unique_positions,
    "stage_network_boxes": [box.comment() for box in stage.networkBoxes()],
    "sop_network_boxes": [box.comment() for box in obj.networkBoxes()],
    "stage_sticky_notes": [note.text() for note in stage.stickyNotes()],
    "bevel": {
        "input": bevel.input(0).path(), "copy_source": copy.input(0).path(), "gradient_input": gradient.input(0).path(),
        "offset": bevel.parm("offset").eval(), "divisions": bevel.parm("divisions").eval(), "errors": list(bevel.errors()),
    },
}
print(json.dumps(result, indent=2))
