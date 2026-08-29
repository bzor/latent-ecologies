"""Add a separate 9:16 portrait camera/render branch to the artist-edited HIP."""
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
from houdini_ai.scar_tissue_edit import SHOTS, portrait_camera_at_frame  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_keyframes(source: hou.Parm, target: hou.Parm) -> None:
    target.deleteAllKeyframes()
    for key in source.keyframes():
        target.setKeyframe(key)


def set_linear_key(parm: hou.Parm, frame: int, value: float) -> None:
    key = hou.Keyframe()
    key.setFrame(frame); key.setValue(value)
    key.setExpression("linear()", hou.exprLanguage.Hscript)
    parm.setKeyframe(key)


def add_portrait_branch(hip: Path) -> dict[str, object]:
    stage = hou.node("/stage")
    if stage is None:
        raise RuntimeError("missing /stage")
    if stage.node("CAM_EDIT_ABC_A_PORTRAIT") is not None:
        raise RuntimeError("portrait branch already exists")
    landscape_camera = stage.node("CAM_EDIT_ABC_A")
    landscape_settings = stage.node("grid_look_settings")
    landscape_rop = stage.node("grid_look_render")
    if None in (landscape_camera, landscape_settings, landscape_rop):
        raise RuntimeError("missing landscape camera/render branch")

    camera = hou.copyNodesTo((landscape_camera,), stage)[0]
    camera.setName("CAM_EDIT_ABC_A_PORTRAIT")
    camera.setComment("9:16 SOCIAL MASTER — portrait-specific A/B/C/A reframing")
    camera.setColor(hou.Color((0.68, 0.38, 0.16)))
    camera.parm("primpath").set("/cameras/portrait_abc_a")
    camera.parm("aspectratiox").set(9); camera.parm("aspectratioy").set(16)
    for parm_name in ("tx", "ty", "tz", "rx", "ry", "focalLength"):
        camera.parm(parm_name).deleteAllKeyframes()
    for shot in SHOTS:
        start, end = shot["frames"]
        for frame in (start, end):
            values = portrait_camera_at_frame(frame)
            for parm_name, source_name in (("tx", "tx"), ("ty", "ty"), ("tz", "tz"), ("rx", "rx"), ("ry", "ry"), ("focalLength", "focal_length")):
                set_linear_key(camera.parm(parm_name), frame, float(values[source_name]))

    settings = hou.copyNodesTo((landscape_settings,), stage)[0]
    settings.setName("portrait_9x16_settings")
    settings.setInput(0, camera)
    settings.setComment("9:16 MASTER — 2160 × 3840; delivery may downsample to 1080 × 1920")
    settings.setColor(hou.Color((0.62, 0.24, 0.20)))
    settings.parm("camera").set("/cameras/portrait_abc_a")
    settings.parm("res_mode").set("autoheight")
    settings.parm("resolutionx").set(2160)
    settings.parm("picture").set(str((hip.parent / "portrait-frames" / "scar-tissue-portrait-$F4.exr").as_posix()))

    rop = hou.copyNodesTo((landscape_rop,), stage)[0]
    rop.setName("portrait_9x16_render")
    rop.setInput(0, settings)
    rop.setComment("PORTRAIT SOCIAL MASTER OUTPUT")
    rop.setColor(hou.Color((0.72, 0.18, 0.16)))

    camera.setPosition(hou.Vector2((5, -21)))
    settings.setPosition(hou.Vector2((5, -33)))
    rop.setPosition(hou.Vector2((5, -36)))
    box = stage.createNetworkBox()
    box.setComment("PORTRAIT 9:16 — CAMERA / QUALITY / OUTPUT")
    box.setColor(hou.Color((0.55, 0.24, 0.18)))
    for node in (camera, settings, rop): box.addItem(node)
    box.fitAroundContents()
    note = stage.createStickyNote()
    note.setText("PORTRAIT SOCIAL MASTER\nCamera: CAM_EDIT_ABC_A_PORTRAIT\nMaster: 2160 × 3840\nDelivery: 1080 × 1920\nOutput: portrait-frames/")
    note.setPosition(hou.Vector2((9, -26))); note.setSize(hou.Vector2((6, 3)))
    return {
        "camera": camera.path(), "settings": settings.path(), "render": rop.path(),
        "aspect_ratio": [9, 16], "master_resolution": [2160, 3840], "delivery_resolution": [1080, 1920],
        "portrait_focals": {shot["label"]: portrait_camera_at_frame(shot["frames"][0])["focal_length"] for shot in SHOTS},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("hip", type=Path)
    args = parser.parse_args()
    hip = args.hip.resolve()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = hip.with_name(f"{hip.stem}.pre-portrait-{timestamp}{hip.suffix}")
    shutil.copy2(hip, backup)
    original = sha(hip)
    hou.hipFile.load(str(hip), suppress_save_prompt=True)
    result = add_portrait_branch(hip)
    hou.hipFile.save(str(hip))
    hou.hipFile.clear(suppress_save_prompt=True)
    hou.hipFile.load(str(hip), suppress_save_prompt=True)
    for path in (result["camera"], result["settings"], result["render"]):
        if hou.node(str(path)) is None:
            shutil.copy2(backup, hip)
            raise RuntimeError(f"reopen verification failed; restored backup: {path}")
    result.update({"hip": str(hip), "backup": str(backup), "original_sha256": original, "updated_sha256": sha(hip)})
    (hip.parent / "portrait-handoff-receipt.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
