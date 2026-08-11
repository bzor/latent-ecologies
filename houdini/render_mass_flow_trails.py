"""Build and Karma-render the Study 002 derived-trail look."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import hou


def set_parm(node: hou.Node, name: str, value: object) -> None:
    parm = node.parm(name)
    if parm is None:
        raise RuntimeError(f"{node.path()} has no parameter named {name}")
    parm.set(value)


def create_material(parent: hou.Node, name: str, color: tuple[float, float, float]) -> hou.Node:
    shader = parent.createNode("mtlxstandard_surface", f"{name}_shader")
    surface = parent.createNode("mtlxsurfacematerial", name)
    surface.setInput(0, shader)
    set_parm(shader, "base", 0.52)
    set_parm(shader, "specular_roughness", 0.42)
    set_parm(shader, "emission", 0.12)
    for prefix in ("base_color", "emission_color"):
        for channel, value in zip("rgb", color):
            set_parm(shader, f"{prefix}{channel}", value)
    return surface


def create_backdrop_material(parent: hou.Node) -> hou.Node:
    shader = parent.createNode("mtlxstandard_surface", "backdrop_shader")
    surface = parent.createNode("mtlxsurfacematerial", "backdrop")
    surface.setInput(0, shader)
    set_parm(shader, "base", 0.75)
    set_parm(shader, "base_colorr", 0.006)
    set_parm(shader, "base_colorg", 0.009)
    set_parm(shader, "base_colorb", 0.014)
    set_parm(shader, "specular_roughness", 0.28)
    set_parm(shader, "metalness", 0.18)
    return surface


def build_trails(cache_dir: Path, system: dict, output: Path) -> None:
    frames = [int(path.stem.split(".")[1]) for path in sorted(cache_dir.glob("state.[0-9][0-9][0-9][0-9].bgeo.sc"))]
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
            position = (values[agent_index * 3], values[agent_index * 3 + 1], 0.0)
            if run:
                prior = run[-1][0]
                if abs(position[0] - prior[0]) > domain_width * 0.5 or abs(position[1] - prior[1]) > domain_height * 0.5:
                    if len(run) >= 2:
                        _add_curve(trails, run, phases[agent_index], system)
                    run = []
            run.append((position, history_index / max(1, len(positions) - 1)))
        if len(run) >= 2:
            _add_curve(trails, run, phases[agent_index], system)
    trails.saveToFile(str(output))


def _add_curve(trails: hou.Geometry, samples: list, phase: int, system: dict) -> None:
    curve = trails.createPolygon()
    curve.setIsClosed(False)
    curve.setAttribValue("phase", int(phase))
    for position, age in samples:
        point = trails.createPoint()
        point.setPosition(position)
        point.setAttribValue("age", age)
        point.setAttribValue("width", float(system["point_size"]) * (0.55 + age * 1.15))
        curve.addVertex(point)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("cache_dir", type=Path)
    parser.add_argument("hip", type=Path)
    parser.add_argument("image", type=Path)
    parser.add_argument("--hdri", type=Path)
    parser.add_argument("--dome-rotation", type=float, default=0.0)
    parser.add_argument("--renderer", choices=("cpu", "xpu"), default="xpu")
    args = parser.parse_args()
    effective = json.loads(args.config.read_text(encoding="utf-8"))
    study = effective.get("study", effective)
    system = study["simulation"]["rule_genome"]["system"]
    render_config = study["render"]
    trail_cache = args.hip.with_name("derived-trails.bgeo.sc")
    args.hip.parent.mkdir(parents=True, exist_ok=True)
    args.image.parent.mkdir(parents=True, exist_ok=True)
    build_trails(args.cache_dir, system, trail_cache)

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
    geo.layoutChildren()

    backdrop_geo = obj.createNode("geo", "mass_flow_backdrop")
    for child in backdrop_geo.children():
        child.destroy()
    backdrop = backdrop_geo.createNode("sphere", "elliptical_slab")
    set_parm(backdrop, "type", "poly")
    set_parm(backdrop, "rows", 72)
    set_parm(backdrop, "cols", 96)
    transform = backdrop_geo.createNode("xform", "shape_backdrop")
    transform.setInput(0, backdrop)
    set_parm(transform, "sx", 4.15)
    set_parm(transform, "sy", 7.35)
    set_parm(transform, "sz", 0.34)
    set_parm(transform, "tz", -0.52)
    backdrop_out = backdrop_geo.createNode("null", "OUT_BACKDROP")
    backdrop_out.setInput(0, transform)
    backdrop_geo.layoutChildren()

    stage = hou.node("/stage")
    backdrop_import = stage.createNode("sopimport", "import_backdrop")
    set_parm(backdrop_import, "soppath", backdrop_out.path())
    set_parm(backdrop_import, "primpath", "/world/backdrop")
    set_parm(backdrop_import, "pathprefix", "/world/backdrop")
    previous = backdrop_import
    for phase in range(3):
        import_node = stage.createNode("sopimport", f"import_phase_{phase}")
        if previous is not None:
            import_node.setInput(0, previous)
        set_parm(import_node, "soppath", outputs[phase].path())
        set_parm(import_node, "primpath", f"/world/trails/phase_{phase}")
        set_parm(import_node, "pathprefix", f"/world/trails/phase_{phase}")
        previous = import_node
    library = stage.createNode("materiallibrary", "trail_materials")
    library.setInput(0, previous)
    palette = ((0.012, 0.18, 0.29), (0.34, 0.055, 0.012), (0.15, 0.035, 0.30))
    materials = [create_material(library, f"phase_{phase}", palette[phase]) for phase in range(3)]
    backdrop_material = create_backdrop_material(library)
    library.layoutChildren()
    assign = stage.createNode("assignmaterial", "assign_trail_materials")
    assign.setInput(0, library)
    set_parm(assign, "nummaterials", 4)
    for index, material in enumerate(materials, 1):
        phase = index - 1
        set_parm(assign, f"primpattern{index}", f"/world/trails/phase_{phase} /world/trails/phase_{phase}/**")
        set_parm(assign, f"matspecpath{index}", material.path().replace(library.path(), "/materials"))
    set_parm(assign, "primpattern4", "/world/backdrop /world/backdrop/**")
    set_parm(assign, "matspecpath4", backdrop_material.path().replace(library.path(), "/materials"))

    camera = stage.createNode("camera", "trail_camera")
    camera.setInput(0, assign)
    set_parm(camera, "primpath", "/cameras/trail")
    set_parm(camera, "tz", 23.2)
    set_parm(camera, "aspectratiox", render_config["width"])
    set_parm(camera, "aspectratioy", render_config["height"])
    light = stage.createNode("domelight::2.0", "trail_environment")
    light.setInput(0, camera)
    set_parm(light, "primpath", "/lights/trail_environment")
    set_parm(light, "ry", args.dome_rotation)
    set_parm(light, "xn__inputsintensity_i0a", 0.75)
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
