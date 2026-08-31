"""Install artist-friendly A/B/C controls for the portrait edit camera."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import hou

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from houdini_ai.scar_tissue_edit import PORTRAIT_VIEW_CONTROLS  # noqa: E402

PARAMETERS = ("tx", "ty", "tz", "rx", "ry", "rz")


def expression(name: str) -> str:
    control = lambda view: f'ch("/obj/PORTRAIT_CAMERA_CONTROLS/VIEW_{view}/{name}")'
    drift = {
        "tx": ("fit($F,1,315,-0.18,0.18)", "0", "fit($F,631,945,-0.19,0.19)", "fit($F,946,1260,0.18,-0.18)"),
        "ty": ("0", "fit($F,316,630,0.10,-0.10)", "0", "0"),
        "tz": ("fit($F,1,315,0.12,-0.12)", "fit($F,316,630,0.30,-0.30)", "fit($F,631,945,0.04,-0.04)", "fit($F,946,1260,-0.12,0.12)"),
        "rx": ("0", "0", "0", "0"), "ry": ("0", "0", "0", "0"), "rz": ("0", "0", "0", "0"),
    }[name]
    return (
        f'if($F<316,{control("A")}+{drift[0]},'
        f'if($F<631,{control("B")}+{drift[1]},'
        f'if($F<946,{control("C")}+{drift[2]},{control("A")}+{drift[3]})))'
    )


def install() -> dict[str, object]:
    obj = hou.node("/obj")
    stage = hou.node("/stage")
    camera = stage.node("CAM_EDIT_ABC_A_PORTRAIT") if stage else None
    if obj is None or camera is None:
        raise RuntimeError("missing /obj or portrait edit camera")
    existing = obj.node("PORTRAIT_CAMERA_CONTROLS")
    if existing is not None:
        raise RuntimeError("portrait camera controls already exist")
    subnet = obj.createNode("subnet", "PORTRAIT_CAMERA_CONTROLS")
    subnet.setPosition(hou.Vector2((8, 0)))
    subnet.setColor(hou.Color((0.68, 0.36, 0.14)))
    subnet.setComment("EDIT THESE THREE NULLS — portrait camera motion remains relative")
    for child in subnet.children(): child.destroy()
    for index, view in enumerate(("A", "B", "C")):
        node = subnet.createNode("null", f"VIEW_{view}")
        node.setPosition(hou.Vector2((0, -index * 3)))
        node.setColor(hou.Color((0.78, 0.42, 0.16)))
        node.setComment(f"PORTRAIT VIEW {view} BASE TRANSFORM — safe to edit")
        values = PORTRAIT_VIEW_CONTROLS[view]
        for name in ("tx", "ty", "tz", "rx", "ry"):
            node.parm(name).set(values[name])
        node.parm("rz").set(0.0)
    note = subnet.createStickyNote()
    note.setText("EDIT VIEW_A / VIEW_B / VIEW_C TRANSFORMS\nThe portrait camera adds its subtle drift automatically.\nVIEW_A drives both A1 and A2.\nDo not edit CAM_EDIT_ABC_A_PORTRAIT motion expressions.")
    note.setPosition(hou.Vector2((3, -2))); note.setSize(hou.Vector2((7, 3)))
    for name in PARAMETERS:
        parm = camera.parm(name)
        if parm is None:
            continue
        parm.deleteAllKeyframes()
        parm.setExpression(expression(name), hou.exprLanguage.Hscript)
    camera.setComment("9:16 SOCIAL MASTER — relative motion driven by /obj/PORTRAIT_CAMERA_CONTROLS")
    return {"subnet": subnet.path(), "controls": [f"{subnet.path()}/VIEW_{view}" for view in ("A", "B", "C")], "camera": camera.path()}


def transforms(camera: hou.Node, frames: tuple[int, ...]) -> dict[str, dict[str, float]]:
    return {str(frame): {name: camera.parm(name).evalAtFrame(frame) for name in PARAMETERS} for frame in frames}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("hip", type=Path)
    parser.add_argument("--probe-only", action="store_true")
    args = parser.parse_args(); hip = args.hip.resolve()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = hip.with_name(f"{hip.stem}.pre-relative-camera-controls-{timestamp}{hip.suffix}")
    shutil.copy2(hip, backup)
    hou.hipFile.load(str(hip), suppress_save_prompt=True)
    frames = (1, 315, 316, 630, 631, 945, 946, 1260)
    camera = hou.node("/stage/CAM_EDIT_ABC_A_PORTRAIT")
    before = transforms(camera, frames)
    result = install()
    camera = hou.node(str(result["camera"]))
    after = transforms(camera, frames)
    for frame in before:
        for name in ("tx", "ty", "tz", "rx", "ry"):
            if abs(before[frame][name] - after[frame][name]) > 1e-6:
                raise RuntimeError(f"control rig changed framing at frame {frame} {name}")
    control_b = hou.node("/obj/PORTRAIT_CAMERA_CONTROLS/VIEW_B")
    control_b.parm("tx").set(control_b.parm("tx").eval() + 1.25)
    shifted = transforms(camera, frames)
    control_b.parm("tx").set(control_b.parm("tx").eval() - 1.25)
    for frame in (316, 630):
        if abs(shifted[str(frame)]["tx"] - after[str(frame)]["tx"] - 1.25) > 1e-6:
            raise RuntimeError("VIEW_B did not offset B")
    for frame in (1, 315, 631, 945, 946, 1260):
        if abs(shifted[str(frame)]["tx"] - after[str(frame)]["tx"]) > 1e-6:
            raise RuntimeError("VIEW_B leaked into another shot")
    if args.probe_only:
        print(json.dumps({"framing_preserved": True, "view_b_isolated": True, **result}, indent=2)); return
    hou.hipFile.save(str(hip)); hou.hipFile.clear(suppress_save_prompt=True); hou.hipFile.load(str(hip), suppress_save_prompt=True)
    reopened_camera = hou.node(str(result["camera"])); reopened = transforms(reopened_camera, frames)
    for frame in after:
        for name in PARAMETERS:
            if abs(reopened[frame][name] - after[frame][name]) > 1e-6:
                shutil.copy2(backup, hip)
                raise RuntimeError(f"reopen changed controlled camera at frame {frame} {name}; restored backup")
    result.update({"hip": str(hip), "backup": str(backup), "sha256": hashlib.sha256(hip.read_bytes()).hexdigest(), "framing_preserved": True, "view_b_isolated": True})
    (hip.parent / "relative-camera-controls-receipt.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
