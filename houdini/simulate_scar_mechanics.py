from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

import hou

ROOT = Path(__file__).resolve().parents[1]
VEX_PATH = ROOT / "houdini/vex/scar_mechanics_stateful.vfl"
MODE_IDS = {"excitable-purse-string-zipper": 0, "tug-zip-fasciculation": 1}


def add_common_attributes(geometry: hou.Geometry) -> None:
    for name, default in (
        ("id", 0), ("class", 0), ("bank", 0), ("edge_index", 0),
        ("activator", 0.0), ("refractory", 0.0), ("myosin", 0.0),
        ("ratchet", 0.0), ("unwrapped_x", 0.0), ("tube_angle", 0.0), ("tube_radius", 0.0),
        ("fused", 0), ("zip_partner", -1),
        ("heading", 0.0), ("phase", 0), ("anchor", -1), ("adhesion_age", 0),
        ("traction", 0.0), ("flow_alignment", 0.0),
        ("mass", 0.0), ("crimp", 0.0), ("strain", 0.0),
        ("fibre_tension", 0.0), ("stability", 0.0), ("bundle_degree", 0.0),
        ("lox", 0.0),
    ):
        geometry.addAttrib(hou.attribType.Point, name, default)
    geometry.addAttrib(hou.attribType.Point, "fdir", (0.0, 1.0, 0.0))
    geometry.addAttrib(hou.attribType.Point, "pull", (0.0, 0.0, 0.0))
    for name, default in (
        ("kind", 0), ("bond", 0.0), ("zip_age", 0), ("latched", 0),
        ("rest_length", 0.0), ("tension", 0.0),
        ("contact_dwell", 0.0), ("bond_age", 0),
    ):
        geometry.addAttrib(hou.attribType.Prim, name, default)
    geometry.addAttrib(hou.attribType.Global, "mutation_branch", -1)
    geometry.addAttrib(hou.attribType.Global, "sim_frame", 0)
    geometry.addAttrib(hou.attribType.Global, "pulse_events", 0)
    geometry.addAttrib(hou.attribType.Global, "zip_events", 0)
    geometry.addAttrib(hou.attribType.Global, "tug_events", 0)
    geometry.addAttrib(hou.attribType.Global, "bond_events", 0)
    geometry.addAttrib(hou.attribType.Global, "late_bond_events", 0)
    geometry.addAttrib(hou.attribType.Global, "adhesion_samples", 0)
    geometry.addAttrib(hou.attribType.Global, "flow_recruit_events", 0)


def initial_zipper_geometry(parameters: dict) -> hou.Geometry:
    geometry = hou.Geometry()
    add_common_attributes(geometry)
    edge_count = int(parameters["edge_count"])
    half_width = float(parameters["bank_half_width"])
    height = float(parameters["wound_height"])
    space_mode = int(parameters.get("zipper_space_mode", 0))
    azimuth = float(parameters.get("tube_azimuth", 0.0))
    banks: dict[int, list[hou.Point]] = {-1: [], 1: []}
    for bank in (-1, 1):
        for index in range(edge_count):
            yn = index / max(1, edge_count - 1)
            y = -height * 0.5 + height * yn
            seam = 0.10 * math.sin(y * 0.78) + 0.035 * math.sin(y * 2.17)
            point = geometry.createPoint()
            if space_mode == 1:
                point.setPosition((
                    seam + bank * half_width * math.cos(azimuth),
                    y,
                    bank * half_width * math.sin(azimuth),
                ))
            else:
                point.setPosition((seam + bank * half_width, y, 0.0))
            point.setAttribValue("id", len(banks[-1]) + len(banks[1]))
            point.setAttribValue("class", 1)
            point.setAttribValue("bank", bank)
            point.setAttribValue("edge_index", index)
            point.setAttribValue("unwrapped_x", seam + bank * half_width)
            point.setAttribValue("tube_angle", azimuth)
            point.setAttribValue("tube_radius", half_width)
            banks[bank].append(point)
    for bank in (-1, 1):
        for index in range(edge_count - 1):
            primitive = geometry.createPolygon()
            primitive.setIsClosed(False)
            primitive.addVertex(banks[bank][index])
            primitive.addVertex(banks[bank][index + 1])
            primitive.setAttribValue("kind", 0)
            primitive.setAttribValue("rest_length", banks[bank][index].position().distanceTo(banks[bank][index + 1].position()))
    for index in (0, edge_count - 1):
        primitive = geometry.createPolygon()
        primitive.setIsClosed(False)
        primitive.addVertex(banks[-1][index])
        primitive.addVertex(banks[1][index])
        primitive.setAttribValue("kind", 0)
        primitive.setAttribValue("rest_length", banks[-1][index].position().distanceTo(banks[1][index].position()))
    for index in range(edge_count):
        primitive = geometry.createPolygon()
        primitive.setIsClosed(False)
        primitive.addVertex(banks[-1][index])
        primitive.addVertex(banks[1][index])
        primitive.setAttribValue("kind", 1)
        primitive.setAttribValue("rest_length", banks[-1][index].position().distanceTo(banks[1][index].position()))
    return geometry


