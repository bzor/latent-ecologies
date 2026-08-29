"""Build four non-destructive Lookdev directions for Study 003 affinity."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from itertools import combinations
from pathlib import Path
from typing import Any

import hou

SCENE_NAME = "nonlocal-affinity-lookdev-directions.hiplc"
DERIVED_ATTRIBUTES = (
    "v", "speed", "accel", "heading", "orient", "curvature",
    "friend_dir", "enemy_dir", "friend_dist", "enemy_dist",
    "affinity_balance", "social_stress", "local_density",
    "displacement", "state",
)


def native(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def errors_for(node: hou.Node) -> list[str]:
    return [f"{child.path()}: {error}" for child in (node, *node.allSubChildren()) for error in child.errors()]


def set_detail(node: hou.Node, snippet: str) -> None:
    node.parm("class").set("detail")
    node.parm("snippet").set(snippet)


def set_point(node: hou.Node, snippet: str) -> None:
    node.parm("class").set("point")
    node.parm("snippet").set(snippet)


def add_empty(geo: hou.Node, name: str) -> hou.Node:
    node = geo.createNode("add", name)
    node.parm("points").set(0)
    node.parm("prims").set(0)
    return node


def build(source: Path, output_dir: Path) -> dict[str, Any]:
    source = source.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / SCENE_NAME
    if destination.exists():
        raise RuntimeError(f"refusing to overwrite existing Lookdev scene: {destination}")
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    hou.hipFile.load(native(source), suppress_save_prompt=True)
    affinity_nodes = [node for node in hou.node("/obj").allSubChildren() if node.type().name() == "bzor::nonlocal_affinity_parallel::1.2"]
    if len(affinity_nodes) != 1:
        raise RuntimeError(f"expected one affinity HDA, found {len(affinity_nodes)}")
    source_node = affinity_nodes[0]
    geo = source_node.parent()
    if geo is None:
        raise RuntimeError("affinity HDA has no geometry parent")

    previous = geo.createNode("timeshift", "PREVIOUS_FRAME")
    previous.setInput(0, source_node)
    previous.parm("frame").setExpression("$F - 1", hou.exprLanguage.Hscript)
    previous2 = geo.createNode("timeshift", "TWO_FRAMES_BACK")
    previous2.setInput(0, source_node)
    previous2.parm("frame").setExpression("$F - 2", hou.exprLanguage.Hscript)
    derive = geo.createNode("attribwrangle", "DERIVE_ORGANISM_ATTRIBUTES")
    derive.setInput(0, source_node)
    derive.setInput(1, previous)
    derive.setInput(2, previous2)
    set_point(derive, r'''
vector previous_p = point(1, "P", @ptnum);
vector previous2_p = point(2, "P", @ptnum);
v@v = @P - previous_p;
v@accel = @P - 2.0 * previous_p + previous2_p;
f@speed = length(v@v);
vector previous_v = previous_p - previous2_p;
v@heading = f@speed > 1e-9 ? normalize(v@v) : normalize(point(0, "P", i@friend) - @P);
p@orient = quaternion(dihedral({0, 0, 1}, v@heading));
f@curvature = (length(previous_v) > 1e-9 && f@speed > 1e-9) ? acos(clamp(dot(normalize(previous_v), v@heading), -1.0, 1.0)) : 0.0;
vector friend_offset = point(0, "P", i@friend) - @P;
vector enemy_offset = @P - point(0, "P", i@enemy);
f@friend_dist = length(friend_offset);
f@enemy_dist = length(enemy_offset);
v@friend_dir = f@friend_dist > 1e-9 ? friend_offset / f@friend_dist : {0, 0, 0};
v@enemy_dir = f@enemy_dist > 1e-9 ? enemy_offset / f@enemy_dist : {0, 0, 0};
float friend_alignment = dot(v@heading, v@friend_dir);
float enemy_alignment = dot(v@heading, v@enemy_dir);
f@affinity_balance = clamp(0.5 + 0.25 * (friend_alignment + enemy_alignment), 0.0, 1.0);
f@social_stress = clamp(0.5 - 0.5 * dot(v@friend_dir, v@enemy_dir), 0.0, 1.0);
int neighbours[] = pcfind(0, "P", @P, 0.035, 32);
f@local_density = clamp(float(len(neighbours)) / 32.0, 0.0, 1.0);
f@displacement = distance(@P, v@anchorP);
f@state = f@affinity_balance < 0.4 ? 0.0 : (f@affinity_balance > 0.6 ? 1.0 : 0.5);
'''.strip())

    # Direct organism view: packed low-poly instances plus sampled short trails.
    organism_shape = geo.createNode("platonic", "ORGANISM_TETRA_INSTANCE")
    organism_shape.parm("type").set(0)
    organism_shape.parm("radius").set(1.0)
    particles = geo.createNode("copytopoints::2.0", "INSTANCE_ORGANISMS")
    particles.setInput(0, organism_shape)
    particles.setInput(1, derive)
    particles.parm("pack").set(1)
    trail_sample = geo.createNode("attribwrangle", "TRAIL_REVIEW_SAMPLE_40K")
    trail_sample.setInput(0, derive)
    set_point(trail_sample, "if (@ptnum % 10 != 0) removepoint(0, @ptnum);\ni@id = @ptnum;")
    trails = geo.createNode("trail", "SHORT_TRAILS_8_FRAMES")
    trails.setInput(0, trail_sample)
    trails.parm("result").set("poly")
    trails.parm("length").set(8)
    trails.parm("inc").set(1)
    trails.parm("matchbyattribute").set(1)
    trails.parm("attributetomatch").set("id")
    particle_merge = geo.createNode("merge", "LOOK_PARTICLE_TRAILS")
    particle_merge.setInput(0, particles)
    particle_merge.setInput(1, trails)

    # Relationship view: no source points, only sampled friend/enemy fibres.
    weave_empty = add_empty(geo, "EMPTY_FOR_AFFINITY_WEAVE")
    weave = geo.createNode("attribwrangle", "LOOK_AFFINITY_WEAVE")
    weave.setInput(0, weave_empty)
    weave.setInput(1, derive)
    set_detail(weave, r'''
addpointattrib(0, "state", 0.5);
addpointattrib(0, "width", 0.001);
addprimattrib(0, "relation_type", 0);
int total = npoints(1);
for (int source = 0; source < total; source += 20) {
    vector origin = point(1, "P", source);
    float stress = point(1, "social_stress", source);
    int friend_target = point(1, "friend", source);
    int enemy_target = point(1, "enemy", source);
    int targets[] = array(friend_target, enemy_target);
    for (int relation = 0; relation < 2; relation++) {
        vector target = point(1, "P", targets[relation]);
        int a = addpoint(0, origin);
        int b = addpoint(0, lerp(origin, target, 0.5) + set(0, 0, (relation == 0 ? 1 : -1) * 0.01 * stress));
        int c = addpoint(0, target);
        int primitive = addprim(0, "polyline", a, b, c);
        float semantic_state = relation == 0 ? 1.0 : 0.0;
        setpointattrib(0, "state", a, semantic_state, "set");
        setpointattrib(0, "state", b, semantic_state, "set");
        setpointattrib(0, "state", c, semantic_state, "set");
        float width = fit(stress, 0.0, 1.0, 0.0005, 0.003);
        setpointattrib(0, "width", a, width, "set");
        setpointattrib(0, "width", b, width, "set");
        setpointattrib(0, "width", c, width, "set");
        setprimattrib(0, "relation_type", primitive, relation, "set");
    }
}
'''.strip())

    # Collective tissue view: social stress and density control a continuous VDB skin.
    membrane_sample = geo.createNode("attribwrangle", "MEMBRANE_REVIEW_SAMPLE_100K")
    membrane_sample.setInput(0, derive)
    set_point(membrane_sample, r'''
if (@ptnum % 4 != 0) removepoint(0, @ptnum);
f@pscale = fit(clamp(0.55 * f@social_stress + 0.45 * f@local_density, 0.0, 1.0), 0.0, 1.0, 0.008, 0.028);
'''.strip())
    membrane = geo.createNode("vdbfromparticles", "LOOK_TENSION_MEMBRANE")
    membrane.setInput(0, membrane_sample)
    membrane.parm("voxelsize").set(0.012)
    membrane.parm("builddistance").set(1)
    membrane.parm("distancename").set("social_tissue")
    membrane.parm("radiusscale").set(1.35)
    membrane.parm("minvoxelradius").set(1.5)

    # Collective flow view: spatially aggregate velocity into a coarse vector anatomy.
    flow_empty = add_empty(geo, "EMPTY_FOR_FLOW_ANATOMY")
    flow = geo.createNode("attribwrangle", "LOOK_FLOW_ANATOMY")
    flow.setInput(0, flow_empty)
    flow.setInput(1, derive)
    set_detail(flow, r'''
addpointattrib(0, "state", 0.5);
addpointattrib(0, "width", 0.001);
addprimattrib(0, "flow_density", 0.0);
vector minimum, maximum;
getbbox(1, minimum, maximum);
int nx = 32, ny = 32, nz = 8;
float radius = 0.055;
for (int z = 0; z < nz; z++) {
    for (int y = 0; y < ny; y++) {
        for (int x = 0; x < nx; x++) {
            vector uvw = set((x + 0.5) / nx, (y + 0.5) / ny, (z + 0.5) / nz);
            vector position = lerp(minimum, maximum, uvw);
            int nearby[] = pcfind(1, "P", position, radius, 64);
            if (len(nearby) < 3) continue;
            vector velocity = {0, 0, 0};
            float balance = 0.0;
            foreach (int point_number; nearby) {
                velocity += point(1, "v", point_number);
                balance += point(1, "affinity_balance", point_number);
            }
            velocity /= len(nearby);
            balance /= len(nearby);
            float magnitude = length(velocity);
            if (magnitude < 1e-7) continue;
            vector direction = normalize(velocity);
            float half_length = fit(clamp(magnitude, 0.0, 0.02), 0.0, 0.02, 0.003, 0.035);
            int a = addpoint(0, position - direction * half_length);
            int b = addpoint(0, position + direction * half_length);
            int primitive = addprim(0, "polyline", a, b);
            setpointattrib(0, "state", a, balance < 0.4 ? 0.0 : (balance > 0.6 ? 1.0 : 0.5), "set");
            setpointattrib(0, "state", b, balance < 0.4 ? 0.0 : (balance > 0.6 ? 1.0 : 0.5), "set");
            float width = fit(clamp(float(len(nearby)) / 64.0, 0.0, 1.0), 0.0, 1.0, 0.0005, 0.004);
            setpointattrib(0, "width", a, width, "set");
            setpointattrib(0, "width", b, width, "set");
            setprimattrib(0, "flow_density", primitive, float(len(nearby)) / 64.0, "set");
        }
    }
}
'''.strip())

    group = geo.parmTemplateGroup()
    look_menu = hou.MenuParmTemplate(
        "look_direction", "Look Direction",
        ("0", "1", "2", "3"),
        ("Particle Organisms + Trails", "Affinity Weave", "Tension Membrane", "Flow Anatomy"),
        default_value=0,
    )
    folder = hou.FolderParmTemplate("lookdev_controls", "Lookdev Directions", folder_type=hou.folderType.Simple)
    folder.addParmTemplate(look_menu)
    group.append(folder)
    geo.setParmTemplateGroup(group)
    selector = geo.createNode("switch", "SELECT_LOOK_DIRECTION")
    for index, node in enumerate((particle_merge, weave, membrane, flow)):
        selector.setInput(index, node)
    selector.parm("input").setExpression('ch("../look_direction")', hou.exprLanguage.Hscript)
    output = geo.createNode("null", "OUTPUT_SELECTED_LOOK")
    output.setInput(0, selector)
    output.setDisplayFlag(True)
    output.setRenderFlag(True)

    positions = {
        source_node: (0.0, 14.0),
        previous: (-3.0, 11.0),
        previous2: (3.0, 11.0),
        derive: (0.0, 8.0),
        organism_shape: (-12.0, 4.0),
        particles: (-12.0, 1.0),
        trail_sample: (-8.0, 4.0),
        trails: (-8.0, 1.0),
        particle_merge: (-10.0, -2.5),
        weave_empty: (-3.0, 4.0),
        weave: (-3.0, -2.5),
        membrane_sample: (4.0, 4.0),
        membrane: (4.0, -2.5),
        flow_empty: (11.0, 4.0),
        flow: (11.0, -2.5),
        selector: (0.0, -7.0),
        output: (0.0, -10.0),
    }
    for node, position in positions.items():
        node.setPosition(hou.Vector2(position))
    source_node.setColor(hou.Color((0.18, 0.34, 0.58)))
    for node in (previous, previous2, derive):
        node.setColor(hou.Color((0.18, 0.58, 0.66)))
    for node in (organism_shape, particles, trail_sample, trails, particle_merge):
        node.setColor(hou.Color((0.42, 0.62, 0.28)))
    for node in (weave_empty, weave):
        node.setColor(hou.Color((0.58, 0.34, 0.66)))
    for node in (membrane_sample, membrane):
        node.setColor(hou.Color((0.65, 0.42, 0.22)))
    for node in (flow_empty, flow):
        node.setColor(hou.Color((0.25, 0.48, 0.72)))
    selector.setColor(hou.Color((0.72, 0.58, 0.18)))
    output.setColor(hou.Color((0.24, 0.68, 0.38)))

    boxes = (
        ("00 Simulation Source + Derived Attributes", (source_node, previous, previous2, derive)),
        ("01 Particle Organisms + Trails", (organism_shape, particles, trail_sample, trails, particle_merge)),
        ("02 Affinity Weave", (weave_empty, weave)),
        ("03 Tension Membrane", (membrane_sample, membrane)),
        ("04 Flow Anatomy", (flow_empty, flow)),
        ("05 Direction Selector", (selector, output)),
    )
    network_boxes = []
    for label, nodes in boxes:
        box = geo.createNetworkBox()
        box.setComment(label)
        for node in nodes:
            box.addItem(node)
        box.fitAroundContents()
        network_boxes.append(box)
    note = geo.createStickyNote()
    note.setText("Study 003 Lookdev directions\n30 fps | simulation 1–650 | 200-step prewarm | visible 201–650\nUse /obj/geo1 Look Direction. Derived attributes are downstream only; Behavior remains unchanged.")
    note.setPosition(hou.Vector2((8.0, 14.0)))
    note.setSize(hou.Vector2((6.0, 4.0)))

    hou.setFrame(201)
    derive.cook(force=True)
    derived_geo = derive.geometry()
    if derived_geo is None:
        raise RuntimeError("derived attribute layer produced no geometry")
    missing = [name for name in DERIVED_ATTRIBUTES if derived_geo.findPointAttrib(name) is None]
    if missing:
        raise RuntimeError(f"missing derived attributes: {missing}")
    source_simstep = int(derived_geo.attribValue("simstep"))
    looks: dict[str, Any] = {}
    for name, node in (
        ("particle-trails", particle_merge),
        ("affinity-weave", weave),
        ("tension-membrane", membrane),
        ("flow-anatomy", flow),
    ):
        try:
            node.cook(force=True)
        except hou.OperationFailed as error:
            raise RuntimeError(f"Look {name} cook failed at {node.path()}: {errors_for(node)}") from error
        cooked = node.geometry()
        node_errors = errors_for(node)
        if cooked is None or len(cooked.prims()) == 0 or node_errors:
            raise RuntimeError(f"Look {name} failed: primitives={0 if cooked is None else len(cooked.prims())}; errors={node_errors}")
        looks[name] = {
            "node_path": node.path(),
            "point_count": len(cooked.points()),
            "primitive_count": len(cooked.prims()),
            "node_errors": node_errors,
        }

    hou.hipFile.save(native(destination))
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_sha:
        raise RuntimeError("source user scene changed during Lookdev build")
    position_groups: dict[tuple[float, float], list[str]] = {}
    for node in positions:
        key = tuple(round(value, 4) for value in node.position())
        position_groups.setdefault(key, []).append(node.name())
    duplicate_positions = [sorted(names) for names in position_groups.values() if len(names) > 1]
    minimum_separation = min(
        math.hypot(left.position()[0] - right.position()[0], left.position()[1] - right.position()[1])
        for left, right in combinations(positions, 2)
    )
    overlapping_boxes = []
    for left, right in combinations(network_boxes, 2):
        left_min, right_min = left.position(), right.position()
        left_max, right_max = left_min + left.size(), right_min + right.size()
        overlaps = not (
            left_max[0] <= right_min[0] or right_max[0] <= left_min[0]
            or left_max[1] <= right_min[1] or right_max[1] <= left_min[1]
        )
        if overlaps:
            overlapping_boxes.append(sorted((left.comment(), right.comment())))
    layout = {
        "duplicate_node_positions": duplicate_positions,
        "overlapping_network_boxes": overlapping_boxes,
        "minimum_node_separation": minimum_separation,
        "layout_direction": "top-to-bottom with parallel Look branches in adjacent columns",
    }
    if duplicate_positions or overlapping_boxes or minimum_separation < 2.0:
        raise RuntimeError(f"Lookdev layout audit failed: {layout}")
    audit = {
        "schema_version": 1,
        "source_hip": native(source),
        "source_sha256": source_sha,
        "output_hip": destination.name,
        "frame": 201,
        "fps": hou.fps(),
        "simulation_range": list(hou.playbar.frameRange()),
        "visible_range": list(hou.playbar.playbackRange()),
        "source_point_count": len(derived_geo.points()),
        "source_simstep": source_simstep,
        "derived_point_attributes": list(DERIVED_ATTRIBUTES),
        "state_coordinates": [0.0, 0.5, 1.0],
        "looks": looks,
        "layout": layout,
        "node_errors": errors_for(derive),
        "behavior_modified": False,
    }
    (output_dir / "audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, sort_keys=True))
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.source, args.output)


if __name__ == "__main__":
    main()
