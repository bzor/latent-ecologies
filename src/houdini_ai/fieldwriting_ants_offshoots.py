from __future__ import annotations

from houdini_ai.fieldwriting_ants import (
    DirectionResult,
    SystemSnapshot,
    Vec3,
    _add,
    _rotate,
    simulate_chiral_highway_pair,
    summarize_direction,
)


def _subtract(left: Vec3, right: Vec3) -> Vec3:
    return (left[0] - right[0], left[1] - right[1], left[2] - right[2])


def _add_scaled(point: Vec3, direction: Vec3, scale: int) -> Vec3:
    return tuple(point[axis] + direction[axis] * scale for axis in range(3))


def _cross(left: Vec3, right: Vec3) -> Vec3:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def detect_translating_tail(
    path: tuple[Vec3, ...],
    *,
    max_period: int = 512,
    minimum_cycles: int = 4,
) -> dict[str, object] | None:
    """Detect an exact repeated tail of step vectors with nonzero translation."""
    if max_period <= 0 or minimum_cycles < 2 or len(path) < minimum_cycles + 1:
        return None
    deltas = tuple(_subtract(current, previous) for previous, current in zip(path, path[1:]))
    largest = min(max_period, len(deltas) // minimum_cycles)
    for period in range(1, largest + 1):
        tail = deltas[-period * minimum_cycles :]
        unit = tail[-period:]
        if any(tail[index : index + period] != unit for index in range(0, len(tail), period)):
            continue
        displacement = tuple(sum(delta[axis] for delta in unit) for axis in range(3))
        if displacement == (0, 0, 0):
            continue
        return {
            "period": period,
            "displacement": displacement,
            "active_axes": sum(value != 0 for value in displacement),
            "cycles_verified": minimum_cycles,
            "tail_steps_verified": period * minimum_cycles,
        }
    return None


def _component_count(points: set[Vec3]) -> int:
    remaining = set(points)
    components = 0
    neighbors = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    while remaining:
        components += 1
        stack = [remaining.pop()]
        while stack:
            point = stack.pop()
            for offset in neighbors:
                neighbor = tuple(point[axis] + offset[axis] for axis in range(3))
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
    return components


def simulate_rul_bridge_variant(variant: str, *, steps: int, snapshot_interval: int) -> DirectionResult:
    """Keep the RUL pair authoritative and add deterministic event-writing layers."""
    supported = {"control", "relay-node", "ladder-exchange", "scar-branch"}
    if variant not in supported:
        raise ValueError(f"unsupported RUL bridge variant: {variant}")
    if steps < 0 or snapshot_interval <= 0:
        raise ValueError("steps must be non-negative and snapshot_interval positive")
    initial_agents = (
        ((-2, 0, 0), (0, 1, 0), (0, 0, 1)),
        ((2, 0, 0), (0, 1, 0), (0, 0, 1)),
    )
    base = simulate_chiral_highway_pair(
        "RUL",
        steps=steps,
        snapshot_interval=snapshot_interval,
        initial_agents=initial_agents,
    )
    event_start = 1_100
    event_duration = 22
    event_interval = 176 if variant == "ladder-exchange" else 88

    def event_steps_until(step: int) -> range:
        if variant == "control" or step < event_start:
            return range(0)
        return range(event_start, step + 1, event_interval)

    def local_axes(path: tuple[Vec3, ...], event_step: int) -> tuple[Vec3, Vec3]:
        forward = _subtract(path[event_step], path[event_step - 1])
        reference = (0, 0, 1) if abs(forward[2]) != 1 else (1, 0, 0)
        normal = _cross(forward, reference)
        secondary = _cross(forward, normal)
        return normal, secondary

    def decoration(step: int) -> tuple[dict[Vec3, float], set[Vec3]]:
        cells: dict[Vec3, float] = {}
        centers: set[Vec3] = set()
        for event_step in event_steps_until(step):
            age = step - event_step
            for path in base.trajectories:
                center = path[event_step]
                centers.add(center)
                normal, secondary = local_axes(path, event_step)
                if variant == "relay-node":
                    cells[center] = 0.5
                    for radius in range(1, 7):
                        for axis in (normal, secondary):
                            cells[_add_scaled(center, axis, radius)] = 0.5
                            cells[_add_scaled(center, axis, -radius)] = 0.5
                elif variant == "ladder-exchange":
                    for offset in range(-10, 11):
                        cells[_add_scaled(center, normal, offset)] = 0.5
                    for offset in (-10, 10):
                        endpoint = _add_scaled(center, normal, offset)
                        cells[_add_scaled(endpoint, secondary, 1)] = 0.5
                        cells[_add_scaled(endpoint, secondary, -1)] = 0.5
                elif variant == "scar-branch":
                    state = 0.5 if age < event_duration else 1.0
                    direction = normal if (event_step // event_interval) % 2 == 0 else tuple(-value for value in normal)
                    for offset in range(0, 23):
                        cells[_add_scaled(center, direction, offset)] = state
        return cells, centers

    metrics = dict(base.metrics)
    event_count = len(tuple(event_steps_until(steps)))
    if variant == "control":
        metrics.update(
            {
                "variant": "control",
                "event_count": 0,
                "event_duration": event_duration,
                "base_rule": "RUL",
                "base_period": 22,
                "authority": "python-reference",
                "primary_trajectory_policy": "unmodified",
            }
        )
        return DirectionResult(base.system, base.steps, base.trajectories, base.field, base.snapshots, metrics)

    transformed_snapshots = []
    for snapshot in base.snapshots:
        cells, centers = decoration(snapshot.step)
        combined = dict(snapshot.field)
        combined.update(cells)
        transformed_snapshots.append(
            SystemSnapshot(
                snapshot.step,
                snapshot.agent_positions,
                tuple(sorted(combined.items())),
                snapshot.event_positions,
                snapshot.agent_frames,
            )
        )
    final_cells, _ = decoration(steps)
    final_field = dict(base.field)
    final_field.update(final_cells)
    healing_transitions = (
        sum(2 for event_step in event_steps_until(steps) if event_step + event_duration <= steps)
        if variant == "scar-branch"
        else 0
    )
    metrics.update(
        {
            "variant": variant,
            "base_rule": "RUL",
            "base_period": 22,
            "authority": "python-reference",
            "primary_trajectory_policy": "unmodified-feed-forward-event-writer",
            "event_writer_coupling": "reads-primary-position-does-not-modify-primary-field-or-frame",
            "event_start": event_start,
            "event_interval": event_interval,
            "event_duration": event_duration,
            "event_count": event_count,
            "event_cells": len(final_cells),
            "healing_transitions": healing_transitions,
        }
    )
    return DirectionResult(
        system="structured-rul-bridge",
        steps=base.steps,
        trajectories=base.trajectories,
        field=tuple(sorted(final_field.items())),
        snapshots=tuple(transformed_snapshots),
        metrics=metrics,
    )


def simulate_rul_bridge_feedback_variant(
    variant: str,
    *,
    steps: int,
    snapshot_interval: int,
    extra_snapshot_steps: tuple[int, ...] = (),
) -> DirectionResult:
    supported = {"control", "relay-node", "ladder-exchange", "scar-branch"}
    if variant not in supported:
        raise ValueError(f"unsupported RUL feedback variant: {variant}")
    initial_agents = (
        ((-2, 0, 0), (0, 1, 0), (0, 0, 1)),
        ((2, 0, 0), (0, 1, 0), (0, 0, 1)),
    )
    if variant == "control" and not extra_snapshot_steps:
        result = simulate_chiral_highway_pair(
            "RUL", steps=steps, snapshot_interval=snapshot_interval, initial_agents=initial_agents
        )
        metrics = dict(result.metrics)
        metrics.update(
            {
                "variant": variant,
                "event_schedule": (),
                "event_duration": 0,
                "restored_scar_events": 0,
                "intervention_coupling": "none",
            }
        )
        return DirectionResult(result.system, result.steps, result.trajectories, result.field, result.snapshots, metrics)

    schedules = {
        "control": ((), 0),
        "relay-node": ((3803, 6403, 9003), 22),
        "ladder-exchange": ((3809, 7009, 10209), 88),
        "scar-branch": ((4000, 6200, 8400), 22),
    }
    event_schedule, event_duration = schedules[variant]
    rules = ("RUL", "LUR")
    agents: list[list[Vec3]] = [[position, forward, up] for position, forward, up in initial_agents]
    field: dict[Vec3, int] = {}
    last_writer: dict[Vec3, int] = {}
    trajectories: list[list[Vec3]] = [[agent[0]] for agent in agents]
    collisions = 0
    shared_rewrites = 0
    collision_positions: set[Vec3] = set()
    event_positions: set[Vec3] = set()
    scar_saved: dict[int, dict[Vec3, int | None]] = {}
    restored_scar_events = 0
    snapshots: list[SystemSnapshot] = []
    snapshot_steps = set(range(0, steps + 1, snapshot_interval)) | {steps}
    snapshot_steps.update(step for step in extra_snapshot_steps if 0 <= step <= steps)
    for event_step in event_schedule:
        for offset in (0, event_duration // 2, event_duration):
            if event_step + offset <= steps:
                snapshot_steps.add(event_step + offset)

    def snapshot(step: int) -> SystemSnapshot:
        return SystemSnapshot(
            step,
            tuple(agent[0] for agent in agents),
            tuple(sorted(field.items())),
            tuple(sorted(collision_positions | event_positions)),
            tuple((agent[1], agent[2]) for agent in agents),
        )

    snapshots.append(snapshot(0))
    for step in range(1, steps + 1):
        if variant == "relay-node":
            for event_step in event_schedule:
                if step in (event_step, event_step + event_duration):
                    point = agents[0][0]
                    state = (field.get(point, 0) + 1) % 3
                    if state:
                        field[point] = state
                    else:
                        field.pop(point, None)
                    event_positions.add(point)
        elif variant == "ladder-exchange":
            for event_step in event_schedule:
                if step in (event_step, event_step + event_duration):
                    agents[0][1], agents[1][1] = agents[1][1], agents[0][1]
                    agents[0][2], agents[1][2] = agents[1][2], agents[0][2]
                    event_positions.update((agents[0][0], agents[1][0]))
        elif variant == "scar-branch":
            for event_step in event_schedule:
                if step == event_step:
                    position, forward, up = agents[0]
                    right = _cross(forward, up)
                    cells = tuple(_add_scaled(position, right, offset) for offset in range(1, 5))
                    scar_saved[event_step] = {point: field.get(point) for point in cells}
                    for point in cells:
                        field[point] = 1
                    event_positions.update(cells)
                elif step == event_step + event_duration:
                    for point, saved in scar_saved[event_step].items():
                        if saved is None:
                            field.pop(point, None)
                        else:
                            field[point] = saved
                    restored_scar_events += 1

        before = dict(field)
        rotated_frames: list[tuple[Vec3, Vec3]] = []
        destinations: list[Vec3] = []
        writes: list[tuple[Vec3, int, int]] = []
        for agent_id, (position, forward, up) in enumerate(agents):
            state = before.get(position, 0)
            command = rules[agent_id][state]
            next_forward, next_up = _rotate(forward, up, command)
            rotated_frames.append((next_forward, next_up))
            destinations.append(_add(position, next_forward))
            writes.append((position, (state + 1) % len(rules[agent_id]), agent_id))
        for point, state, agent_id in writes:
            if point in last_writer and last_writer[point] != agent_id:
                shared_rewrites += 1
            last_writer[point] = agent_id
            if state:
                field[point] = state
            else:
                field.pop(point, None)

        blocked: set[int] = set()
        if destinations[0] == destinations[1]:
            collisions += 1
            collision_positions.add(destinations[0])
            field[destinations[0]] = max(1, field.get(destinations[0], 0))
            last_writer[destinations[0]] = -1
            shared_rewrites += 1
            blocked = {0, 1}
        for agent_id, agent in enumerate(agents):
            forward, up = rotated_frames[agent_id]
            destination = destinations[agent_id]
            if agent_id in blocked:
                forward, up = _rotate(forward, up, "U" if agent_id == 0 else "D")
                destination = agent[0]
            agent[:] = [destination, forward, up]
            trajectories[agent_id].append(destination)
        if step in snapshot_steps:
            snapshots.append(snapshot(step))

    return DirectionResult(
        system="rul-bridge-feedback",
        steps=steps,
        trajectories=tuple(tuple(path) for path in trajectories),
        field=tuple(sorted(field.items())),
        snapshots=tuple(snapshots),
        metrics={
            "variant": variant,
            "base_rule": "RUL",
            "mirrored_rule": "LUR",
            "base_period": 22,
            "schedule": "synchronous-pre-read-intervention-read-intent-commit",
            "collision_policy": "same-destination-pitch-apart",
            "event_schedule": event_schedule,
            "event_duration": event_duration,
            "event_count": len(event_schedule),
            "restored_scar_events": restored_scar_events,
            "collisions": collisions,
            "shared_rewrites": shared_rewrites,
            "initial_agents": initial_agents,
            "intervention_coupling": "causal-primary-field-or-frame",
            "authority": "python-reference",
        },
    )


def analyze_offshoot_candidate(
    result: DirectionResult,
    *,
    max_period: int = 512,
    minimum_cycles: int = 4,
) -> dict[str, object]:
    summary = summarize_direction(result)
    tails = [
        detect_translating_tail(path, max_period=max_period, minimum_cycles=minimum_cycles)
        for path in result.trajectories
    ]
    spans = summary["axis_spans"]
    bounding_volume = max(1, (spans[0] + 1) * (spans[1] + 1) * (spans[2] + 1))
    density = len(result.field) / bounding_volume
    field_points = {point for point, _ in result.field}
    displacements = [tail["displacement"] for tail in tails if tail is not None]
    distinct_translations = len(displacements) == 2 and displacements[0] != displacements[1]
    all_translate = len(displacements) == len(result.trajectories)
    volumetric = all(span > 0 for span in spans)
    interaction = result.metrics.get("shared_rewrites", 0) > 0
    sparse = density <= 0.2
    classic_like_gate = all_translate and distinct_translations and volumetric and interaction and sparse
    return {
        "translating_tails": tails,
        "both_agents_translate": all_translate,
        "distinct_translation_vectors": distinct_translations,
        "occupied_density": round(density, 8),
        "field_components": _component_count(field_points),
        "volumetric_extent": volumetric,
        "shared_field_interaction": interaction,
        "sparse_highway_morphology": sparse,
        "classic_like_gate": classic_like_gate,
        "gate_definition": {
            "minimum_cycles": minimum_cycles,
            "maximum_period": max_period,
            "requirements": [
                "both exact translating tails detected",
                "distinct translation vectors",
                "nonzero extent on x/y/z",
                "cross-lineage shared-field rewrite",
                "occupied-field density <= 0.2",
            ],
        },
    }
