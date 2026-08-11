"""Run the deterministic Study 002 high-density Houdini/VEX capability probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from array import array
from pathlib import Path
from typing import Any

import hou


def add_spare_parms(node: hou.Node, values: dict[str, float | int]) -> None:
    group = node.parmTemplateGroup()
    for name, value in values.items():
        if isinstance(value, int):
            template = hou.IntParmTemplate(name, name.replace("_", " ").title(), 1, default_value=(value,))
        else:
            template = hou.FloatParmTemplate(name, name.replace("_", " ").title(), 1, default_value=(value,))
        group.append(template)
    node.setParmTemplateGroup(group)


def fraction(value: float) -> float:
    return value - math.floor(value)


def initial_geometry(system: dict[str, Any], seed: int) -> hou.Geometry:
    count = int(system["agent_count"])
    width = float(system["domain_width"])
    height = float(system["domain_height"])
    depth = float(system["domain_depth"])
    geometry = hou.Geometry()
    geometry.addAttrib(hou.attribType.Point, "id", 0)
    geometry.addAttrib(hou.attribType.Point, "phase", 0)
    geometry.addAttrib(hou.attribType.Point, "v", (0.0, 0.0, 0.0))
    geometry.addAttrib(hou.attribType.Point, "previous_v", (0.0, 0.0, 0.0))
    geometry.addAttrib(hou.attribType.Point, "speed", 0.0)
    geometry.addAttrib(hou.attribType.Point, "curvature", 0.0)
    geometry.addAttrib(hou.attribType.Point, "density_hint", 0.0)
    geometry.addAttrib(hou.attribType.Point, "pscale", float(system["point_size"]))
    golden = 0.6180339887498949
    for agent_id in range(count):
        phase = agent_id % 3
        y = ((agent_id + 0.5) / count - 0.5) * height * 0.94
        jitter_a = fraction((agent_id + seed * 17) * golden) - 0.5
        jitter_b = fraction((agent_id + seed * 31) * 0.414213562373095) - 0.5
        center = math.sin(y * 0.45 + phase * math.tau / 3.0) * width * 0.285
        x = center + (jitter_a + jitter_b) * width * 0.13
        depth_center = math.cos(y * 0.37 - phase * math.tau / 3.0) * depth * 0.28
        z = depth_center + (jitter_a - jitter_b) * depth * 0.12
        point = geometry.createPoint()
        point.setPosition((x, y, z))
        point.setAttribValue("id", agent_id)
        point.setAttribValue("phase", phase)
        heading = y * 0.31 + phase * math.tau / 3.0
        velocity = (math.sin(heading) * 0.16, 0.32 + math.cos(heading) * 0.08, math.cos(heading * 0.71) * 0.08)
        point.setAttribValue("v", velocity)
        point.setAttribValue("previous_v", velocity)
        point.setAttribValue("speed", math.hypot(velocity[0], velocity[1]))
    return geometry


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def geometry_digest(geometry: hou.Geometry) -> str:
    digest = hashlib.sha256()
    for attribute in ("P", "v", "previous_v", "speed", "curvature", "density_hint"):
        digest.update(attribute.encode("ascii"))
        # Parallel VEX may vary by a few float ULPs across processes. Quantize to
        # 1e-5 so the digest records materially identical state, not task order.
        digest.update(array("q", (round(value * 100000) for value in geometry.pointFloatAttribValues(attribute))).tobytes())
    for attribute in ("id", "phase"):
        digest.update(attribute.encode("ascii"))
        digest.update(array("i", geometry.pointIntAttribValues(attribute)).tobytes())
    return digest.hexdigest()


def checkpoint_record(geometry: hou.Geometry, frame: int, elapsed: float) -> dict[str, Any]:
    positions = geometry.pointFloatAttribValues("P")
    speeds = geometry.pointFloatAttribValues("speed")
    xs = positions[0::3]
    ys = positions[1::3]
    zs = positions[2::3]
    return {
        "frame": frame,
        "agent_count": len(speeds),
        "mean_speed": sum(speeds) / len(speeds),
        "max_speed": max(speeds),
        "bounds": [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)],
        "elapsed_seconds": elapsed,
    }


def review_record(geometry: hou.Geometry, frame: int, review_count: int) -> dict[str, Any]:
    count = len(geometry.points())
    stride = max(1, count // review_count)
    positions = geometry.pointFloatAttribValues("P")
    speeds = geometry.pointFloatAttribValues("speed")
    phases = geometry.pointIntAttribValues("phase")
    points = []
    for index in range(0, count, stride):
        points.append([
            round(positions[index * 3], 5), round(positions[index * 3 + 1], 5),
            round(speeds[index], 5), phases[index],
        ])
        if len(points) >= review_count:
            break
    return {"frame": frame, "points": points}


def run(config_path: Path, cache_dir: Path, metrics_path: Path, review_path: Path, frame_end: int | None) -> None:
    effective = json.loads(config_path.read_text(encoding="utf-8"))
    study = effective.get("study", effective)
    simulation = study["simulation"]
    system = simulation["rule_genome"]["system"]
    start = int(simulation["frame_start"])
    end = int(frame_end or simulation["frame_end"])
    prewarm_frames = int(system.get("prewarm_frames", 0))
    interval = int(system["checkpoint_interval"])
    checkpoint_frames = {start, end, *range(interval, end + 1, interval)}
    cache_dir.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    root = Path(__file__).resolve().parents[1]
    snippet = (root / "houdini" / "vex" / "lib" / "agent_core.vfl").read_text(encoding="utf-8")
    snippet += "\n" + (root / "houdini" / "vex" / "mass_flow_agents.vfl").read_text(encoding="utf-8")
    geometry = initial_geometry(system, int(study["seed"]))
    initial_frame = start - prewarm_frames
    previous_path = cache_dir / ("state.prewarm.0.bgeo.sc" if prewarm_frames else f"state.{start:04d}.bgeo.sc")
    geometry.saveToFile(str(previous_path))

    hou.hipFile.clear(suppress_save_prompt=True)
    network = hou.node("/obj").createNode("geo", "mass_flow_probe")
    for child in network.children():
        child.destroy()
    source = network.createNode("file", "previous_state")
    source.parm("file").set(str(previous_path))
    update = network.createNode("attribwrangle", "mass_flow_update")
    update.setInput(0, source)
    update.setInput(1, source)
    update.parm("snippet").set(snippet)
    values = {
        "fps": simulation["fps"], "current_frame": initial_frame,
        **{key: system[key] for key in (
            "domain_width", "domain_height", "domain_depth", "flow_scale", "flow_strength", "depth_strength",
            "phase_strength", "avoidance_radius", "avoidance_strength", "flock_radius", "flock_id_window",
            "alignment_strength", "cohesion_strength", "separation_radius", "separation_strength",
            "wander_strength", "drag", "max_speed",
        )},
    }
    add_spare_parms(update, values)
    for frame in range(initial_frame + 1, start + 1):
        source.parm("file").set(str(previous_path))
        source.parm("reload").pressButton()
        update.parm("current_frame").set(frame)
        update.cook(force=True)
        geometry = update.geometry().freeze()
        previous_path = cache_dir / (
            f"state.{start:04d}.bgeo.sc" if frame == start else f"state.prewarm.{(frame - initial_frame) % 2}.bgeo.sc"
        )
        geometry.saveToFile(str(previous_path))
    records = []
    reviews = []
    started = time.perf_counter()
    records.append(checkpoint_record(geometry, start, 0.0))
    reviews.append(review_record(geometry, start, int(system["review_agent_count"])))
    cache_hashes = {previous_path.name: sha256(previous_path)}
    state_hashes = {str(start): geometry_digest(geometry)}

    for frame in range(start + 1, end + 1):
        source.parm("file").set(str(previous_path))
        source.parm("reload").pressButton()
        update.parm("current_frame").set(frame)
        update.cook(force=True)
        geometry = update.geometry().freeze()
        if frame in checkpoint_frames:
            checkpoint = cache_dir / f"state.{frame:04d}.bgeo.sc"
            geometry.saveToFile(str(checkpoint))
            previous_path = checkpoint
            cache_hashes[checkpoint.name] = sha256(checkpoint)
            state_hashes[str(frame)] = geometry_digest(geometry)
            elapsed = time.perf_counter() - started
            records.append(checkpoint_record(geometry, frame, elapsed))
            reviews.append(review_record(geometry, frame, int(system["review_agent_count"])))
        else:
            transient = cache_dir / "state.transient.bgeo.sc"
            geometry.saveToFile(str(transient))
            previous_path = transient

    total = time.perf_counter() - started
    payload = {
        "study_id": study["id"], "seed": study["seed"], "agent_count": system["agent_count"],
        "frame_start": start, "frame_end": end, "prewarm_frames": prewarm_frames, "elapsed_seconds": total,
        "agent_frames_per_second": system["agent_count"] * max(0, end - start + prewarm_frames) / max(total, 1e-9),
        "checkpoints": records, "cache_sha256": cache_hashes, "state_sha256": state_hashes,
    }
    metrics_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    review_path.write_text(json.dumps({"study_id": study["id"], "frames": reviews}) + "\n", encoding="utf-8")
    print(f"agents: {system['agent_count']}")
    print(f"frames: {start}-{end}")
    print(f"elapsed_seconds: {total:.3f}")
    print(f"agent_frames_per_second: {payload['agent_frames_per_second']:.0f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("cache_dir", type=Path)
    parser.add_argument("metrics", type=Path)
    parser.add_argument("review", type=Path)
    parser.add_argument("--frame-end", type=int)
    args = parser.parse_args()
    run(args.config, args.cache_dir, args.metrics, args.review, args.frame_end)


if __name__ == "__main__":
    main()