def initial_fascicle_geometry(parameters: dict, seed: int) -> hou.Geometry:
    geometry = hou.Geometry()
    add_common_attributes(geometry)
    rng = random.Random(seed)
    fibre_count = int(parameters["fibre_count"])
    agent_count = int(parameters["agent_count"])
    width = float(parameters["domain_width"])
    height = float(parameters["domain_height"])
    fibres: list[hou.Point] = []
    for fibre_id in range(fibre_count):
        y = rng.uniform(-height * 0.48, height * 0.48)
        seam = 0.28 * math.sin(y * 0.72) + 0.09 * math.sin(y * 1.91)
        x = max(-width * 0.45, min(width * 0.45, seam + rng.gauss(0.0, width * 0.18)))
        angle = rng.uniform(-math.pi, math.pi)
        point = geometry.createPoint()
        point.setPosition((x, y, 0.0))
        point.setAttribValue("id", fibre_id)
        point.setAttribValue("class", 2)
        point.setAttribValue("fdir", (math.cos(angle), math.sin(angle), 0.0))
        point.setAttribValue("mass", rng.uniform(0.72, 1.0))
        point.setAttribValue("crimp", rng.uniform(0.70, 0.98))
        point.setAttribValue("stability", rng.uniform(0.02, 0.08))
        fibres.append(point)
    for agent_id in range(agent_count):
        point = geometry.createPoint()
        point.setPosition((rng.uniform(-width * 0.45, width * 0.45), rng.uniform(-height * 0.45, height * 0.45), 0.0))
        point.setAttribValue("id", agent_id)
        point.setAttribValue("class", 0)
        point.setAttribValue("heading", rng.uniform(-math.pi, math.pi))
        point.setAttribValue("traction", rng.uniform(0.65, 1.0))
    radius = float(parameters["candidate_radius"])
    max_neighbors = int(parameters["max_candidate_neighbors"])
    degree = [0] * fibre_count
    candidates: list[tuple[float, int, int]] = []
    for a in range(fibre_count):
        for b in range(a + 1, fibre_count):
            distance = fibres[a].position().distanceTo(fibres[b].position())
            if distance <= radius:
                candidates.append((distance, a, b))
    for distance, a, b in sorted(candidates):
        if degree[a] >= max_neighbors or degree[b] >= max_neighbors:
            continue
        primitive = geometry.createPolygon()
        primitive.setIsClosed(False)
        primitive.addVertex(fibres[a])
        primitive.addVertex(fibres[b])
        primitive.setAttribValue("kind", 2)
        primitive.setAttribValue("rest_length", distance)
        degree[a] += 1
        degree[b] += 1
    return geometry


