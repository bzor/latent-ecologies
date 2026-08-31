"""Connect the portrait camera branch after the final lighting rig."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

import hou
from pxr import UsdLux

CONTROL_PARAMETERS = ("tx", "ty", "tz", "rx", "ry", "rz")
EXPECTED_LIGHTS = {
    "/lights/dome_fill",
    "/lights/grazing_area_key",
    "/lights/cool_rim",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def control_values(stage: hou.Node) -> dict[str, dict[str, float]]:
    return {
        view: {
            name: stage.node(f"PORTRAIT_VIEW_{view}_CTRL").parm(name).eval()
            for name in CONTROL_PARAMETERS
        }
        for view in "ABC"
    }


def light_paths(node: hou.Node) -> set[str]:
    return {
        str(prim.GetPath())
        for prim in node.stage().Traverse()
        if prim.HasAPI(UsdLux.LightAPI)
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("hip", type=Path)
    args = parser.parse_args()
    hip = args.hip.resolve()
    backup = hip.with_name(
        f"{hip.stem}.pre-portrait-lighting-{datetime.now().strftime('%Y%m%d-%H%M%S')}{hip.suffix}"
    )
    shutil.copy2(hip, backup)
    original_sha = sha256(hip)

    hou.hipFile.load(str(hip), suppress_save_prompt=True)
    stage = hou.node("/stage")
    lighting = stage.node("cool_rim")
    first_control = stage.node("PORTRAIT_VIEW_A_CTRL")
    settings = stage.node("portrait_9x16_settings")
    if None in (lighting, first_control, settings):
        raise RuntimeError("missing portrait control or final lighting node")

    before_controls = control_values(stage)
    previous_input = first_control.input(0).path() if first_control.input(0) else None
    first_control.setInput(0, lighting)
    hou.hipFile.save(str(hip))

    hou.hipFile.clear(suppress_save_prompt=True)
    hou.hipFile.load(str(hip), suppress_save_prompt=True)
    stage = hou.node("/stage")
    first_control = stage.node("PORTRAIT_VIEW_A_CTRL")
    settings = stage.node("portrait_9x16_settings")
    after_controls = control_values(stage)
    lights = light_paths(settings)

    if first_control.input(0).path() != "/stage/cool_rim":
        shutil.copy2(backup, hip)
        raise RuntimeError("portrait lighting connection failed after reopen; restored backup")
    for view in "ABC":
        for name in CONTROL_PARAMETERS:
            if abs(before_controls[view][name] - after_controls[view][name]) > 1e-9:
                shutil.copy2(backup, hip)
                raise RuntimeError(
                    f"artist control changed during lighting repair: {view}.{name}; restored backup"
                )
    if lights != EXPECTED_LIGHTS:
        shutil.copy2(backup, hip)
        raise RuntimeError(
            f"portrait branch light mismatch after reopen: {sorted(lights)}; restored backup"
        )

    report = {
        "hip": str(hip),
        "backup": str(backup),
        "original_sha256": original_sha,
        "updated_sha256": sha256(hip),
        "previous_portrait_input": previous_input,
        "updated_portrait_input": first_control.input(0).path(),
        "portrait_lights": sorted(lights),
        "artist_controls_preserved": after_controls,
    }
    receipt = hip.parent / "portrait-lighting-repair-receipt.json"
    receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
