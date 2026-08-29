"""Build and independently verify the generic 00_look Karma playground."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import hou


def native(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def set_parm(node: hou.Node, name: str, value: object) -> None:
    parm = node.parm(name)
    if parm is None:
        raise RuntimeError(f"{node.path()} has no parameter named {name}")
    parm.set(value)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


_CACHE_FRAME = re.compile(r"(\d{3,6})(?=\.(?:bgeo|vdb)(?:\.sc)?$)", re.IGNORECASE)


def cache_frame(path: str | Path) -> int | None:
    match = _CACHE_FRAME.search(str(path))
    return int(match.group(1)) if match else None


def cache_expression(path: Path) -> str:
    value = native(path)
    return _CACHE_FRAME.sub(lambda match: f"$F{len(match.group(1))}", value)


def create_material(parent: hou.Node, name: str, color: tuple[float, float, float], roughness: float) -> hou.Node:
    shader = parent.createNode("mtlxstandard_surface", f"{name}_SHADER")
    material = parent.createNode("mtlxsurfacematerial", name)
    material.setInput(0, shader)
    for channel, value in zip(("base_colorr", "base_colorg", "base_colorb"), color):
        set_parm(shader, channel, value)
    set_parm(shader, "specular_roughness", roughness)
    return material


def add_stage_controls(stage: hou.Node) -> None:
    group = stage.parmTemplateGroup()
    folder = hou.FolderParmTemplate("playground_controls", "00 Look Playground", folder_type=hou.folderType.Simple)
    lighting = hou.MenuParmTemplate(
        "lighting_mode", "Lighting Mode", ("0", "1"), ("Dome", "Photographer"), default_value=1,
    )
    lighting.setHelp("Switch between the neutral dome and editable Key / Fill / Rim rig.")
    folder.addParmTemplate(lighting)
    group.append(folder)
    stage.setParmTemplateGroup(group)


def build(packet_path: Path, output_dir: Path, project_root: Path) -> None:
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    layout = packet["workspace_layout"]
    hip_path = output_dir / layout["hip_path"]
    if hip_path.exists():
        raise RuntimeError(f"refusing to overwrite existing 00_look playground: {hip_path}")
    cache_records = packet["source_cache_receipt"]
    if not cache_records:
        raise RuntimeError("00_look requires at least one frozen simulation cache")
    cache_path = (project_root / cache_records[0]["path"]).resolve()
    if not cache_path.is_file() or sha256(cache_path) != cache_records[0]["sha256"]:
        raise RuntimeError("00_look source cache no longer matches its frozen receipt")

    hou.hipFile.clear(suppress_save_prompt=True)
    frames = [frame for record in cache_records if (frame := cache_frame(record["path"])) is not None]
    frame_start, frame_end = (min(frames), max(frames)) if frames else (1, 1)
    hou.playbar.setFrameRange(frame_start, frame_end)
    hou.playbar.setPlaybackRange(frame_start, frame_end)
    hou.setFrame(frame_start)
    obj = hou.node("/obj")
    sim = obj.createNode("geo", "PLAYGROUND_SIM")
    for child in sim.children():
        child.destroy()
    source = sim.createNode("file", "SOURCE_PROMOTED_SIMULATION")
    set_parm(source, "file", cache_expression(cache_path))
    source.cook(force=True)
    geometry = source.geometry()
    if geometry is None or (len(geometry.points()) == 0 and len(geometry.prims()) == 0):
        raise RuntimeError("00_look source cache cooked no geometry")
    bounds = geometry.boundingBox()
    center = bounds.center()
    size = bounds.sizevec()
    scale = max(float(size[0]), float(size[1]), float(size[2]), 1.0)

    display_scale = sim.createNode("attribwrangle", "ENSURE_POINT_VISIBILITY")
    display_scale.setInput(0, source)
    set_parm(
        display_scale,
        "snippet",
        'if (!haspointattrib(0, "pscale")) f@pscale = chf("fallback_pscale");',
    )
    controls = display_scale.parmTemplateGroup()
    controls.append(
        hou.FloatParmTemplate(
            "fallback_pscale",
            "Fallback Point Scale",
            1,
            default_value=(scale * 0.05,),
            min=0.0,
            max=scale * 0.2,
            min_is_strict=True,
        )
    )
    display_scale.setParmTemplateGroup(controls)
    output = sim.createNode("null", "OUT_SIMULATION")
    output.setInput(0, display_scale)
    output.setDisplayFlag(True)
    output.setRenderFlag(True)
    source.setPosition(hou.Vector2((0.0, 3.0)))
    display_scale.setPosition(hou.Vector2((0.0, 0.0)))
    output.setPosition(hou.Vector2((0.0, -3.0)))
    sim.setColor(hou.Color((0.18, 0.48, 0.72)))
    note = sim.createStickyNote()
    note.setText("READ-ONLY PROMOTED SIMULATION\nBuild Look experiments downstream of OUT_SIMULATION.")
    note.setPosition(hou.Vector2((3.0, 2.0)))
    note.setSize(hou.Vector2((5.0, 2.0)))

    output.cook(force=True)

    environment = obj.createNode("geo", "PLAYGROUND_ENVIRONMENT")
    for child in environment.children():
        child.destroy()
    floor = environment.createNode("grid", "NEUTRAL_FLOOR")
    set_parm(floor, "orient", "xy")
    set_parm(floor, "sizex", scale * 4.0)
    set_parm(floor, "sizey", scale * 4.0)
    transform = environment.createNode("xform", "PLACE_FLOOR")
    transform.setInput(0, floor)
    set_parm(transform, "tx", float(center[0]))
    set_parm(transform, "ty", float(center[1]))
    set_parm(transform, "tz", float(bounds.minvec()[2]) - scale * 0.08)
    env_output = environment.createNode("null", "OUT_ENVIRONMENT")
    env_output.setInput(0, transform)
    env_output.setDisplayFlag(True)
    env_output.setRenderFlag(True)
    floor.setPosition(hou.Vector2((0.0, 3.0)))
    transform.setPosition(hou.Vector2((0.0, 0.0)))
    env_output.setPosition(hou.Vector2((0.0, -3.0)))
    environment.setColor(hou.Color((0.32, 0.36, 0.40)))

    stage = hou.node("/stage")
    for child in stage.children():
        child.destroy()
    add_stage_controls(stage)
    import_sim = stage.createNode("sopimport", "IMPORT_SIMULATION")
    set_parm(import_sim, "soppath", output.path())
    set_parm(import_sim, "primpath", "/World/Simulation")
    set_parm(import_sim, "pathprefix", "/World/Simulation")
    set_parm(import_sim, "enable_attribs", 1)
    set_parm(import_sim, "attribs", "* ^__* ^usd*")
    import_env = stage.createNode("sopimport", "IMPORT_ENVIRONMENT")
    set_parm(import_env, "soppath", env_output.path())
    set_parm(import_env, "primpath", "/World/Environment")
    set_parm(import_env, "pathprefix", "/World/Environment")
    merge = stage.createNode("merge", "MERGE_SCENE")
    merge.setInput(0, import_sim)
    merge.setInput(1, import_env)

    library = stage.createNode("materiallibrary", "MATERIALS_STARTER")
    library.setInput(0, merge)
    create_material(library, "SIM_STARTER", (0.72, 0.78, 0.86), 0.38)
    create_material(library, "FLOOR_NEUTRAL", (0.095, 0.11, 0.14), 0.72)
    library.layoutChildren()
    assign = stage.createNode("assignmaterial", "ASSIGN_STARTER_MATERIALS")
    assign.setInput(0, library)
    set_parm(assign, "nummaterials", 2)
    set_parm(assign, "primpattern1", "/World/Simulation /World/Simulation/**")
    set_parm(assign, "matspecpath1", "/materials/SIM_STARTER")
    set_parm(assign, "primpattern2", "/World/Environment /World/Environment/**")
    set_parm(assign, "matspecpath2", "/materials/FLOOR_NEUTRAL")

    camera = stage.createNode("camera", "CAM_PLAYGROUND")
    camera.setInput(0, assign)
    set_parm(camera, "primpath", "/World/Cameras/Playground")
    set_parm(camera, "tx", float(center[0]))
    set_parm(camera, "ty", float(center[1]))
    set_parm(camera, "tz", float(bounds.maxvec()[2]) + scale * 3.4)
    set_parm(camera, "focalLength", 55.0)
    set_parm(camera, "aspectratiox", 1.0)
    set_parm(camera, "aspectratioy", 1.0)

    dome = stage.createNode("domelight::3.0", "LIGHT_DOME")
    dome.setInput(0, camera)
    set_parm(dome, "primpath", "/World/Lights/Dome")
    set_parm(dome, "xn__inputsintensity_i0a", 1.2)
    for channel, value in zip(
        ("xn__inputscolor_ztar", "xn__inputscolor_ztag", "xn__inputscolor_ztab"),
        (0.82, 0.88, 1.0),
    ):
        set_parm(dome, channel, value)

    key = stage.createNode("distantlight::2.0", "KEY")
    key.setInput(0, camera)
    set_parm(key, "primpath", "/World/Lights/Key")
    set_parm(key, "rx", -12.0)
    set_parm(key, "ry", 25.0)
    set_parm(key, "xn__inputsintensity_i0a", 4.0)
    fill = stage.createNode("distantlight::2.0", "FILL")
    fill.setInput(0, key)
    set_parm(fill, "primpath", "/World/Lights/Fill")
    set_parm(fill, "rx", -20.0)
    set_parm(fill, "ry", -45.0)
    set_parm(fill, "xn__inputsintensity_i0a", 1.5)
    rim = stage.createNode("distantlight::2.0", "RIM")
    rim.setInput(0, fill)
    set_parm(rim, "primpath", "/World/Lights/Rim")
    set_parm(rim, "rx", 25.0)
    set_parm(rim, "ry", 155.0)
    set_parm(rim, "xn__inputsintensity_i0a", 3.0)

    selector = stage.createNode("switch", "SELECT_LIGHTING_MODE")
    selector.setInput(0, dome)
    selector.setInput(1, rim)
    selector.parm("input").setExpression('ch("../lighting_mode")', hou.exprLanguage.Hscript)
    settings = stage.createNode("karmarendersettings", "RENDER_KARMA_SETTINGS")
    settings.setInput(0, selector)
    set_parm(settings, "primpath", "/Render/Playground")
    set_parm(settings, "camera", "/World/Cameras/Playground")
    set_parm(settings, "picture", native(output_dir / layout["render_directory"] / "playground.$F4.exr"))
    set_parm(settings, "res_mode", "manual")
    set_parm(settings, "resolutionx", 768)
    set_parm(settings, "engine", "cpu")
    set_parm(settings, "samplesperpixel", 4)
    set_parm(settings, "pathtracedsamples", 16)
    set_parm(settings, "enabledof", 0)
    set_parm(settings, "enablemblur", 0)
    set_parm(settings, "point_style", "Spheres")
    set_parm(settings, "curve_style", "Rounded Curves")
    render = stage.createNode("usdrender_rop", "OUT_KARMA")
    render.setInput(0, settings)
    set_parm(render, "renderer", "BRAY_HdKarma")
    set_parm(render, "loppath", settings.path())
    set_parm(render, "rendersettings", "/Render/Playground")
    set_parm(render, "trange", 0)

    positions = {
        import_sim: (-4, 15), import_env: (4, 15), merge: (0, 12), library: (0, 9), assign: (0, 6),
        camera: (0, 3), dome: (-5, 0), key: (5, 0), fill: (5, -3), rim: (5, -6),
        selector: (0, -9), settings: (0, -12), render: (0, -15),
    }
    for node, position in positions.items():
        node.setPosition(hou.Vector2(position))
    for node in (import_sim, import_env, merge):
        node.setColor(hou.Color((0.22, 0.48, 0.68)))
    for node in (library, assign):
        node.setColor(hou.Color((0.48, 0.34, 0.66)))
    camera.setColor(hou.Color((0.36, 0.56, 0.72)))
    for node in (dome, key, fill, rim, selector):
        node.setColor(hou.Color((0.72, 0.56, 0.18)))
    settings.setColor(hou.Color((0.62, 0.34, 0.22)))
    render.setColor(hou.Color((0.22, 0.68, 0.38)))
    for label, nodes in (
        ("01 Imports + Starter Materials", (import_sim, import_env, merge, library, assign)),
        ("02 Editable Camera", (camera,)),
        ("03 Dome or Photographer Lighting", (dome, key, fill, rim, selector)),
        ("04 Karma Settings + Output", (settings, render)),
    ):
        box = stage.createNetworkBox()
        box.setComment(label)
        for node in nodes:
            box.addItem(node)
        box.fitAroundContents()
    stage_note = stage.createStickyNote()
    stage_note.setText("00 LOOK PLAYGROUND\nSwitch /stage Lighting Mode. Tweak anything. Not a review candidate.")
    stage_note.setPosition(hou.Vector2((9, 12)))
    stage_note.setSize(hou.Vector2((6, 3)))

    hou.hipFile.save(native(hip_path))


def verify(packet_path: Path, hip_path: Path, audit_path: Path) -> bool:
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    try:
        hou.hipFile.load(native(hip_path), suppress_save_prompt=True, ignore_load_warnings=False)
    except hou.Error as error:
        errors.append(str(error))
    required = {
        "source_file": "/obj/PLAYGROUND_SIM/SOURCE_PROMOTED_SIMULATION",
        "source_node": "/obj/PLAYGROUND_SIM/OUT_SIMULATION",
        "visibility_node": "/obj/PLAYGROUND_SIM/ENSURE_POINT_VISIBILITY",
        "floor_node": "/obj/PLAYGROUND_ENVIRONMENT/NEUTRAL_FLOOR",
        "floor_placement": "/obj/PLAYGROUND_ENVIRONMENT/PLACE_FLOOR",
        "environment_node": "/obj/PLAYGROUND_ENVIRONMENT/OUT_ENVIRONMENT",
        "simulation_import": "/stage/IMPORT_SIMULATION",
        "environment_import": "/stage/IMPORT_ENVIRONMENT",
        "scene_merge": "/stage/MERGE_SCENE",
        "material_library": "/stage/MATERIALS_STARTER",
        "material_assignment": "/stage/ASSIGN_STARTER_MATERIALS",
        "camera_node": "/stage/CAM_PLAYGROUND",
        "dome_light": "/stage/LIGHT_DOME",
        "key_light": "/stage/KEY",
        "fill_light": "/stage/FILL",
        "rim_light": "/stage/RIM",
        "lighting_selector": "/stage/SELECT_LIGHTING_MODE",
        "karma_settings": "/stage/RENDER_KARMA_SETTINGS",
        "render_output": "/stage/OUT_KARMA",
    }
    nodes = {key: hou.node(path) for key, path in required.items()}
    for key, node in nodes.items():
        if node is None:
            errors.append(f"missing {key}: {required[key]}")
    expected_types = {
        "source_file": "file",
        "source_node": "null",
        "visibility_node": "attribwrangle",
        "floor_node": "grid",
        "floor_placement": "xform",
        "environment_node": "null",
        "simulation_import": "sopimport",
        "environment_import": "sopimport",
        "scene_merge": "merge",
        "material_library": "materiallibrary",
        "material_assignment": "assignmaterial",
        "camera_node": "camera",
        "dome_light": "domelight::3.0",
        "key_light": "distantlight::2.0",
        "fill_light": "distantlight::2.0",
        "rim_light": "distantlight::2.0",
        "lighting_selector": "switch",
        "karma_settings": "karmarendersettings",
        "render_output": "usdrender_rop",
    }
    for key, expected_type in expected_types.items():
        node = nodes[key]
        if node is not None and node.type().name() != expected_type:
            errors.append(f"{node.path()} has type {node.type().name()}, expected {expected_type}")
    source = nodes["source_node"]
    source_file = nodes["source_file"]
    source_geometry = None
    cache_sequence: list[dict[str, Any]] = []
    source_records = packet.get("source_cache_receipt", [])
    if source_file is not None and source is not None and source_records:
        first_record = source_records[0]
        first_frame = cache_frame(first_record["path"])
        hou.setFrame(first_frame if first_frame is not None else hou.playbar.frameRange()[0])
        evaluated_first = Path(source_file.evalParm("file")).resolve()
        relative_first = Path(first_record["path"])
        project_root = evaluated_first
        for _ in relative_first.parts:
            project_root = project_root.parent
        expected_expression = cache_expression(project_root / relative_first)
        if source_file.parm("file").unexpandedString() != expected_expression:
            errors.append("source File SOP expression is not bound to the frozen cache sequence")
        for index, record in enumerate(source_records):
            candidate = (project_root / record["path"]).resolve()
            frame = cache_frame(record["path"])
            if frame is not None:
                hou.setFrame(frame)
            evaluated = Path(source_file.evalParm("file")).resolve()
            record_errors: list[str] = []
            if evaluated != candidate:
                record_errors.append("File SOP did not evaluate to this frozen frame")
            if not candidate.is_file():
                record_errors.append("frozen cache frame is missing")
            elif candidate.stat().st_size != record["bytes"] or sha256(candidate) != record["sha256"]:
                record_errors.append("frozen cache frame bytes or hash changed")
            try:
                source_file.cook(force=True)
                source.cook(force=True)
                geometry = source.geometry()
                if geometry is None or (len(geometry.points()) == 0 and len(geometry.prims()) == 0):
                    record_errors.append("import chain cooked no geometry")
                elif index == 0:
                    source_geometry = geometry.freeze()
            except hou.Error as error:
                record_errors.append(f"import chain cook failed: {error}")
            errors.extend(f"cache {record['path']}: {message}" for message in record_errors)
            cache_sequence.append({
                "path": str(candidate),
                "frame": frame,
                "bytes": candidate.stat().st_size if candidate.is_file() else None,
                "sha256": sha256(candidate) if candidate.is_file() else None,
                "errors": record_errors,
            })
        hou.setFrame(first_frame if first_frame is not None else hou.playbar.frameRange()[0])
    else:
        errors.append("source cache sequence or import nodes are unavailable")
    environment = nodes["environment_node"]
    if environment is not None:
        try:
            environment.cook(force=True)
            if environment.geometry() is None or len(environment.geometry().prims()) == 0:
                errors.append("neutral environment cooked no geometry")
        except hou.Error as error:
            errors.append(f"neutral environment cook failed: {error}")
    visibility = nodes["visibility_node"]
    if visibility is not None and visibility.parm("fallback_pscale") is None:
        errors.append("point-visibility fallback control is missing")
    library = nodes["material_library"]
    if library is not None:
        for material_name in ("SIM_STARTER", "FLOOR_NEUTRAL"):
            material = library.node(material_name)
            shader = library.node(f"{material_name}_SHADER")
            if material is None or material.type().name() != "mtlxsurfacematerial":
                errors.append(f"starter material is missing: {material_name}")
            if shader is None or shader.type().name() != "mtlxstandard_surface":
                errors.append(f"starter MaterialX shader is missing: {material_name}")
            if material is not None and (not material.inputs() or material.inputs()[0] != shader):
                errors.append(f"starter material is not connected to its shader: {material_name}")
    assignment = nodes["material_assignment"]
    if assignment is not None:
        expected_assignments = (
            ("/World/Simulation /World/Simulation/**", "/materials/SIM_STARTER"),
            ("/World/Environment /World/Environment/**", "/materials/FLOOR_NEUTRAL"),
        )
        if assignment.evalParm("nummaterials") != len(expected_assignments):
            errors.append("starter material assignment count is incorrect")
        for index, (primitive_pattern, material_path) in enumerate(expected_assignments, 1):
            if (
                assignment.evalParm(f"primpattern{index}") != primitive_pattern
                or assignment.evalParm(f"matspecpath{index}") != material_path
            ):
                errors.append(f"starter material assignment {index} is incorrect")
    if nodes["simulation_import"] is not None and nodes["simulation_import"].evalParm("soppath") != required["source_node"]:
        errors.append("simulation LOP import does not target the verified simulation output")
    if nodes["environment_import"] is not None and nodes["environment_import"].evalParm("soppath") != required["environment_node"]:
        errors.append("environment LOP import does not target the verified floor output")
    stage = hou.node("/stage")
    lighting = stage.parm("lighting_mode") if stage else None
    selector = nodes["lighting_selector"]
    if lighting is None or selector is None:
        errors.append("lighting mode control is unavailable")
    else:
        for mode in (0, 1):
            lighting.set(mode)
            if int(selector.evalParm("input")) != mode:
                errors.append(f"lighting selector did not switch to mode {mode}")
        selector_inputs = selector.inputs()
        if (
            len(selector_inputs) < 2
            or selector_inputs[0] != nodes["dome_light"]
            or selector_inputs[1] != nodes["rim_light"]
        ):
            errors.append("lighting selector is not wired to the dome and photographer branches")
    settings = nodes["karma_settings"]
    if settings is not None:
        try:
            settings.cook(force=True)
        except hou.Error as error:
            errors.append(f"Karma settings cook failed: {error}")
    expected_connections = (
        (nodes["visibility_node"], nodes["source_file"]),
        (nodes["source_node"], nodes["visibility_node"]),
        (nodes["floor_placement"], nodes["floor_node"]),
        (nodes["environment_node"], nodes["floor_placement"]),
        (nodes["material_library"], nodes["scene_merge"]),
        (nodes["material_assignment"], nodes["material_library"]),
        (nodes["camera_node"], nodes["material_assignment"]),
        (nodes["dome_light"], nodes["camera_node"]),
        (nodes["key_light"], nodes["camera_node"]),
        (nodes["fill_light"], nodes["key_light"]),
        (nodes["rim_light"], nodes["fill_light"]),
        (nodes["karma_settings"], nodes["lighting_selector"]),
        (nodes["render_output"], nodes["karma_settings"]),
    )
    for downstream, upstream in expected_connections:
        if downstream is not None and (not downstream.inputs() or downstream.inputs()[0] != upstream):
            errors.append(f"{downstream.path()} is not connected to the required upstream node")
    merge = nodes["scene_merge"]
    if merge is not None:
        merge_inputs = merge.inputs()
        if (
            len(merge_inputs) < 2
            or merge_inputs[0] != nodes["simulation_import"]
            or merge_inputs[1] != nodes["environment_import"]
        ):
            errors.append("scene merge does not combine the verified simulation and environment imports")
    camera = nodes["camera_node"]
    camera_framing: dict[str, Any] = {"auto_framed": False}
    if camera is not None and source_geometry is not None:
        bounds = source_geometry.boundingBox()
        center = bounds.center()
        position = [camera.evalParm(name) for name in ("tx", "ty", "tz")]
        auto_framed = (
            abs(position[0] - float(center[0])) < 1e-5
            and abs(position[1] - float(center[1])) < 1e-5
            and position[2] > float(bounds.maxvec()[2])
        )
        if not auto_framed:
            errors.append("playground camera is not framed from the simulation bounds")
        camera_framing = {
            "auto_framed": auto_framed,
            "simulation_center": [float(value) for value in center],
            "camera_position": position,
        }
    render_configuration = {
        "camera": settings.evalParm("camera") if settings is not None else None,
        "picture": settings.parm("picture").unexpandedString() if settings is not None else None,
        "resolution_x": settings.evalParm("resolutionx") if settings is not None else None,
        "point_style": settings.evalParm("point_style") if settings is not None else None,
        "renderer": nodes["render_output"].evalParm("renderer") if nodes["render_output"] is not None else None,
    }
    if (
        render_configuration["camera"] != "/World/Cameras/Playground"
        or not isinstance(render_configuration["picture"], str)
        or not render_configuration["picture"].endswith("playground.$F4.exr")
        or render_configuration["resolution_x"] != 768
        or render_configuration["point_style"] != "Spheres"
        or render_configuration["renderer"] != "BRAY_HdKarma"
    ):
        errors.append("Karma render configuration is incomplete")
    inspected = [node for node in nodes.values() if node is not None]
    inspected.extend(node for node in (hou.node("/stage/KEY"), hou.node("/stage/FILL"), hou.node("/stage/RIM")) if node)
    for node in inspected:
        errors.extend(f"{node.path()}: {message}" for message in node.errors())
    evaluated_cache = Path(source_file.evalParm("file")) if source_file is not None else None
    audit: dict[str, Any] = {
        "schema_version": 1,
        "verification_engine": "fresh-hython-reopen",
        "hip_path": str(hip_path.resolve()),
        "hip_sha256": sha256(hip_path),
        "passed": not errors,
        **required,
        "lighting_modes": packet["features"]["lighting_modes"],
        "photographer_lights": ["KEY", "FILL", "RIM"],
        "node_errors": errors,
        "source_cache_path": str(evaluated_cache) if evaluated_cache is not None else None,
        "source_cache_sha256": (
            sha256(evaluated_cache) if evaluated_cache is not None and evaluated_cache.is_file() else None
        ),
        "source_cache_bytes": (
            evaluated_cache.stat().st_size if evaluated_cache is not None and evaluated_cache.is_file() else None
        ),
        "cache_sequence": cache_sequence,
        "frame_range": [int(hou.playbar.frameRange()[0]), int(hou.playbar.frameRange()[1])],
        "camera_framing": camera_framing,
        "render_configuration": render_configuration,
    }
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return not errors


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("packet", type=Path)
    build_parser.add_argument("output", type=Path)
    build_parser.add_argument("project_root", type=Path)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("packet", type=Path)
    verify_parser.add_argument("hip", type=Path)
    verify_parser.add_argument("audit", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        build(args.packet.resolve(), args.output.resolve(), args.project_root.resolve())
        return 0
    return 0 if verify(args.packet.resolve(), args.hip.resolve(), args.audit.resolve()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