def state_digest(geometry: hou.Geometry) -> str:
    points = []
    for point in geometry.points():
        points.append((
            int(point.attribValue("id")),
            tuple(round(float(value), 6) for value in point.position()),
            round(float(point.attribValue("activator")), 6),
            round(float(point.attribValue("refractory")), 6),
            round(float(point.attribValue("myosin")), 6),
            round(float(point.attribValue("ratchet")), 6),
            round(float(point.attribValue("unwrapped_x")), 6),
            round(float(point.attribValue("tube_angle")), 6),
            round(float(point.attribValue("tube_radius")), 6),
            int(point.attribValue("fused")), int(point.attribValue("zip_partner")),
            round(float(point.attribValue("heading")), 6), int(point.attribValue("phase")),
            int(point.attribValue("anchor")), int(point.attribValue("adhesion_age")),
            round(float(point.attribValue("traction")), 6),
            round(float(point.attribValue("flow_alignment")), 6),
            tuple(round(float(value), 6) for value in point.attribValue("fdir")),
            round(float(point.attribValue("mass")), 6), round(float(point.attribValue("crimp")), 6),
            round(float(point.attribValue("strain")), 6), round(float(point.attribValue("fibre_tension")), 6),
            round(float(point.attribValue("stability")), 6), round(float(point.attribValue("bundle_degree")), 6),
            round(float(point.attribValue("lox")), 6),
            tuple(round(float(value), 6) for value in point.attribValue("pull")),
        ))
    primitives = []
    for primitive in geometry.prims():
        primitives.append((
            int(primitive.attribValue("kind")),
            tuple(vertex.point().number() for vertex in primitive.vertices()),
            round(float(primitive.attribValue("bond")), 6),
            int(primitive.attribValue("zip_age")), int(primitive.attribValue("latched")),
            round(float(primitive.attribValue("rest_length")), 6),
            round(float(primitive.attribValue("tension")), 6),
            round(float(primitive.attribValue("contact_dwell")), 6),
            int(primitive.attribValue("bond_age")),
        ))
    payload = {"points": points, "primitives": primitives}
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode("utf-8")).hexdigest()


def kinetic_state_digest(geometry: hou.Geometry) -> str:
    payload = {
        "points": [(
            int(point.attribValue("id")),
            round(float(point.attribValue("activator")), 6),
            round(float(point.attribValue("refractory")), 6),
            round(float(point.attribValue("myosin")), 6),
            round(float(point.attribValue("ratchet")), 6),
            int(point.attribValue("fused")),
            int(point.attribValue("zip_partner")),
        ) for point in geometry.points()],
        "zipper_primitives": [(
            int(primitive.attribValue("kind")),
            tuple(vertex.point().number() for vertex in primitive.vertices()),
            round(float(primitive.attribValue("bond")), 6),
            int(primitive.attribValue("zip_age")),
            int(primitive.attribValue("latched")),
        ) for primitive in geometry.prims() if int(primitive.attribValue("kind")) == 1],
        "pulse_events": int(geometry.attribValue("pulse_events")),
        "zip_events": int(geometry.attribValue("zip_events")),
    }
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode("utf-8")).hexdigest()


def configure_wrangle(node: hou.SopNode, values: dict, vex_source: str) -> None:
    group = node.parmTemplateGroup()
    for name, value in values.items():
        if isinstance(value, int):
            template = hou.IntParmTemplate(name, name, 1, default_value=(value,))
        else:
            template = hou.FloatParmTemplate(name, name, 1, default_value=(float(value),))
        group.append(template)
    node.setParmTemplateGroup(group)
    for name, value in values.items():
        node.parm(name).set(value)
    node.parm("class").set("detail")
    node.parm("snippet").set(vex_source)


def review_record(geometry: hou.Geometry, frame: int) -> dict:
    return {
        "frame": frame,
        "points": [{
            "id": int(point.attribValue("id")),
            "class": int(point.attribValue("class")),
            "bank": int(point.attribValue("bank")),
            "edge_index": int(point.attribValue("edge_index")),
            "P": [round(float(value), 5) for value in point.position()],
            "activator": round(float(point.attribValue("activator")), 5),
            "myosin": round(float(point.attribValue("myosin")), 5),
            "ratchet": round(float(point.attribValue("ratchet")), 5),
            "unwrapped_x": round(float(point.attribValue("unwrapped_x")), 5),
            "tube_angle": round(float(point.attribValue("tube_angle")), 5),
            "tube_radius": round(float(point.attribValue("tube_radius")), 5),
            "fused": int(point.attribValue("fused")),
            "heading": round(float(point.attribValue("heading")), 5),
            "phase": int(point.attribValue("phase")),
            "anchor": int(point.attribValue("anchor")),
            "traction": round(float(point.attribValue("traction")), 5),
            "flow_alignment": round(float(point.attribValue("flow_alignment")), 5),
            "fdir": [round(float(value), 5) for value in point.attribValue("fdir")],
            "mass": round(float(point.attribValue("mass")), 5),
            "crimp": round(float(point.attribValue("crimp")), 5),
            "fibre_tension": round(float(point.attribValue("fibre_tension")), 5),
            "stability": round(float(point.attribValue("stability")), 5),
            "bundle_degree": round(float(point.attribValue("bundle_degree")), 5),
            "lox": round(float(point.attribValue("lox")), 5),
        } for point in geometry.points()],
        "primitives": [{
            "kind": int(primitive.attribValue("kind")),
            "points": [vertex.point().number() for vertex in primitive.vertices()],
            "bond": round(float(primitive.attribValue("bond")), 5),
            "latched": int(primitive.attribValue("latched")),
            "tension": round(float(primitive.attribValue("tension")), 5),
            "contact_dwell": round(float(primitive.attribValue("contact_dwell")), 5),
            "bond_age": int(primitive.attribValue("bond_age")),
        } for primitive in geometry.prims()],
    }


