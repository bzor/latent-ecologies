"""Build and optionally Karma-render the Scar Tissue memory-grid look."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import hou


AGENT_SCALE = 0.015
AGENT_LAYER_HEIGHT = 0.90
HAIR_HISTORY_FRAMES = 12
HAIR_HISTORY_ALPHA = 0.28
HAIR_BEND_EXPONENT = 2.2
HAIR_MAXIMUM_LEAN = 0.58
HAIR_ROOT_SCALE = 1.0
HAIR_TIP_SCALE = 0.0
TRAIL_RADIUS = 0.004
CUBE_VERTICAL_COLOR_EXPONENT = 2.0
CUBE_BEVEL_WIDTH = 0.006
CUBE_BEVEL_DIVISIONS = 1
PALETTES = {
    "neutral": {
        "ground": ((0.075, 0.082, 0.086), 0.0, 0.58),
        "grid": ((0.16, 0.18, 0.19), 0.0, 0.44),
        "hairs": ((0.62, 0.65, 0.64), 0.15, 0.32),
        "chrome": ((0.72, 0.74, 0.76), 1.0, 0.10),
    },
    "mineral-wound": {
        "ground": ((0.035, 0.026, 0.024), 0.0, 0.62),
        "grid": ((0.23, 0.075, 0.052), 0.05, 0.48),
        "hairs": ((0.88, 0.38, 0.18), 0.12, 0.30),
        "chrome": ((0.82, 0.55, 0.27), 1.0, 0.14),
    },
    "bioluminal-depth": {
        "ground": ((0.012, 0.018, 0.032), 0.0, 0.55),
        "grid": ((0.025, 0.11, 0.15), 0.08, 0.40),
        "hairs": ((0.06, 0.78, 0.66), 0.18, 0.24),
        "chrome": ((0.22, 0.48, 0.92), 1.0, 0.11),
    },
    "orchid-signal": {
        "ground": ((0.045, 0.025, 0.060), 0.0, 0.60),
        "grid": ((0.19, 0.075, 0.25), 0.04, 0.45),
        "hairs": ((0.92, 0.26, 0.68), 0.12, 0.27),
        "chrome": ((0.42, 0.82, 0.95), 1.0, 0.12),
    },
}
CAMERAS = {
    "tight-isometric": {"tx": 7.8, "ty": 11.5, "tz": 15.8, "rx": -34.0, "ry": 25.5, "focal_length": 64.0},
    "low-grazing": {"tx": 7.8, "ty": 3.8, "tz": 15.8, "rx": -15.0, "ry": 25.5, "focal_length": 64.0},
    "intimate-tracking": {"tx": 5.3, "ty": 4.6, "tz": 10.8, "rx": -21.5, "ry": 25.5, "focal_length": 68.0},
}


def set_parm(node: hou.Node, name: str, value: object) -> None:
    parm = node.parm(name)
    if parm is None:
        raise RuntimeError(f"{node.path()} has no parameter named {name}")
    parm.set(value)


def load_frame(cache_dir: Path, frame: int) -> hou.Geometry:
    geometry = hou.Geometry()
    geometry.loadFromFile(str(cache_dir / f"vex-state.{frame:04d}.bgeo.sc"))
    return geometry


def add_curve(geometry: hou.Geometry, positions: list[tuple[float, float, float]]) -> None:
    if len(positions) < 2:
        return
    primitive = geometry.createPolygon()
    primitive.setIsClosed(False)
    for position in positions:
        point = geometry.createPoint()
        point.setPosition(position)
        primitive.addVertex(point)


def derive_frame(cache_dir: Path, frame: int, metrics: dict, output: Path) -> dict[str, int]:
    count = int(metrics["agent_count"])
    gx, gy = (int(value) for value in metrics["grid"])
    width, depth = 9.0, 13.5
    cell_x, cell_z = width / gx, depth / gy
    source = load_frame(cache_dir, frame)
    agents, cells = source.points()[:count], source.points()[count:]
    history = [
        load_frame(cache_dir, history_frame).points()[count:]
        for history_frame in range(max(1, frame - HAIR_HISTORY_FRAMES + 1), frame + 1)
    ]

    field = hou.Geometry()
    field.addAttrib(hou.attribType.Point, "scale", (1.0, 1.0, 1.0))
    field.addAttrib(hou.attribType.Point, "memory", 0.0)
    field.addAttrib(hou.attribType.Point, "Cd", (0.0, 0.0, 0.0))
    field.addAttrib(hou.attribType.Point, "state_index", 0.0)
    field.addAttrib(hou.attribType.Point, "state_strength", 0.0)
    field.addAttrib(hou.attribType.Point, "id", 0)
    maximum_memory = 0.0
    maximum_idle = 0
    maximum_state = 0
    maximum_display_color = 0.0
    for cell_index, cell in enumerate(cells):
        x, z = float(cell.position()[0]), float(cell.position()[1])
        memory = float(cell.attribValue("scar_value"))
        normalized = max(0.0, min(1.0, memory / 1.25))
        eased = normalized * normalized * (3.0 - 2.0 * normalized)
        idle = int(cell.attribValue("scar_idle"))
        state = int(cell.attribValue("scar_state"))
        recency = 1.0 - max(0.0, min(1.0, idle / 96.0))
        low = (0.030, 0.095, 0.125)
        reinforced = (0.035, 0.34, 0.95)
        saturated = (0.10, 0.95, 0.82)
        target = low if state == 0 else reinforced if state == 1 else saturated
        state_mix = eased if state == 0 else 0.68 + 0.32 * eased
        active = tuple(low[channel] + (target[channel] - low[channel]) * state_mix for channel in range(3))
        idle_factor = 0.72 + 0.28 * recency if state == 0 else 0.88 + 0.12 * recency
        color = tuple(value * idle_factor for value in active)
        height = 0.055 + 0.72 * eased
        point = field.createPoint()
        point.setPosition((x, height * 0.5, z))
        point.setAttribValue("scale", (cell_x * 0.88, height, cell_z * 0.88))
        point.setAttribValue("memory", memory)
        point.setAttribValue("Cd", color)
        point.setAttribValue("state_index", state * 0.5)
        point.setAttribValue("state_strength", idle_factor)
        point.setAttribValue("id", cell_index)
        maximum_memory = max(maximum_memory, memory)
        maximum_idle = max(maximum_idle, idle)
        maximum_state = max(maximum_state, state)
        maximum_display_color = max(maximum_display_color, *color)
    field.saveToFile(str(output / f"field.{frame:04d}.bgeo.sc"))

    hairs = hou.Geometry()
    hair_count = 0
    maximum_hair_tip_height = 0.0
    for cell_index, cell in enumerate(cells):
        smoothed_memory = 0.0
        smoothed_direction = [0.0, 0.0]
        initialized = False
        for history_cells in history:
            sample = history_cells[cell_index]
            sample_memory = float(sample.attribValue("scar_value"))
            sample_direction = tuple(float(value) for value in sample.attribValue("scar_direction"))
            if not initialized:
                smoothed_memory = sample_memory
                smoothed_direction = [sample_direction[0], sample_direction[1]]
                initialized = True
            else:
                smoothed_memory += (sample_memory - smoothed_memory) * HAIR_HISTORY_ALPHA
                smoothed_direction[0] += (sample_direction[0] - smoothed_direction[0]) * HAIR_HISTORY_ALPHA
                smoothed_direction[1] += (sample_direction[1] - smoothed_direction[1]) * HAIR_HISTORY_ALPHA
        memory = smoothed_memory
        direction = tuple(smoothed_direction)
        direction_length = math.hypot(direction[0], direction[1])
        if memory < 0.12 or direction_length < 1e-6:
            continue
        x, z = float(cell.position()[0]), float(cell.position()[1])
        normalized = max(0.0, min(1.0, memory / 1.25))
        eased = normalized * normalized * (3.0 - 2.0 * normalized)
        height = 0.055 + 0.72 * eased
        lean = min(HAIR_MAXIMUM_LEAN, 0.12 + memory * 0.20)
        dx, dz = direction[0] / direction_length * lean, direction[1] / direction_length * lean
        hair_height = 0.48 + min(0.34, memory * 0.20)
        tip_height = min(0.90, height + hair_height)
        maximum_hair_tip_height = max(maximum_hair_tip_height, tip_height)
        curve_points = []
        for step in range(5):
            t = step / 4.0
            lateral = t ** HAIR_BEND_EXPONENT
            curve_points.append((x + dx * lateral, height + (tip_height - height) * t, z + dz * lateral))
        add_curve(hairs, curve_points)
        hair_count += 1
    hairs.saveToFile(str(output / f"hairs.{frame:04d}.bgeo.sc"))

    heads = hou.Geometry()
    heads.addAttrib(hou.attribType.Point, "pscale", AGENT_SCALE)
    for agent in agents:
        point = heads.createPoint()
        point.setPosition((float(agent.position()[0]), AGENT_LAYER_HEIGHT, float(agent.position()[1])))
    heads.saveToFile(str(output / f"agents.{frame:04d}.bgeo.sc"))

    trails = hou.Geometry()
    history_frames = list(range(max(1, frame - 20), frame + 1, 2))
    history = [load_frame(cache_dir, value).points()[:count] for value in history_frames]
    starts = hou.Geometry()
    starts.addAttrib(hou.attribType.Point, "pscale", AGENT_SCALE)
    for agent_index in range(count):
        position = history[0][agent_index].position()
        point = starts.createPoint()
        point.setPosition((float(position[0]), AGENT_LAYER_HEIGHT, float(position[1])))
    starts.saveToFile(str(output / f"trail-starts.{frame:04d}.bgeo.sc"))
    trail_count = 0
    for agent_index in range(count):
        run: list[tuple[float, float, float]] = []
        for points in history:
            position = points[agent_index].position()
            current = (float(position[0]), AGENT_LAYER_HEIGHT, float(position[1]))
            if run and (abs(current[0] - run[-1][0]) > width * 0.5 or abs(current[2] - run[-1][2]) > depth * 0.5):
                add_curve(trails, run)
                trail_count += int(len(run) >= 2)
                run = []
            run.append(current)
        add_curve(trails, run)
        trail_count += int(len(run) >= 2)
    trails.saveToFile(str(output / f"trails.{frame:04d}.bgeo.sc"))
    return {"hairs": hair_count, "trails": trail_count, "starts": count, "maximum_hair_tip_height": maximum_hair_tip_height, "scar_value_max": maximum_memory, "scar_idle_max": maximum_idle, "scar_state_max": maximum_state, "display_color_max": maximum_display_color}


def material(parent: hou.Node, name: str, color: tuple[float, float, float], metalness: float, roughness: float) -> hou.Node:
    shader = parent.createNode("mtlxstandard_surface", f"{name}_shader")
    surface = parent.createNode("mtlxsurfacematerial", name)
    surface.setInput(0, shader)
    set_parm(shader, "base", 1.0)
    set_parm(shader, "metalness", metalness)
    set_parm(shader, "specular_roughness", roughness)
    for channel, value in zip("rgb", color):
        set_parm(shader, f"base_color{channel}", value)
    return surface


def color_attribute_material(parent: hou.Node, name: str, metalness: float, roughness: float) -> hou.Node:
    shader = parent.createNode("mtlxstandard_surface", f"{name}_shader")
    surface = parent.createNode("mtlxsurfacematerial", name)
    state_index = parent.createNode("mtlxgeompropvalue", "state_index")
    set_parm(state_index, "geomprop", "state_index"); set_parm(state_index, "signature", "float")
    state_mix = parent.createNode("mtlxgeompropvalue", "state_mix")
    set_parm(state_mix, "geomprop", "state_mix"); set_parm(state_mix, "signature", "float")
    colors = []
    for node_name, color in (
        ("EDIT_STATE_COLOR_0", (0.030, 0.095, 0.125)),
        ("EDIT_STATE_COLOR_0_5", (0.035, 0.34, 0.95)),
        ("EDIT_STATE_COLOR_1", (0.10, 0.95, 0.82)),
    ):
        node = parent.createNode("mtlxconstant", node_name)
        set_parm(node, "signature", "color3")
        for channel, value in zip("rgb", color):
            set_parm(node, f"value_color3{channel}", value)
        colors.append(node)
    reinforced = parent.createNode("mtlxifgreater", "state_0_or_0_5")
    set_parm(reinforced, "signature", "color3"); set_parm(reinforced, "value2", 0.25)
    reinforced.setNamedInput("value1", state_index, "out")
    reinforced.setNamedInput("in1", colors[1], "out"); reinforced.setNamedInput("in2", colors[0], "out")
    palette = parent.createNode("mtlxifgreater", "state_0_05_or_1")
    set_parm(palette, "signature", "color3"); set_parm(palette, "value2", 0.75)
    palette.setNamedInput("value1", state_index, "out")
    palette.setNamedInput("in1", colors[2], "out"); palette.setNamedInput("in2", reinforced, "out")
    floor = parent.createNode("mtlxconstant", "EDIT_CUBE_BASE_COLOR")
    set_parm(floor, "signature", "color3")
    for channel, value in zip("rgb", (0.012, 0.018, 0.032)):
        set_parm(floor, f"value_color3{channel}", value)
    mix = parent.createNode("mtlxmix", "state_palette_with_floor_base")
    set_parm(mix, "signature", "color3")
    mix.setNamedInput("fg", palette, "out")
    mix.setNamedInput("bg", floor, "out")
    mix.setNamedInput("mix", state_mix, "out")
    shader.setNamedInput("base_color", mix, "out")
    surface.setInput(0, shader)
    set_parm(shader, "base", 1.0)
    set_parm(shader, "metalness", metalness)
    set_parm(shader, "specular_roughness", roughness)
    return surface


def build_hip(output: Path, image_pattern: Path, render: bool, frames: list[int], render_width: int, samples: int, palette_name: str, camera_name: str) -> Path:
    hou.hipFile.clear(suppress_save_prompt=True)
    obj = hou.node("/obj")
    geo = obj.createNode("geo", "scar_tissue_grid_look")
    for child in geo.children(): child.destroy()

    field_file = geo.createNode("file", "field_instances")
    set_parm(field_file, "file", str(output / "field.$F4.bgeo.sc"))
    cube = geo.createNode("box", "unit_memory_cube")
    set_parm(cube, "type", "poly")
    cubes = geo.createNode("copytopoints::2.0", "memory_cubes")
    cubes.setInput(0, cube); cubes.setInput(1, field_file)
    set_parm(cubes, "targetattribs", "1")
    set_parm(cubes, "applyattribs1", "Cd memory state_index state_strength")
    bevel = geo.createNode("polybevel::3.0", "fixed_world_highlight_bevel")
    bevel.setInput(0, cubes)
    set_parm(bevel, "offset", CUBE_BEVEL_WIDTH)
    set_parm(bevel, "divisions", CUBE_BEVEL_DIVISIONS)
    cube_gradient = geo.createNode("attribwrangle", "floor_to_state_tip_color")
    cube_gradient.setInput(0, bevel)
    set_parm(cube_gradient, "class", "point")
    set_parm(cube_gradient, "snippet", f'''float normalized = clamp(f@memory / 1.25, 0.0, 1.0);
float eased = normalized * normalized * (3.0 - 2.0 * normalized);
float height = 0.055 + 0.72 * eased;
float vertical = pow(clamp(@P.y / max(height, 1e-6), 0.0, 1.0), {CUBE_VERTICAL_COLOR_EXPONENT});
vector floor_color = set(0.012, 0.018, 0.032);
f@state_mix = vertical * f@state_strength;
@Cd = lerp(floor_color, @Cd, vertical);''')
    cube_out = geo.createNode("null", "OUT_MEMORY_CUBES"); cube_out.setInput(0, cube_gradient)

    hair_file = geo.createNode("file", "direction_hairs")
    set_parm(hair_file, "file", str(output / "hairs.$F4.bgeo.sc"))
    hair_taper = geo.createNode("attribwrangle", "hair_root_to_point_taper")
    hair_taper.setInput(0, hair_file)
    set_parm(hair_taper, "class", "point")
    set_parm(hair_taper, "snippet", f'''int vertex = pointvertex(0, @ptnum);
int primitive = vertexprim(0, vertex);
int index = vertexprimindex(0, vertex);
int count = primvertexcount(0, primitive);
float u = count > 1 ? float(index) / float(count - 1) : 0.0;
f@pscale = lerp({HAIR_ROOT_SCALE}, {HAIR_TIP_SCALE}, u);''')
    hair_wire = geo.createNode("polywire", "hair_radius")
    hair_wire.setInput(0, hair_taper); set_parm(hair_wire, "radius", 0.005); set_parm(hair_wire, "div", 5); set_parm(hair_wire, "usescaleattrib", "attrib"); set_parm(hair_wire, "scaleattrib", "pscale")
    hair_out = geo.createNode("null", "OUT_DIRECTION_HAIRS"); hair_out.setInput(0, hair_wire)

    agent_file = geo.createNode("file", "agent_points"); set_parm(agent_file, "file", str(output / "agents.$F4.bgeo.sc"))
    sphere = geo.createNode("sphere", "chrome_agent"); set_parm(sphere, "type", "poly"); set_parm(sphere, "rows", 8); set_parm(sphere, "cols", 12)
    agent_copy = geo.createNode("copytopoints::2.0", "chrome_agents"); agent_copy.setInput(0, sphere); agent_copy.setInput(1, agent_file)
    agent_out = geo.createNode("null", "OUT_CHROME_AGENTS"); agent_out.setInput(0, agent_copy)

    start_file = geo.createNode("file", "trail_start_points"); set_parm(start_file, "file", str(output / "trail-starts.$F4.bgeo.sc"))
    start_sphere = geo.createNode("sphere", "trail_start_sphere"); set_parm(start_sphere, "type", "poly"); set_parm(start_sphere, "rows", 8); set_parm(start_sphere, "cols", 12)
    start_copy = geo.createNode("copytopoints::2.0", "trail_start_agents"); start_copy.setInput(0, start_sphere); start_copy.setInput(1, start_file)
    start_out = geo.createNode("null", "OUT_TRAIL_STARTS"); start_out.setInput(0, start_copy)

    trail_file = geo.createNode("file", "agent_trails"); set_parm(trail_file, "file", str(output / "trails.$F4.bgeo.sc"))
    trail_wire = geo.createNode("polywire", "trail_radius"); trail_wire.setInput(0, trail_file); set_parm(trail_wire, "radius", TRAIL_RADIUS); set_parm(trail_wire, "div", 6)
    trail_out = geo.createNode("null", "OUT_AGENT_TRAILS"); trail_out.setInput(0, trail_wire)
    geo.layoutChildren()

    ground_geo = obj.createNode("geo", "overscan_ground")
    for child in ground_geo.children(): child.destroy()
    ground = ground_geo.createNode("box", "ground_slab"); set_parm(ground, "sizex", 15.0); set_parm(ground, "sizey", 0.08); set_parm(ground, "sizez", 20.0); set_parm(ground, "ty", -0.09)
    ground_out = ground_geo.createNode("null", "OUT_OVERSCAN_GROUND"); ground_out.setInput(0, ground)

    stage = hou.node("/stage"); previous = None
    outputs = (("ground", ground_out), ("grid", cube_out), ("hairs", hair_out), ("starts", start_out), ("agents", agent_out), ("trails", trail_out))
    for name, node in outputs:
        imp = stage.createNode("sopimport", f"import_{name}")
        if previous: imp.setInput(0, previous)
        set_parm(imp, "soppath", node.path()); set_parm(imp, "primpath", f"/world/{name}"); set_parm(imp, "pathprefix", f"/world/{name}")
        if name == "grid":
            set_parm(imp, "enable_attribs", True)
            set_parm(imp, "attribs", "* ^__* ^usd*")
        previous = imp
    library = stage.createNode("materiallibrary", "neutral_look_materials"); library.setInput(0, previous)
    palette = PALETTES[palette_name]
    materials = {}
    for name, values in palette.items():
        if name == "grid" and palette_name == "bioluminal-depth":
            materials[name] = color_attribute_material(library, name, values[1], values[2])
        else:
            materials[name] = material(library, name, *values)
    assign = stage.createNode("assignmaterial", "assign_neutral_materials"); assign.setInput(0, library); set_parm(assign, "nummaterials", len(materials))
    material_targets = {
        "ground": "/world/ground /world/ground/**",
        "grid": "/world/grid /world/grid/**",
        "hairs": "/world/hairs /world/hairs/**",
        "chrome": "/world/starts /world/starts/** /world/agents /world/agents/** /world/trails /world/trails/**",
    }
    for index, (name, mat) in enumerate(materials.items(), 1):
        set_parm(assign, f"primpattern{index}", material_targets[name])
        set_parm(assign, f"matspecpath{index}", mat.path().replace(library.path(), "/materials"))
    camera = stage.createNode("camera", "technical_camera"); camera.setInput(0, assign); set_parm(camera, "primpath", "/cameras/technical")
    camera_values = CAMERAS[camera_name]
    for name in ("tx", "ty", "tz", "rx", "ry"):
        set_parm(camera, name, camera_values[name])
    set_parm(camera, "focalLength", camera_values["focal_length"])
    dome = stage.createNode("domelight::2.0", "dome_fill"); dome.setInput(0, camera); set_parm(dome, "primpath", "/lights/dome_fill"); set_parm(dome, "xn__inputsintensity_i0a", 0.42)
    key = stage.createNode("light", "grazing_area_key"); key.setInput(0, dome); set_parm(key, "primpath", "/lights/grazing_area_key"); set_parm(key, "lighttype", "UsdLuxRectLight"); set_parm(key, "tx", -6.0); set_parm(key, "ty", 8.0); set_parm(key, "tz", 4.0); set_parm(key, "rx", -52.0); set_parm(key, "ry", -28.0); set_parm(key, "rz", -18.0); set_parm(key, "xn__inputswidth_zta", 7.0); set_parm(key, "xn__inputsheight_mva", 5.0); set_parm(key, "xn__inputsintensity_i0a", 3.2); set_parm(key, "xn__inputsexposure_vya", 1.0); set_parm(key, "xn__inputsnormalize_i0a", True)
    rim = stage.createNode("light", "cool_rim"); rim.setInput(0, key); set_parm(rim, "primpath", "/lights/cool_rim"); set_parm(rim, "lighttype", "UsdLuxRectLight"); set_parm(rim, "tx", 7.0); set_parm(rim, "ty", 6.0); set_parm(rim, "tz", -5.0); set_parm(rim, "rx", -38.0); set_parm(rim, "ry", 142.0); set_parm(rim, "rz", 12.0); set_parm(rim, "xn__inputswidth_zta", 5.0); set_parm(rim, "xn__inputsheight_mva", 3.0); set_parm(rim, "xn__inputsintensity_i0a", 1.6); set_parm(rim, "xn__inputsexposure_vya", 0.5); set_parm(rim, "xn__inputsnormalize_i0a", True); set_parm(rim, "xn__inputscolor_ztar", 0.46); set_parm(rim, "xn__inputscolor_ztag", 0.68); set_parm(rim, "xn__inputscolor_ztab", 1.0)
    settings = stage.createNode("karmarendersettings", "grid_look_settings"); settings.setInput(0, rim); set_parm(settings, "camera", "/cameras/technical"); set_parm(settings, "picture", image_pattern.as_posix()); set_parm(settings, "res_mode", "autoheight"); set_parm(settings, "resolutionx", render_width); set_parm(settings, "samplesperpixel", samples)
    rop = stage.createNode("usdrender_rop", "grid_look_render"); rop.setInput(0, settings); set_parm(rop, "renderer", "Karma XPU"); set_parm(rop, "soho_foreground", True); set_parm(rop, "mkpath", True)
    stage.layoutChildren()
    hip = output / "scar-tissue-grid-look.hiplc"; hou.hipFile.save(str(hip))
    if render:
        for frame in frames:
            hou.setFrame(frame); set_parm(settings, "picture", str(output / "frames" / f"frame-{frame:04d}.png")); rop.render(frame_range=(frame, frame, 1))
    return hip


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cache_dir", type=Path); parser.add_argument("metrics", type=Path); parser.add_argument("output", type=Path)
    parser.add_argument("--frames", default="1,30,60,90,120,150,180,210,240,270,300")
    parser.add_argument("--width", type=int, default=360)
    parser.add_argument("--samples", type=int, default=4)
    parser.add_argument("--palette", choices=tuple(PALETTES), default="neutral")
    parser.add_argument("--camera", choices=tuple(CAMERAS), default="tight-isometric")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args(); frames = [int(value) for value in args.frames.split(",")]
    args.output.mkdir(parents=True, exist_ok=True); (args.output / "frames").mkdir(exist_ok=True)
    metrics = json.loads(args.metrics.read_text(encoding="utf-8")); hair_counts = {}; trail_counts = {}; start_counts = {}; maximum_hair_tip_height = {}; cube_color_ranges = {}
    for frame in frames:
        counts = derive_frame(args.cache_dir.resolve(), frame, metrics, args.output.resolve()); hair_counts[str(frame)] = counts["hairs"]; trail_counts[str(frame)] = counts["trails"]; start_counts[str(frame)] = counts["starts"]; maximum_hair_tip_height[str(frame)] = counts["maximum_hair_tip_height"]; cube_color_ranges[str(frame)] = {"scar_value_max": counts["scar_value_max"], "scar_idle_max": counts["scar_idle_max"], "scar_state_max": counts["scar_state_max"], "display_color_max": counts["display_color_max"]}
    hip = build_hip(args.output.resolve(), args.output.resolve() / "frames" / "frame-$F4.png", not args.build_only, frames, args.width, args.samples, args.palette, args.camera)
    receipt = {"schema_version": 1, "look": "memory-grid-hairs-chrome-agents", "camera_preset": args.camera, "camera_parameters": CAMERAS[args.camera], "palette": args.palette, "palette_roles": PALETTES[args.palette], "cube_color_mapping": "scar-value-plus-idle-and-state", "cube_color_attributes": ["scar_value", "scar_idle", "scar_state"], "cube_state_color_roles": {"0": "blue-slate", "1": "electric-blue", "2": "teal"}, "cube_vertical_color_profile": "floor-to-state-tip-power", "cube_vertical_color_exponent": CUBE_VERTICAL_COLOR_EXPONENT, "cube_color_ranges": cube_color_ranges, "frames": frames, "render_width": args.width, "samples_per_pixel": args.samples, "field_instances_per_frame": int(metrics["field_point_count"]), "hair_curves_per_frame": hair_counts, "maximum_hair_tip_height": maximum_hair_tip_height, "hair_temporal_easing": "exponential-history", "hair_history_frames": HAIR_HISTORY_FRAMES, "hair_history_alpha": HAIR_HISTORY_ALPHA, "hair_bend_profile": "power-toward-tip", "hair_bend_exponent": HAIR_BEND_EXPONENT, "hair_maximum_lean": HAIR_MAXIMUM_LEAN, "hair_radius_profile": "linear-root-to-point", "hair_root_scale": HAIR_ROOT_SCALE, "hair_tip_scale": HAIR_TIP_SCALE, "agent_instances_per_frame": int(metrics["agent_count"]), "agent_scale": AGENT_SCALE, "agent_layer_height": AGENT_LAYER_HEIGHT, "trail_layer_height": AGENT_LAYER_HEIGHT, "trail_start_instances_per_frame": start_counts, "trail_endpoint_scale": AGENT_SCALE, "trail_curves_per_frame": trail_counts, "trail_radius": TRAIL_RADIUS, "trail_material": "chrome", "agent_system_material": "shared-chrome", "cube_height_mapping": "smoothstep", "cube_bevel_width": CUBE_BEVEL_WIDTH, "cube_bevel_divisions": CUBE_BEVEL_DIVISIONS, "cube_bevel_space": "fixed-world-after-instance-scale", "overscan_ground": True, "hip": {"path": hip.name, "bytes": hip.stat().st_size, "sha256": sha(hip)}}
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output.resolve())


if __name__ == "__main__": main()
