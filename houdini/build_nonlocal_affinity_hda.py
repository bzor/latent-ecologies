"""Build and verify an artist-editable Non-Local Affinity SOP HDA."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from array import array
from pathlib import Path
from typing import Any

import hou

from houdini_ai.nonlocal_affinity import relationship_digest
from houdini_ai.overlay_parameter_manifest import validate_overlay_parameter_manifest

TYPE_NAME = "bzor::nonlocal_affinity_parallel::1.3"
ASSET_FILE = "nonlocal-affinity-parallel.hda"
DEMO_FILE = "nonlocal-affinity-parallel-demo.hiplc"
ARTIST_PARAMETERS = (
    "contraction", "attraction", "repulsion", "softening",
    "seed", "new_seed", "num_points", "total_points",
    "rewire_probability", "rewires_per_event", "event_schedule_steps",
    "steps_per_frame", "apply_rewires", "depth_scale",
    "start_frame", "point_size", "reset_simulation",
    "overlay_variation_number", "overlay_variation_title",
    "overlay_manifest_path", "export_overlay_manifest",
)


def native(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def geometry_digest(geometry: hou.Geometry) -> str:
    digest = hashlib.sha256()
    digest.update(array("q", (round(value * 10_000_000) for value in geometry.pointFloatAttribValues("P"))).tobytes())
    digest.update(array("i", geometry.pointIntAttribValues("friend")).tobytes())
    digest.update(array("i", geometry.pointIntAttribValues("enemy")).tobytes())
    return digest.hexdigest()


def add_float_parm(node: hou.Node, name: str, value: float) -> None:
    group = node.parmTemplateGroup()
    group.append(hou.FloatParmTemplate(name, name.replace("_", " ").title(), 1, default_value=(value,)))
    node.setParmTemplateGroup(group)


def add_toggle_parm(node: hou.Node, name: str, value: bool) -> None:
    group = node.parmTemplateGroup()
    group.append(hou.ToggleParmTemplate(name, name.replace("_", " ").title(), default_value=value))
    node.setParmTemplateGroup(group)


def overlay_parm(
    template: hou.ParmTemplate,
    key: str,
    units: str,
    comparison_range: tuple[float, float] | None = None,
) -> hou.ParmTemplate:
    """Tag a curated artist control for overlay-manifest export."""
    tags = dict(template.tags())
    tags.update({"bzor_overlay_key": key, "bzor_overlay_units": units})
    if comparison_range is not None:
        tags["bzor_overlay_min"] = str(comparison_range[0])
        tags["bzor_overlay_max"] = str(comparison_range[1])
    template.setTags(tags)
    return template


def hda_python_module_source() -> str:
    """Return the self-contained one-click manifest exporter embedded in the HDA."""
    return r'''
import hashlib
import json
import re
from pathlib import Path

import hou


def _slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "untitled"


def _value(parm):
    type_name = str(parm.parmTemplate().type()).lower()
    if "toggle" in type_name:
        return bool(parm.eval())
    if "int" in type_name:
        return int(parm.eval())
    if "float" in type_name:
        return float(parm.eval())
    return parm.evalAsString()


def _value_type(parm):
    type_name = str(parm.parmTemplate().type()).lower()
    if "toggle" in type_name:
        return "toggle"
    if "int" in type_name:
        return "integer"
    if "float" in type_name:
        return "float"
    return "string"


def export_overlay_manifest(node):
    number = int(node.evalParm("overlay_variation_number"))
    # The Study assigns the behavior axis; an asset built before it existed has no
    # such parm and reports the first behavior.
    behavior_parm = node.parm("overlay_behavior_number")
    behavior_number = int(behavior_parm.eval()) if behavior_parm is not None else 1
    title = node.evalParm("overlay_variation_title").strip()
    if number < 1 or number > 999:
        raise hou.NodeError("Overlay variation number must be between 1 and 999")
    if not title:
        raise hou.NodeError("Overlay variation title is required")

    parameters = []
    for parm in node.parms():
        tags = parm.parmTemplate().tags()
        key = tags.get("bzor_overlay_key")
        if not key:
            continue
        record = {
            "key": key,
            "label": parm.parmTemplate().label(),
            "parameter": parm.name(),
            "type": _value_type(parm),
            "value": _value(parm),
            "units": tags.get("bzor_overlay_units", "scalar"),
            "animated": bool(parm.isTimeDependent()),
        }
        if "bzor_overlay_min" in tags and "bzor_overlay_max" in tags:
            record["comparison_range"] = [float(tags["bzor_overlay_min"]), float(tags["bzor_overlay_max"])]
        parameters.append(record)

    hip_path = hou.hipFile.path()
    dirty = bool(hou.hipFile.hasUnsavedChanges())
    hip_sha256 = None
    hip_file = Path(hip_path)
    if hip_file.is_file() and not dirty:
        hip_sha256 = "sha256:" + hashlib.sha256(hip_file.read_bytes()).hexdigest()
    manifest = {
        "schema_version": 1,
        "variation": {
            "behavior_number": behavior_number,
            "number": number,
            "title": title,
            "file_stem": "bhvr_{:03d}_var_{:03d}_{}".format(behavior_number, number, _slug(title)),
        },
        "source": {
            "hip_path": hip_path,
            "hip_sha256": hip_sha256,
            "hip_dirty": dirty,
            "node_path": node.path(),
            "asset_type": node.type().name(),
            "frame": float(hou.frame()),
        },
        "parameters": parameters,
    }
    output = Path(node.parm("overlay_manifest_path").evalAsString())
    if output.suffix.lower() != ".json":
        raise hou.NodeError("Overlay manifest path must end in .json")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    node.setUserData("bzor_overlay_manifest", str(output))
    return manifest
'''.strip() + "\n"


def build_initial_geometry(prepared: dict[str, Any], path: Path, cohort_size: int) -> None:
    positions = prepared["initial_positions"]
    count = len(positions)
    if cohort_size < 1 or count % cohort_size:
        raise ValueError("cohort size must divide the prepared population")
    geometry = hou.Geometry()
    vectors = [hou.Vector3(value[0], value[1], value[2] if len(value) > 2 else 0.0) for value in positions]
    geometry.createPoints(vectors)
    geometry.addAttrib(hou.attribType.Point, "friend", 0)
    geometry.addAttrib(hou.attribType.Point, "enemy", 0)
    geometry.addAttrib(hou.attribType.Point, "anchorP", hou.Vector3())
    geometry.addAttrib(hou.attribType.Point, "cohort_offset", hou.Vector3())
    geometry.setPointIntAttribValues("friend", array("i", prepared["friends"]))
    geometry.setPointIntAttribValues("enemy", array("i", prepared["enemies"]))
    anchors: list[float] = []
    offsets: list[float] = []
    for index, position in enumerate(vectors):
        anchor = vectors[(index // cohort_size) * cohort_size]
        anchors.extend(anchor)
        offsets.extend(position - anchor)
    geometry.setPointFloatAttribValues("anchorP", anchors)
    geometry.setPointFloatAttribValues("cohort_offset", offsets)
    events = prepared["rewire_events"]
    for name, values in (
        ("event_steps", [int(event["step"]) for event in events]),
        ("event_points", [int(event["point"]) for event in events]),
        ("event_friends", [int(event["friend"]) for event in events]),
        ("event_enemies", [int(event["enemy"]) for event in events]),
    ):
        geometry.addArrayAttrib(hou.attribType.Global, name, hou.attribData.Int)
        geometry.setGlobalAttribValue(name, tuple(values))
    geometry.addAttrib(hou.attribType.Global, "simstep", 0)
    geometry.setGlobalAttribValue("simstep", 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    geometry.saveToFile(native(path))


def artist_parameter_group(parameters: dict[str, float], defaults: dict[str, Any]) -> hou.ParmTemplateGroup:
    group = hou.ParmTemplateGroup()
    group.append(hou.LabelParmTemplate(
        "identity_notice",
        "Identity",
        column_labels=("Cohorts are disabled: every Canvas point is one simulation point. Changing seed, Canvas points, rewiring, or schedule horizon regenerates a deterministic receipt.",),
    ))
    canvas = hou.FolderParmTemplate("canvas", "Canvas Identity & Events", folder_type=hou.folderType.Simple)
    canvas.addParmTemplate(overlay_parm(
        hou.IntParmTemplate("seed", "Deterministic Seed", 1, default_value=(int(defaults["seed"]),), min=0, max=2147483647, min_is_strict=True, max_is_strict=True),
        "behavior.seed", "integer",
    ))
    canvas.addParmTemplate(hou.ButtonParmTemplate(
        "new_seed", "New Seed",
        script_callback="import random; node = kwargs['node']; node.parm('seed').set(random.SystemRandom().randrange(0, 2147483648)); solver = node.node('solver/d'); solver.parm('resimulate').pressButton() if solver is not None else None",
        script_callback_language=hou.scriptLanguage.Python,
    ))
    points = hou.IntParmTemplate("num_points", "Canvas Points", 1, default_value=(int(defaults["num_points"]),), min=2, max=500000, min_is_strict=True, max_is_strict=True)
    points.setHelp("Direct simulation-point count. Cohort duplication is disabled. Hard maximum: 500,000.")
    canvas.addParmTemplate(overlay_parm(points, "behavior.point_count", "points", (2, 500000)))
    canvas.addParmTemplate(overlay_parm(
        hou.FloatParmTemplate("rewire_probability", "Rewire Probability / Step", 1, default_value=(float(defaults["rewire_probability"]),), min=0.0, max=1.0, min_is_strict=True, max_is_strict=True),
        "behavior.rewire_probability", "probability", (0.0, 1.0),
    ))
    canvas.addParmTemplate(overlay_parm(
        hou.IntParmTemplate("rewires_per_event", "Rewires / Event", 1, default_value=(int(defaults["rewires_per_event"]),), min=1, max=64, min_is_strict=True, max_is_strict=True),
        "behavior.rewires_per_event", "count", (1, 64),
    ))
    schedule = hou.IntParmTemplate("event_schedule_steps", "Event Schedule Steps", 1, default_value=(int(defaults["event_schedule_steps"]),), min=1, max=5000, min_is_strict=True, max_is_strict=True)
    schedule.setHelp("Precomputes deterministic Canvas rewire events through this many simulation steps.")
    canvas.addParmTemplate(overlay_parm(schedule, "behavior.event_schedule_steps", "steps", (1, 5000)))
    group.append(canvas)

    spatial = hou.FolderParmTemplate("spatial", "Spatial Lift", folder_type=hou.folderType.Simple)
    total = hou.IntParmTemplate("total_points", "Total Output Points", 1, default_value=(int(defaults["num_points"]),))
    total.setDefaultExpression(('ch("num_points")',))
    total.setDefaultExpressionLanguage((hou.scriptLanguage.Hscript,))
    total.setConditional(hou.parmCondType.DisableWhen, "{ num_points >= 0 }")
    spatial.addParmTemplate(overlay_parm(total, "behavior.total_points", "points"))
    depth = hou.FloatParmTemplate("depth_scale", "Depth Scale", 1, default_value=(1.0,), min=0.0, max=4.0)
    depth.setHelp("Scales the shallow Z lift. Values other than 1 create a new spatial identity.")
    spatial.addParmTemplate(overlay_parm(depth, "behavior.depth_scale", "scale", (0.0, 4.0)))
    group.append(spatial)

    dynamics = hou.FolderParmTemplate("dynamics", "Dynamics", folder_type=hou.folderType.Simple)
    dynamics.addParmTemplate(overlay_parm(hou.FloatParmTemplate("contraction", "Contraction", 1, default_value=(parameters["contraction"],), min=0.95, max=1.01), "behavior.contraction", "coefficient", (0.95, 1.01)))
    dynamics.addParmTemplate(overlay_parm(hou.FloatParmTemplate("attraction", "Attraction", 1, default_value=(parameters["attraction"],), min=0.0, max=0.08), "behavior.attraction", "coefficient", (0.0, 0.08)))
    dynamics.addParmTemplate(overlay_parm(hou.FloatParmTemplate("repulsion", "Repulsion", 1, default_value=(parameters["repulsion"],), min=0.0, max=0.08), "behavior.repulsion", "coefficient", (0.0, 0.08)))
    dynamics.addParmTemplate(overlay_parm(hou.FloatParmTemplate("softening", "Softening", 1, default_value=(parameters["softening"],), min=0.0001, max=0.1, min_is_strict=True), "behavior.softening", "coefficient", (0.0001, 0.1)))
    rewires = hou.ToggleParmTemplate("apply_rewires", "Apply Ordered Rewires", default_value=True)
    rewires.setHelp("Disabling the prepared event schedule creates a new graph behavior.")
    dynamics.addParmTemplate(overlay_parm(rewires, "behavior.apply_rewires", "boolean"))
    group.append(dynamics)

    playback = hou.FolderParmTemplate("playback", "Playback", folder_type=hou.folderType.Simple)
    playback.addParmTemplate(overlay_parm(hou.IntParmTemplate("steps_per_frame", "Steps / Display Frame", 1, default_value=(1,), min=1, max=12, min_is_strict=True, max_is_strict=True), "playback.steps_per_frame", "steps", (1, 12)))
    playback.addParmTemplate(overlay_parm(hou.IntParmTemplate("start_frame", "Start Frame", 1, default_value=(1,), min=1, max=100000, min_is_strict=True), "playback.start_frame", "frame"))
    playback.addParmTemplate(overlay_parm(hou.FloatParmTemplate("point_size", "Point Size", 1, default_value=(0.006,), min=0.0001, max=0.05, min_is_strict=True), "look.point_size", "houdini-units", (0.0001, 0.05)))
    reset = hou.ButtonParmTemplate(
        "reset_simulation", "Reset Simulation",
        script_callback="node = kwargs['node']; solver = node.node('solver/d'); solver.parm('resimulate').pressButton() if solver is not None else None",
        script_callback_language=hou.scriptLanguage.Python,
    )
    playback.addParmTemplate(reset)
    group.append(playback)

    overlay = hou.FolderParmTemplate("overlay_detail", "Overlay Detail", folder_type=hou.folderType.Simple)
    overlay.addParmTemplate(hou.LabelParmTemplate(
        "overlay_notice",
        "Parameter Manifest",
        column_labels=("Exports curated Behavior and Look controls for the detail generator. Save the HIP first when a checksum-bound snapshot is required.",),
    ))
    overlay.addParmTemplate(hou.IntParmTemplate("overlay_variation_number", "Variation Number", 1, default_value=(1,), min=1, max=999, min_is_strict=True, max_is_strict=True))
    overlay.addParmTemplate(hou.StringParmTemplate("overlay_variation_title", "Variation Title", 1, default_value=("Primary Treatment",)))
    overlay.addParmTemplate(hou.StringParmTemplate(
        "overlay_manifest_path", "Manifest Path", 1,
        default_value=("$HIP/$HIPNAME.overlay-parameters.json",),
        string_type=hou.stringParmType.FileReference,
        file_type=hou.fileType.Any,
    ))
    overlay.addParmTemplate(hou.ButtonParmTemplate(
        "export_overlay_manifest", "Export Overlay Parameter Manifest",
        script_callback="kwargs['node'].hdaModule().export_overlay_manifest(kwargs['node'])",
        script_callback_language=hou.scriptLanguage.Python,
    ))
    group.append(overlay)
    return group


def procedural_generator_code(defaults: dict[str, Any]) -> str:
    template = r'''
from array import array
import hou

node = hou.pwd()
asset = node.parent()
geo = node.geometry()
source = node.inputs()[0].geometry()
seed = int(asset.evalParm("seed")) & 0xFFFFFFFF
num_points = int(asset.evalParm("num_points"))
rewire_probability = float(asset.evalParm("rewire_probability"))
rewires_per_event = int(asset.evalParm("rewires_per_event"))
event_schedule_steps = int(asset.evalParm("event_schedule_steps"))
if num_points < 2 or num_points > 500000:
    raise hou.NodeError("Canvas Points must be between 2 and 500,000")
canonical = (
    seed == __SEED__
    and num_points == __NUM_POINTS__
    and abs(rewire_probability - __REWIRE_PROBABILITY__) <= 1e-12
    and rewires_per_event == __REWIRES_PER_EVENT__
    and event_schedule_steps == __EVENT_SCHEDULE_STEPS__
)
geo.clear()
if canonical:
    geo.merge(source)
    geo.addAttrib(hou.attribType.Global, "identity_source", "promoted-embedded-receipt")
    geo.setGlobalAttribValue("identity_source", "promoted-embedded-receipt")
else:
    class Mulberry32:
        def __init__(self, value):
            self.state = value & 0xFFFFFFFF
        @staticmethod
        def imul(left, right):
            return ((left & 0xFFFFFFFF) * (right & 0xFFFFFFFF)) & 0xFFFFFFFF
        def random(self):
            self.state = (self.state + 0x6D2B79F5) & 0xFFFFFFFF
            value = self.state
            value = self.imul(value ^ (value >> 15), value | 1)
            value ^= (value + self.imul(value ^ (value >> 7), value | 61)) & 0xFFFFFFFF
            value &= 0xFFFFFFFF
            return ((value ^ (value >> 14)) & 0xFFFFFFFF) / 4294967296.0

    canvas_rng = Mulberry32(seed)
    flat = [canvas_rng.random() * 2.0 - 1.0 for _ in range(num_points * 2)]
    planar = [flat[index:index + 2] for index in range(0, len(flat), 2)]
    anchor_friends = [int(canvas_rng.random() * num_points) for _ in range(num_points)]
    anchor_enemies = [int(canvas_rng.random() * num_points) for _ in range(num_points)]
    anchor_events = []
    for step in range(1, event_schedule_steps + 1):
        if canvas_rng.random() < rewire_probability:
            for _ in range(rewires_per_event):
                anchor_events.append({
                    "step": step,
                    "point": int(canvas_rng.random() * num_points),
                    "friend": int(canvas_rng.random() * num_points),
                    "enemy": int(canvas_rng.random() * num_points),
                })

    depth_rng = Mulberry32(seed ^ 0x9E3779B9)
    anchors = [hou.Vector3(position[0], position[1], (depth_rng.random() * 2.0 - 1.0) * 0.15) for position in planar]
    geo.createPoints(anchors)
    geo.addAttrib(hou.attribType.Point, "friend", 0)
    geo.addAttrib(hou.attribType.Point, "enemy", 0)
    geo.addAttrib(hou.attribType.Point, "anchorP", hou.Vector3())
    geo.setPointIntAttribValues("friend", array("i", anchor_friends))
    geo.setPointIntAttribValues("enemy", array("i", anchor_enemies))
    geo.setPointFloatAttribValues("anchorP", [component for anchor in anchors for component in anchor])
    for name, values in (
        ("event_steps", [event["step"] for event in anchor_events]),
        ("event_points", [event["point"] for event in anchor_events]),
        ("event_friends", [event["friend"] for event in anchor_events]),
        ("event_enemies", [event["enemy"] for event in anchor_events]),
    ):
        geo.addArrayAttrib(hou.attribType.Global, name, hou.attribData.Int)
        geo.setGlobalAttribValue(name, tuple(values))
    geo.addAttrib(hou.attribType.Global, "simstep", 0)
    geo.setGlobalAttribValue("simstep", 0)
    geo.addAttrib(hou.attribType.Global, "identity_source", "procedural-canvas-receipt")
    geo.setGlobalAttribValue("identity_source", "procedural-canvas-receipt")
'''
    replacements = {
        "__SEED__": repr(int(defaults["seed"])),
        "__NUM_POINTS__": repr(int(defaults["num_points"])),
        "__REWIRE_PROBABILITY__": repr(float(defaults["rewire_probability"])),
        "__REWIRES_PER_EVENT__": repr(int(defaults["rewires_per_event"])),
        "__EVENT_SCHEDULE_STEPS__": repr(int(defaults["event_schedule_steps"])),
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    return template.strip() + "\n"


def build_network(parent: hou.Node, initial_path: Path, parameters: dict[str, float], defaults: dict[str, Any]) -> hou.Node:
    subnet = parent.createNode("subnet", "NONLOCAL_AFFINITY_PARALLEL")
    subnet.setParmTemplateGroup(artist_parameter_group(parameters, defaults))
    source = subnet.createNode("file", "EMBEDDED_PROMOTED_INITIAL_STATE")
    source.parm("file").set(native(initial_path))
    generator = subnet.createNode("python", "PREPARE_CANVAS_AND_COHORT_RECEIPT")
    generator.setInput(0, source)
    generator.parm("python").set(procedural_generator_code(defaults))
    generator.parm("maintainstate").set(False)
    initialize = subnet.createNode("attribwrangle", "INITIAL_IDENTITY_CONTROLS")
    initialize.setInput(0, generator)
    initialize.parm("class").set("point")
    initialize.parm("snippet").set(
        'float depth = chf("depth_scale");\n'
        'if (abs(depth - 1.0) > 1e-8) {\n'
        '    @P.z *= depth;\n'
        '}\n'
        'f@pscale = chf("point_size");\n'
    )
    for name, default in (("depth_scale", 1.0), ("point_size", 0.006)):
        add_float_parm(initialize, name, default)
        initialize.parm(name).setExpression(f'ch("../{name}")', hou.exprLanguage.Hscript)
    solver = subnet.createNode("solver", "solver")
    solver.allowEditingOfContents(propagate=True)
    solver.setInput(0, initialize)
    solver.parm("startframe").setExpression('ch("../start_frame") + 1', hou.exprLanguage.Hscript)
    solver.parm("substep").set(1)
    dopnet = solver.node("d")
    if dopnet is None:
        raise RuntimeError("Solver SOP has no internal DOP network")
    sopsolver = solver.node("d/s")
    if sopsolver is None:
        raise RuntimeError("Solver SOP has no internal SOP Solver")
    previous = sopsolver.node("Prev_Frame")
    output = sopsolver.node("OUT")
    if previous is None or output is None:
        raise RuntimeError("Solver SOP feedback nodes are unavailable")
    apply_events = sopsolver.createNode("attribwrangle", "APPLY_ORDERED_REWIRES")
    apply_events.setInput(0, previous)
    apply_events.parm("class").set("detail")
    apply_events.parm("snippet").set(
        'int step = detail(0, "simstep", 0) + 1;\n'
        'if (chi("apply_rewires")) {\n'
        '    int steps[] = detail(0, "event_steps");\n'
        '    int points[] = detail(0, "event_points");\n'
        '    int friends[] = detail(0, "event_friends");\n'
        '    int enemies[] = detail(0, "event_enemies");\n'
        '    for (int i = 0; i < len(steps); i++) {\n'
        '        if (steps[i] == step) {\n'
        '            setpointattrib(0, "friend", points[i], friends[i], "set");\n'
        '            setpointattrib(0, "enemy", points[i], enemies[i], "set");\n'
        '        }\n'
        '    }\n'
        '}\n'
        'setdetailattrib(0, "simstep", step, "set");\n'
    )
    add_toggle_parm(apply_events, "apply_rewires", True)
    apply_events.parm("apply_rewires").setExpression('ch("../../../../apply_rewires")', hou.exprLanguage.Hscript)
    integrate = sopsolver.createNode("attribwrangle", "INTEGRATE_POINTS_SYNCHRONOUSLY")
    integrate.setInput(0, apply_events)
    integrate.parm("class").set("point")
    integrate.parm("snippet").set(
        'vector origin = point(0, "P", @ptnum);\n'
        'int friend_index = point(0, "friend", @ptnum);\n'
        'int enemy_index = point(0, "enemy", @ptnum);\n'
        'vector friend_offset = point(0, "P", friend_index) - origin;\n'
        'vector enemy_offset = point(0, "P", enemy_index) - origin;\n'
        'float softening = chf("softening");\n'
        'vector toward = friend_offset / (softening + length(friend_offset));\n'
        'vector away = enemy_offset / (softening + length(enemy_offset));\n'
        '@P = chf("contraction") * origin + chf("attraction") * toward - chf("repulsion") * away;\n'
    )
    for name in ("contraction", "attraction", "repulsion", "softening"):
        add_float_parm(integrate, name, parameters[name])
        integrate.parm(name).setExpression(f'ch("../../../../{name}")', hou.exprLanguage.Hscript)
    output.setInput(0, integrate)
    cadence = subnet.createNode("timeshift", "STEPS_PER_DISPLAY_FRAME")
    cadence.setInput(0, solver)
    cadence.parm("frame").setExpression('ch("../start_frame") + ($F - ch("../start_frame")) * ch("../steps_per_frame")', hou.exprLanguage.Hscript)
    switch = subnet.createNode("switch", "OUTPUT_INITIAL_OR_SIMULATION")
    switch.setInput(0, initialize)
    switch.setInput(1, cadence)
    switch.parm("input").setExpression('$F >= ch("../start_frame") + 1', hou.exprLanguage.Hscript)
    final = subnet.createNode("null", "OUTPUT_SIMULATION_POINTS")
    final.setInput(0, switch)
    final.setDisplayFlag(True)
    final.setRenderFlag(True)
    source.setPosition(hou.Vector2(0, 0))
    generator.setPosition(hou.Vector2(0, -1.5))
    initialize.setPosition(hou.Vector2(0, -3.0))
    solver.setPosition(hou.Vector2(0, -4.5))
    cadence.setPosition(hou.Vector2(0, -6.0))
    switch.setPosition(hou.Vector2(0, -7.5))
    final.setPosition(hou.Vector2(0, -9.0))
    subnet.setColor(hou.Color((0.18, 0.42, 0.62)))
    return subnet


def node_errors(node: hou.Node) -> list[str]:
    errors: list[str] = []
    for child in (node, *node.allSubChildren()):
        errors.extend(f"{child.path()}: {error}" for error in child.errors())
    return errors


def run(
    preset_path: Path,
    prepared_path: Path,
    output: Path,
    verify_steps: int,
    cohort_size: int,
    expected_metrics_path: Path | None,
    prepared_schedule_steps: int,
) -> dict[str, Any]:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    preset = json.loads(preset_path.read_text(encoding="utf-8"))
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    count = len(prepared["initial_positions"])
    if cohort_size == 0:
        cohort_size = 1
    if cohort_size != 1:
        raise ValueError("cohorts are disabled; --cohort-size must be 1")
    preset_parameters = preset["parameters"]
    parameters = {
        "contraction": float(preset_parameters["contraction"]),
        "attraction": float(preset_parameters["attraction"]),
        "repulsion": float(preset_parameters["repulsion"]),
        "softening": float(preset_parameters["softening"]),
    }
    defaults = {
        "seed": int(preset["seed"]),
        "num_points": count,
        "rewire_probability": float(preset["rewiring"]["probability_per_simulation_step"]),
        "rewires_per_event": int(preset["rewiring"]["rewires_per_event"]),
        "event_schedule_steps": prepared_schedule_steps,
    }
    initial_path = output / "initial-state.bgeo.sc"
    build_initial_geometry(prepared, initial_path, cohort_size)
    hda_path = output / ASSET_FILE
    hip_path = output / DEMO_FILE
    if hda_path.exists():
        hda_path.unlink()
    hou.hipFile.clear(suppress_save_prompt=True)
    container = hou.node("/obj").createNode("geo", "NONLOCAL_AFFINITY_PLAYGROUND")
    for child in container.children():
        child.destroy()
    subnet = build_network(container, initial_path, parameters, defaults)
    asset = subnet.createDigitalAsset(
        name=TYPE_NAME,
        hda_file_name=native(hda_path),
        description="Bzor Non-Local Affinity | Parallel",
        min_num_inputs=0,
        max_num_inputs=0,
        save_as_embedded=False,
    )
    definition = asset.type().definition()
    if definition is None:
        raise RuntimeError("HDA definition was not created")
    definition.addSection("InitialState.bgeo.sc", initial_path.read_bytes())
    asset.allowEditingOfContents()
    embedded_source = asset.node("EMBEDDED_PROMOTED_INITIAL_STATE")
    if embedded_source is None:
        raise RuntimeError("embedded initial-state node is unavailable")
    embedded_source.parm("file").set("opdef:/bzor::Sop/nonlocal_affinity_parallel::1.3?InitialState.bgeo.sc")
    definition.updateFromNode(asset)
    definition.setParmTemplateGroup(artist_parameter_group(parameters, defaults))
    definition.addSection("PythonModule", hda_python_module_source())
    asset.matchCurrentDefinition()
    hou.setFrame(1)
    asset.cook(force=True)
    hou.hipFile.save(native(hip_path))

    hou.hipFile.clear(suppress_save_prompt=True)
    hou.hda.installFile(native(hda_path))
    audit_container = hou.node("/obj").createNode("geo", "HDA_FRESH_SESSION_AUDIT")
    for child in audit_container.children():
        child.destroy()
    audit_node = audit_container.createNode(TYPE_NAME, "NONLOCAL_AFFINITY_PARALLEL")
    hou.setFrame(1)
    audit_node.cook(force=True)
    initial_geometry = audit_node.geometry()
    if initial_geometry is None:
        raise RuntimeError("HDA audit produced no initial geometry")
    initial_point_count = len(initial_geometry.points())
    hou.setFrame(verify_steps + 1)
    audit_node.cook(force=True)
    geometry = audit_node.geometry()
    if geometry is None:
        raise RuntimeError("HDA audit produced no geometry")
    audit_errors = node_errors(audit_node)
    if geometry.findPointAttrib("friend") is None or geometry.findPointAttrib("enemy") is None:
        raise RuntimeError(f"HDA audit is missing relationship attributes; points={len(geometry.points())}; errors={audit_errors}")
    friends = list(geometry.pointIntAttribValues("friend"))
    enemies = list(geometry.pointIntAttribValues("enemy"))
    final_point_count = len(geometry.points())
    final_state_sha = geometry_digest(geometry)
    final_relationship_sha = relationship_digest(friends, enemies)
    expected_metrics = (
        json.loads(expected_metrics_path.read_text(encoding="utf-8"))
        if expected_metrics_path is not None
        else None
    )
    batch_backend_match = None
    if expected_metrics is not None:
        if int(expected_metrics.get("steps", -1)) != verify_steps:
            raise ValueError("expected metrics horizon does not match --verify-steps")
        batch_backend_match = bool(
            final_state_sha == expected_metrics.get("final_state_sha256")
            and final_relationship_sha == expected_metrics.get("final_relationship_sha256")
        )
        if not batch_backend_match:
            raise RuntimeError("fresh-session HDA state does not match the expected batch backend")

    audit_node.parm("num_points").set(16)
    audit_node.parm("seed").set((int(defaults["seed"]) + 1) & 0x7FFFFFFF)
    audit_node.parm("steps_per_frame").set(3)
    audit_node.parm("reset_simulation").pressButton()
    hou.setFrame(1)
    audit_node.cook(force=True)
    procedural_initial = audit_node.geometry()
    if procedural_initial is None:
        raise RuntimeError("procedural count probe produced no initial geometry")
    procedural_total = len(procedural_initial.points())
    procedural_source = procedural_initial.attribValue("identity_source")
    hou.setFrame(2)
    audit_node.cook(force=True)
    procedural_stepped = audit_node.geometry()
    procedural_errors = node_errors(audit_node)
    procedural_friends = list(procedural_stepped.pointIntAttribValues("friend")) if procedural_stepped is not None else []
    procedural_enemies = list(procedural_stepped.pointIntAttribValues("enemy")) if procedural_stepped is not None else []
    procedural_probe = {
        "num_points": 16,
        "total_points": procedural_total,
        "identity_source": procedural_source,
        "steps_per_frame": 3,
        "simstep_at_frame_2": int(procedural_stepped.attribValue("simstep")) if procedural_stepped is not None else None,
        "final_state_sha256": geometry_digest(procedural_stepped) if procedural_stepped is not None else None,
        "final_relationship_sha256": relationship_digest(procedural_friends, procedural_enemies) if procedural_stepped is not None else None,
        "node_errors": procedural_errors,
    }
    if procedural_total != 16 or procedural_source != "procedural-canvas-receipt" or procedural_errors:
        raise RuntimeError(f"procedural count probe failed: {procedural_probe}")

    audit_node.parm("num_points").set(500000)
    audit_node.parm("steps_per_frame").set(1)
    audit_node.parm("reset_simulation").pressButton()
    hou.setFrame(1)
    audit_node.cook(force=True)
    maximum_geometry = audit_node.geometry()
    if maximum_geometry is None:
        raise RuntimeError("500k maximum-count probe produced no geometry")
    maximum_friends = list(maximum_geometry.pointIntAttribValues("friend"))
    maximum_enemies = list(maximum_geometry.pointIntAttribValues("enemy"))
    maximum_positions = maximum_geometry.pointFloatAttribValues("P")
    maximum_errors = node_errors(audit_node)
    maximum_probe = {
        "num_points": 500000,
        "total_points": len(maximum_geometry.points()),
        "relationships_in_range": all(0 <= value < 500000 for value in maximum_friends) and all(0 <= value < 500000 for value in maximum_enemies),
        "positions_finite": all(math.isfinite(value) for value in maximum_positions),
        "node_errors": maximum_errors,
    }
    if maximum_probe["total_points"] != 500000 or not maximum_probe["relationships_in_range"] or not maximum_probe["positions_finite"] or maximum_errors:
        raise RuntimeError(f"500k maximum-count probe failed: {maximum_probe}")

    manifest_path = output / "audit-overlay-parameter-manifest.json"
    audit_node.parm("num_points").set(int(defaults["num_points"]))
    audit_node.parm("seed").set(int(defaults["seed"]))
    audit_node.parm("attraction").set(0.035)
    audit_node.parm("overlay_variation_number").set(7)
    audit_node.parm("overlay_variation_title").set("Graph Tension")
    audit_node.parm("overlay_manifest_path").set(native(manifest_path))
    audit_node.parm("export_overlay_manifest").pressButton()
    exported_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_errors = validate_overlay_parameter_manifest(exported_manifest)
    if manifest_errors:
        raise RuntimeError("HDA overlay parameter manifest failed validation: " + "; ".join(manifest_errors))
    manifest_probe = {
        "variation": exported_manifest["variation"],
        "parameter_keys": [parameter["key"] for parameter in exported_manifest["parameters"]],
        "path": native(manifest_path),
    }
    audit = {
        "schema_version": 1,
        "asset_type": TYPE_NAME,
        "asset_file": ASSET_FILE,
        "demo_hip": DEMO_FILE,
        "state_authority": "vex-geometry",
        "prepared_source": prepared_path.name,
        "population_count_mode": "direct-canvas-points",
        "routing": "no-cohorts",
        "point_count": final_point_count,
        "initial_point_count": initial_point_count,
        "verified_steps": verify_steps,
        "final_state_sha256": final_state_sha,
        "final_relationship_sha256": final_relationship_sha,
        "batch_backend_match": batch_backend_match,
        "artist_parameters": [name for name in ARTIST_PARAMETERS if audit_node.parm(name) is not None],
        "canonical_defaults": defaults,
        "procedural_count_probe": procedural_probe,
        "maximum_count_probe": maximum_probe,
        "overlay_parameter_manifest_probe": manifest_probe,
        "num_points_hard_maximum": 500000,
        "num_points_ui_maximum": int(audit_node.parm("num_points").parmTemplate().maxValue()),
        "graph_receipt_preserving_parameters": ["contraction", "attraction", "repulsion", "softening", "point_size", "start_frame", "steps_per_frame"],
        "promoted_identity_variation_parameters": ["seed", "num_points", "rewire_probability", "rewires_per_event", "event_schedule_steps", "apply_rewires", "depth_scale"],
        "node_errors": audit_errors,
        "interactive_semantics": "frame 1 is initial state; with Steps / Display Frame = S, frame N+1 contains N×S synchronous steps",
        "ordered_events": "serial detail stage before parallel point integration",
        "batch_backend_retained": True,
    }
    (output / "audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, sort_keys=True))
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("preset", type=Path)
    parser.add_argument("prepared", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--verify-steps", type=int, default=6)
    parser.add_argument("--cohort-size", type=int, default=1, help="legacy compatibility; cohorts are disabled and this must be 1")
    parser.add_argument("--expected-metrics", type=Path)
    parser.add_argument("--prepared-schedule-steps", type=int, default=240)
    args = parser.parse_args()
    run(
        args.preset, args.prepared, args.output, args.verify_steps, args.cohort_size,
        args.expected_metrics, args.prepared_schedule_steps,
    )


if __name__ == "__main__":
    main()
