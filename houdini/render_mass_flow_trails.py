"""Build and Karma-render the Study 002 derived-trail look."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import hou


def set_parm(node: hou.Node, name: str, value: object) -> None:
    parm = node.parm(name)
    if parm is None:
        raise RuntimeError(f"{node.path()} has no parameter named {name}")
    parm.set(value)


def create_material(
    parent: hou.Node, name: str, color: tuple[float, float, float], *, metalness: float = 0.0, roughness: float = 0.42
) -> hou.Node:
    shader = parent.createNode("mtlxstandard_surface", f"{name}_shader")
    surface = parent.createNode("mtlxsurfacematerial", name)
    surface.setInput(0, shader)
    set_parm(shader, "base", 1.0)
    set_parm(shader, "metalness", metalness)
    set_parm(shader, "specular_roughness", roughness)
    set_parm(shader, "emission", 0.0)
    for channel, value in zip("rgb", color):
        set_parm(shader, f"base_color{channel}", value)
    return surface


def create_white_background_material(parent: hou.Node) -> hou.Node:
    shader = parent.createNode("mtlxstandard_surface", "white_background_shader")
    surface = parent.createNode("mtlxsurfacematerial", "white_background")
    surface.setInput(0, shader)
    set_parm(shader, "base", 1.0)
    for channel in "rgb":
        set_parm(shader, f"base_color{channel}", 0.0761)
    set_parm(shader, "specular_roughness", 0.72)
    return surface


def build_trails(cache_dir: Path, system: dict, output: Path, heads_output: Path, end_frame: int | None = None) -> None:
    frames = [int(path.stem.split(".")[1]) for path in sorted(cache_dir.glob("state.[0-9][0-9][0-9][0-9].bgeo.sc"))]
    if end_frame is not None:
        frames = [frame for frame in frames if frame <= end_frame]
    frames = frames[-int(system.get("trail_history_checkpoints", len(frames))):]
    geometries = []
    for frame in frames:
        geometry = hou.Geometry()
        geometry.loadFromFile(str(cache_dir / f"state.{frame:04d}.bgeo.sc"))
        geometries.append(geometry)
    if len(geometries) < 2:
        raise RuntimeError("derived trails require at least two cached checkpoints")
    count = len(geometries[0].points())
    stride = max(1, count // int(system["review_agent_count"]))
    positions = [geometry.pointFloatAttribValues("P") for geometry in geometries]
    phases = geometries[0].pointIntAttribValues("phase")
    domain_width, domain_height = float(system["domain_width"]), float(system["domain_height"])

    trails = hou.Geometry()
    trails.addAttrib(hou.attribType.Prim, "phase", 0)
    trails.addAttrib(hou.attribType.Point, "width", 0.012)
    trails.addAttrib(hou.attribType.Point, "age", 0.0)
    for agent_index in range(0, count, stride):
        run = []
        for history_index, values in enumerate(positions):
            position = (
                values[agent_index * 3],
                values[agent_index * 3 + 1],
                values[agent_index * 3 + 2],
            )
            if run:
                prior = run[-1][0]
                if abs(position[0] - prior[0]) > domain_width * 0.5 or abs(position[1] - prior[1]) > domain_height * 0.5:
                    if len(run) >= 2:
                        _add_curve(trails, run, phases[agent_index], system)
                    run = []
            run.append((position, history_index / max(1, len(positions) - 1)))
        if len(run) >= 2:
            _add_curve(trails, run, phases[agent_index], system)
    depth_size = trails.boundingBox().sizevec()[2]
    if float(system.get("domain_depth", 0.0)) > 0 and depth_size < float(system["domain_depth"]) * 0.1:
        raise RuntimeError(f"volumetric trail export collapsed to {depth_size:.6f} units of depth")
    trails.saveToFile(str(output))

    heads = hou.Geometry()
    heads.addAttrib(hou.attribType.Point, "phase", 0)
    heads.addAttrib(hou.attribType.Point, "endpoint", 0)
    heads.addAttrib(hou.attribType.Point, "pscale", float(system["head_scale"]))
    endpoint_positions = ((0, positions[0]), (1, positions[-1]))
    for agent_index in range(0, count, stride):
        for endpoint_role, endpoint in endpoint_positions:
            point = heads.createPoint()
            point.setPosition(endpoint[agent_index * 3:agent_index * 3 + 3])
            point.setAttribValue("phase", phases[agent_index])
            point.setAttribValue("endpoint", endpoint_role)
            point.setAttribValue(
                "pscale", float(system["head_scale"]) * (float(system.get("start_head_scale", 1.0)) if endpoint_role == 0 else 1.0)
            )
    heads.saveToFile(str(heads_output))


def _add_curve(trails: hou.Geometry, samples: list, phase: int, system: dict) -> None:
    samples = _smooth_samples(samples, int(system.get("trail_smoothing_max_subdivisions", 6)))
    curve = trails.createPolygon()
    curve.setIsClosed(False)
    curve.setAttribValue("phase", int(phase))
    for position, age in samples:
        point = trails.createPoint()
        point.setPosition(position)
        point.setAttribValue("age", age)
        width_scale = float(system.get("lead_phase_width_scale", 1.0)) if phase == int(system.get("lead_phase", -1)) else 1.0
        point.setAttribValue("width", float(system["point_size"]) * width_scale * (0.55 + age * 1.15))
        curve.addVertex(point)


def _smooth_samples(samples: list, max_subdivisions: int) -> list:
    """Return a Catmull-Rom interpolation that preserves every sampled endpoint."""
    if len(samples) < 3 or max_subdivisions < 2:
        return samples

    def subtract(left: tuple[float, float, float], right: tuple[float, float, float]) -> tuple[float, float, float]:
        return tuple(a - b for a, b in zip(left, right))

    def length(vector: tuple[float, float, float]) -> float:
        return math.sqrt(sum(component * component for component in vector))

    def turn_angle(before: tuple[float, float, float], after: tuple[float, float, float]) -> float:
        before_length, after_length = length(before), length(after)
        if before_length <= 1e-8 or after_length <= 1e-8:
            return 0.0
        cosine = sum(a * b for a, b in zip(before, after)) / (before_length * after_length)
        return math.acos(max(-1.0, min(1.0, cosine)))

    smoothed = []
    for index in range(len(samples) - 1):
        previous = samples[max(0, index - 1)][0]
        start, start_age = samples[index]
        end, end_age = samples[index + 1]
        following = samples[min(len(samples) - 1, index + 2)][0]
        entering = subtract(start, previous)
        leaving = subtract(following, end)
        angle = max(turn_angle(entering, subtract(end, start)), turn_angle(subtract(end, start), leaving))
        subdivisions = min(max_subdivisions, max(1, 1 + math.ceil(angle / 0.45)))
        for subdivision in range(subdivisions):
            time = subdivision / subdivisions
            time_squared, time_cubed = time * time, time * time * time
            basis_start = 2 * time_cubed - 3 * time_squared + 1
            basis_in = time_cubed - 2 * time_squared + time
            basis_end = -2 * time_cubed + 3 * time_squared
            basis_out = time_cubed - time_squared
            position = tuple(
                basis_start * start[channel]
                + basis_in * (end[channel] - previous[channel]) * 0.5
                + basis_end * end[channel]
                + basis_out * (following[channel] - start[channel]) * 0.5
                for channel in range(3)
            )
            age = start_age + (end_age - start_age) * time
            smoothed.append((position, age))
    smoothed.append(samples[-1])
    return smoothed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("cache_dir", type=Path)
    parser.add_argument("hip", type=Path)
    parser.add_argument("image", type=Path)
    parser.add_argument("--hdri", type=Path)
    parser.add_argument("--dome-rotation", type=float, default=-106.0)
    parser.add_argument("--dome-intensity", type=float, default=1.6)
    parser.add_argument("--renderer", choices=("cpu", "xpu"), default="xpu")
    parser.add_argument("--end-frame", type=int, help="build trails and heads through this cached checkpoint")
    args = parser.parse_args()
    effective = json.loads(args.config.read_text(encoding="utf-8"))
    study = effective.get("study", effective)
    system = study["simulation"]["rule_genome"]["system"]
    render_config = study["render"]
    trail_cache = args.hip.with_name("derived-trails.bgeo.sc")
    head_cache = args.hip.with_name("agent-heads.bgeo.sc")
    args.hip.parent.mkdir(parents=True, exist_ok=True)
    args.image.parent.mkdir(parents=True, exist_ok=True)
    build_trails(args.cache_dir, system, trail_cache, head_cache, args.end_frame)

    hou.hipFile.clear(suppress_save_prompt=True)
    obj = hou.node("/obj")
    geo = obj.createNode("geo", "mass_flow_trails")
    for child in geo.children():
        child.destroy()
    source = geo.createNode("file", "derived_trails")
    set_parm(source, "file", str(trail_cache))
    outputs = {}
    for phase in range(3):
        select = geo.createNode("attribwrangle", f"select_phase_{phase}")
        select.setInput(0, source)
        set_parm(select, "class", 1)
        set_parm(select, "snippet", f"if (i@phase != {phase}) removeprim(0, @primnum, 1);")
        output = geo.createNode("null", f"OUT_PHASE_{phase}")
        output.setInput(0, select)
        outputs[phase] = output

    head_source = geo.createNode("file", "agent_heads")
    set_parm(head_source, "file", str(head_cache))
    head_sphere = geo.createNode("sphere", "head_sphere")
    set_parm(head_sphere, "type", "poly")
    set_parm(head_sphere, "rows", 8)
    set_parm(head_sphere, "cols", 12)
    head_outputs = {}
    for phase in range(3):
        for endpoint_role, endpoint_name in ((0, "start"), (1, "end")):
            select = geo.createNode("attribwrangle", f"select_{endpoint_name}_heads_phase_{phase}")
            select.setInput(0, head_source)
            set_parm(select, "class", 2)
            set_parm(
                select,
                "snippet",
                f"if (i@phase != {phase} || i@endpoint != {endpoint_role}) removepoint(0, @ptnum);",
            )
            copies = geo.createNode("copytopoints::2.0", f"copy_{endpoint_name}_heads_phase_{phase}")
            copies.setInput(0, head_sphere)
            copies.setInput(1, select)
            output = geo.createNode("null", f"OUT_{endpoint_name.upper()}_HEADS_PHASE_{phase}")
            output.setInput(0, copies)
            head_outputs[(phase, endpoint_role)] = output
    geo.layoutChildren()

    # Camera-relative backing card: at the fixed observation camera's origin and
    # orientation this is equivalent to a parented grid offset behind the artwork.
    # Overscan keeps white in every pixel through small future framing adjustments.
    background_geo = obj.createNode("geo", "camera_white_background")
    for child in background_geo.children():
        child.destroy()
    background = background_geo.createNode("box", "camera_backing_card")
    set_parm(background, "sizex", 16.0)
    set_parm(background, "sizey", 28.5)
    set_parm(background, "sizez", 0.04)
    set_parm(background, "tz", -3.0)
    background_out = background_geo.createNode("null", "OUT_BACKGROUND")
    background_out.setInput(0, background)
    background_geo.layoutChildren()

    stage = hou.node("/stage")
    background_import = stage.createNode("sopimport", "import_camera_background")
    set_parm(background_import, "soppath", background_out.path())
    set_parm(background_import, "primpath", "/world/camera_background")
    set_parm(background_import, "pathprefix", "/world/camera_background")
    previous = background_import
    for phase in range(3):
        import_node = stage.createNode("sopimport", f"import_phase_{phase}")
        if previous is not None:
            import_node.setInput(0, previous)
        set_parm(import_node, "soppath", outputs[phase].path())
        set_parm(import_node, "primpath", f"/world/trails/phase_{phase}")
        set_parm(import_node, "pathprefix", f"/world/trails/phase_{phase}")
        previous = import_node
    for phase in range(3):
        for endpoint_role, endpoint_name in ((0, "start"), (1, "end")):
            import_node = stage.createNode("sopimport", f"import_{endpoint_name}_heads_phase_{phase}")
            import_node.setInput(0, previous)
            set_parm(import_node, "soppath", head_outputs[(phase, endpoint_role)].path())
            set_parm(import_node, "primpath", f"/world/heads/{endpoint_name}/phase_{phase}")
            set_parm(import_node, "pathprefix", f"/world/heads/{endpoint_name}/phase_{phase}")
            previous = import_node
    library = stage.createNode("materiallibrary", "trail_materials")
    library.setInput(0, previous)
    material_specs = (
        ((0.155, 0.18, 0.195), 0.0, 0.30),
        ((0.025, 0.025, 0.025), 1.0, 0.22),
        ((0.01, 0.0074, 0.0134), 0.0, 0.42),
    )
    materials = [
        create_material(library, f"phase_{phase}", color, metalness=metalness, roughness=roughness)
        for phase, (color, metalness, roughness) in enumerate(material_specs)
    ]
    start_materials = [
        create_material(library, f"start_phase_{phase}", tuple(channel * 0.42 for channel in color), roughness=0.76)
        for phase, (color, _, _) in enumerate(material_specs)
    ]
    background_material = create_white_background_material(library)
    library.layoutChildren()
    assign = stage.createNode("assignmaterial", "assign_trail_materials")
    assign.setInput(0, library)
    set_parm(assign, "nummaterials", 7)
    for index, material in enumerate(materials, 1):
        phase = index - 1
        set_parm(
            assign,
            f"primpattern{index}",
            f"/world/trails/phase_{phase} /world/trails/phase_{phase}/** "
            f"/world/heads/end/phase_{phase} /world/heads/end/phase_{phase}/**",
        )
        set_parm(assign, f"matspecpath{index}", material.path().replace(library.path(), "/materials"))
    for index, material in enumerate(start_materials, 4):
        phase = index - 4
        set_parm(assign, f"primpattern{index}", f"/world/heads/start/phase_{phase} /world/heads/start/phase_{phase}/**")
        set_parm(assign, f"matspecpath{index}", material.path().replace(library.path(), "/materials"))
    set_parm(assign, "primpattern7", "/world/camera_background /world/camera_background/**")
    set_parm(assign, "matspecpath7", background_material.path().replace(library.path(), "/materials"))

    camera = stage.createNode("camera", "trail_camera")
    camera.setInput(0, assign)
    set_parm(camera, "primpath", "/cameras/trail")
    set_parm(camera, "tz", 45.0)
    set_parm(camera, "focalLength", 100.0)
    set_parm(camera, "focusDistance", 44.0)
    set_parm(camera, "fStop", 0.09)
    set_parm(camera, "aspectratiox", render_config["width"])
    set_parm(camera, "aspectratioy", render_config["height"])
    light = stage.createNode("domelight::2.0", "trail_environment")
    light.setInput(0, camera)
    set_parm(light, "primpath", "/lights/trail_environment")
    set_parm(light, "ry", args.dome_rotation)
    set_parm(light, "xn__inputsintensity_i0a", args.dome_intensity)
    set_parm(light, "xn__inputsexposure_vya", -0.35)
    if args.hdri:
        set_parm(light, "xn__inputstexturefile_r3ah", args.hdri.resolve().as_posix())
    settings = stage.createNode("karmarendersettings", "trail_settings")
    settings.setInput(0, light)
    set_parm(settings, "camera", "/cameras/trail")
    set_parm(settings, "picture", args.image.resolve().as_posix())
    set_parm(settings, "res_mode", "autoheight")
    set_parm(settings, "resolutionx", render_config["width"])
    set_parm(settings, "samplesperpixel", 4)
    render = stage.createNode("usdrender_rop", "trail_render")
    render.setInput(0, settings)
    set_parm(render, "renderer", "Karma XPU" if args.renderer == "xpu" else "Karma CPU")
    set_parm(render, "soho_foreground", True)
    set_parm(render, "mkpath", True)
    stage.layoutChildren()
    hou.hipFile.save(str(args.hip.resolve()))
    render.render(frame_range=(1, 1, 1))
    print(f"trail_curves: {len(hou.Geometry().points()) if False else trail_cache}")
    print(f"trail_image: {args.image.resolve()}")
    print(f"trail_renderer: Karma {args.renderer.upper()}")


if __name__ == "__main__":
    main()
