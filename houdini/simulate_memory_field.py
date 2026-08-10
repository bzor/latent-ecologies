"""Run and cache the deterministic Memory Field VEX simulation."""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any

import hou


AGENT_VECTOR_ATTRIBUTES = (
    "v",
    "resource_steer",
    "inhibition_steer",
    "occupancy_steer",
    "boundary_steer",
    "relic_normal",
    "relic_tangent",
    "relic_avoidance",
    "relic_resource_attraction",
)
AGENT_FLOAT_ATTRIBUTES = (
    "speed",
    "resource_intake",
    "local_resource",
    "local_inhibition",
    "deposit_strength",
    "relic_distance",
)
AGENT_INT_ATTRIBUTES = ("id", "lineage_id", "age", "state", "boundary_contact", "orbit_direction")


def relic_radius(angle: float, relic: dict[str, float]) -> float:
    prong = max(0.0, math.cos(3.0 * (angle - relic["relic_orientation"])))
    return relic["relic_hub_radius"] + relic["relic_prong_length"] * prong ** relic["relic_prong_power"]


def create_initial_geometry(config: dict[str, Any]) -> hou.Geometry:
    study = config["study"]
    system = study["simulation"]["rule_genome"]["system"]
    domain = system["domain"]
    relic = system["relic"]
    rng = random.Random(study["seed"])
    geometry = hou.Geometry()
    geometry.addAttrib(hou.attribType.Point, "kind", 0)
    for name in AGENT_INT_ATTRIBUTES:
        geometry.addAttrib(hou.attribType.Point, name, 0)
    for name in AGENT_FLOAT_ATTRIBUTES:
        geometry.addAttrib(hou.attribType.Point, name, 0.0)
    for name in AGENT_VECTOR_ATTRIBUTES:
        geometry.addAttrib(hou.attribType.Point, name, (0.0, 0.0, 0.0))
    geometry.addAttrib(hou.attribType.Point, "resource", 0.0)
    geometry.addAttrib(hou.attribType.Point, "inhibition", 0.0)
    geometry.addAttrib(hou.attribType.Point, "occupancy", 0)
    geometry.addAttrib(hou.attribType.Point, "grid_x", -1)
    geometry.addAttrib(hou.attribType.Point, "grid_y", -1)

    width = domain["domain_width"]
    height = domain["domain_height"]
    grid_width = system["grid_width"]
    grid_height = system["grid_height"]
    patches = [
        (rng.uniform(-width * 0.42, width * 0.42), rng.uniform(-height * 0.42, height * 0.42), rng.uniform(0.8, 1.5))
        for _ in range(5)
    ]
    for grid_y in range(grid_height):
        y = -height * 0.5 + height * grid_y / (grid_height - 1)
        for grid_x in range(grid_width):
            x = -width * 0.5 + width * grid_x / (grid_width - 1)
            point = geometry.createPoint()
            point.setPosition((x, y, 0))
            point.setAttribValue("kind", 1)
            point.setAttribValue("grid_x", grid_x)
            point.setAttribValue("grid_y", grid_y)
            radius = relic_radius(math.atan2(y, x), relic)
            distance = math.hypot(x, y) - radius
            if distance <= 0:
                resource = 0.0
            else:
                # Bias the halo into broad opposing sectors so portrait traffic
                # develops a vertical rhythm without imposing a global flow force.
                angle = math.atan2(y, x)
                sector_bias = 0.62 + 0.38 * abs(math.sin(angle))
                halo = math.exp(-((distance - 0.55) ** 2) / 0.18) * 0.72 * sector_bias
                patch_resource = sum(
                    amplitude * math.exp(-((x - px) ** 2 + (y - py) ** 2) / 3.2)
                    for px, py, amplitude in patches
                )
                resource = min(1.0, 0.08 + halo + patch_resource * 0.28)
            point.setAttribValue("resource", resource)

    for agent_id in range(system["agent_count"]):
        while True:
            x = rng.uniform(-width * 0.46, width * 0.46)
            y = rng.uniform(-height * 0.46, height * 0.46)
            if math.hypot(x, y) > relic_radius(math.atan2(y, x), relic) + 0.25:
                break
        heading = rng.uniform(-math.pi, math.pi)
        speed = rng.uniform(system["agent"]["min_speed"], system["agent"]["max_speed"] * 0.65)
        point = geometry.createPoint()
        point.setPosition((x, y, 0))
        point.setAttribValue("kind", 0)
        point.setAttribValue("id", agent_id)
        point.setAttribValue("lineage_id", 0)
        point.setAttribValue("orbit_direction", 1 if rng.random() >= 0.5 else -1)
        point.setAttribValue("v", (math.cos(heading) * speed, math.sin(heading) * speed, 0))
        point.setAttribValue("speed", speed)
        point.setAttribValue("relic_distance", math.hypot(x, y) - relic_radius(math.atan2(y, x), relic))
    return geometry


