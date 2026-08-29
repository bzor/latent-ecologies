"""Build the editable Scar Tissue A-B-C-A Houdini handoff scene."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import hou

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from houdini_ai.scar_tissue_edit import CAMERA_PRESETS, SHOTS, camera_at_frame  # noqa: E402

from render_scar_tissue_grid_look import (
    CUBE_BEVEL_DIVISIONS,
    CUBE_BEVEL_WIDTH,
    build_hip,
    derive_frame,
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def linear_key(parm: hou.Parm, frame: int, value: float) -> None:
    key = hou.Keyframe()
    key.setFrame(frame)
    key.setValue(value)
    key.setExpression("linear()", hou.exprLanguage.Hscript)
    parm.setKeyframe(key)


def animate_camera(camera: hou.Node) -> None:
    camera.setName("CAM_EDIT_ABC_A", unique_name=True)
    for name in ("tx", "ty", "tz", "rx", "ry", "focalLength"):
        parm = camera.parm(name)
        if parm is not None:
            parm.deleteAllKeyframes()
    for shot in SHOTS:
        preset = CAMERA_PRESETS[shot["preset"]]
        start, end = shot["frames"]
        for name in ("tx", "ty", "tz"):
            parm = camera.parm(name)
            if parm is not None:
                linear_key(parm, start, shot["motion"][name][0])
                linear_key(parm, end, shot["motion"][name][1])
        for name in ("rx", "ry"):
            parm = camera.parm(name)
            if parm is not None:
                linear_key(parm, start, preset[name])
                linear_key(parm, end, preset[name])
        focal = camera.parm("focalLength")
        if focal is not None:
            linear_key(focal, start, preset["focal_length"])
            linear_key(focal, end, preset["focal_length"])
    for name, value in (("fstop", 0.0), ("focusDistance", 10.0)):
        parm = camera.parm(name)
        if parm is not None:
            parm.set(value)


def position_group(parent: hou.Node, names: list[str], x: float, title: str, color: hou.Color) -> None:
    nodes = [parent.node(name) for name in names]
    nodes = [node for node in nodes if node is not None]
    for index, node in enumerate(nodes):
        node.setPosition(hou.Vector2(x, -index * 3.0))
    if not nodes:
        return
    box = parent.createNetworkBox()
    box.setComment(title)
    box.setColor(color)
    for node in nodes:
        box.addItem(node)
    box.fitAroundContents()


def organise_scene() -> None:
    obj = hou.node("/obj")
    geo = obj.node("scar_tissue_grid_look")
    ground = obj.node("overscan_ground")
    if geo is not None:
        geo.setPosition(hou.Vector2(0, 0))
        position_group(geo, ["field_instances", "unit_memory_cube", "memory_cubes", "fixed_world_highlight_bevel", "floor_to_state_tip_color", "OUT_MEMORY_CUBES"], 0, "MEMORY FIELD — CACHE → HEIGHT → FIXED BEVEL → COLOUR", hou.Color((0.18, 0.42, 0.55)))
        position_group(geo, ["direction_hairs", "hair_root_to_point_taper", "hair_radius", "OUT_DIRECTION_HAIRS"], 7, "DIRECTION HAIRS", hou.Color((0.12, 0.48, 0.38)))
        position_group(geo, ["agent_points", "chrome_agent", "chrome_agents", "OUT_CHROME_AGENTS"], 12, "AGENT HEADS", hou.Color((0.28, 0.38, 0.62)))
        position_group(geo, ["trail_start_points", "trail_start_sphere", "trail_start_agents", "OUT_TRAIL_STARTS"], 19, "TRAIL TAILS", hou.Color((0.28, 0.38, 0.62)))
        position_group(geo, ["agent_trails", "trail_radius", "OUT_AGENT_TRAILS"], 27, "AGENT TRAILS", hou.Color((0.28, 0.38, 0.62)))
        note = geo.createStickyNote()
        note.setText("AUTHORITATIVE CACHE\nFrames 1–1260\nBehavior is frozen. Tweak Look downstream only.")
        note.setPosition(hou.Vector2(-4.5, 1.5))
        note.setSize(hou.Vector2(4.0, 2.0))
    if ground is not None:
        ground.setPosition(hou.Vector2(5, -2))
        children = list(ground.children())
        for index, node in enumerate(children):
            node.setPosition(hou.Vector2(index * 3.0, 0))

    stage = hou.node("/stage")
    imports = [stage.node(f"import_{name}") for name in ("ground", "grid", "hairs", "starts", "agents", "trails")]
    imports = [node for node in imports if node is not None]
    for index, node in enumerate(imports):
        node.setPosition(hou.Vector2(0, -index * 2.0))
    box = stage.createNetworkBox(); box.setComment("01 — GEOMETRY IMPORTS"); box.setColor(hou.Color((0.18, 0.34, 0.48)))
    for node in imports: box.addItem(node)
    if imports: box.fitAroundContents()
    positions = {
        "neutral_look_materials": (0, -14), "assign_neutral_materials": (0, -17),
        "CAM_EDIT_ABC_A": (0, -21), "dome_fill": (0, -25), "grazing_area_key": (0, -27), "cool_rim": (0, -29),
        "grid_look_settings": (0, -33), "grid_look_render": (0, -36),
    }
    for name, position in positions.items():
        node = stage.node(name)
        if node is not None: node.setPosition(hou.Vector2(*position))
    for title, names, color in (
        ("02 — MATERIALS / COLOUR", ["neutral_look_materials", "assign_neutral_materials"], hou.Color((0.42, 0.24, 0.48))),
        ("03 — CAMERA / DOF", ["CAM_EDIT_ABC_A"], hou.Color((0.48, 0.36, 0.16))),
        ("04 — LIGHTING", ["dome_fill", "grazing_area_key", "cool_rim"], hou.Color((0.50, 0.45, 0.18))),
        ("05 — QUALITY / OUTPUT", ["grid_look_settings", "grid_look_render"], hou.Color((0.48, 0.20, 0.20))),
    ):
        nodes = [stage.node(name) for name in names if stage.node(name) is not None]
        if nodes:
            group = stage.createNetworkBox(); group.setComment(title); group.setColor(color)
            for node in nodes: group.addItem(node)
            group.fitAroundContents()
    note = stage.createStickyNote()
    note.setText("FINAL TWEAKS\nColour: 02 Materials\nDOF: 03 Camera\nLighting: 04 Lighting\nSamples/output: 05 Quality\n\nTimeline: 45 fps, frames 1–1260\nCuts: 1 / 316 / 631 / 946")
    note.setPosition(hou.Vector2(5, -18))
    note.setSize(hou.Vector2(8, 4))
    library = stage.node("neutral_look_materials")
    if library is not None:
        children = list(library.children())
        for index, node in enumerate(children):
            node.setPosition(hou.Vector2((index % 5) * 6.0, -(index // 5) * 3.0))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cache_dir", type=Path)
    parser.add_argument("metrics", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--build-only", action="store_true")
    parser.add_argument("--reuse-derived", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True); (output / "frames").mkdir(exist_ok=True)
    metrics = json.loads(args.metrics.read_text(encoding="utf-8"))
    if not args.build_only and not args.reuse_derived:
        for frame in range(1, 1261):
            derive_frame(args.cache_dir.resolve(), frame, metrics, output)
    if args.reuse_derived:
        for frame in range(1, 1261):
            for prefix in ("field", "hairs", "agents", "trail-starts", "trails"):
                path = output / f"{prefix}.{frame:04d}.bgeo.sc"
                if not path.is_file():
                    raise FileNotFoundError(f"missing derived handoff geometry: {path}")
    source_hip = build_hip(output, output / "frames" / "frame-$F4.png", False, [1, 1260], 1920, 32, "bioluminal-depth", "tight-isometric")
    hou.hipFile.load(str(source_hip), suppress_save_prompt=True)
    hou.setFps(45.0)
    hou.playbar.setFrameRange(1, 1260); hou.playbar.setPlaybackRange(1, 1260)
    camera = hou.node("/stage/technical_camera")
    if camera is None: raise RuntimeError("generated scene has no camera")
    animate_camera(camera)
    settings = hou.node("/stage/grid_look_settings")
    if settings is not None:
        if settings.parm("resolutionx") is not None: settings.parm("resolutionx").set(1920)
        if settings.parm("samplesperpixel") is not None: settings.parm("samplesperpixel").set(32)
    organise_scene()
    target = output / "scar-tissue-abc-a-handoff.hiplc"
    hou.hipFile.save(str(target))
    source_hip.unlink(missing_ok=True)
    receipt = {
        "schema_version": 1, "artifact": "editable-houdini-handoff", "timeline_fps": 45,
        "source_fps": 30, "speed_multiplier": 1.5, "frame_range": [1, 1260], "duration_seconds": 28.0,
        "source_behavior_component_id": "component-behavior-b3bcc837c3e2",
        "source_look_component_id": "component-look-6013004ba32c",
        "source_palette_component_id": "component-palette-a52433fdb147",
        "source_cache": args.cache_dir.resolve().as_posix(),
        "shots": [{"label": shot["label"], "camera": shot["camera"], "preset": shot["preset"], "frames": shot["frames"], "duration_seconds": 7.0, "camera_motion": "subtle", "motion": shot["motion"]} for shot in SHOTS],
        "cube_bevel_width": CUBE_BEVEL_WIDTH, "cube_bevel_divisions": CUBE_BEVEL_DIVISIONS,
        "cube_bevel_space": "fixed-world-after-instance-scale",
        "state_palette_ramp_positions": [0.0, 0.5, 1.0], "state_palette_primvar": "state_index", "state_mix_primvar": "state_mix",
        "lighting_rig": ["dome_fill", "grazing_area_key", "cool_rim"],
        "editable_controls": {"materials": "/stage/neutral_look_materials/EDIT_STATE_COLOR_0 /stage/neutral_look_materials/EDIT_STATE_COLOR_0_5 /stage/neutral_look_materials/EDIT_STATE_COLOR_1", "depth_of_field": "/stage/CAM_EDIT_ABC_A", "lighting": "/stage/dome_fill /stage/grazing_area_key /stage/cool_rim", "quality": "/stage/grid_look_settings", "render": "/stage/grid_look_render"},
        "hip": {"path": target.name, "bytes": target.stat().st_size, "sha256": sha(target)},
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(target)


if __name__ == "__main__": main()
