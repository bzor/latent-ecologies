"""Build the Curve-first Rapid Surgical Zipper Look starter from the Basic template."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path
from typing import Any

import hou
from pxr import UsdShade

SIM = "/obj/PLAYGROUND_SIM"
SOURCE = f"{SIM}/SOURCE_PROMOTED_SIMULATION"
OUT_POINTS = f"{SIM}/OUT_POINT_INSTANCES"
OUT_EDGES = f"{SIM}/OUT_EDGE_POLYLINES"
OUT_SOURCE = f"{SIM}/OUT_SIMULATION"


def native(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def set_parm(node: hou.Node, name: str, value: object) -> None:
    parm = node.parm(name)
    if parm is None:
        raise RuntimeError(f"{node.path()} has no parameter {name}")
    parm.set(value)


def set_if_present(node: hou.Node, name: str, value: object) -> None:
    parm = node.parm(name)
    if parm is not None:
        parm.set(value)


def add_render_controls(container: hou.Node) -> None:
    group = container.parmTemplateGroup()
    existing = group.findFolder("Curve-first Render Controls")
    if existing is not None:
        return
    folder = hou.FolderParmTemplate("curve_first_render", "Curve-first Render Controls")
    folder.addParmTemplate(hou.FloatParmTemplate(
        "point_radius", "Point Sphere Radius", 1, default_value=(0.028,),
        min=0.002, max=0.20, min_is_strict=True,
    ))
    folder.addParmTemplate(hou.FloatParmTemplate(
        "bank_width", "Bank Edge Width", 1, default_value=(0.012,),
        min=0.001, max=0.12, min_is_strict=True,
    ))
    folder.addParmTemplate(hou.FloatParmTemplate(
        "zipper_width", "Zipper Edge Width", 1, default_value=(0.008,),
        min=0.001, max=0.12, min_is_strict=True,
    ))
    group.append(folder)
    container.setParmTemplateGroup(group)


def create_material(parent: hou.Node, name: str, color: tuple[float, float, float], roughness: float) -> None:
    shader = parent.node(f"{name}_SHADER") or parent.createNode("mtlxstandard_surface", f"{name}_SHADER")
    material = parent.node(name) or parent.createNode("mtlxsurfacematerial", name)
    material.setInput(0, shader)
    for channel, value in zip(("base_colorr", "base_colorg", "base_colorb"), color):
        set_parm(shader, channel, value)
    set_parm(shader, "specular_roughness", roughness)


def cache_records(selection: Path) -> list[dict[str, Any]]:
    manifest = json.loads((selection / "package-manifest.json").read_text(encoding="utf-8"))
    records = [item for item in manifest["files"] if item["path"].startswith("run/cache/vex-state.")]
    records.sort(key=lambda item: item["path"])
    if len(records) != 300:
        raise RuntimeError(f"expected 300 promoted caches, found {len(records)}")
    for index, item in enumerate(records, start=1):
        expected = f"run/cache/vex-state.{index:04d}.bgeo.sc"
        if item["path"] != expected:
            raise RuntimeError(f"cache sequence is not contiguous: {item['path']} != {expected}")
    return records


def verify_record(path: Path, record: dict[str, Any]) -> None:
    if not path.is_file() or path.stat().st_size != record["bytes"] or sha256(path) != record["sha256"]:
        raise RuntimeError(f"promoted cache does not match its frozen receipt: {path}")


def build(selection: Path, template: Path, output: Path, receipt_path: Path) -> dict[str, Any]:
    if output.exists():
        raise RuntimeError(f"refusing to overwrite artist Look HIP: {output}")
    selection_record = json.loads((selection / "selection.json").read_text(encoding="utf-8"))
    if selection_record["component_id"] != "component-behavior-4d1068fdc350":
        raise RuntimeError("selection is not the promoted Rapid Surgical Zipper component")
    records = cache_records(selection)
    for record in (records[0], records[149], records[-1]):
        verify_record(selection / record["path"], record)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template, output)
    template_sha = sha256(template)

    hou.hipFile.load(native(output), suppress_save_prompt=True, ignore_load_warnings=True)
    hou.setFps(30.0)
    hou.playbar.setFrameRange(1, 300)
    hou.playbar.setPlaybackRange(1, 300)
    hou.setFrame(1)

    container = hou.node(SIM)
    if container is None:
        raise RuntimeError("Basic template is missing /obj/PLAYGROUND_SIM")
    source = hou.node(SOURCE)
    if source is None or source.type().name() != "file":
        raise RuntimeError("Basic template is missing its promoted simulation File SOP")
    for child in list(container.children()):
        if child != source:
            child.destroy()
    add_render_controls(container)
    set_parm(source, "file", native(selection / "run/cache/vex-state.$F4.bgeo.sc"))
    source.setPosition(hou.Vector2(0, 8))
    source.cook(force=True)
    source_geometry = source.geometry()
    if source_geometry is None:
        raise RuntimeError("promoted cache cooked no geometry")
    if len(source_geometry.points()) != 256 or len(source_geometry.prims()) != 384:
        raise RuntimeError(
            f"unexpected promoted topology: {len(source_geometry.points())} points, "
            f"{len(source_geometry.prims())} primitives"
        )
    bounds = source_geometry.boundingBox()
    center = bounds.center()
    extent = bounds.sizevec()
    scale = max(float(extent[0]), float(extent[1]), float(extent[2]), 1.0)

    point_controls = container.createNode("attribwrangle", "POINT_RENDER_CONTROLS")
    point_controls.setInput(0, source)
    set_parm(point_controls, "class", "point")
    set_parm(point_controls, "snippet", 'f@pscale = ch("../point_radius"); s@render_layer = "points";')
    sphere = container.createNode("sphere", "POINT_SPHERE_PROTOTYPE")
    set_if_present(sphere, "type", "poly")
    set_if_present(sphere, "freq", 2)
    for name in ("radx", "rady", "radz"):
        set_if_present(sphere, name, 1.0)
    copy = container.createNode("copytopoints::2.0", "INSTANCE_POINT_SPHERES")
    copy.setInput(0, sphere)
    copy.setInput(1, point_controls)
    set_parm(copy, "pack", 1)
    out_points = container.createNode("null", "OUT_POINT_INSTANCES")
    out_points.setInput(0, copy)

    edge_controls = container.createNode("attribwrangle", "EDGE_RENDER_CONTROLS")
    edge_controls.setInput(0, source)
    set_parm(edge_controls, "class", "primitive")
    set_parm(
        edge_controls, "snippet",
        'f@width = i@kind == 0 ? ch("../bank_width") : ch("../zipper_width"); '
        's@name = i@kind == 0 ? "bank_edges" : "zipper_edges"; '
        's@render_layer = "edges";',
    )
    out_edges = container.createNode("null", "OUT_EDGE_POLYLINES")
    out_edges.setInput(0, edge_controls)
    out_source = container.createNode("null", "OUT_SIMULATION")
    out_source.setInput(0, source)
    out_source.setDisplayFlag(True)
    out_source.setRenderFlag(False)

    positions = {
        point_controls: (-6, 4), sphere: (-10, 4), copy: (-6, 0), out_points: (-6, -4),
        edge_controls: (5, 4), out_edges: (5, 0), out_source: (0, -5),
    }
    for node, position in positions.items():
        node.setPosition(hou.Vector2(position))
    for label, nodes in (
        ("POINTS — PACKED SPHERES / POINTINSTANCER", (point_controls, sphere, copy, out_points)),
        ("EDGES — AUTHORITATIVE BANK + ZIPPER POLYLINES", (edge_controls, out_edges)),
        ("READ-ONLY PROMOTED CACHE", (source, out_source)),
    ):
        box = container.createNetworkBox(); box.setComment(label)
        for node in nodes: box.addItem(node)
        box.fitAroundContents()
    note = container.createStickyNote()
    note.setText(
        "CURVE-FIRST LOOK STARTER\n"
        "256 promoted points → packed sphere PointInstancer\n"
        "384 authoritative primitives → rounded BasisCurves\n"
        "Edit only render controls and downstream Look nodes."
    )
    note.setPosition(hou.Vector2(10, 8)); note.setSize(hou.Vector2(6, 3))

    environment = hou.node("/obj/PLAYGROUND_ENVIRONMENT")
    floor = hou.node("/obj/PLAYGROUND_ENVIRONMENT/NEUTRAL_FLOOR")
    floor_place = hou.node("/obj/PLAYGROUND_ENVIRONMENT/PLACE_FLOOR")
    if environment is None or floor is None or floor_place is None:
        raise RuntimeError("Basic template is missing its neutral environment")
    set_if_present(floor, "sizex", scale * 10.0)
    set_if_present(floor, "sizey", scale * 10.0)
    set_if_present(floor_place, "tx", float(center[0]))
    set_if_present(floor_place, "ty", float(center[1]))
    set_if_present(floor_place, "tz", float(bounds.minvec()[2]) - scale * 0.06)

    main_camera = hou.node("/obj/main_cam")
    if main_camera is None:
        raise RuntimeError("Basic template is missing /obj/main_cam")
    camera_x = float(center[0]) + scale * 1.05
    camera_z = float(center[2]) + scale * 2.20
    focus_distance = math.hypot(camera_x - float(center[0]), camera_z - float(center[2]))
    camera_ry = math.degrees(math.atan2(camera_x - float(center[0]), camera_z - float(center[2])))
    set_parm(main_camera, "tx", camera_x)
    set_parm(main_camera, "ty", float(center[1]))
    set_parm(main_camera, "tz", camera_z)
    set_parm(main_camera, "ry", camera_ry)
    set_parm(main_camera, "focal", 80.0)
    set_parm(main_camera, "focus", focus_distance)
    set_parm(main_camera, "fstop", 11.0)
    set_parm(main_camera, "resx", 1080)
    set_parm(main_camera, "resy", 1350)

    stage = hou.node("/stage")
    if stage is None:
        raise RuntimeError("Basic template is missing /stage")
    old_import = stage.node("IMPORT_SIMULATION")
    if old_import is not None:
        old_import.destroy()
    import_points = stage.createNode("sopimport", "IMPORT_POINT_INSTANCES")
    set_parm(import_points, "soppath", OUT_POINTS)
    set_parm(import_points, "enable_pathprefix", 1)
    set_parm(import_points, "pathprefix", "/World/RenderPoints")
    set_parm(import_points, "primpath", "/World/RenderPoints")
    set_parm(import_points, "enable_packedhandling", 1)
    set_parm(import_points, "packedhandling", "pointinstancer")
    set_parm(import_points, "enable_attribs", 1)
    set_parm(import_points, "attribs", "* ^__* ^usd*")

    import_edges = stage.createNode("sopimport", "IMPORT_EDGE_POLYLINES")
    set_parm(import_edges, "soppath", OUT_EDGES)
    set_parm(import_edges, "enable_pathprefix", 1)
    set_parm(import_edges, "pathprefix", "/World/RenderEdges")
    set_parm(import_edges, "primpath", "/World/RenderEdges")
    set_parm(import_edges, "enable_attribs", 1)
    set_parm(import_edges, "attribs", "* ^__* ^usd*")
    set_parm(import_edges, "enable_setmissingwidths", 1)
    set_parm(import_edges, "setmissingwidths", float(container.evalParm("bank_width")))

    import_environment = stage.node("IMPORT_ENVIRONMENT")
    import_camera = stage.node("IMPORT_MAIN_CAM")
    merge = stage.node("MERGE_SCENE")
    library = stage.node("MATERIALS_STARTER")
    assign = stage.node("ASSIGN_STARTER_MATERIALS")
    camera_edit = stage.node("camera_edit")
    if any(node is None for node in (import_environment, import_camera, merge, library, assign, camera_edit)):
        raise RuntimeError("Basic template render graph is incomplete")
    for index in range(len(merge.inputs())):
        merge.setInput(index, None)
    merge.setInput(0, import_points)
    merge.setInput(1, import_edges)
    merge.setInput(2, import_environment)
    merge.setInput(3, import_camera)
    library.setInput(0, merge)
    set_if_present(library, "matpathprefix", "/materials/")
    create_material(library, "POINTS_STARTER", (0.74, 0.78, 0.84), 0.36)
    create_material(library, "EDGES_STARTER", (0.30, 0.34, 0.40), 0.48)
    create_material(library, "FLOOR_NEUTRAL", (0.095, 0.11, 0.14), 0.72)
    assign.setInput(0, library)
    set_parm(assign, "nummaterials", 3)
    assignments = (
        ("/World/RenderPoints /World/RenderPoints/**", "/materials/POINTS_STARTER"),
        ("/World/RenderEdges /World/RenderEdges/**", "/materials/EDGES_STARTER"),
        ("/World/Environment /World/Environment/**", "/materials/FLOOR_NEUTRAL"),
    )
    for index, (pattern, material) in enumerate(assignments, start=1):
        set_parm(assign, f"primpattern{index}", pattern)
        set_parm(assign, f"matspecpath{index}", material)
    camera_edit.setInput(0, assign)

    settings = stage.node("RENDER_KARMA_SETTINGS")
    render = stage.node("OUT_KARMA")
    selector = stage.node("SELECT_LIGHTING_MODE")
    if settings is None or render is None or selector is None:
        raise RuntimeError("Basic template is missing Karma output or lighting selection")
    settings.setInput(0, selector)
    set_parm(settings, "camera", "/main_cam")
    set_parm(settings, "picture", native(output.parent / "var_004_rapid-surgical-zipper.look_r001.renders/beauty.$F4.exr"))
    set_parm(settings, "engine", "xpu")
    set_parm(settings, "resolutionx", 1080)
    set_parm(settings, "samplesperpixel", 64)
    set_parm(settings, "pathtracedsamples", 128)
    set_parm(settings, "enabledof", 0)
    set_if_present(settings, "point_style", "Spheres")
    set_if_present(settings, "curve_style", "Rounded Curves")
    render.setInput(0, settings)
    set_parm(render, "renderer", "BRAY_HdKarma")
    set_parm(render, "loppath", settings.path())
    set_parm(render, "rendersettings", "/Render/Playground")
    set_if_present(render, "trange", 1)
    set_if_present(render, "f1", 1)
    set_if_present(render, "f2", 300)
    set_if_present(render, "f3", 1)

    import_points.setPosition(hou.Vector2(-6, 18)); import_edges.setPosition(hou.Vector2(0, 18))
    import_environment.setPosition(hou.Vector2(6, 18)); import_camera.setPosition(hou.Vector2(12, 18))
    merge.setPosition(hou.Vector2(2, 14)); library.setPosition(hou.Vector2(2, 10)); assign.setPosition(hou.Vector2(2, 6))
    hou.hipFile.save(native(output))
    return verify(selection, template, output, receipt_path, template_sha)


def verify(selection: Path, template: Path, output: Path, receipt_path: Path, template_sha: str | None = None) -> dict[str, Any]:
    hou.hipFile.clear(suppress_save_prompt=True)
    hou.hipFile.load(native(output), suppress_save_prompt=True, ignore_load_warnings=False)
    records = cache_records(selection)
    errors: list[str] = []
    source = hou.node(SOURCE)
    out_points = hou.node(OUT_POINTS)
    out_edges = hou.node(OUT_EDGES)
    settings = hou.node("/stage/RENDER_KARMA_SETTINGS")
    if any(node is None for node in (source, out_points, out_edges, settings)):
        raise RuntimeError("reopened starter is missing required source/render nodes")
    cache_checks = []
    source_counts = None
    render_counts = None
    usd_types: list[str] = []
    usd_paths: dict[str, str] = {}
    material_bindings: dict[str, str | None] = {}
    for frame in range(1, 301):
        hou.setFrame(frame)
        record = records[frame - 1]
        expected = (selection / record["path"]).resolve()
        evaluated = Path(source.evalParm("file")).resolve()
        frame_errors = []
        if evaluated != expected:
            frame_errors.append("File SOP evaluated to the wrong promoted cache")
        try:
            verify_record(expected, record)
        except RuntimeError as error:
            frame_errors.append(str(error))
        source.cook(force=True); out_points.cook(force=True); out_edges.cook(force=True)
        source_geometry = source.geometry(); point_geometry = out_points.geometry(); edge_geometry = out_edges.geometry()
        if source_geometry is None or point_geometry is None or edge_geometry is None:
            frame_errors.append("one or more render geometry outputs cooked no geometry")
        else:
            counts = {"points": len(source_geometry.points()), "edge_primitives": len(source_geometry.prims())}
            rendered = {"point_instances": len(point_geometry.prims()), "edge_polylines": len(edge_geometry.prims())}
            if counts != {"points": 256, "edge_primitives": 384}:
                frame_errors.append(f"source topology changed: {counts}")
            if rendered != {"point_instances": 256, "edge_polylines": 384}:
                frame_errors.append(f"render topology changed: {rendered}")
            if frame == 1:
                source_counts = counts; render_counts = rendered
        settings.cook(force=True)
        stage = settings.stage()
        prims = list(stage.Traverse())
        frame_types = sorted({prim.GetTypeName() for prim in prims if prim.GetTypeName()})
        if "PointInstancer" not in frame_types:
            frame_errors.append("Solaris stage has no PointInstancer")
        if "BasisCurves" not in frame_types:
            frame_errors.append("Solaris stage has no BasisCurves")
        frame_bindings: dict[str, str | None] = {}
        for prim in prims:
            if prim.GetTypeName() in {"PointInstancer", "BasisCurves"}:
                material, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
                frame_bindings[prim.GetPath().pathString] = material.GetPath().pathString if material else None
        if not any(value == "/materials/POINTS_STARTER" for value in frame_bindings.values()):
            frame_errors.append("PointInstancer is not bound to POINTS_STARTER")
        if not any(value == "/materials/EDGES_STARTER" for value in frame_bindings.values()):
            frame_errors.append("BasisCurves are not bound to EDGES_STARTER")
        if frame == 150:
            usd_types = frame_types
            usd_paths = {
                prim.GetPath().pathString: prim.GetTypeName()
                for prim in prims if prim.GetTypeName() in {"PointInstancer", "BasisCurves"}
            }
            material_bindings = frame_bindings
        cache_checks.append({"frame": frame, "path": native(expected), "sha256": sha256(expected), "errors": frame_errors})
        errors.extend(f"frame {frame}: {message}" for message in frame_errors)

    point_ancestors = {node.path() for node in out_points.inputAncestors()}
    edge_ancestors = {node.path() for node in out_edges.inputAncestors()}
    if SOURCE not in point_ancestors or SOURCE not in edge_ancestors:
        errors.append("promoted cache File SOP is not an active ancestor of both render layers")
    required_nodes = [
        source, out_points, out_edges, hou.node("/stage/IMPORT_POINT_INSTANCES"),
        hou.node("/stage/IMPORT_EDGE_POLYLINES"), hou.node("/stage/MATERIALS_STARTER"),
        hou.node("/stage/ASSIGN_STARTER_MATERIALS"), settings, hou.node("/stage/OUT_KARMA"),
    ]
    for node in required_nodes:
        if node is None:
            errors.append("required node is missing")
        else:
            errors.extend(f"{node.path()}: {message}" for message in node.errors())
    timeline = {
        "fps": float(hou.fps()),
        "frame_range": [int(hou.playbar.frameRange()[0]), int(hou.playbar.frameRange()[1])],
        "duration_seconds": (hou.playbar.frameRange()[1] - hou.playbar.frameRange()[0] + 1) / hou.fps(),
    }
    if timeline != {"fps": 30.0, "frame_range": [1, 300], "duration_seconds": 10.0}:
        errors.append(f"timeline is not 30 fps / 10 seconds: {timeline}")
    receipt = {
        "schema_version": 1,
        "state": "artist-ready-starter",
        "passed": not errors,
        "source_component_id": "component-behavior-4d1068fdc350",
        "source_selection": native(selection),
        "source_cache_expression": source.parm("file").unexpandedString(),
        "active_cache_ancestor": SOURCE if SOURCE in point_ancestors and SOURCE in edge_ancestors else None,
        "source_geometry": source_counts,
        "render_geometry": render_counts,
        "control_defaults": {
            "point_radius": hou.node(SIM).evalParm("point_radius"),
            "bank_width": hou.node(SIM).evalParm("bank_width"),
            "zipper_width": hou.node(SIM).evalParm("zipper_width"),
        },
        "camera": {
            "translation": [hou.node("/obj/main_cam").evalParm(name) for name in ("tx", "ty", "tz")],
            "rotation_y": hou.node("/obj/main_cam").evalParm("ry"),
            "focus": hou.node("/obj/main_cam").evalParm("focus"),
            "fstop": hou.node("/obj/main_cam").evalParm("fstop"),
        },
        "environment": {
            "floor_size": [
                hou.node("/obj/PLAYGROUND_ENVIRONMENT/NEUTRAL_FLOOR").evalParm("sizex"),
                hou.node("/obj/PLAYGROUND_ENVIRONMENT/NEUTRAL_FLOOR").evalParm("sizey"),
            ],
        },
        "usd_primitive_types": usd_types,
        "usd_render_primitives": usd_paths,
        "material_bindings": material_bindings,
        "timeline": timeline,
        "template": {"path": native(template), "sha256": template_sha or sha256(template)},
        "starter_hip": {"path": native(output), "bytes": output.stat().st_size, "sha256": sha256(output)},
        "cache_checks": cache_checks,
        "verified_frame_count": len(cache_checks),
        "render_configuration": {
            "renderer": hou.node("/stage/OUT_KARMA").evalParm("renderer"),
            "engine": settings.evalParm("engine"),
            "camera": settings.evalParm("camera"),
            "picture": settings.parm("picture").unexpandedString(),
            "resolution": [settings.evalParm("resolutionx"), settings.evalParm("resolutiony")],
            "samples_per_pixel": settings.evalParm("samplesperpixel"),
            "path_traced_samples": settings.evalParm("pathtracedsamples"),
            "depth_of_field_enabled": bool(settings.evalParm("enabledof")),
        },
        "artist_controls": {
            "point_radius": "/obj/PLAYGROUND_SIM/point_radius",
            "bank_width": "/obj/PLAYGROUND_SIM/bank_width",
            "zipper_width": "/obj/PLAYGROUND_SIM/zipper_width",
            "points_material": "/stage/MATERIALS_STARTER/POINTS_STARTER_SHADER",
            "edges_material": "/stage/MATERIALS_STARTER/EDGES_STARTER_SHADER",
        },
        "lighting_modes": ["LIGHT_DOME_V1", "LIGHT_DOME_V2", "LIGHT_DOME_V3", "KEY/FILL/RIM"],
        "node_errors": errors,
        "houdini_version": hou.applicationVersionString(),
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if errors:
        raise RuntimeError("; ".join(errors))
    print(json.dumps(receipt, sort_keys=True))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("build", "verify"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--selection", type=Path, required=True)
        sub.add_argument("--template", type=Path, required=True)
        sub.add_argument("--output", type=Path, required=True)
        sub.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build":
        build(args.selection.resolve(), args.template.resolve(), args.output.resolve(), args.receipt.resolve())
    else:
        verify(args.selection.resolve(), args.template.resolve(), args.output.resolve(), args.receipt.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
