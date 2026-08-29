"""Run a sparse-cache, VEX-authoritative 3D Nonlocal Affinity simulation."""

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

from houdini_ai.nonlocal_affinity import (
    AffinityConfig,
    AffinityParameters,
    prepare_reference_run,
    relationship_digest,
    simulate_prepared,
)


def _native(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _geometry_digest(geometry: hou.Geometry) -> str:
    digest = hashlib.sha256()
    digest.update(array("q", (round(value * 10_000_000) for value in geometry.pointFloatAttribValues("P"))).tobytes())
    digest.update(array("i", geometry.pointIntAttribValues("friend")).tobytes())
    digest.update(array("i", geometry.pointIntAttribValues("enemy")).tobytes())
    return digest.hexdigest()


def _initial_geometry(prepared: dict[str, object]) -> hou.Geometry:
    geometry = hou.Geometry()
    positions = [
        hou.Vector3(position[0], position[1], position[2] if len(position) > 2 else 0.0)
        for position in prepared["initial_positions"]
    ]
    geometry.createPoints(positions)
    geometry.addAttrib(hou.attribType.Point, "friend", 0)
    geometry.addAttrib(hou.attribType.Point, "enemy", 0)
    geometry.setPointIntAttribValues("friend", array("i", prepared["friends"]))
    geometry.setPointIntAttribValues("enemy", array("i", prepared["enemies"]))
    return geometry


def _apply_events(geometry: hou.Geometry, events: list[dict[str, int]]) -> None:
    count = len(geometry.points())
    friend_attrib = geometry.findPointAttrib("friend")
    enemy_attrib = geometry.findPointAttrib("enemy")
    if friend_attrib is None or enemy_attrib is None:
        raise RuntimeError("affinity state is missing relationship attributes")
    for event in events:
        point_index = int(event["point"])
        friend = int(event["friend"])
        enemy = int(event["enemy"])
        if any(index < 0 or index >= count for index in (point_index, friend, enemy)):
            raise RuntimeError("rewire event references a missing point")
        point = geometry.point(point_index)
        if point is None:
            raise RuntimeError("rewire event references a missing point")
        point.setAttribValue(friend_attrib, friend)
        point.setAttribValue(enemy_attrib, enemy)


def _add_float_parm(node: hou.Node, name: str, value: float) -> None:
    group = node.parmTemplateGroup()
    group.append(hou.FloatParmTemplate(name, name.replace("_", " ").title(), 1, default_value=(value,)))
    node.setParmTemplateGroup(group)


def _checkpoint_record(geometry: hou.Geometry, step: int, elapsed: float) -> dict[str, Any]:
    positions = geometry.pointFloatAttribValues("P")
    xs, ys, zs = positions[0::3], positions[1::3], positions[2::3]
    radii = [math.sqrt(x * x + y * y + z * z) for x, y, z in zip(xs, ys, zs)]
    invalid_values = sum(not math.isfinite(value) for value in positions)
    return {
        "step": step,
        "agent_count": len(xs),
        "bounds": [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)],
        "radial_mean": sum(radii) / len(radii),
        "radial_extent": max(radii),
        "invalid_values": invalid_values,
        "elapsed_seconds": elapsed,
    }