def frame_record(geometry: hou.Geometry, frame: int, include_field: bool) -> dict[str, Any]:
    agents = [point for point in geometry.points() if point.intAttribValue("kind") == 0]
    fields = [point for point in geometry.points() if point.intAttribValue("kind") == 1]
    speeds = [point.floatAttribValue("speed") for point in agents]
    resource = [point.floatAttribValue("resource") for point in fields]
    inhibition = [point.floatAttribValue("inhibition") for point in fields]
    record: dict[str, Any] = {
        "frame": frame,
        "active": sum(point.intAttribValue("state") == 0 for point in agents),
        "dormant": sum(point.intAttribValue("state") == 1 for point in agents),
        "terminated": sum(point.intAttribValue("state") == 2 for point in agents),
        "mean_speed": sum(speeds) / len(speeds),
        "max_speed": max(speeds),
        "resource_total": sum(resource),
        "inhibition_mean": sum(inhibition) / len(inhibition),
        "inhibition_max": max(inhibition),
        "boundary_contacts": sum(point.intAttribValue("boundary_contact") for point in agents),
        "clockwise": sum(point.intAttribValue("orbit_direction") < 0 for point in agents),
        "counterclockwise": sum(point.intAttribValue("orbit_direction") >= 0 for point in agents),
        "agents": [
            {
                "id": point.intAttribValue("id"),
                "position": [round(value, 6) for value in point.position()],
                "velocity": [round(value, 6) for value in point.attribValue("v")],
                "resource_steer": [round(value, 6) for value in point.attribValue("resource_steer")],
                "inhibition_steer": [round(value, 6) for value in point.attribValue("inhibition_steer")],
                "relic_avoidance": [round(value, 6) for value in point.attribValue("relic_avoidance")],
                "relic_distance": round(point.floatAttribValue("relic_distance"), 6),
                "resource_intake": round(point.floatAttribValue("resource_intake"), 6),
                "state": point.intAttribValue("state"),
            }
            for point in agents
        ],
    }
    if include_field:
        record["field"] = {
            "resource": [round(value, 6) for value in resource],
            "inhibition": [round(value, 6) for value in inhibition],
            "occupancy": [point.intAttribValue("occupancy") for point in fields],
        }
    return record


def simulate(hip_path: Path, config_path: Path, cache_dir: Path, metrics_path: Path, frame_end: int | None) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    simulation = config["study"]["simulation"]
    start = simulation["frame_start"]
    end = min(simulation["frame_end"], frame_end) if frame_end else simulation["frame_end"]
    review_frames = {start, end}
    if end == simulation["frame_end"]:
        review_frames.update(round(start + (end - start) * fraction) for fraction in (0.25, 0.5, 0.75))

    hou.hipFile.load(str(hip_path), suppress_save_prompt=True, ignore_load_warnings=False)
    file_node = hou.node("/obj/memory_field_simulation/previous_state")
    output = hou.node("/obj/memory_field_simulation/OUT_STATE")
    if file_node is None or output is None:
        raise RuntimeError("generated HIP is missing the Memory Field simulation network")

    cache_dir.mkdir(parents=True, exist_ok=True)
    records = []
    initial_path = cache_dir / f"state.{start:04d}.bgeo.sc"
    geometry = create_initial_geometry(config)
    geometry.saveToFile(str(initial_path))
    records.append(frame_record(geometry, start, start in review_frames))

    previous_path = initial_path
    for frame in range(start + 1, end + 1):
        file_node.parm("file").set(str(previous_path))
        hou.setFrame(frame)
        geometry = output.geometry()
        if geometry is None:
            raise RuntimeError(f"simulation produced no geometry at frame {frame}")
        current_path = cache_dir / f"state.{frame:04d}.bgeo.sc"
        geometry.saveToFile(str(current_path))
        records.append(frame_record(geometry, frame, frame in review_frames))
        previous_path = current_path
        if frame % 24 == 0 or frame == end:
            print(f"simulated_frame: {frame}", flush=True)

    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps({"frames": records}, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"cache_dir: {cache_dir}")
    print(f"metrics: {metrics_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("hip", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("cache_dir", type=Path)
    parser.add_argument("metrics", type=Path)
    parser.add_argument("--frame-end", type=int)
    args = parser.parse_args()
    simulate(args.hip.resolve(), args.config.resolve(), args.cache_dir.resolve(), args.metrics.resolve(), args.frame_end)


if __name__ == "__main__":
    main()
