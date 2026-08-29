"""Build and measure a tiny VEX-authoritative Nonlocal Affinity parity tracer."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import hou


def _native(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def _set_event(geometry: hou.Geometry, event: dict[str, int] | None) -> None:
    values = {
        "rewire_point": event["point"] if event else -1,
        "rewire_friend": event["friend"] if event else -1,
        "rewire_enemy": event["enemy"] if event else -1,
    }
    for name, value in values.items():
        if geometry.findGlobalAttrib(name) is None:
            geometry.addAttrib(hou.attribType.Global, name, -1)
        geometry.setGlobalAttribValue(name, value)


def _apply_events(geometry: hou.Geometry, events: list[dict[str, int]]) -> None:
    """Apply the prepared stochastic batch before one VEX integration cook."""

    points = geometry.points()
    friend_attrib = geometry.findPointAttrib("friend")
    enemy_attrib = geometry.findPointAttrib("enemy")
    if friend_attrib is None or enemy_attrib is None:
        raise RuntimeError("cached affinity geometry is missing relationship attributes")
    for event in events:
        point_index = int(event["point"])
        if point_index < 0 or point_index >= len(points):
            raise RuntimeError("rewire event references a missing point")
        points[point_index].setAttribValue(friend_attrib, int(event["friend"]))
        points[point_index].setAttribValue(enemy_attrib, int(event["enemy"]))
    _set_event(geometry, None)


def _create_initial(prepared: dict[str, object], path: Path) -> None:
    geometry = hou.Geometry()
    friend_attrib = geometry.addAttrib(hou.attribType.Point, "friend", 0)
    enemy_attrib = geometry.addAttrib(hou.attribType.Point, "enemy", 0)
    for index, position in enumerate(prepared["initial_positions"]):
        point = geometry.createPoint()
        point.setPosition(hou.Vector3(float(position[0]), float(position[1]), 0.0))
        point.setAttribValue(friend_attrib, int(prepared["friends"][index]))
        point.setAttribValue(enemy_attrib, int(prepared["enemies"][index]))
    _set_event(geometry, None)
    geometry.saveToFile(_native(path))


def _load(path: Path) -> hou.Geometry:
    geometry = hou.Geometry()
    geometry.loadFromFile(_native(path))
    return geometry


def _state_digest(positions: list[list[float]], friends: list[int], enemies: list[int]) -> str:
    payload = {
        "positions": [[round(value, 9) for value in position] for position in positions],
        "friends": friends,
        "enemies": enemies,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _positions(geometry: hou.Geometry) -> list[list[float]]:
    return [[point.position().x(), point.position().y()] for point in geometry.points()]


def run(input_path: Path, output: Path) -> dict[str, object]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    config = payload["config"]
    prepared = payload["prepared"]
    reference = payload["reference"]
    output.mkdir(parents=True, exist_ok=True)
    cache = output / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    (output / "temp").mkdir(exist_ok=True)

    initial = cache / "nonlocal-affinity.0000.bgeo.sc"
    _create_initial(prepared, initial)

    hou.hipFile.clear(suppress_save_prompt=True)
    container = hou.node("/obj").createNode("geo", "nonlocal_affinity_parity")
    for child in container.children():
        child.destroy()
    file_node = container.createNode("file", "previous_vex_state")
    wrangle = container.createNode("attribwrangle", "faithful_nonlocal_affinity_step")
    wrangle.setInput(0, file_node)
    wrangle.parm("class").set("point")
    vex_path = Path(__file__).resolve().parent / "vex" / "nonlocal_affinity_step.vfl"
    wrangle.parm("snippet").set(vex_path.read_text(encoding="utf-8"))
    display = container.createNode("null", "VEX_AUTHORITATIVE_STATE")
    display.setInput(0, wrangle)
    display.setDisplayFlag(True)
    display.setRenderFlag(True)
    container.layoutChildren()

    events: dict[int, list[dict[str, int]]] = {}
    for event in prepared["rewire_events"]:
        events.setdefault(int(event["step"]), []).append(event)
    prior = initial
    errors: list[str] = []
    trajectory = [{"step": 0, "positions": _positions(_load(initial))}]
    for step in range(1, int(config["steps"]) + 1):
        input_geometry = _load(prior)
        _apply_events(input_geometry, events.get(step, []))
        step_input = cache / f"input.{step:04d}.bgeo.sc"
        input_geometry.saveToFile(_native(step_input))
        file_node.parm("file").set(_native(step_input))
        file_node.parm("reload").pressButton()
        wrangle.cook(force=True)
        step_errors = [str(error) for error in wrangle.errors()]
        errors.extend(f"step {step}: {error}" for error in step_errors)
        if step_errors:
            raise RuntimeError("; ".join(errors))
        cooked = wrangle.geometry()
        if cooked is None or len(cooked.points()) != int(config["agent_count"]):
            raise RuntimeError(f"step {step}: cooked geometry has the wrong point count")
        prior = cache / f"nonlocal-affinity.{step:04d}.bgeo.sc"
        cooked.saveToFile(_native(prior))
        trajectory.append({"step": step, "positions": _positions(cooked)})

    final_geometry = _load(prior)
    points = final_geometry.points()
    positions = _positions(final_geometry)
    friends = [int(point.attribValue("friend")) for point in points]
    enemies = [int(point.attribValue("enemy")) for point in points]
    position_errors = [
        math.dist(position, reference["final_positions"][index])
        for index, position in enumerate(positions)
    ]
    maximum_position_error = max(position_errors, default=0.0)
    comparison_tolerance = max(1e-6, int(config["steps"]) * 2e-6)
    relationship_match = friends == reference["friends"] and enemies == reference["enemies"]
    hip_path = output / "nonlocal-affinity-parity.hiplc"
    hou.hipFile.save(_native(hip_path))

    metrics: dict[str, object] = {
        "engine": "hython-vex",
        "state_authority": "vex-geometry",
        "reference_comparison": "measured",
        "comparison_tolerance": comparison_tolerance,
        "reference_tolerance_passed": maximum_position_error <= comparison_tolerance,
        "vex_cook_count": int(config["steps"]),
        "agent_count": len(points),
        "vex_errors": errors,
        "maximum_position_error": maximum_position_error,
        "mean_position_error": sum(position_errors) / max(1, len(position_errors)),
        "relationship_indices_match": relationship_match,
        "state_sha256": _state_digest(positions, friends, enemies),
        "state_digest_source": "reloaded-final-cache",
        "trajectory_frame_count": len(trajectory),
        "final_cache": str(prior.relative_to(output)).replace("\\", "/"),
        "hip": hip_path.name,
    }
    (output / "trajectory.json").write_text(
        json.dumps({"state_authority": "vex-geometry", "frames": trajectory}, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    (output / "vex-parity.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metrics


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: hython probe_nonlocal_affinity.py INPUT_JSON OUTPUT_DIR")
    result = run(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(result, sort_keys=True))