def largest_bond_component_fraction(geometry: hou.Geometry, fibre_count: int) -> float:
    adjacency = {index: set() for index in range(fibre_count)}
    active_nodes: set[int] = set()
    for primitive in geometry.prims():
        if int(primitive.attribValue("kind")) != 2 or not int(primitive.attribValue("latched")):
            continue
        points = [vertex.point().number() for vertex in primitive.vertices()]
        if len(points) != 2:
            continue
        a, b = points
        adjacency[a].add(b)
        adjacency[b].add(a)
        active_nodes.update((a, b))
    largest = 0
    seen: set[int] = set()
    for root in active_nodes:
        if root in seen:
            continue
        stack = [root]
        size = 0
        seen.add(root)
        while stack:
            node = stack.pop()
            size += 1
            for neighbor in adjacency[node]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        largest = max(largest, size)
    return largest / max(1, fibre_count)


def empty_domain_fraction(geometry: hou.Geometry, fibre_count: int, width: float, height: float) -> float:
    gx, gy = 16, 24
    occupied: set[tuple[int, int]] = set()
    for point in geometry.points()[:fibre_count]:
        if float(point.attribValue("mass")) <= 0.05:
            continue
        x, y = point.position().x(), point.position().y()
        cx = min(gx - 1, max(0, int((x / width + 0.5) * gx)))
        cy = min(gy - 1, max(0, int((y / height + 0.5) * gy)))
        occupied.add((cx, cy))
    return 1.0 - len(occupied) / (gx * gy)