def _review_record(geometry: hou.Geometry, step: int, review_count: int) -> dict[str, Any]:
    count = len(geometry.points())
    stride = max(1, count // review_count)
    positions = geometry.pointFloatAttribValues("P")
    points = []
    for index in range(0, count, stride):
        points.append([
            round(positions[index * 3], 6),
            round(positions[index * 3 + 1], 6),
            round(positions[index * 3 + 2], 6),
        ])
        if len(points) >= review_count:
            break
    return {"step": step, "points": points}


def _config_from_validated_preset(
    preset: dict[str, Any], *, agent_count: int, dimensions: int, steps: int,
) -> AffinityConfig:
    if preset.get("mechanism") != "nonlocal-affinity-v1":
        raise ValueError("unsupported affinity mechanism")
    if preset.get("production_hint", {}).get("execution_authorized") is not False:
        raise ValueError("preset must remain inert at the production boundary")
    probability = float(preset["rewiring"]["probability_per_simulation_step"])
    denominator = 1000
    exclusive_max = max(1, min(denominator + 1, round(probability * denominator) + 1))
    parameters = preset["parameters"]
    return AffinityConfig(
        seed=int(preset["seed"]),
        agent_count=agent_count,
        dimensions=dimensions,
        steps=steps,
        rewire_gate_denominator=denominator,
        rewire_gate_exclusive_max=exclusive_max,
        rewires_per_event=int(preset["rewiring"]["rewires_per_event"]),
        parameters=AffinityParameters(
            contraction=float(parameters["contraction"]),
            attraction=float(parameters["attraction"]),
            repulsion=float(parameters["repulsion"]),
            softening=float(parameters["softening"]),
        ),
    )


def run(
    preset_path: Path,
    output: Path,
    *,
    agent_count: int,
    dimensions: int,
    steps: int,
    checkpoint_interval: int,
    review_interval: int,
    review_count: int,
    compare_reference: bool,
    prepared_path: Path | None,
) -> dict[str, Any]:
    if dimensions not in {2, 3}:
        raise ValueError("the production runner requires dimensions=2 or dimensions=3")
    if checkpoint_interval < 1 or review_interval < 1 or review_count < 1:
        raise ValueError("checkpoint_interval, review_interval, and review_count must be positive")
    preset = json.loads(preset_path.read_text(encoding="utf-8"))
    config = _config_from_validated_preset(
        preset, agent_count=agent_count, dimensions=dimensions, steps=steps,
    )
    prepared = (
        json.loads(prepared_path.read_text(encoding="utf-8"))
        if prepared_path is not None
        else prepare_reference_run(config)
    )
    events_by_step: dict[int, list[dict[str, int]]] = {}
    for event in prepared["rewire_events"]:
        events_by_step.setdefault(int(event["step"]), []).append(event)

    output.mkdir(parents=True, exist_ok=True)
    cache = output / "cache"
    cache.mkdir(exist_ok=True)
    (output / "temp").mkdir(exist_ok=True)
    checkpoint_steps = {0, steps, *range(checkpoint_interval, steps + 1, checkpoint_interval)}
    review_steps = {0, steps, *range(review_interval, steps + 1, review_interval)}
    geometry = _initial_geometry(prepared)
    initial_path = cache / "state.0000.bgeo.sc"
    geometry.saveToFile(_native(initial_path))

    hou.hipFile.clear(suppress_save_prompt=True)
    network = hou.node("/obj").createNode("geo", "nonlocal_affinity_3d")
    for child in network.children():
        child.destroy()
    source = network.createNode("file", "previous_vex_state")
    update = network.createNode("attribwrangle", "nonlocal_affinity_3d_step")
    update.setInput(0, source)
    update.parm("class").set("point")
    snippet = (Path(__file__).resolve().parent / "vex" / "nonlocal_affinity_production_step.vfl").read_text(encoding="utf-8")
    update.parm("snippet").set(snippet)
    for name in ("contraction", "attraction", "repulsion", "softening"):
        _add_float_parm(update, name, float(getattr(config.parameters, name)))
    update.moveToGoodPosition()

    started = time.perf_counter()
    checkpoints = [_checkpoint_record(geometry, 0, 0.0)]
    reviews = [_review_record(geometry, 0, review_count)]
    cache_hashes = {initial_path.name: _sha256(initial_path)}
    state_hashes = {"0": _geometry_digest(geometry)}
    vex_errors: list[str] = []
    transient = cache / "state.transient.bgeo.sc"

    for step in range(1, steps + 1):
        _apply_events(geometry, events_by_step.get(step, []))
        geometry.saveToFile(_native(transient))
        source.parm("file").set(_native(transient))
        source.parm("reload").pressButton()
        update.cook(force=True)
        step_errors = [str(error) for error in update.errors()]
        vex_errors.extend(f"step {step}: {error}" for error in step_errors)
        if step_errors:
            raise RuntimeError("; ".join(vex_errors))
        cooked = update.geometry()
        if cooked is None or len(cooked.points()) != agent_count:
            raise RuntimeError(f"step {step}: cooked geometry has the wrong point count")
        geometry = cooked.freeze()
        if step in review_steps:
            reviews.append(_review_record(geometry, step, review_count))
        if step in checkpoint_steps:
            checkpoint = cache / f"state.{step:04d}.bgeo.sc"
            geometry.saveToFile(_native(checkpoint))
            elapsed = time.perf_counter() - started
            cache_hashes[checkpoint.name] = _sha256(checkpoint)
            state_hashes[str(step)] = _geometry_digest(geometry)
            checkpoints.append(_checkpoint_record(geometry, step, elapsed))

    final_path = cache / f"state.{steps:04d}.bgeo.sc"
    final_geometry = hou.Geometry()
    final_geometry.loadFromFile(_native(final_path))
    final_positions = final_geometry.pointFloatAttribValues("P")
    final_friends = list(final_geometry.pointIntAttribValues("friend"))
    final_enemies = list(final_geometry.pointIntAttribValues("enemy"))

    maximum_position_error = None
    mean_position_error = None
    p95_position_error = None
    p99_position_error = None
    relationship_match = None
    tolerance_passed = None
    material_tolerance_passed = None
    reference_mean_radius = None
    comparison_tolerance = None
    if compare_reference:
        reference = simulate_prepared(config, prepared)
        position_errors = [
            math.dist(
                final_positions[index * 3:index * 3 + dimensions],
                reference["final_positions"][index],
            )
            for index in range(agent_count)
        ]
        position_errors.sort()
        maximum_position_error = max(position_errors, default=0.0)
        mean_position_error = sum(position_errors) / max(1, len(position_errors))
        p95_position_error = position_errors[round((len(position_errors) - 1) * 0.95)] if position_errors else 0.0
        p99_position_error = position_errors[round((len(position_errors) - 1) * 0.99)] if position_errors else 0.0
        reference_radii = [math.sqrt(sum(value * value for value in position)) for position in reference["final_positions"]]
        reference_mean_radius = sum(reference_radii) / max(1, len(reference_radii))
        comparison_tolerance = max(1e-6, steps * 2e-6)
        tolerance_passed = maximum_position_error <= comparison_tolerance
        relationship_match = final_friends == reference["friends"] and final_enemies == reference["enemies"]
        material_tolerance_passed = bool(
            relationship_match
            and mean_position_error <= max(1e-6, reference_mean_radius * 0.0001)
            and p99_position_error <= max(1e-6, reference_mean_radius * 0.001)
            and maximum_position_error <= max(1e-6, reference_mean_radius * 0.005)
        )

    source.parm("file").set(_native(final_path))
    source.parm("reload").pressButton()
    final_display = network.createNode("null", "VEX_AUTHORITATIVE_FINAL")
    final_display.setInput(0, source)
    final_display.setDisplayFlag(True)
    final_display.setRenderFlag(True)
    update.setDisplayFlag(False)
    network.layoutChildren()
    hip_path = output / "nonlocal-affinity-3d.hiplc"
    hou.hipFile.save(_native(hip_path))

    elapsed = time.perf_counter() - started
    metrics: dict[str, Any] = {
        "schema_version": 1,
        "engine": "hython-vex-rotating-cache",
        "state_authority": "vex-geometry",
        "preset_id": preset["id"],
        "preset_title": preset["title"],
        "preset_sha256": _sha256(preset_path),
        "prepared_source": "external-receipt" if prepared_path is not None else "python-random-v1",
        "prepared_sha256": _sha256(prepared_path) if prepared_path is not None else None,
        "seed": config.seed,
        "agent_count": agent_count,
        "dimensions": dimensions,
        "steps": steps,
        "parameters": preset["parameters"],
        "rewiring": preset["rewiring"],
        "rewire_count": len(prepared["rewire_events"]),
        "vex_cook_count": steps,
        "vex_errors": vex_errors,
        "elapsed_seconds": elapsed,
        "agent_steps_per_second": agent_count * steps / max(elapsed, 1e-9),
        "durable_checkpoint_steps": sorted(checkpoint_steps),
        "review_sample_steps": sorted(review_steps),
        "checkpoints": checkpoints,
        "cache_sha256": cache_hashes,
        "state_sha256": state_hashes,
        "final_state_sha256": _geometry_digest(final_geometry),
        "final_relationship_sha256": relationship_digest(final_friends, final_enemies),
        "state_digest_source": "reloaded-final-cache",
        "final_cache": str(final_path.relative_to(output)).replace("\\", "/"),
        "hip": hip_path.name,
        "reference_comparison": "measured" if compare_reference else "not-run",
        "comparison_tolerance": comparison_tolerance,
        "maximum_position_error": maximum_position_error,
        "mean_position_error": mean_position_error,
        "p95_position_error": p95_position_error,
        "p99_position_error": p99_position_error,
        "reference_mean_radius": reference_mean_radius,
        "reference_tolerance_passed": tolerance_passed,
        "reference_material_tolerance": {
            "mean_fraction_of_mean_radius": 0.0001,
            "p99_fraction_of_mean_radius": 0.001,
            "max_fraction_of_mean_radius": 0.005,
        },
        "reference_material_tolerance_passed": material_tolerance_passed,
        "relationship_indices_match": relationship_match,
        "look_status": "deferred",
        "trails_status": "deferred",
    }
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "review.json").write_text(
        json.dumps({"preset_id": preset["id"], "dimensions": dimensions, "frames": reviews}, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    (output / "effective-preset.json").write_text(json.dumps(preset, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "preset_id": preset["id"],
        "agent_count": agent_count,
        "steps": steps,
        "elapsed_seconds": elapsed,
        "final_state_sha256": metrics["final_state_sha256"],
    }, sort_keys=True))
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("preset", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--agent-count", type=int, required=True)
    parser.add_argument("--dimensions", type=int, default=3)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--checkpoint-interval", type=int, default=12)
    parser.add_argument("--review-interval", type=int, default=12)
    parser.add_argument("--review-count", type=int, default=5000)
    parser.add_argument("--prepared", type=Path)
    parser.add_argument("--compare-reference", action="store_true")
    args = parser.parse_args()
    run(
        args.preset,
        args.output,
        agent_count=args.agent_count,
        dimensions=args.dimensions,
        steps=args.steps,
        checkpoint_interval=args.checkpoint_interval,
        review_interval=args.review_interval,
        review_count=args.review_count,
        compare_reference=args.compare_reference,
        prepared_path=args.prepared,
    )


if __name__ == "__main__":
    main()
