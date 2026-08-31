"""Relayout the artist-edited Scar Tissue HIP top-to-bottom without changing scene data."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

import hou


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scene_snapshot() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for root_path in ("/obj/scar_tissue_grid_look", "/stage", "/stage/neutral_look_materials"):
        root = hou.node(root_path)
        if root is None:
            continue
        for node in (root, *root.allSubChildren()):
            parms = []
            for parm in node.parms():
                try:
                    raw = repr(parm.rawValue())
                except hou.Error:
                    raw = "<unavailable>"
                keys = []
                for key in parm.keyframes():
                    keys.append((key.frame(), key.asCode()))
                parms.append((parm.name(), raw, keys))
            inputs = [(index, source.path() if source else None) for index, source in enumerate(node.inputs())]
            records.append({"path": node.path(), "type": node.type().name(), "parms": sorted(parms), "inputs": inputs})
    records.sort(key=lambda record: str(record["path"]))
    return records


def scene_fingerprint() -> str:
    payload = json.dumps(scene_snapshot(), sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def set_positions(parent_path: str, positions: dict[str, tuple[float, float]]) -> None:
    parent = hou.node(parent_path)
    if parent is None:
        raise RuntimeError(f"missing network: {parent_path}")
    for name, position in positions.items():
        node = parent.node(name)
        if node is not None:
            node.setPosition(hou.Vector2(position))


def refit_boxes(parent_path: str) -> None:
    parent = hou.node(parent_path)
    if parent is None:
        return
    for box in parent.networkBoxes():
        box.fitAroundContents()


def relayout() -> None:
    set_positions("/stage", {
        "import_ground": (0, 0), "import_grid": (0, -2), "import_hairs": (0, -4),
        "import_starts": (0, -6), "import_agents": (0, -8), "import_trails": (0, -10),
        "neutral_look_materials": (0, -14), "assign_neutral_materials": (0, -17),
        "CAM_EDIT_ABC_A": (0, -21),
        "dome_fill": (0, -25), "grazing_area_key": (0, -27), "cool_rim": (0, -29),
        "grid_look_settings": (0, -33), "grid_look_render": (0, -36),
    })
    set_positions("/obj/scar_tissue_grid_look", {
        "field_instances": (0, 0), "unit_memory_cube": (3, 0), "memory_cubes": (1.5, -3),
        "fixed_world_highlight_bevel": (1.5, -6), "floor_to_state_tip_color": (1.5, -9),
        "normal1": (1.5, -12), "OUT_MEMORY_CUBES": (1.5, -15),
        "direction_hairs": (7, 0), "hair_root_to_point_taper": (7, -3),
        "hair_radius": (7, -6), "OUT_DIRECTION_HAIRS": (7, -9),
        "agent_points": (12, 0), "chrome_agent": (15, 0), "chrome_agents": (13.5, -3),
        "OUT_CHROME_AGENTS": (13.5, -6),
        "trail_start_points": (19, 0), "trail_start_sphere": (22, 0), "trail_start_agents": (20.5, -3),
        "OUT_TRAIL_STARTS": (20.5, -6),
        "agent_trails": (27, 0), "trail_radius": (27, -3), "OUT_AGENT_TRAILS": (27, -6),
    })
    set_positions("/stage/neutral_look_materials", {
        "ground_shader": (0, 0), "ground": (0, -3),
        "state_index": (6, 0), "EDIT_STATE_COLOR_0": (9, 0), "EDIT_STATE_COLOR_0_5": (12, 0),
        "EDIT_STATE_COLOR_1": (15, 0), "state_0_or_0_5": (10.5, -3),
        "state_0_05_or_1": (10.5, -6), "state_mix": (15, -6), "EDIT_CUBE_BASE_COLOR": (18, -6),
        "state_palette_with_floor_base": (12, -9), "grid_shader": (12, -12), "grid": (12, -15),
        "hairs_shader": (24, 0), "hairs": (24, -3),
        "chrome_shader": (30, 0), "chrome": (30, -3),
    })
    for path in ("/obj/scar_tissue_grid_look", "/stage"):
        refit_boxes(path)
    sop = hou.node("/obj/scar_tissue_grid_look")
    if sop and sop.stickyNotes():
        sop.stickyNotes()[0].setPosition(hou.Vector2((-5, 1.5)))
    stage = hou.node("/stage")
    if stage and stage.stickyNotes():
        stage.stickyNotes()[0].setPosition(hou.Vector2((5, -18)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("hip", type=Path)
    args = parser.parse_args()
    hip = args.hip.resolve()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = hip.with_name(f"{hip.stem}.pre-vertical-layout-{timestamp}{hip.suffix}")
    shutil.copy2(hip, backup)
    original_sha = sha(hip)
    hou.hipFile.load(str(hip), suppress_save_prompt=True)
    before_snapshot = scene_snapshot()
    before = scene_fingerprint()
    relayout()
    after_snapshot = scene_snapshot()
    after = scene_fingerprint()
    if after != before:
        diagnostics = hip.with_name("vertical-layout-mismatch.json")
        diagnostics.write_text(json.dumps({"before": before_snapshot, "after": after_snapshot}, indent=2, default=str), encoding="utf-8")
        raise RuntimeError("scene data changed during position-only relayout")
    hou.hipFile.save(str(hip))
    hou.hipFile.clear(suppress_save_prompt=True)
    hou.hipFile.load(str(hip), suppress_save_prompt=True)
    reopened_snapshot = scene_snapshot()
    reopened = scene_fingerprint()
    if reopened != before:
        diagnostics = hip.with_name("vertical-layout-reopen-mismatch.json")
        diagnostics.write_text(json.dumps({"before": before_snapshot, "reopened": reopened_snapshot}, indent=2, default=str), encoding="utf-8")
        shutil.copy2(backup, hip)
        raise RuntimeError("reopened scene data differs; restored backup")
    report = {
        "hip": str(hip), "backup": str(backup),
        "original_sha256": original_sha, "updated_sha256": sha(hip),
        "scene_fingerprint": before, "verified_position_only": True,
    }
    report_path = hip.with_name("vertical-layout-receipt.json")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
