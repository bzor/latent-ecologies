from __future__ import annotations

import hashlib
import json
import math
import random
from pathlib import Path
from typing import Any, Mapping

MUTATIONS = {"saturation-repulsion", "directional-scar", "refractory-healing", "directional-refractory"}


def config_from_experiment(experiment: Mapping[str, Any]) -> dict[str, Any]:
    parameters = dict(experiment["parameters"])
    return {
        "id": experiment["id"],
        "seed": parameters.pop("seed"),
        "frame_start": parameters.pop("frame_start"),
        "frame_end": parameters.pop("frame_end"),
        "fps": parameters.pop("fps"),
        "system": parameters,
    }


def _fold(value: float, extent: float) -> float:
    return (value + extent * 0.5) % extent - extent * 0.5


def _cell(value: float, extent: float, count: int) -> int:
    return min(count - 1, int(((value / extent) + 0.5) % 1.0 * count))


def _digest(
    agents: list[list[float]],
    field: list[float],
    direction_x: list[float] | None = None,
    direction_y: list[float] | None = None,
    idle: list[int] | None = None,
) -> str:
    payload = {
        "agents": [[round(value, 6) for value in agent] for agent in agents],
        "field": [round(value, 6) for value in field],
        "direction_x": [round(value, 6) for value in (direction_x or [])],
        "direction_y": [round(value, 6) for value in (direction_y or [])],
        "idle": list(idle or []),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def simulate_scar_tissue_reference(config: Mapping[str, Any]) -> dict[str, Any]:
    """Run a cheap deterministic reference model used by tests and pre-Houdini scouting."""
    system = config["system"]
    mutation = str(system["mutation"])
    if mutation not in MUTATIONS:
        raise ValueError(f"unknown scar-tissue mutation: {mutation}")
    width, height = float(system["domain_width"]), float(system["domain_height"])
    gx, gy = int(system["grid_width"]), int(system["grid_height"])
    count = int(system["agent_count"])
    fps = float(config["fps"])
    rng = random.Random(int(config["seed"]))
    agents = []
    for agent_id in range(count):
        band = (agent_id % 3 - 1) * width * 0.18
        x = _fold(band + rng.uniform(-width * 0.14, width * 0.14), width)
        y = rng.uniform(-height * 0.48, height * 0.48)
        heading = math.pi * 0.5 + rng.uniform(-0.55, 0.55)
        agents.append([x, y, heading])

    field = [0.0] * (gx * gy)
    direction_x = [0.0] * len(field)
    direction_y = [0.0] * len(field)
    idle = [0] * len(field)
    saturated_ever: set[int] = set()
    occupied_last: set[int] = set()
    abandoned_ever: set[int] = set()
    regrown_ever: set[int] = set()
    checkpoints = []
    review = []
    start, end = int(config["frame_start"]), int(config["frame_end"])
    checkpoint_interval = max(1, round((end - start) / 5))
    speed = float(system["speed"])
    deposit = float(system["deposit"])
    decay = float(system["decay"])
    attraction = float(system["attraction_threshold"])
    saturation = float(system["saturation_threshold"])
    strength = float(system["field_strength"])

    def index(x: int, y: int) -> int:
        return (y % gy) * gx + (x % gx)

    for frame in range(start, end + 1):
        occupied: set[int] = set()
        local_values = []
        agent_direction = []
        agent_idle = []
        for agent_id, agent in enumerate(agents):
            x, y, heading = agent
            cx, cy = _cell(x, width, gx), _cell(y, height, gy)
            center_index = index(cx, cy)
            center = field[center_index]
            agent_direction.append([direction_x[center_index], direction_y[center_index]])
            agent_idle.append(idle[center_index])
            grad_x = field[index(cx + 1, cy)] - field[index(cx - 1, cy)]
            grad_y = field[index(cx, cy + 1)] - field[index(cx, cy - 1)]
            base = math.sin(y * 0.37 + frame * 0.021 + agent_id * 0.017) * 0.42
            target = math.pi * 0.5 + base
            profile = random.Random(int(config["seed"]) + agent_id * 7919).random()
            movement_phase = (frame + int(profile * 91.0)) % 120
            if mutation == "saturation-repulsion":
                sign = -1.0 if center >= saturation else 1.0
                target += math.atan2(grad_y * sign, grad_x * sign) * strength * min(1.0, center + 0.1)
            elif mutation in {"directional-scar", "directional-refractory"}:
                if center > attraction and abs(direction_x[center_index]) + abs(direction_y[center_index]) > 1e-6 and (
                    mutation != "directional-refractory" or movement_phase < 28.0 + 36.0 * profile
                ):
                    target = math.atan2(direction_y[center_index], direction_x[center_index])
                target += math.atan2(grad_y, grad_x) * 0.18
                if mutation == "directional-refractory" and 64 <= movement_phase < 88 and (
                    center >= saturation or (center >= attraction and idle[center_index] < 12)
                ):
                    handedness = -1.0 if random.Random(int(config["seed"]) + agent_id * 3571).random() < 0.5 else 1.0
                    target += handedness * math.pi * (0.18 + 0.30 * profile)
            else:
                refractory = center >= saturation or (center >= attraction and idle[center_index] < 12)
                sign = -1.0 if refractory else 1.0
                target += math.atan2(grad_y * sign, grad_x * sign) * strength * 0.72
            turn = math.atan2(math.sin(target - heading), math.cos(target - heading))
            turn_limit = 0.04 + 0.14 * profile if mutation == "directional-refractory" else 0.28
            heading += max(-turn_limit, min(turn_limit, turn))
            wander_profile = 0.45 + 1.35 * (1.0 - profile) if mutation == "directional-refractory" else 1.0
            heading += math.sin(agent_id * 12.9898 + frame * 0.071) * 0.025 * wander_profile
            x = _fold(x + math.cos(heading) * speed / fps, width)
            y = _fold(y + math.sin(heading) * speed / fps, height)
            agent[:] = [x, y, heading]
            cx, cy = _cell(x, width, gx), _cell(y, height, gy)
            cell_index = index(cx, cy)
            occupied.add(cell_index)
            old = field[cell_index]
            field[cell_index] = min(2.0, old + deposit)
            blend = deposit / max(field[cell_index], deposit)
            direction_x[cell_index] = direction_x[cell_index] * (1.0 - blend) + math.cos(heading) * blend
            direction_y[cell_index] = direction_y[cell_index] * (1.0 - blend) + math.sin(heading) * blend
            local_values.append(field[cell_index])

        for cell_index, value in enumerate(field):
            idle[cell_index] = 0 if cell_index in occupied else idle[cell_index] + 1
            effective_decay = decay
            if mutation in {"refractory-healing", "directional-refractory"} and idle[cell_index] > 8:
                effective_decay = min(effective_decay, 0.96)
            field[cell_index] = value * effective_decay
            direction_x[cell_index] *= effective_decay
            direction_y[cell_index] *= effective_decay
            if value >= saturation:
                saturated_ever.add(cell_index)
            if cell_index in saturated_ever and value < saturation:
                regrown_ever.add(cell_index)
        abandoned_ever.update(cell for cell in occupied_last - occupied if field[cell] >= attraction)
        occupied_last = occupied

        if frame == start or frame == end or (frame - start) % checkpoint_interval == 0:
            xs, ys = [agent[0] for agent in agents], [agent[1] for agent in agents]
            checkpoints.append(
                {
                    "frame": frame,
                    "bounds": [min(xs), min(ys), max(xs), max(ys)],
                    "field_mean": sum(field) / len(field),
                    "field_max": max(field),
                    "reinforced_cells": sum(value >= attraction for value in field),
                    "saturated_cells": sum(value >= saturation for value in field),
                    "abandoned_cells": len(abandoned_ever),
                    "regrown_cells": len(regrown_ever),
                    "mean_local_field": sum(local_values) / max(1, len(local_values)),
                }
            )
            review.append(
                {
                    "frame": frame,
                    "agents": [[round(value, 5) for value in agent] for agent in agents],
                    "field": [round(value, 5) for value in field],
                    "direction_x": [round(value, 5) for value in direction_x],
                    "direction_y": [round(value, 5) for value in direction_y],
                    "idle": list(idle),
                    "agent_direction": [[round(value, 5) for value in direction] for direction in agent_direction],
                    "agent_idle": list(agent_idle),
                }
            )

    return {
        "experiment_id": config["id"],
        "seed": config["seed"],
        "mutation": mutation,
        "agent_count": count,
        "frame_start": start,
        "frame_end": end,
        "grid": [gx, gy],
        "state_sha256": _digest(agents, field, direction_x, direction_y, idle),
        "checkpoints": checkpoints,
        "review": review,
    }


def validate_behavior_metrics(metrics: Mapping[str, Any], config: Mapping[str, Any]) -> Mapping[str, Any]:
    system = config["system"]
    if metrics.get("agent_count") != system["agent_count"]:
        raise ValueError("metrics report the wrong agent count")
    if metrics.get("frame_start") != config["frame_start"] or metrics.get("frame_end") != config["frame_end"]:
        raise ValueError("metrics report the wrong frame range")
    half_width = float(system["domain_width"]) * 0.5
    half_height = float(system["domain_height"]) * 0.5
    for checkpoint in metrics.get("checkpoints", []):
        bounds = checkpoint.get("bounds", [])
        if len(bounds) != 4 or bounds[0] < -half_width - 1e-6 or bounds[2] > half_width + 1e-6 or bounds[1] < -half_height - 1e-6 or bounds[3] > half_height + 1e-6:
            raise ValueError(f"checkpoint {checkpoint.get('frame')} escaped bounds")
    return metrics


def materially_equivalent_behavior_metrics(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    return (
        a.get("seed") == b.get("seed")
        and a.get("mutation") == b.get("mutation")
        and a.get("state_sha256") == b.get("state_sha256")
        and a.get("checkpoints") == b.get("checkpoints")
    )


def render_instrument_frames(
    metrics: Mapping[str, Any], config: Mapping[str, Any], output_dir: Path, size: tuple[int, int] = (360, 540)
) -> dict[str, Path]:
    from PIL import Image, ImageDraw

    output_dir.mkdir(parents=True, exist_ok=True)
    width, height = size
    gx, gy = metrics["grid"]
    system = config["system"]
    domain_width, domain_height = system["domain_width"], system["domain_height"]
    record = metrics["review"][-1]

    def field_image(mode: str) -> Image.Image:
        image = Image.new("RGB", size, (5, 8, 7))
        pixels = image.load()
        for py in range(height):
            cy = min(gy - 1, int(py / height * gy))
            for px in range(width):
                cx = min(gx - 1, int(px / width * gx))
                value = record["field"][cy * gx + cx]
                normalized = min(1.0, value / max(system["saturation_threshold"], 1e-6))
                if mode == "field_state":
                    pixels[px, py] = (round(10 + 28 * normalized), round(18 + 190 * normalized), round(24 + 105 * normalized))
                else:
                    pixels[px, py] = (round(12 + 220 * normalized), round(17 + 110 * (1 - normalized)), round(18 + 32 * normalized))
        return image

    field_state = field_image("field_state")
    transition = field_image("transition")
    agent_state = field_state.copy()
    draw = ImageDraw.Draw(agent_state)
    for x, y, heading in record["agents"]:
        px = round((x / domain_width + 0.5) * width)
        py = round((0.5 - y / domain_height) * height)
        dx, dy = math.cos(heading) * 4, -math.sin(heading) * 4
        draw.line((px - dx, py - dy, px + dx, py + dy), fill=(225, 240, 220), width=1)
        draw.ellipse((px - 1, py - 1, px + 1, py + 1), fill=(220, 255, 100))
    outputs = {
        "agent_state": output_dir / "agent-state.png",
        "field_state": output_dir / "field-state.png",
        "transition": output_dir / "transition.png",
    }
    agent_state.save(outputs["agent_state"])
    field_state.save(outputs["field_state"])
    transition.save(outputs["transition"])
    return outputs
