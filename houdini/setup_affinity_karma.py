"""Add a compact Karma/Solaris setup to the artist-edited affinity HIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from itertools import combinations
from pathlib import Path
from typing import Any

import hou

SCENE_NAME = "nonlocal-affinity-karma-lookdev.hiplc"
PICKER_LABELS = ("Particle Organisms + Trails", "Affinity Weave", "Tension Membrane")
STAGE_NODE_NAMES = (
    "IMPORT_SELECTED_LOOK", "IMPORT_BACKDROP", "MERGE_LOOK_AND_ENVIRONMENT",
    "LIGHT_DOME", "CAM_REVIEW", "RENDER_KARMA_SETTINGS", "OUT_KARMA",
)


def native(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def node_errors(nodes: list[hou.Node]) -> list[str]:
    errors = []
    for node in nodes:
        errors.extend(f"{child.path()}: {error}" for child in (node, *node.allSubChildren()) for error in child.errors())
    return errors


def build(source: Path, output_dir: Path, *, skip_render: bool) -> dict[str, Any]:
    source = source.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / SCENE_NAME
    backup = output_dir / "source-artist-edit.hiplc"
    if destination.exists() or backup.exists():
        raise RuntimeError("Karma handoff already exists; refusing to overwrite artist work")
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    shutil.copy2(source, backup)
    shutil.copy2(source, destination)
    hou.hipFile.load(native(destination), suppress_save_prompt=True)
    geo = hou.node("/obj/geo1")
    if geo is None or geo.parm("look_direction") is None:
        raise RuntimeError("artist Lookdev geometry or Look Direction control is missing")

    # Simple neutral floor/backdrop, kept separate from the artist's Look SOP network.
    backdrop = hou.node("/obj").createNode("geo", "KARMA_BACKDROP")
    for child in backdrop.children():
        child.destroy()
    grid = backdrop.createNode("grid", "BACKDROP_FLOOR")
    grid.parm("orient").set("xy")
    grid.parm("sizex").set(5.0)
    grid.parm("sizey").set(5.0)
    grid.parm("rows").set(2)
    grid.parm("cols").set(2)
    grid.parm("tz").set(-0.82)
    backdrop_colour = backdrop.createNode("attribwrangle", "BACKDROP_NEUTRAL_DISPLAY")
    backdrop_colour.setInput(0, grid)
    backdrop_colour.parm("class").set("point")
    backdrop_colour.parm("snippet").set("v@Cd = set(0.055, 0.065, 0.08);")
    backdrop_output = backdrop.createNode("null", "OUT_BACKDROP")
    backdrop_output.setInput(0, backdrop_colour)
    backdrop_output.setDisplayFlag(True)
    backdrop_output.setRenderFlag(True)
    grid.setPosition(hou.Vector2((0.0, 4.0)))
    backdrop_colour.setPosition(hou.Vector2((0.0, 1.0)))
    backdrop_output.setPosition(hou.Vector2((0.0, -2.0)))
    backdrop.setPosition(hou.Vector2((3.0, -1.5)))

    stage = hou.node("/stage")
    if stage is None:
        raise RuntimeError("Solaris /stage context is unavailable")
    for child in stage.children():
        child.destroy()
    group = stage.parmTemplateGroup()
    folder = hou.FolderParmTemplate("affinity_karma_controls", "Affinity Karma Review", folder_type=hou.folderType.Simple)
    picker = hou.MenuParmTemplate(
        "look_selection", "Look Selection",
        ("0", "1", "2"), PICKER_LABELS,
        default_value=1,
    )
    picker.setHelp("Selects the first three approved Look directions and drives /obj/geo1/look_direction.")
    folder.addParmTemplate(picker)
    group.append(folder)
    stage.setParmTemplateGroup(group)
    geo.parm("look_direction").deleteAllKeyframes()
    geo.parm("look_direction").setExpression('ch("/stage/look_selection")', hou.exprLanguage.Hscript)

    import_look = stage.createNode("sopimport", "IMPORT_SELECTED_LOOK")
    import_look.parm("soppath").set("/obj/geo1/OUTPUT_SELECTED_LOOK")
    import_look.parm("primpath").set("/World/AffinityLook")
    import_look.parm("pathprefix").set("/World/AffinityLook")
    import_look.parm("enable_attribs").set(1)
    import_look.parm("attribs").set("* ^__* ^usd*")
    import_look.parm("authortimesamples").set("auto")
    import_backdrop = stage.createNode("sopimport", "IMPORT_BACKDROP")
    import_backdrop.parm("soppath").set("/obj/KARMA_BACKDROP/OUT_BACKDROP")
    import_backdrop.parm("primpath").set("/World/Backdrop")
    import_backdrop.parm("pathprefix").set("/World/Backdrop")
    import_backdrop.parm("enable_attribs").set(1)
    import_backdrop.parm("attribs").set("P N Cd")
    merge = stage.createNode("merge", "MERGE_LOOK_AND_ENVIRONMENT")
    merge.setInput(0, import_look)
    merge.setInput(1, import_backdrop)
    dome = stage.createNode("domelight::3.0", "LIGHT_DOME")
    dome.setInput(0, merge)
    dome.parm("primpath").set("/World/Lights/Dome")
    dome.parm("xn__inputsintensity_i0a").set(0.7)
    dome.parm("xn__inputsexposure_vya").set(0.0)
    dome.parm("xn__inputscolor_ztar").set(0.82)
    dome.parm("xn__inputscolor_ztag").set(0.88)
    dome.parm("xn__inputscolor_ztab").set(1.0)
    camera = stage.createNode("camera", "CAM_REVIEW")
    camera.setInput(0, dome)
    camera.parm("primpath").set("/World/Cameras/Review")
    object_camera = hou.node("/obj/LOOKDEV_REVIEW_CAMERA")
    camera_values = {
        "tx": object_camera.evalParm("tx") if object_camera else 0.0,
        "ty": object_camera.evalParm("ty") if object_camera else 0.0,
        "tz": object_camera.evalParm("tz") if object_camera else 3.2,
        "rx": object_camera.evalParm("rx") if object_camera else 0.0,
        "ry": object_camera.evalParm("ry") if object_camera else 0.0,
        "rz": object_camera.evalParm("rz") if object_camera else 0.0,
    }
    for name, value in camera_values.items():
        camera.parm(name).set(value)
    camera.parm("focalLength").set(object_camera.evalParm("focal") if object_camera else 55.0)
    camera.parm("aspectratiox").set(1.0)
    camera.parm("aspectratioy").set(1.0)
    settings = stage.createNode("karmarendersettings", "RENDER_KARMA_SETTINGS")
    settings.setInput(0, camera)
    settings.parm("primpath").set("/Render/AffinityKarma")
    settings.parm("camera").set("/World/Cameras/Review")
    settings.parm("picture").set(native(output_dir / "renders" / "affinity-karma.$F4.exr"))
    settings.parm("res_mode").set("manual")
    settings.parm("resolutionx").set(512)
    settings.parm("engine").set("cpu")
    settings.parm("samplesperpixel").set(2)
    settings.parm("pathtracedsamples").set(8)
    settings.parm("enabledof").set(0)
    settings.parm("enablemblur").set(0)
    settings.parm("point_style").set("Spheres")
    settings.parm("curve_style").set("Rounded Curves")
    render = stage.createNode("usdrender_rop", "OUT_KARMA")
    render.setInput(0, settings)
    render.parm("renderer").set("BRAY_HdKarma")
    render.parm("loppath").set(settings.path())
    render.parm("rendersettings").set("/Render/AffinityKarma")
    render.parm("trange").set(0)
    render.parm("f1").set(201)
    render.parm("f2").set(650)
    render.parm("f3").set(1)

    positions = {
        import_look: (-3.0, 10.0), import_backdrop: (3.0, 10.0), merge: (0.0, 7.0),
        dome: (0.0, 4.0), camera: (0.0, 1.0), settings: (0.0, -2.0), render: (0.0, -5.0),
    }
    for node, position in positions.items():
        node.setPosition(hou.Vector2(position))
    import_look.setColor(hou.Color((0.42, 0.62, 0.28)))
    import_backdrop.setColor(hou.Color((0.28, 0.42, 0.58)))
    merge.setColor(hou.Color((0.25, 0.52, 0.62)))
    dome.setColor(hou.Color((0.72, 0.58, 0.20)))
    camera.setColor(hou.Color((0.48, 0.38, 0.68)))
    settings.setColor(hou.Color((0.62, 0.36, 0.22)))
    render.setColor(hou.Color((0.24, 0.68, 0.38)))
    box_specs = (
        ("01 Geometry Imports", (import_look, import_backdrop, merge)),
        ("02 Environment + Camera", (dome, camera)),
        ("03 Karma Quality + Output", (settings, render)),
    )
    boxes = []
    for label, nodes in box_specs:
        box = stage.createNetworkBox()
        box.setComment(label)
        for node in nodes:
            box.addItem(node)
        box.fitAroundContents()
        boxes.append(box)
    note = stage.createStickyNote()
    note.setText("Affinity Karma starter\nUse /stage Look Selection for the first three Look directions.\nNeutral backdrop + dome | 512×512 | Karma CPU | frame 201 tracer.")
    note.setPosition(hou.Vector2((6.0, 10.0)))
    note.setSize(hou.Vector2((5.5, 3.5)))

    hou.setFrame(201)
    picker_validation = []
    for index, label in enumerate(PICKER_LABELS):
        stage.parm("look_selection").set(index)
        picker_validation.append({"index": index, "label": label, "driven_obj_value": int(geo.evalParm("look_direction"))})
    stage.parm("look_selection").set(1)
    stage_nodes = [stage.node(name) for name in STAGE_NODE_NAMES]
    errors = node_errors([backdrop, *stage_nodes])
    overlaps = []
    for left, right in combinations(boxes, 2):
        left_min, right_min = left.position(), right.position()
        left_max, right_max = left_min + left.size(), right_min + right.size()
        if not (left_max[0] <= right_min[0] or right_max[0] <= left_min[0] or left_max[1] <= right_min[1] or right_max[1] <= left_min[1]):
            overlaps.append(sorted((left.comment(), right.comment())))
    if errors or any(item["driven_obj_value"] != item["index"] for item in picker_validation) or overlaps:
        raise RuntimeError(json.dumps({"errors": errors, "picker": picker_validation, "overlaps": overlaps}, sort_keys=True))

    render_probe = {"attempted": False, "path": None, "exists": False, "bytes": 0}
    if not skip_render:
        render_dir = output_dir / "renders"
        render_dir.mkdir(parents=True, exist_ok=True)
        stage.parm("look_selection").set(1)
        settings.parm("resolutionx").set(256)
        settings.parm("samplesperpixel").set(1)
        settings.parm("pathtracedsamples").set(4)
        probe_path = render_dir / "affinity-karma.0201.exr"
        render_probe["attempted"] = True
        render.parm("execute").pressButton()
        render_probe.update({"path": native(probe_path), "exists": probe_path.is_file(), "bytes": probe_path.stat().st_size if probe_path.is_file() else 0})
        if not probe_path.is_file() or probe_path.stat().st_size == 0:
            raise RuntimeError(f"Karma tracer did not produce {probe_path}")
        stage.parm("look_selection").set(1)
        settings.parm("resolutionx").set(512)
        settings.parm("samplesperpixel").set(2)
        settings.parm("pathtracedsamples").set(8)
    hou.setFrame(201)
    hou.hipFile.save(native(destination))
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_sha:
        raise RuntimeError("source artist-edited HIP was modified")
    audit = {
        "schema_version": 1,
        "source_artist_edit": native(source),
        "source_sha256": source_sha,
        "source_artist_edit_preserved": True,
        "output_hip": destination.name,
        "picker_labels": list(PICKER_LABELS),
        "picker_values": [0, 1, 2],
        "picker_validation": picker_validation,
        "stage_nodes": list(STAGE_NODE_NAMES),
        "backdrop_sop": "/obj/KARMA_BACKDROP/OUT_BACKDROP",
        "dome_light_prim": "/World/Lights/Dome",
        "camera_prim": "/World/Cameras/Review",
        "render_settings_prim": "/Render/AffinityKarma",
        "render_probe": render_probe,
        "layout": {"overlapping_network_boxes": overlaps, "direction": "top-to-bottom"},
        "node_errors": errors,
    }
    (output_dir / "audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, sort_keys=True))
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--skip-render", action="store_true")
    args = parser.parse_args()
    build(args.source, args.output, skip_render=args.skip_render)


if __name__ == "__main__":
    main()