def run(experiment: dict, output_dir: Path) -> None:
    mode_name = str(experiment["mode"])
    if mode_name == "excitable-purse-string-zipper":
        parameters = {
            "edge_count": 64,
            "bank_half_width": 1.15,
            "wound_height": 11.5,
            "activator_decay": 0.34,
            "refractory_decay": 0.055,
            "wave_transfer": 0.82,
            "myosin_response": 0.58,
            "ratchet_rate": 0.18,
            "ratchet_heterogeneity": 0.0,
            "closure_gain": 0.66,
            "zip_capture": 1.38,
            "zip_rate": 0.085,
            "zip_front_boost": 0.0,
            "zipper_space_mode": 0,
            "tube_azimuth": 0.0,
            "tube_twist_turns": 0.0,
            **experiment.get("parameters", {}),
        }
        initial = initial_zipper_geometry(parameters)
    elif mode_name == "tug-zip-fasciculation":
        parameters = {
            "fibre_count": 128,
            "agent_count": 24,
            "domain_width": 8.0,
            "domain_height": 12.0,
            "candidate_radius": 1.42,
            "max_candidate_neighbors": 5,
            "agent_speed": 0.055,
            "wander_strength": 0.075,
            "adhesion_radius": 1.55,
            "traction_gain": 0.11,
            "pull_decay": 0.76,
            "uncrimp_rate": 0.075,
            "lox_deposit": 0.085,
            "lox_retention": 0.982,
            "dwell_rate": 0.15,
            "dwell_decay": 0.035,
            "bond_rate": 0.075,
            "bond_threshold": 0.42,
            "fibre_move_gain": 0.035,
            "flow_mode": 0,
            "flow_strength": 0.0,
            "flow_scale": 0.52,
            "flow_time_rate": 0.025,
            "flow_center_pull": 0.18,
            "flow_recruit_radius": 0.0,
            "flow_recruit_gain": 0.0,
            **experiment.get("parameters", {}),
        }
        initial = initial_fascicle_geometry(parameters, int(experiment.get("seed", 9137)))
    else:
        raise ValueError(mode_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / "cache"
    cache_dir.mkdir(exist_ok=True)
    input_cache = output_dir / "initial.bgeo.sc"
    initial.saveToFile(str(input_cache))
    network = hou.node("/obj").createNode("geo", "scar_mechanics_vex_authoritative")
    for child in network.children():
        child.destroy()
    source = network.createNode("file", "previous_vex_state")
    update = network.createNode("attribwrangle", "advance_state_one_frame")
    update.setInput(0, source)
    vex_source = VEX_PATH.read_text(encoding="utf-8")
    values = {"mode": MODE_IDS[mode_name], "frame": int(experiment["frame_start"]), "frame_end": int(experiment["frame_end"]), **parameters}
    configure_wrangle(update, values, vex_source)
    source.parm("file").set(str(input_cache))
    start, end = int(experiment["frame_start"]), int(experiment["frame_end"])
    review = []
    cache_hashes = {}
    vex_errors = []
    cooked = None
    final_cache = None
    peak_excited_fraction = 0.0
    for frame in range(start, end + 1):
        update.parm("frame").set(frame)
        source.parm("file").set(str(input_cache if frame == start else final_cache))
        source.parm("reload").pressButton()
        update.cook(force=True)
        errors = list(update.errors())
        if errors:
            vex_errors.extend([f"frame {frame}: {error}" for error in errors])
            raise RuntimeError("; ".join(vex_errors))
        cooked = update.geometry().freeze()
        final_cache = cache_dir / f"vex-state.{frame:04d}.bgeo.sc"
        cooked.saveToFile(str(final_cache))
        cache_hashes[final_cache.name] = hashlib.sha256(final_cache.read_bytes()).hexdigest()
        record = review_record(cooked, frame)
        review.append(record)
        if mode_name == "excitable-purse-string-zipper" and frame > start + 8:
            excited = sum(point["activator"] > 0.55 for point in record["points"]) / len(record["points"])
            peak_excited_fraction = max(peak_excited_fraction, excited)
    assert cooked is not None and final_cache is not None
    input_cache.unlink(missing_ok=True)
    source.parm("file").set(str(final_cache))
    source.parm("reload").pressButton()
    source.setDisplayFlag(True)
    source.setRenderFlag(True)
    update.setDisplayFlag(False)
    update.setRenderFlag(False)
    network.layoutChildren()
    hip_path = output_dir / "scar-mechanics.hiplc"
    hou.hipFile.save(str(hip_path))
    reloaded = hou.Geometry()
    reloaded.loadFromFile(str(final_cache))
    common_metrics = {
        "experiment_id": experiment["id"], "mode": mode_name, "mutation_branch": MODE_IDS[mode_name],
        "engine": "houdini-vex-authoritative", "state_authority": "vex-geometry",
        "frame_start": start, "frame_end": end, "vex_cook_count": end - start + 1,
        "cache_count": len(cache_hashes), "cache_sha256": cache_hashes, "vex_errors": vex_errors,
        "point_count": len(reloaded.points()), "primitive_count": len(reloaded.prims()),
        "state_sha256": state_digest(reloaded), "state_digest_source": "reloaded-display-cache",
        "display_cache_sha256": cache_hashes[final_cache.name],
        "hip_sha256": hashlib.sha256(hip_path.read_bytes()).hexdigest(),
        "vex_sha256": hashlib.sha256(vex_source.encode("utf-8")).hexdigest(),
        "review": review,
    }
    if mode_name == "excitable-purse-string-zipper":
        edge_count = int(parameters["edge_count"])
        gaps = []
        antipodal_errors = []
        for index in range(edge_count):
            left = reloaded.point(index).position()
            right = reloaded.point(edge_count + index).position()
            left_seam = 0.10 * math.sin(left.y() * 0.78) + 0.035 * math.sin(left.y() * 2.17)
            right_seam = 0.10 * math.sin(right.y() * 0.78) + 0.035 * math.sin(right.y() * 2.17)
            gaps.append(abs(
                float(reloaded.point(edge_count + index).attribValue("unwrapped_x"))
                - float(reloaded.point(index).attribValue("unwrapped_x"))
            ))
            left_angle = math.atan2(left.z(), left.x() - left_seam)
            right_angle = math.atan2(right.z(), right.x() - right_seam)
            antipodal_errors.append(abs(math.atan2(
                math.sin(right_angle - left_angle - math.pi),
                math.cos(right_angle - left_angle - math.pi),
            )))
        z_values = [point.position().z() for point in reloaded.points()]
        bank_angles = []
        for index in range(edge_count):
            point = reloaded.point(edge_count + index)
            position = point.position()
            seam = 0.10 * math.sin(position.y() * 0.78) + 0.035 * math.sin(position.y() * 2.17)
            bank_angles.append(math.atan2(position.z(), position.x() - seam))
        winding = 0.0
        for previous, current in zip(bank_angles, bank_angles[1:]):
            winding += math.atan2(math.sin(current - previous), math.cos(current - previous))
        latched = [primitive for primitive in reloaded.prims() if int(primitive.attribValue("kind")) == 1 and int(primitive.attribValue("latched"))]
        latched_indices = [int(primitive.vertices()[0].point().attribValue("edge_index")) for primitive in latched]
        zipper_span = (max(latched_indices) - min(latched_indices)) / max(1, edge_count - 1) if len(latched_indices) > 1 else 0.0
        common_metrics.update({
            "traveling_pulse_events": int(reloaded.attribValue("pulse_events")),
            "zip_events": int(reloaded.attribValue("zip_events")),
            "peak_excited_fraction_after_initialization": peak_excited_fraction,
            "ratchet_total": sum(float(point.attribValue("ratchet")) for point in reloaded.points()),
            "closure_fraction": 1.0 - sum(gaps) / (len(gaps) * 2.0 * float(parameters["bank_half_width"])),
            "radial_closure_fraction": 1.0 - sum(
                float(reloaded.point(index).attribValue("tube_radius"))
                + float(reloaded.point(edge_count + index).attribValue("tube_radius"))
                for index in range(edge_count)
            ) / (edge_count * 2.0 * float(parameters["bank_half_width"])),
            "latched_zipper_count": len(latched), "zipper_front_span": zipper_span,
            "zipper_space_mode": int(parameters["zipper_space_mode"]),
            "tube_azimuth": float(parameters["tube_azimuth"]),
            "tube_twist_turns": float(parameters["tube_twist_turns"]),
            "helix_winding_turns": abs(winding) / math.tau,
            "z_extent": max(z_values) - min(z_values),
            "axis_antipodal_error_max": max(antipodal_errors),
            "kinetic_state_sha256": kinetic_state_digest(reloaded),
        })
    else:
        fibre_count = int(parameters["fibre_count"])
        candidate_bonds = [primitive for primitive in reloaded.prims() if int(primitive.attribValue("kind")) == 2]
        latched_bonds = [primitive for primitive in candidate_bonds if int(primitive.attribValue("latched"))]
        bond_events = int(reloaded.attribValue("bond_events"))
        common_metrics.update({
            "candidate_bond_count": len(candidate_bonds),
            "candidate_bond_count_initial": len([primitive for primitive in initial.prims() if int(primitive.attribValue("kind")) == 2]),
            "tug_events": int(reloaded.attribValue("tug_events")),
            "uncrimped_fibre_count": sum(float(point.attribValue("crimp")) < 0.5 for point in reloaded.points()[:fibre_count]),
            "latched_bond_count": len(latched_bonds),
            "largest_bond_component_fraction": largest_bond_component_fraction(reloaded, fibre_count),
            "late_bond_event_fraction": int(reloaded.attribValue("late_bond_events")) / max(1, bond_events),
            "bond_events": bond_events,
            "empty_domain_fraction": empty_domain_fraction(reloaded, fibre_count, float(parameters["domain_width"]), float(parameters["domain_height"])),
            "adhesion_phase_fraction": int(reloaded.attribValue("adhesion_samples")) / max(1, int(parameters["agent_count"]) * (end - start + 1)),
            "flow_alignment_mean": sum(
                float(point.attribValue("flow_alignment"))
                for point in reloaded.points()[fibre_count:fibre_count + int(parameters["agent_count"])]
            ) / max(1, int(parameters["agent_count"])),
            "flow_recruit_events": int(reloaded.attribValue("flow_recruit_events")),
        })
    metrics = common_metrics
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    experiment = json.loads(args.experiment.read_text(encoding="utf-8"))
    run(experiment, args.output.resolve())


if __name__ == "__main__":
    main()
