"""Build a reopenable Houdini Scar Tissue diagnostic from the reference behavior model."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import hou


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from houdini_ai.behavior_lab import config_from_experiment, simulate_scar_tissue_reference  # noqa: E402


MUTATION_IDS = {"saturation-repulsion": 0, "directional-scar": 1, "refractory-healing": 2, "directional-refractory": 3, "fibrotic-remodeling": 4, "wound-contractile-remodeling": 5, "purse-string-closure": 6, "collagen-crosslink-weave": 7, "keloid-signal-bloom": 8}


def initial_state_geometry(config: dict) -> hou.Geometry:
    """Create topology only; VEX initializes and evolves all simulation state."""
    geometry = hou.Geometry()
    geometry.addAttrib(hou.attribType.Point, "state_class", 0)
    geometry.addAttrib(hou.attribType.Point, "id", 0)
    geometry.addAttrib(hou.attribType.Point, "heading", 0.0)
    geometry.addAttrib(hou.attribType.Point, "v", (0.0, 0.0, 0.0))
    geometry.addAttrib(hou.attribType.Point, "scar_value", 0.0)
    geometry.addAttrib(hou.attribType.Point, "provisional_matrix", 0.0)
    geometry.addAttrib(hou.attribType.Point, "mature_collagen", 0.0)
    geometry.addAttrib(hou.attribType.Point, "wound_signal", 0.0)
    geometry.addAttrib(hou.attribType.Point, "tension_direction", (0.0, 0.0, 0.0))
    geometry.addAttrib(hou.attribType.Point, "scar_contraction", 0.0)
    geometry.addAttrib(hou.attribType.Point, "crosslink_density", 0.0)
    geometry.addAttrib(hou.attribType.Point, "fibrotic_signal", 0.0)
    geometry.addAttrib(hou.attribType.Point, "scar_direction", (0.0, 0.0, 0.0))
    geometry.addAttrib(hou.attribType.Point, "scar_idle", 0)
    geometry.addAttrib(hou.attribType.Point, "scar_state", 0)
    geometry.addAttrib(hou.attribType.Global, "behavior_frame", 0)
    geometry.addAttrib(hou.attribType.Global, "mutation_branch", -1)
    geometry.addAttrib(hou.attribType.Global, "branch_agent_updates", 0)
    geometry.addAttrib(hou.attribType.Global, "decayed_cells_total", 0)
    system = config["system"]
    count = int(system["agent_count"])
    gx, gy = int(system["grid_width"]), int(system["grid_height"])
    width, height = float(system["domain_width"]), float(system["domain_height"])
    for agent_id in range(count):
        point = geometry.createPoint()
        point.setAttribValue("state_class", 0)
        point.setAttribValue("id", agent_id)
    for cell in range(gx * gy):
        cx, cy = cell % gx, cell // gx
        point = geometry.createPoint()
        point.setPosition(((cx + 0.5) / gx * width - width * 0.5, (cy + 0.5) / gy * height - height * 0.5, -0.05))
        point.setAttribValue("state_class", 1)
        point.setAttribValue("id", cell)
    return geometry


def state_digest(geometry: hou.Geometry, agent_count: int) -> str:
    payload = []
    for point in geometry.points():
        position = tuple(round(float(value), 6) for value in point.position())
        direction = tuple(round(float(value), 6) for value in point.attribValue("scar_direction"))
        payload.append((
            position,
            round(float(point.attribValue("heading")), 6),
            round(float(point.attribValue("scar_value")), 6),
            direction,
            int(point.attribValue("scar_idle")),
            round(float(point.attribValue("provisional_matrix")), 6),
            round(float(point.attribValue("mature_collagen")), 6),
            round(float(point.attribValue("wound_signal")), 6),
            tuple(round(float(value), 6) for value in point.attribValue("tension_direction")),
            round(float(point.attribValue("scar_contraction")), 6),
            round(float(point.attribValue("crosslink_density")), 6),
            round(float(point.attribValue("fibrotic_signal")), 6),
        ))
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode("utf-8")).hexdigest()


def run_vex_authoritative(config: dict, output_dir: Path) -> None:
    """Advance cached Houdini geometry repeatedly; Python never evolves state."""
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / "cache"
    cache_dir.mkdir(exist_ok=True)
    hou.hipFile.clear(suppress_save_prompt=True)
    network = hou.node("/obj").createNode("geo", "scar_tissue_vex_authoritative")
    for child in network.children():
        child.destroy()
    source = network.createNode("file", "previous_vex_state")
    update = network.createNode("attribwrangle", "advance_state_one_frame")
    update.setInput(0, source)
    update.parm("class").set("detail")
    vex_source = (ROOT / "houdini/vex/scar_tissue_stateful.vfl").read_text(encoding="utf-8")
    update.parm("snippet").set(vex_source)
    system = config["system"]
    values = {
        "agent_count": int(system["agent_count"]), "grid_width": int(system["grid_width"]),
        "grid_height": int(system["grid_height"]), "current_frame": int(config["frame_start"]),
        "start_frame": int(config["frame_start"]), "mutation": MUTATION_IDS[system["mutation"]],
        "seed": int(config["seed"]), "refractory_frames": 4, "fps": float(config["fps"]),
        "domain_width": float(system["domain_width"]), "domain_height": float(system["domain_height"]),
        "scar_decay": float(system["decay"]), "healing_decay": min(float(system["decay"]), 0.92),
        "deposit_amount": float(system["deposit"]), "attraction_threshold": float(system["attraction_threshold"]),
        "saturation_threshold": float(system["saturation_threshold"]), "field_strength": float(system["field_strength"]),
        "wander_strength": 0.025, "speed": float(system["speed"]),
        "provisional_retention": float(system.get("provisional_retention", 0.985)),
        "collagen_maturation": float(system.get("collagen_maturation", 0.035)),
        "collagen_retention": float(system.get("collagen_retention", 0.9995)),
        "wound_width": float(system.get("wound_width", 1.15)),
        "wound_amplitude": float(system.get("wound_amplitude", 0.62)),
        "wound_attraction": float(system.get("wound_attraction", 0.24)),
        "wound_deposit_gain": float(system.get("wound_deposit_gain", 1.5)),
        "peripheral_deposit": float(system.get("peripheral_deposit", 0.22)),
        "reinforcement_gain": float(system.get("reinforcement_gain", 0.8)),
        "tension_alignment": float(system.get("tension_alignment", 0.32)),
        "contraction_rate": float(system.get("contraction_rate", 0.0012)),
        "contraction_retention": float(system.get("contraction_retention", 0.9985)),
        "weave_angle": float(system.get("weave_angle", 0.68)),
        "crosslink_gain": float(system.get("crosslink_gain", 0.85)),
        "crosslink_retention": float(system.get("crosslink_retention", 0.999)),
        "signal_retention": float(system.get("signal_retention", 0.985)),
        "signal_gain": float(system.get("signal_gain", 0.34)),
        "signal_feedback": float(system.get("signal_feedback", 0.085)),
        "signal_diffusion": float(system.get("signal_diffusion", 0.12)),
        "signal_clearance": float(system.get("signal_clearance", 0.018)),
    }
    group = update.parmTemplateGroup()
    for name, value in values.items():
        template = hou.IntParmTemplate(name, name, 1, default_value=(value,)) if isinstance(value, int) else hou.FloatParmTemplate(name, name, 1, default_value=(value,))
        group.append(template)
    update.setParmTemplateGroup(group)
    for name, value in values.items():
        update.parm(name).set(value)

    input_cache = cache_dir / "vex-state-input.bgeo.sc"
    initial_state_geometry(config).saveToFile(str(input_cache))
    source.parm("file").set(str(input_cache))
    cache_hashes = {}
    vex_errors = []
    checkpoints = []
    review = []
    final_cache = None
    cooked = None
    saturated_ever = set()
    abandoned_ever = set()
    returned_ever = set()
    occupied_last = set()
    directional_alignment_samples = 0
    start, end = int(config["frame_start"]), int(config["frame_end"])
    for frame in range(start, end + 1):
        source.parm("reload").pressButton()
        update.parm("current_frame").set(frame)
        try:
            update.cook(force=True)
        except hou.OperationFailed as exc:
            node_errors = list(update.errors())
            raise RuntimeError(f"Stateful VEX cook failed at frame {frame}: {'; '.join(node_errors) or exc}") from exc
        errors = list(update.errors())
        vex_errors.extend(errors)
        if errors:
            raise RuntimeError(f"Stateful VEX cook failed at frame {frame}: {'; '.join(errors)}")
        cooked = update.geometry()
        if cooked is None:
            raise RuntimeError(f"Stateful VEX produced no geometry at frame {frame}")
        final_cache = cache_dir / f"vex-state.{frame:04d}.bgeo.sc"
        cooked.saveToFile(str(final_cache))
        cache_hashes[final_cache.name] = hashlib.sha256(final_cache.read_bytes()).hexdigest()
        agents = cooked.points()[: int(system["agent_count"])]
        xs, ys = [float(point.position()[0]) for point in agents], [float(point.position()[1]) for point in agents]
        field = cooked.points()[int(system["agent_count"]):]
        field_values = [float(point.attribValue("scar_value")) for point in field]
        occupied = {index for index, point in enumerate(field) if int(point.attribValue("scar_idle")) == 0}
        saturated_ever.update(index for index, value in enumerate(field_values) if value >= float(system["saturation_threshold"]))
        returned_ever.update(index for index in saturated_ever if field_values[index] < float(system["attraction_threshold"]))
        abandoned_ever.update(index for index in occupied_last - occupied if field_values[index] >= float(system["attraction_threshold"]))
        occupied_last = occupied
        for point in agents:
            scar = float(point.attribValue("scar_value"))
            direction = hou.Vector3(point.attribValue("scar_direction"))
            velocity = hou.Vector3(point.attribValue("v"))
            if scar >= float(system["attraction_threshold"]) and direction.length() > 1e-6 and velocity.length() > 1e-6:
                directional_alignment_samples += int(abs(direction.normalized().dot(velocity.normalized())) >= 0.7)
        checkpoints.append({
            "frame": frame, "bounds": [min(xs), min(ys), max(xs), max(ys)],
            "field_mean": sum(float(point.attribValue("scar_value")) for point in field) / len(field),
            "field_max": max(float(point.attribValue("scar_value")) for point in field),
            "reinforced_cells": sum(float(point.attribValue("scar_value")) >= float(system["attraction_threshold"]) for point in field),
            "saturated_cells": sum(float(point.attribValue("scar_value")) >= float(system["saturation_threshold"]) for point in field),
            "abandoned_cells": len(abandoned_ever), "returned_cells": len(returned_ever),
            "provisional_matrix_total": sum(float(point.attribValue("provisional_matrix")) for point in field),
            "mature_collagen_total": sum(float(point.attribValue("mature_collagen")) for point in field),
            "contraction_total": sum(float(point.attribValue("scar_contraction")) for point in field),
            "crosslink_total": sum(float(point.attribValue("crosslink_density")) for point in field),
            "fibrotic_signal_total": sum(float(point.attribValue("fibrotic_signal")) for point in field),
        })
        review.append({
            "frame": frame,
            "agents": [
                [round(float(point.position()[0]), 5), round(float(point.position()[1]), 5), round(float(point.attribValue("heading")), 5)]
                for point in agents
            ],
            "field": [round(float(point.attribValue("scar_value")), 5) for point in field],
            "direction_x": [round(float(point.attribValue("scar_direction")[0]), 5) for point in field],
            "direction_y": [round(float(point.attribValue("scar_direction")[1]), 5) for point in field],
            "idle": [int(point.attribValue("scar_idle")) for point in field],
            "provisional_matrix": [round(float(point.attribValue("provisional_matrix")), 5) for point in field],
            "mature_collagen": [round(float(point.attribValue("mature_collagen")), 5) for point in field],
            "wound_signal": [round(float(point.attribValue("wound_signal")), 5) for point in field],
            "tension_x": [round(float(point.attribValue("tension_direction")[0]), 5) for point in field],
            "tension_y": [round(float(point.attribValue("tension_direction")[1]), 5) for point in field],
            "contraction": [round(float(point.attribValue("scar_contraction")), 5) for point in field],
            "crosslink": [round(float(point.attribValue("crosslink_density")), 5) for point in field],
            "fibrotic_signal": [round(float(point.attribValue("fibrotic_signal")), 5) for point in field],
        })
        source.parm("file").set(str(final_cache))

    assert cooked is not None and final_cache is not None
    input_cache.unlink(missing_ok=True)
    source.parm("file").set(str(final_cache))
    source.setDisplayFlag(True)
    source.setRenderFlag(True)
    update.setDisplayFlag(False)
    update.setRenderFlag(False)
    network.layoutChildren()
    hip_path = output_dir / "scar-tissue.hiplc"
    hou.hipFile.save(str(hip_path))
    count = int(system["agent_count"])
    reloaded = hou.Geometry()
    reloaded.loadFromFile(str(final_cache))
    cooked = reloaded
    field_points = cooked.points()[count:]
    agent_mean_turns = []
    agent_signed_turn_rates = []
    for agent_index in range(count):
        headings = [float(record["agents"][agent_index][2]) for record in review]
        signed_turns = [math.atan2(math.sin(current - previous), math.cos(current - previous)) for previous, current in zip(headings, headings[1:])]
        agent_mean_turns.append(sum(abs(value) for value in signed_turns) / max(1, len(signed_turns)))
        agent_signed_turn_rates.append(abs(sum(signed_turns)) / max(1, len(signed_turns)))
    gx, gy = int(system["grid_width"]), int(system["grid_height"])
    fibrotic_signals = [float(point.attribValue("fibrotic_signal")) for point in field_points]
    fibrotic_foci = 0
    for cy in range(gy):
        for cx in range(gx):
            value = fibrotic_signals[cy * gx + cx]
            neighbors = [
                fibrotic_signals[((cy + dy) % gy) * gx + ((cx + dx) % gx)]
                for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy
            ]
            if value > 0.10 and value >= max(neighbors) and value > min(neighbors):
                fibrotic_foci += 1
    metrics = {
        "experiment_id": config["id"], "seed": config["seed"], "mutation": system["mutation"],
        "agent_count": count, "field_point_count": len(field_points), "grid": [system["grid_width"], system["grid_height"]],
        "frame_start": start, "frame_end": end, "engine": "houdini-vex-authoritative",
        "state_authority": "vex-geometry", "reference_comparison": "not-run",
        "state_digest_fields": ["P", "heading", "scar_value", "scar_direction", "scar_idle", "provisional_matrix", "mature_collagen", "wound_signal", "tension_direction", "scar_contraction", "crosslink_density", "fibrotic_signal"],
        "verification_scope": "all frames persisted from prior cooked VEX geometry",
        "state_sha256": state_digest(cooked, count), "state_digest_source": "reloaded-display-cache",
        "display_cache_sha256": cache_hashes[final_cache.name],
        "cache_sha256": cache_hashes, "hip_sha256": hashlib.sha256(hip_path.read_bytes()).hexdigest(),
        "vex_sha256": hashlib.sha256(vex_source.encode("utf-8")).hexdigest(), "vex_cook_count": end - start + 1,
        "vex_errors": vex_errors, "mutation_branch": int(cooked.attribValue("mutation_branch")),
        "final_frame_agent_updates": int(cooked.attribValue("branch_agent_updates")),
        "cumulative_agent_updates": count * (end - start + 1),
        "branch_agent_updates": int(cooked.attribValue("branch_agent_updates")),
        "deposited_cells": sum(float(point.attribValue("scar_value")) > 0 for point in field_points),
        "oriented_cells": sum(hou.Vector3(point.attribValue("scar_direction")).length() > 1e-6 for point in field_points),
        "idle_cells": sum(int(point.attribValue("scar_idle")) > 0 for point in field_points),
        "cumulative_decayed_cell_updates": int(cooked.attribValue("decayed_cells_total")),
        "decayed_cells": int(cooked.attribValue("decayed_cells_total")),
        "abandoned_cells": len(abandoned_ever), "returned_cells": len(returned_ever),
        "directional_alignment_samples": directional_alignment_samples, "checkpoints": checkpoints,
        "provisional_matrix_cells": sum(float(point.attribValue("provisional_matrix")) > 1e-6 for point in field_points),
        "mature_collagen_cells": sum(float(point.attribValue("mature_collagen")) > 1e-6 for point in field_points),
        "provisional_matrix_total": sum(float(point.attribValue("provisional_matrix")) for point in field_points),
        "mature_collagen_total": sum(float(point.attribValue("mature_collagen")) for point in field_points),
        "collagen_retention_ratio": float(values["collagen_retention"]),
        "wound_cells": sum(float(point.attribValue("wound_signal")) >= 0.45 for point in field_points),
        "wound_cell_fraction": sum(float(point.attribValue("wound_signal")) >= 0.45 for point in field_points) / len(field_points),
        "wound_collagen_concentration_ratio": (
            sum(float(point.attribValue("mature_collagen")) for point in field_points if float(point.attribValue("wound_signal")) >= 0.45)
            / max(1e-12, sum(float(point.attribValue("mature_collagen")) for point in field_points))
        ),
        "tension_aligned_cells": sum(
            float(point.attribValue("mature_collagen")) >= float(system["attraction_threshold"])
            and hou.Vector3(point.attribValue("scar_direction")).length() > 1e-6
            and hou.Vector3(point.attribValue("tension_direction")).length() > 1e-6
            and abs(hou.Vector3(point.attribValue("scar_direction")).normalized().dot(hou.Vector3(point.attribValue("tension_direction")).normalized())) >= 0.7
            for point in field_points
        ),
        "contraction_cells": sum(float(point.attribValue("scar_contraction")) > 1e-6 for point in field_points),
        "contraction_total": sum(float(point.attribValue("scar_contraction")) for point in field_points),
        "mature_collagen_max": max(float(point.attribValue("mature_collagen")) for point in field_points),
        "relief_potential_max": max(float(point.attribValue("mature_collagen")) + 0.8 * float(point.attribValue("scar_contraction")) for point in field_points),
        "wound_edge_cells": sum(0.16 <= float(point.attribValue("wound_signal")) <= 0.62 for point in field_points),
        "wound_edge_fraction": sum(0.16 <= float(point.attribValue("wound_signal")) <= 0.62 for point in field_points) / len(field_points),
        "edge_collagen_concentration_ratio": (
            sum(float(point.attribValue("mature_collagen")) for point in field_points if 0.16 <= float(point.attribValue("wound_signal")) <= 0.62)
            / max(1e-12, sum(float(point.attribValue("mature_collagen")) for point in field_points))
        ),
        "bridge_cells": sum(
            float(point.attribValue("wound_signal")) > 0.62
            and float(point.attribValue("mature_collagen")) >= float(system["attraction_threshold"])
            for point in field_points
        ),
        "crosslink_cells": sum(float(point.attribValue("crosslink_density")) > 1e-6 for point in field_points),
        "crosslink_total": sum(float(point.attribValue("crosslink_density")) for point in field_points),
        "crosslink_max": max(float(point.attribValue("crosslink_density")) for point in field_points),
        "crosslinked_relief_max": max(
            float(point.attribValue("mature_collagen")) + 1.2 * float(point.attribValue("crosslink_density"))
            for point in field_points
        ),
        "fibrotic_signal_cells": sum(value > 0.02 for value in fibrotic_signals),
        "fibrotic_signal_total": sum(fibrotic_signals),
        "fibrotic_signal_max": max(fibrotic_signals),
        "fibrotic_foci": fibrotic_foci,
        "signal_weighted_collagen": sum(
            signal * float(point.attribValue("mature_collagen"))
            for signal, point in zip(fibrotic_signals, field_points)
        ),
        "agent_mean_turn_spread": max(agent_mean_turns) - min(agent_mean_turns),
        "tight_turning_agent_fraction": sum(value >= 0.24 for value in agent_mean_turns) / count,
        "looping_agent_fraction": sum(value >= 0.12 for value in agent_signed_turn_rates) / count,
        "review": review,
    }
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def geometry_from_record(record: dict, config: dict) -> hou.Geometry:
    geometry = hou.Geometry()
    geometry.addAttrib(hou.attribType.Point, "id", 0)
    geometry.addAttrib(hou.attribType.Point, "heading", 0.0)
    geometry.addAttrib(hou.attribType.Point, "pscale", 0.025)
    geometry.addAttrib(hou.attribType.Point, "v", (0.0, 0.0, 0.0))
    geometry.addAttrib(hou.attribType.Point, "scar_gradient", (0.0, 0.0, 0.0))
    geometry.addAttrib(hou.attribType.Point, "scar_direction", (0.0, 0.0, 0.0))
    geometry.addAttrib(hou.attribType.Point, "scar_value", 0.0)
    geometry.addAttrib(hou.attribType.Point, "scar_idle", 0)
    geometry.addAttrib(hou.attribType.Point, "speed", 0.0)
    geometry.addAttrib(hou.attribType.Point, "deposit", 0.0)
    gx, gy = config["system"]["grid_width"], config["system"]["grid_height"]
    width, height = config["system"]["domain_width"], config["system"]["domain_height"]
    for agent_id, (x, y, heading) in enumerate(record["agents"]):
        point = geometry.createPoint()
        point.setPosition((x, y, 0.0))
        point.setAttribValue("id", agent_id)
        point.setAttribValue("heading", heading)
        velocity = (math.cos(heading) * config["system"]["speed"], math.sin(heading) * config["system"]["speed"], 0.0)
        point.setAttribValue("v", velocity)
        cx = min(gx - 1, int(((x / width) + 0.5) % 1.0 * gx))
        cy = min(gy - 1, int(((y / height) + 0.5) % 1.0 * gy))
        field = record["field"]
        direction_x = record.get("direction_x", [0.0] * len(field))
        direction_y = record.get("direction_y", [0.0] * len(field))
        idle = record.get("idle", [0] * len(field))
        sample = lambda dx, dy: field[((cy + dy) % gy) * gx + ((cx + dx) % gx)]
        gradient = (sample(1, 0) - sample(-1, 0), sample(0, 1) - sample(0, -1), 0.0)
        point.setAttribValue("scar_gradient", gradient)
        sampled_direction = record.get("agent_direction", [])[agent_id] if record.get("agent_direction") else (direction_x[cy * gx + cx], direction_y[cy * gx + cx])
        point.setAttribValue("scar_direction", (sampled_direction[0], sampled_direction[1], 0.0))
        point.setAttribValue("scar_value", field[cy * gx + cx])
        sampled_idle = record.get("agent_idle", [])[agent_id] if record.get("agent_idle") else idle[cy * gx + cx]
        point.setAttribValue("scar_idle", sampled_idle)
    geometry.addAttrib(hou.attribType.Global, "behavior_frame", int(record["frame"]))
    geometry.addAttrib(hou.attribType.Global, "mutation", str(config["system"]["mutation"]))
    return geometry


def run(experiment_path: Path, output_dir: Path) -> None:
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    config = config_from_experiment(experiment)
    metrics = simulate_scar_tissue_reference(config)
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / "cache"
    cache_dir.mkdir(exist_ok=True)

    hou.hipFile.clear(suppress_save_prompt=True)
    network = hou.node("/obj").createNode("geo", "scar_tissue_behavior")
    for child in network.children():
        child.destroy()
    source = network.createNode("file", "diagnostic_cache")
    update = network.createNode("attribwrangle", "scar_tissue_vex_update")
    update.setInput(0, source)
    vex_source = (ROOT / "houdini/vex/lib/agent_core.vfl").read_text(encoding="utf-8")
    vex_source += "\n" + (ROOT / "houdini/vex/scar_tissue_agents.vfl").read_text(encoding="utf-8")
    update.parm("snippet").set(vex_source)
    mutation = {"saturation-repulsion": 0, "directional-scar": 1, "refractory-healing": 2}[config["system"]["mutation"]]
    values = {
        "fps": config["fps"], "current_frame": config["frame_start"], "mutation": mutation,
        "attraction_threshold": config["system"]["attraction_threshold"],
        "saturation_threshold": config["system"]["saturation_threshold"], "refractory_frames": 12,
        "wander_strength": 0.025, "field_strength": config["system"]["field_strength"],
        "max_speed": config["system"]["speed"] * 1.4, "drag": 0.82,
        "domain_width": config["system"]["domain_width"], "domain_height": config["system"]["domain_height"],
        "deposit_amount": config["system"]["deposit"],
    }
    group = update.parmTemplateGroup()
    for name, value in values.items():
        template = hou.IntParmTemplate(name, name, 1, default_value=(value,)) if isinstance(value, int) else hou.FloatParmTemplate(name, name, 1, default_value=(value,))
        group.append(template)
    update.setParmTemplateGroup(group)
    cache_hashes = {}
    final_cache = None
    vex_cook_count = 0
    vex_displaced_points = 0
    vex_directional_points = 0
    vex_idle_points = 0
    vex_idle_samples = 0
    vex_errors = []
    input_path = cache_dir / "vex-input.bgeo.sc"
    for record in metrics["review"]:
        geometry_from_record(record, config).saveToFile(str(input_path))
        source.parm("file").set(str(input_path))
        source.parm("reload").pressButton()
        update.parm("current_frame").set(record["frame"])
        update.cook(force=True)
        node_errors = list(update.errors())
        vex_errors.extend(node_errors)
        if node_errors:
            raise RuntimeError(f"VEX update failed at frame {record['frame']}: {'; '.join(node_errors)}")
        cooked = update.geometry()
        if cooked is None:
            raise RuntimeError(f"VEX update produced no geometry at frame {record['frame']}")
        source_positions = [tuple(point.position()) for point in geometry_from_record(record, config).points()]
        source_geometry = geometry_from_record(record, config)
        vex_directional_points += sum(
            1 for point in source_geometry.points()
            if point.attribValue("scar_value") >= config["system"]["attraction_threshold"]
            and hou.Vector3(point.attribValue("scar_direction")).length() > 1e-6
        )
        vex_idle_points += sum(1 for point in source_geometry.points() if point.attribValue("scar_idle") > 0)
        vex_idle_samples += len(source_geometry.points())
        cooked_positions = [tuple(point.position()) for point in cooked.points()]
        vex_displaced_points += sum(
            1 for before, after in zip(source_positions, cooked_positions)
            if any(abs(a - b) > 1e-9 for a, b in zip(before, after))
        )
        path = cache_dir / f"state.{record['frame']:04d}.bgeo.sc"
        cooked.saveToFile(str(path))
        cache_hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        final_cache = path
        vex_cook_count += 1
    input_path.unlink(missing_ok=True)
    source.parm("file").set(str(final_cache))
    source.setDisplayFlag(True)
    source.setRenderFlag(True)
    update.setDisplayFlag(False)
    update.setRenderFlag(False)
    network.addSpareParmTuple(hou.StringParmTemplate("experiment_id", "Experiment ID", 1, default_value=(config["id"],)))
    network.addSpareParmTuple(hou.StringParmTemplate("mutation", "Mutation", 1, default_value=(config["system"]["mutation"],)))
    network.layoutChildren()
    hip_path = output_dir / "scar-tissue.hiplc"
    hou.hipFile.save(str(hip_path))

    metrics["cache_sha256"] = cache_hashes
    metrics["reference_state_sha256"] = metrics["state_sha256"]
    metrics["display_cache_sha256"] = cache_hashes[final_cache.name]
    metrics["verification_scope"] = "base mutation checkpoint agent-wrangle smoke probe"
    metrics["hip_sha256"] = hashlib.sha256(hip_path.read_bytes()).hexdigest()
    metrics["engine"] = "houdini-vex-hybrid"
    metrics["vex_sha256"] = hashlib.sha256(vex_source.encode("utf-8")).hexdigest()
    metrics["vex_cook_count"] = vex_cook_count
    metrics["vex_errors"] = vex_errors
    metrics["vex_displaced_points"] = vex_displaced_points
    metrics["vex_directional_points"] = vex_directional_points
    metrics["vex_idle_points"] = vex_idle_points
    metrics["vex_idle_samples"] = vex_idle_samples
    metrics["vex_idle_source"] = "reference-agent-cell"
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"experiment: {config['id']}")
    print(f"mutation: {config['system']['mutation']}")
    print(f"frames: {config['frame_start']}-{config['frame_end']}")
    print(f"hip: {hip_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--engine", choices=("reference-hybrid", "vex-authoritative"), default="reference-hybrid")
    args = parser.parse_args()
    if args.engine == "vex-authoritative":
        experiment = json.loads(args.experiment.resolve().read_text(encoding="utf-8"))
        run_vex_authoritative(config_from_experiment(experiment), args.output.resolve())
    else:
        run(args.experiment.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
