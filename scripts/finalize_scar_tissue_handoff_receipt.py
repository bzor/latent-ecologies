from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from houdini_ai.scar_tissue_edit import SHOTS

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "work/studio/handoffs/scar-tissue-abc-a-v1"
GENERIC = DIRECTORY / "receipt.json"
HIP = DIRECTORY / "scar-tissue-abc-a-handoff.hiplc"

if GENERIC.is_file():
    shutil.copy2(GENERIC, DIRECTORY / "proxy-frame-receipt.json")
receipt = {
    "schema_version": 1,
    "artifact": "editable-houdini-handoff",
    "timeline_fps": 45,
    "source_fps": 30,
    "speed_multiplier": 1.5,
    "frame_range": [1, 1260],
    "duration_seconds": 28.0,
    "source_behavior_component_id": "component-behavior-b3bcc837c3e2",
    "source_look_component_id": "component-look-6013004ba32c",
    "source_palette_component_id": "component-palette-a52433fdb147",
    "source_cache": (ROOT / "work/studio/probes/scar-tissue/directional-refractory-v3/cache").resolve().as_posix(),
    "shots": [
        {
            "label": shot["label"], "camera": shot["camera"], "preset": shot["preset"],
            "frames": shot["frames"], "duration_seconds": 7.0, "camera_motion": "subtle", "motion": shot["motion"],
        }
        for shot in SHOTS
    ],
    "cube_bevel_width": 0.006,
    "cube_bevel_divisions": 1,
    "cube_bevel_space": "fixed-world-after-instance-scale",
    "state_palette_ramp_positions": [0.0, 0.5, 1.0],
    "state_palette_primvar": "state_index",
    "state_mix_primvar": "state_mix",
    "lighting_rig": ["dome_fill", "grazing_area_key", "cool_rim"],
    "editable_controls": {
        "materials": "/stage/neutral_look_materials/EDIT_STATE_COLOR_0 /stage/neutral_look_materials/EDIT_STATE_COLOR_0_5 /stage/neutral_look_materials/EDIT_STATE_COLOR_1",
        "depth_of_field": "/stage/CAM_EDIT_ABC_A",
        "lighting": "/stage/dome_fill /stage/grazing_area_key /stage/cool_rim",
        "quality": "/stage/grid_look_settings",
        "render": "/stage/grid_look_render",
    },
    "hip": {
        "path": HIP.name,
        "bytes": HIP.stat().st_size,
        "sha256": hashlib.sha256(HIP.read_bytes()).hexdigest(),
    },
}
text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
(DIRECTORY / "handoff-receipt.json").write_text(text, encoding="utf-8")
GENERIC.write_text(text, encoding="utf-8")
print(json.dumps(receipt["hip"], indent=2))
