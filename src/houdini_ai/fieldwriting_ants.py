from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
import shutil
import subprocess

Vec3 = tuple[int, int, int]
Scalar = int | float


def _add(a: Vec3, b: Vec3) -> Vec3:
    return a[0] + b[0], a[1] + b[1], a[2] + b[2]


def _neg(a: Vec3) -> Vec3:
    return -a[0], -a[1], -a[2]


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


@dataclass(frozen=True)
class AntSnapshot:
    step: int
    position: Vec3
    forward: Vec3
    up: Vec3
    field: tuple[tuple[Vec3, Scalar], ...] = ()


@dataclass(frozen=True)
class SystemSnapshot:
    step: int
    agent_positions: tuple[Vec3, ...]
    field: tuple[tuple[Vec3, Scalar], ...]
    event_positions: tuple[Vec3, ...] = ()
    agent_frames: tuple[tuple[Vec3, Vec3], ...] = ()


@dataclass(frozen=True)
class DirectionResult:
    system: str
    steps: int
    trajectories: tuple[tuple[Vec3, ...], ...]
    field: tuple[tuple[Vec3, Scalar], ...]
    snapshots: tuple[SystemSnapshot, ...]
    metrics: dict[str, int | float | str]


@dataclass(frozen=True)
class SimulationResult:
    steps: int
    commands: tuple[str, ...]
    unique_cells: int
    final: AntSnapshot
    trajectory: tuple[Vec3, ...]
    snapshots: tuple[AntSnapshot, ...]
    field: tuple[tuple[Vec3, Scalar], ...]


def _rotate(forward: Vec3, up: Vec3, command: str) -> tuple[Vec3, Vec3]:
    right = _cross(forward, up)
    if command == "R":
        return right, up
    if command == "L":
        return _neg(right), up
    if command == "U":
        return up, _neg(forward)
    if command == "D":
        return _neg(up), forward
    raise ValueError(f"unsupported turn command: {command}")


def simulate_langton_2d(rule: str, steps: int) -> SimulationResult:
    if not rule or any(command not in "LR" for command in rule):
        raise ValueError("2D Langton rules must be non-empty strings over L/R")
    if steps < 0:
        raise ValueError("steps must be non-negative")
    field: defaultdict[Vec3, int] = defaultdict(int)
    position: Vec3 = (0, 0, 0)
    directions: tuple[Vec3, ...] = ((1, 0, 0), (0, -1, 0), (-1, 0, 0), (0, 1, 0))
    heading = 0
    commands: list[str] = []
    trajectory: list[Vec3] = [position]
    for _ in range(steps):
        state = field[position]
        command = rule[state]
        field[position] = (state + 1) % len(rule)
        heading = (heading + (1 if command == "R" else -1)) % 4
        position = _add(position, directions[heading])
        commands.append(command)
        trajectory.append(position)
    final = AntSnapshot(
        step=steps,
        position=position,
        forward=directions[heading],
        up=(0, 0, 1),
        field=tuple(sorted(field.items())),
    )
    return SimulationResult(
        steps=steps,
        commands=tuple(commands),
        unique_cells=len(field),
        final=final,
        trajectory=tuple(trajectory),
        snapshots=(AntSnapshot(0, (0, 0, 0), (1, 0, 0), (0, 0, 1), ()), final),
        field=final.field,
    )


def simulate_shared_2d_colony(rule: str, steps: int, snapshot_interval: int) -> DirectionResult:
    if not rule or any(command not in "LR" for command in rule):
        raise ValueError("2D colony rules must be non-empty strings over L/R")
    if steps < 0 or snapshot_interval <= 0:
        raise ValueError("steps must be non-negative and snapshot_interval positive")
    directions: tuple[Vec3, ...] = ((1, 0, 0), (0, -1, 0), (-1, 0, 0), (0, 1, 0))
    positions: list[Vec3] = [(-1, 0, 0), (1, 0, 0)]
    headings = [3, 1]
    field: dict[Vec3, int] = {}
    trajectories: list[list[Vec3]] = [[position] for position in positions]
    collisions: set[Vec3] = set()
    collision_count = 0
    snapshots: list[SystemSnapshot] = []

    def snapshot(step: int) -> SystemSnapshot:
        return SystemSnapshot(
            step,
            tuple(positions),
            tuple(sorted((point, state) for point, state in field.items() if state != 0)),
            tuple(sorted(collisions)),
        )

    snapshots.append(snapshot(0))
    for step in range(1, steps + 1):
        before = dict(field)
        destinations: list[Vec3] = []
        next_headings: list[int] = []
        writes: dict[Vec3, int] = {}
        for position, heading in zip(positions, headings):
            state = before.get(position, 0)
            command = rule[state]
            next_heading = (heading + (1 if command == "R" else -1)) % 4
            destinations.append(_add(position, directions[next_heading]))
            next_headings.append(next_heading)
            writes[position] = (state + 1) % len(rule)
        for point, state in writes.items():
            if state:
                field[point] = state
            else:
                field.pop(point, None)

        blocked: set[int] = set()
        if destinations[0] == destinations[1]:
            collision_count += 1
            collisions.add(destinations[0])
            blocked = {0, 1}
            field[destinations[0]] = len(rule) - 1
        for agent_id in range(2):
            if agent_id in blocked:
                headings[agent_id] = (next_headings[agent_id] + 2) % 4
            else:
                headings[agent_id] = next_headings[agent_id]
                positions[agent_id] = destinations[agent_id]
            trajectories[agent_id].append(positions[agent_id])
        if step % snapshot_interval == 0 or step == steps:
            snapshots.append(snapshot(step))

    return DirectionResult(
        system="shared-2d-reference",
        steps=steps,
        trajectories=tuple(tuple(path) for path in trajectories),
        field=tuple(sorted((point, state) for point, state in field.items() if state != 0)),
        snapshots=tuple(snapshots),
        metrics={
            "rule": rule,
            "schedule": "synchronous-read-intent-commit",
            "collision_policy": "same-destination-block-reverse",
            "collisions": collision_count,
            "contested_cells": len(collisions),
        },
    )


def enumerate_near_rules(base_rule: str) -> list[dict[str, int | str]]:
    if not base_rule or any(command not in "LRUD" for command in base_rule):
        raise ValueError("base rule must use L/R/U/D")
    records: list[dict[str, int | str]] = []
    for index, original in enumerate(base_rule):
        for replacement in "LRUD":
            if replacement != original:
                records.append(
                    {
                        "rule": base_rule[:index] + replacement + base_rule[index + 1 :],
                        "operation": "substitute",
                        "index": index,
                        "detail": f"{original}->{replacement}",
                        "edit_distance": 1,
                    }
                )
    for index in range(len(base_rule)):
        records.append(
            {
                "rule": base_rule[:index] + base_rule[index + 1 :],
                "operation": "delete",
                "index": index,
                "detail": base_rule[index],
                "edit_distance": 1,
            }
        )
    for index in range(len(base_rule) + 1):
        for insertion in "LRUD":
            records.append(
                {
                    "rule": base_rule[:index] + insertion + base_rule[index:],
                    "operation": "insert",
                    "index": index,
                    "detail": insertion,
                    "edit_distance": 1,
                }
            )
    return records


def simulate_hamann(rule: str, steps: int, snapshot_interval: int | None = None) -> SimulationResult:
    if not rule or any(command not in "LRUD" for command in rule):
        raise ValueError("Hamann rules must be non-empty strings over L/R/U/D")
    if steps < 0:
        raise ValueError("steps must be non-negative")
    if snapshot_interval is not None and snapshot_interval <= 0:
        raise ValueError("snapshot_interval must be positive")

    field: defaultdict[Vec3, int] = defaultdict(int)
    position: Vec3 = (0, 0, 0)
    forward: Vec3 = (1, 0, 0)
    up: Vec3 = (0, 0, 1)
    commands: list[str] = []
    trajectory: list[Vec3] = [position]
    snapshots: list[AntSnapshot] = []

    def snapshot(step: int) -> AntSnapshot:
        return AntSnapshot(step, position, forward, up, tuple(sorted(field.items())))

    if snapshot_interval is not None:
        snapshots.append(snapshot(0))

    for step in range(1, steps + 1):
        state = field[position]
        command = rule[state]
        field[position] = (state + 1) % len(rule)
        forward, up = _rotate(forward, up, command)
        position = _add(position, forward)
        commands.append(command)
        trajectory.append(position)
        if snapshot_interval is not None and (step % snapshot_interval == 0 or step == steps):
            snapshots.append(snapshot(step))

    final = snapshot(steps)
    return SimulationResult(
        steps=steps,
        commands=tuple(commands),
        unique_cells=len(field),
        final=final,
        trajectory=tuple(trajectory),
        snapshots=tuple(snapshots),
        field=final.field,
    )


def hamann_direction_result(rule: str, steps: int, snapshot_interval: int) -> DirectionResult:
    simulation = simulate_hamann(rule, steps, snapshot_interval)
    snapshots = tuple(
        SystemSnapshot(
            snapshot.step,
            (snapshot.position,),
            tuple((point, state) for point, state in snapshot.field if state != 0),
            (),
            ((snapshot.forward, snapshot.up),),
        )
        for snapshot in simulation.snapshots
    )
    reported_periods = {"RRLU": 32, "RUL": 22, "RLRUUUL": 25_436}
    return DirectionResult(
        system="hamann-frame-highway",
        steps=steps,
        trajectories=(simulation.trajectory,),
        field=tuple((point, state) for point, state in simulation.field if state != 0),
        snapshots=snapshots,
        metrics={
            "rule": rule,
            "visited_cells": simulation.unique_cells,
            "reported_period_candidate": reported_periods.get(rule, "unreported"),
            "detected_tail_period": detect_tail_period(
                simulation.commands,
                [period for period in (22, 32, 188, 25_436) if period <= max(1, steps // 3)],
            )
            or "not-detected",
        },
    )


def simulate_ring_excavator(
    rule: str, steps: int, snapshot_interval: int, shell_radius: int = 1
) -> DirectionResult:
    if not rule or any(command not in "LRUD" for command in rule):
        raise ValueError("ring-excavator rules must use L/R/U/D")
    if steps < 0 or snapshot_interval <= 0 or shell_radius <= 0:
        raise ValueError("steps must be non-negative; snapshot_interval and shell_radius must be positive")

    field: dict[Vec3, int] = {}
    position: Vec3 = (0, 0, 0)
    forward: Vec3 = (1, 0, 0)
    up: Vec3 = (0, 0, 1)
    trajectory: list[Vec3] = [position]
    snapshots: list[SystemSnapshot] = []
    ring_writes = 0
    center_erases = 0
    phase = 0

    def snapshot(step: int) -> SystemSnapshot:
        return SystemSnapshot(step, (position,), tuple(sorted(field.items())))

    snapshots.append(snapshot(0))
    for step in range(1, steps + 1):
        state = field.get(position, 0)
        command = rule[(phase + state) % len(rule)]
        phase = (phase + 1) % len(rule)
        if position in field:
            center_erases += 1
            field.pop(position)
        forward, up = _rotate(forward, up, command)
        position = _add(position, forward)
        right = _cross(forward, up)
        ring_offsets = []
        for a in range(-shell_radius, shell_radius + 1):
            for b in range(-shell_radius, shell_radius + 1):
                if max(abs(a), abs(b)) == shell_radius:
                    ring_offsets.append(
                        (
                            right[0] * a + up[0] * b,
                            right[1] * a + up[1] * b,
                            right[2] * a + up[2] * b,
                        )
                    )
        for offset in ring_offsets:
            ring_cell = _add(position, offset)
            field[ring_cell] = min(2, field.get(ring_cell, 0) + 1)
            ring_writes += 1
        trajectory.append(position)
        if step % snapshot_interval == 0 or step == steps:
            snapshots.append(snapshot(step))

    solid_cells = sum(state == 2 for state in field.values())
    return DirectionResult(
        system="ring-excavator",
        steps=steps,
        trajectories=(tuple(trajectory),),
        field=tuple(sorted(field.items())),
        snapshots=tuple(snapshots),
        metrics={
            "ring_writes": ring_writes,
            "center_erases": center_erases,
            "shell_radius": shell_radius,
            "solid_cells": solid_cells,
            "scaffold_cells": sum(state == 1 for state in field.values()),
        },
    )


def simulate_collision_colony(
    rule: str,
    steps: int,
    snapshot_interval: int,
    collision_policy: str = "scar-reverse",
    initial_agents: tuple[tuple[Vec3, Vec3, Vec3], ...] | None = None,
    transaction_order: tuple[int, ...] | None = None,
) -> DirectionResult:
    if not rule or any(command not in "LRUD" for command in rule):
        raise ValueError("collision-colony rules must use L/R/U/D")
    if collision_policy not in {"scar-reverse", "frame-exchange"}:
        raise ValueError("unsupported collision policy")
    if steps < 0 or snapshot_interval <= 0:
        raise ValueError("steps must be non-negative and snapshot_interval positive")

    if initial_agents is None:
        initial_agents = (
            ((3, 0, 0), (-1, 0, 0), (0, 0, 1)),
            ((-3, 0, 0), (1, 0, 0), (0, 0, 1)),
            ((0, 3, 0), (0, -1, 0), (0, 0, 1)),
            ((0, -3, 0), (0, 1, 0), (0, 0, 1)),
            ((0, 0, 3), (0, 0, -1), (0, 1, 0)),
            ((0, 0, -3), (0, 0, 1), (0, 1, 0)),
        )
    if transaction_order is None:
        transaction_order = tuple(range(len(initial_agents)))
    if sorted(transaction_order) != list(range(len(initial_agents))):
        raise ValueError("transaction_order must contain every agent exactly once")
    agents: list[list[Vec3]] = [[position, forward, up] for position, forward, up in initial_agents]
    field: dict[Vec3, int] = {}
    trajectories: list[list[Vec3]] = [[agent[0]] for agent in agents]
    collision_positions: set[Vec3] = set()
    collision_count = 0
    frame_exchanges = 0
    snapshots: list[SystemSnapshot] = []

    def snapshot(step: int) -> SystemSnapshot:
        return SystemSnapshot(
            step,
            tuple(agent[0] for agent in agents),
            tuple(sorted(field.items())),
            tuple(sorted(collision_positions)),
            tuple((agent[1], agent[2]) for agent in agents),
        )

    snapshots.append(snapshot(0))
    for step in range(1, steps + 1):
        before = dict(field)
        proposals: dict[Vec3, list[int]] = {}
        rotated_frames: list[tuple[Vec3, Vec3] | None] = [None] * len(agents)
        write_intents: dict[Vec3, list[int]] = {}
        for agent_id in transaction_order:
            position, forward, up = agents[agent_id]
            state = before.get(position, 0)
            written = (state + 1) % 3
            write_intents.setdefault(position, []).append(written)
            command = rule[(state + agent_id % 2) % len(rule)]
            next_forward, next_up = _rotate(forward, up, command)
            rotated_frames[agent_id] = (next_forward, next_up)
            destination = _add(position, next_forward)
            proposals.setdefault(destination, []).append(agent_id)

        for position, states in write_intents.items():
            written = max(states)
            if written:
                field[position] = written
            else:
                field.pop(position, None)

        blocked: set[int] = set()
        exchange_from: dict[int, int] = {}
        for destination, contenders in proposals.items():
            if len(contenders) > 1:
                collision_count += 1
                collision_positions.add(destination)
                field[destination] = 2
                blocked.update(contenders)
                if collision_policy == "frame-exchange":
                    ordered = sorted(contenders)
                    frame_exchanges += len(ordered)
                    for index, agent_id in enumerate(ordered):
                        exchange_from[agent_id] = ordered[(index + 1) % len(ordered)]

        for agent_id, agent in enumerate(agents):
            position = agent[0]
            forward, up = rotated_frames[agent_id]
            destination = _add(position, forward)
            if agent_id in blocked:
                if collision_policy == "frame-exchange":
                    forward, up = rotated_frames[exchange_from[agent_id]]
                else:
                    forward, up = _rotate(forward, up, "R" if agent_id % 2 == 0 else "L")
                destination = position
            agent[:] = [destination, forward, up]
            trajectories[agent_id].append(destination)

        if step % snapshot_interval == 0 or step == steps:
            snapshots.append(snapshot(step))

    return DirectionResult(
        system="collision-colony",
        steps=steps,
        trajectories=tuple(tuple(path) for path in trajectories),
        field=tuple(sorted(field.items())),
        snapshots=tuple(snapshots),
        metrics={
            "collisions": collision_count,
            "contested_cells": len(collision_positions),
            "collision_policy": collision_policy,
            "frame_exchanges": frame_exchanges,
            "occupied_cells": len(field),
            "agent_count": len(agents),
            "schedule": "synchronous-read-intent-commit",
            "transaction_order": transaction_order,
            "initial_agents": initial_agents,
        },
    )


def simulate_chiral_highway_pair(
    rule: str,
    steps: int,
    snapshot_interval: int,
    initial_agents: tuple[tuple[Vec3, Vec3, Vec3], tuple[Vec3, Vec3, Vec3]] | None = None,
    rules: tuple[str, str] | None = None,
    rule_phase_offsets: tuple[int, int] = (0, 0),
) -> DirectionResult:
    if not rule or any(command not in "LRUD" for command in rule):
        raise ValueError("chiral highway rules must use L/R/U/D")
    if steps < 0 or snapshot_interval <= 0:
        raise ValueError("steps must be non-negative and snapshot_interval positive")
    mirrored = rule.translate(str.maketrans({"L": "R", "R": "L"}))
    rule_pairing = "mirrored"
    if rules is None:
        rules = (rule, mirrored)
    else:
        if len(rules[0]) != len(rules[1]) or not rules[0] or any(
            command not in "LRUD" for paired_rule in rules for command in paired_rule
        ):
            raise ValueError("explicit chiral highway rules must be non-empty L/R/U/D strings of equal length")
        rule_pairing = "explicit"
    if len(rule_phase_offsets) != 2:
        raise ValueError("rule_phase_offsets must contain two integers")
    if initial_agents is None:
        initial_agents = (
            ((-1, 0, 0), (0, 1, 0), (0, 0, 1)),
            ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
        )
    agents: list[list[Vec3]] = [[position, forward, up] for position, forward, up in initial_agents]
    field: dict[Vec3, int] = {}
    last_writer: dict[Vec3, int] = {}
    trajectories: list[list[Vec3]] = [[agent[0]] for agent in agents]
    collision_positions: set[Vec3] = set()
    snapshots: list[SystemSnapshot] = []
    collisions = 0
    shared_rewrites = 0

    def snapshot(step: int) -> SystemSnapshot:
        return SystemSnapshot(
            step,
            tuple(agent[0] for agent in agents),
            tuple(sorted(field.items())),
            tuple(sorted(collision_positions)),
            tuple((agent[1], agent[2]) for agent in agents),
        )

    snapshots.append(snapshot(0))
    for step in range(1, steps + 1):
        before = dict(field)
        rotated_frames: list[tuple[Vec3, Vec3]] = []
        destinations: list[Vec3] = []
        writes: list[tuple[Vec3, int, int]] = []
        for agent_id, (position, forward, up) in enumerate(agents):
            state = before.get(position, 0)
            command = rules[agent_id][(state + rule_phase_offsets[agent_id]) % len(rules[agent_id])]
            next_forward, next_up = _rotate(forward, up, command)
            rotated_frames.append((next_forward, next_up))
            destinations.append(_add(position, next_forward))
            writes.append((position, (state + 1) % len(rule), agent_id))
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
        if step % snapshot_interval == 0 or step == steps:
            snapshots.append(snapshot(step))

    return DirectionResult(
        system="chiral-highway-pair",
        steps=steps,
        trajectories=tuple(tuple(path) for path in trajectories),
        field=tuple(sorted(field.items())),
        snapshots=tuple(snapshots),
        metrics={
            "right_rule": rules[0],
            "left_rule": rules[1],
            "rule_pairing": rule_pairing,
            "rule_phase_offsets": rule_phase_offsets,
            "schedule": "synchronous-read-intent-commit",
            "collision_policy": "same-destination-pitch-apart",
            "collisions": collisions,
            "shared_rewrites": shared_rewrites,
            "initial_agents": initial_agents,
            "initial_separation": math.dist(initial_agents[0][0], initial_agents[1][0]),
        },
    )


def simulate_wound_healing_colony(rule: str, steps: int, snapshot_interval: int) -> DirectionResult:
    if not rule or any(command not in "LRUD" for command in rule):
        raise ValueError("wound-healing rules must use L/R/U/D")
    if steps < 0 or snapshot_interval <= 0:
        raise ValueError("steps must be non-negative and snapshot_interval positive")
    agents: list[list[Vec3]] = [
        [(3, 0, 0), (-1, 0, 0), (0, 0, 1)],
        [(-3, 0, 0), (1, 0, 0), (0, 0, 1)],
        [(0, 3, 0), (0, -1, 0), (0, 0, 1)],
        [(0, -3, 0), (0, 1, 0), (0, 0, 1)],
        [(0, 0, 3), (0, 0, -1), (0, 1, 0)],
        [(0, 0, -3), (0, 0, 1), (0, 1, 0)],
    ]
    field: dict[Vec3, float] = {}
    trajectories: list[list[Vec3]] = [[agent[0]] for agent in agents]
    collision_positions: set[Vec3] = set()
    snapshots: list[SystemSnapshot] = []
    collision_count = 0
    wounds_written = 0
    healing_transitions = 0
    erasures = 0

    def snapshot(step: int) -> SystemSnapshot:
        return SystemSnapshot(
            step,
            tuple(agent[0] for agent in agents),
            tuple(sorted(field.items())),
            tuple(sorted(collision_positions)),
            tuple((agent[1], agent[2]) for agent in agents),
        )

    snapshots.append(snapshot(0))
    for step in range(1, steps + 1):
        proposals: dict[Vec3, list[int]] = {}
        rotated_frames: list[tuple[Vec3, Vec3]] = []
        for agent_id, (position, forward, up) in enumerate(agents):
            state = field.get(position, 0.0)
            if state == 0.0:
                field[position] = 0.5
                wounds_written += 1
            elif state == 0.5:
                field[position] = 1.0
                healing_transitions += 1
            else:
                field.pop(position, None)
                erasures += 1
            state_index = 0 if state == 0.0 else 1 if state == 0.5 else 2
            command = rule[(state_index + agent_id % 2) % len(rule)]
            next_forward, next_up = _rotate(forward, up, command)
            destination = _add(position, next_forward)
            rotated_frames.append((next_forward, next_up))
            proposals.setdefault(destination, []).append(agent_id)

        blocked: set[int] = set()
        for destination, contenders in proposals.items():
            if len(contenders) > 1:
                collision_count += 1
                collision_positions.add(destination)
                previous = field.get(destination, 0.0)
                if previous == 0.5:
                    field[destination] = 1.0
                    healing_transitions += 1
                else:
                    field[destination] = 0.5
                    wounds_written += 1
                blocked.update(contenders)

        for agent_id, agent in enumerate(agents):
            position = agent[0]
            forward, up = rotated_frames[agent_id]
            destination = _add(position, forward)
            if agent_id in blocked:
                forward, up = _rotate(forward, up, "R" if agent_id % 2 == 0 else "L")
                destination = position
            agent[:] = [destination, forward, up]
            trajectories[agent_id].append(destination)
        if step % snapshot_interval == 0 or step == steps:
            snapshots.append(snapshot(step))

    return DirectionResult(
        system="wound-healing-colony",
        steps=steps,
        trajectories=tuple(tuple(path) for path in trajectories),
        field=tuple(sorted(field.items())),
        snapshots=tuple(snapshots),
        metrics={
            "rule": rule,
            "semantic_cycle": "0->0.5->1->0",
            "collisions": collision_count,
            "contested_cells": len(collision_positions),
            "wounds_written": wounds_written,
            "healing_transitions": healing_transitions,
            "erasures": erasures,
            "agent_count": len(agents),
        },
    )


def summarize_direction(result: DirectionResult) -> dict[str, object]:
    points = [point for path in result.trajectories for point in path]
    points.extend(point for point, _ in result.field)
    if points:
        xs, ys, zs = zip(*points)
        bounds = [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)]
    else:
        bounds = [0, 0, 0, 0, 0, 0]
    spans = [bounds[3] - bounds[0], bounds[4] - bounds[1], bounds[5] - bounds[2]]
    positive_spans = [span for span in spans if span > 0]
    nonplanarity = min(positive_spans) / max(positive_spans) if len(positive_spans) == 3 else 0.0
    payload = {
        "trajectories": result.trajectories,
        "field": result.field,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    summary: dict[str, object] = {
        "system": result.system,
        "steps": result.steps,
        "agent_count": len(result.trajectories),
        "trajectory_samples": sum(len(path) for path in result.trajectories),
        "field_cells": len(result.field),
        "state_counts": {
            str(state): sum(value == state for _, value in result.field)
            for state in sorted({value for _, value in result.field})
        },
        "bounds": bounds,
        "axis_spans": spans,
        "nonplanarity_ratio": round(nonplanarity, 6),
        "state_sha256": digest,
    }
    summary.update(result.metrics)
    return summary


def render_direction_frames(
    result: DirectionResult,
    output_dir: "Path",
    size: tuple[int, int] = (720, 720),
    profile: str = "default",
) -> list["Path"]:
    from pathlib import Path

    from PIL import Image, ImageDraw, ImageFont

    if profile not in {"default", "microcell", "anatomy"}:
        raise ValueError("unsupported render profile")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    width, height = size
    supersample = 2
    canvas_size = (width * supersample, height * supersample)
    azimuth = -0.78
    elevation = 0.56
    cosine, sine = math.cos(azimuth), math.sin(azimuth)
    sin_elevation, cos_elevation = math.sin(elevation), math.cos(elevation)

    def project_raw(point: Vec3) -> tuple[float, float, float]:
        x, y, z = point
        screen_x = x * cosine - y * sine
        screen_y = x * sine * sin_elevation + y * cosine * sin_elevation + z * cos_elevation
        depth = -x * sine * cos_elevation - y * cosine * cos_elevation + z * sin_elevation
        return screen_x, screen_y, depth

    all_points = [point for path in result.trajectories for point in path]
    all_points.extend(point for point, _ in result.field)
    projected = [project_raw(point) for point in all_points] or [(0.0, 0.0, 0.0)]
    min_x, max_x = min(p[0] for p in projected), max(p[0] for p in projected)
    min_y, max_y = min(p[1] for p in projected), max(p[1] for p in projected)
    span_x, span_y = max(1.0, max_x - min_x), max(1.0, max_y - min_y)
    scale = min(canvas_size[0] * 0.78 / span_x, canvas_size[1] * 0.72 / span_y)
    center_x, center_y = (min_x + max_x) * 0.5, (min_y + max_y) * 0.5

    def project(point: Vec3) -> tuple[int, int, float]:
        x, y, depth = project_raw(point)
        return (
            round(canvas_size[0] * 0.5 + (x - center_x) * scale),
            round(canvas_size[1] * 0.52 - (y - center_y) * scale),
            depth,
        )

    lineage_colors = ((72, 224, 180), (170, 188, 184), (204, 176, 154), (145, 170, 198), (198, 157, 195), (165, 195, 137))
    paths: list[Path] = []
    for frame_index, snapshot in enumerate(result.snapshots):
        image = Image.new("RGB", canvas_size, (8, 10, 10))
        draw = ImageDraw.Draw(image, "RGB")
        for point, state in sorted(snapshot.field, key=lambda item: project_raw(item[0])[2]):
            px, py, _ = project(point)
            radius = 1 if profile == "microcell" else 2
            if state == 0.5:
                color = (61, 91, 82)
            elif state == 1:
                color = (92, 111, 105)
            elif state == 2:
                color = (139, 151, 145)
            else:
                color = (169, 176, 171)
            draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=color)
        for agent_id, trajectory in enumerate(result.trajectories):
            visible = trajectory[: min(len(trajectory), snapshot.step + 1)]
            visible = visible[-256:]
            if len(visible) > 1:
                points = [(project(point)[0], project(point)[1]) for point in visible]
                draw.line(
                    points,
                    fill=lineage_colors[agent_id % len(lineage_colors)],
                    width=2 if profile == "microcell" else 3,
                )
        for event in snapshot.event_positions:
            px, py, _ = project(event)
            draw.ellipse((px - 6, py - 6, px + 6, py + 6), outline=(235, 89, 139), width=2)
        for agent_id, position in enumerate(snapshot.agent_positions):
            px, py, _ = project(position)
            color = lineage_colors[agent_id % len(lineage_colors)]
            agent_radius = 3 if profile == "microcell" else 5
            draw.ellipse(
                (px - agent_radius, py - agent_radius, px + agent_radius, py + agent_radius),
                fill=color,
                outline=(244, 246, 240),
                width=1,
            )
        if profile == "anatomy":
            for position, (forward, up) in zip(snapshot.agent_positions, snapshot.agent_frames):
                origin = project(position)
                forward_tip = project(
                    (position[0] + forward[0] * 8, position[1] + forward[1] * 8, position[2] + forward[2] * 8)
                )
                up_tip = project((position[0] + up[0] * 8, position[1] + up[1] * 8, position[2] + up[2] * 8))
                draw.line((origin[:2], forward_tip[:2]), fill=(237, 104, 94), width=3)
                draw.line((origin[:2], up_tip[:2]), fill=(104, 157, 235), width=3)

            panel_margin = 16
            panel_gap = 10
            panel_height = round(canvas_size[1] * 0.24)
            panel_width = (canvas_size[0] - panel_margin * 2 - panel_gap * 2) // 3
            panel_top = canvas_size[1] - panel_height - panel_margin
            axis_pairs = ((0, 1, "XY"), (0, 2, "XZ"), (1, 2, "YZ"))
            coordinate_ranges = [
                (min(point[axis] for point in all_points), max(point[axis] for point in all_points))
                for axis in range(3)
            ]
            for panel_index, (axis_a, axis_b, label) in enumerate(axis_pairs):
                left = panel_margin + panel_index * (panel_width + panel_gap)
                right = left + panel_width
                bottom = panel_top + panel_height
                draw.rectangle((left, panel_top, right, bottom), fill=(11, 14, 14), outline=(70, 82, 78), width=1)
                min_a, max_a = coordinate_ranges[axis_a]
                min_b, max_b = coordinate_ranges[axis_b]
                span_a, span_b = max(1, max_a - min_a), max(1, max_b - min_b)
                panel_scale = min((panel_width - 22) / span_a, (panel_height - 34) / span_b)

                def panel_point(point: Vec3) -> tuple[int, int]:
                    return (
                        round(left + 11 + (point[axis_a] - min_a) * panel_scale),
                        round(bottom - 11 - (point[axis_b] - min_b) * panel_scale),
                    )

                for point, _ in snapshot.field:
                    sx, sy = panel_point(point)
                    draw.point((sx, sy), fill=(103, 116, 111))
                for agent_id, trajectory in enumerate(result.trajectories):
                    visible = trajectory[: min(len(trajectory), snapshot.step + 1)][-256:]
                    if len(visible) > 1:
                        draw.line(
                            [panel_point(point) for point in visible],
                            fill=lineage_colors[agent_id % len(lineage_colors)],
                            width=2,
                        )
                draw.text((left + 8, panel_top + 6), label, fill=(196, 203, 196), font=ImageFont.load_default())
        draw.text((28, 24), result.system.upper().replace("-", " "), fill=(220, 224, 216), font=ImageFont.load_default())
        draw.text((28, 44), f"STEP {snapshot.step:07d}", fill=(129, 141, 136), font=ImageFont.load_default())
        image = image.resize(size, Image.Resampling.LANCZOS)
        path = output_dir / f"frame-{frame_index:04d}.png"
        image.save(path)
        paths.append(path)
    return paths


def package_direction(
    result: DirectionResult,
    output_dir: "Path",
    fps: int = 12,
    size: tuple[int, int] = (720, 720),
    ffmpeg: str = "ffmpeg",
    render_profile: str = "default",
) -> dict[str, "Path"]:
    from pathlib import Path

    from PIL import Image, ImageDraw, ImageFont

    if fps <= 0:
        raise ValueError("fps must be positive")
    executable = shutil.which(ffmpeg)
    if not executable:
        raise FileNotFoundError(f"ffmpeg executable not found: {ffmpeg}")
    output_dir = Path(output_dir)
    frames_dir = output_dir / "frames"
    stills_dir = output_dir / "stills"
    frames_dir.mkdir(parents=True, exist_ok=True)
    stills_dir.mkdir(parents=True, exist_ok=True)
    for stale in frames_dir.glob("frame-*.png"):
        stale.unlink()
    frames = render_direction_frames(result, frames_dir, size=size, profile=render_profile)

    video = output_dir / "motion-timelapse.mp4"
    if video.exists():
        video.unlink()
    subprocess.run(
        [
            executable,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(frames_dir / "frame-%04d.png"),
            "-frames:v",
            str(len(frames)),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(video),
        ],
        check=True,
    )
    if not video.exists() or video.stat().st_size == 0:
        raise RuntimeError("ffmpeg did not create the review video")

    indices = {"early": 0, "middle": len(frames) // 2, "late": len(frames) - 1}
    still_paths: dict[str, Path] = {}
    for label, index in indices.items():
        target = stills_dir / f"{label}.png"
        shutil.copy2(frames[index], target)
        still_paths[label] = target

    contact_sheet = output_dir / "contact-sheet.png"
    sheet = Image.new("RGB", (size[0] * 3, size[1] + 32), (17, 19, 18))
    draw = ImageDraw.Draw(sheet)
    for column, (label, path) in enumerate(still_paths.items()):
        with Image.open(path) as image:
            sheet.paste(image.convert("RGB"), (column * size[0], 32))
        draw.text((column * size[0] + 12, 10), label.upper(), fill=(220, 224, 216), font=ImageFont.load_default())
    sheet.save(contact_sheet)

    metrics_path = output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(summarize_direction(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def record(path: Path) -> dict[str, object]:
        data = path.read_bytes()
        return {
            "path": path.relative_to(output_dir).as_posix(),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }

    receipt_path = output_dir / "receipt.json"
    receipt = {
        "schema_version": 1,
        "system": result.system,
        "steps": result.steps,
        "frame_semantics": "Each encoded frame is a true deterministic simulation snapshot; intervals are timelapsed, not interpolated.",
        "render_profile": render_profile,
        "fps": fps,
        "size": list(size),
        "frames": [record(path) for path in frames],
        "artifacts": {
            "video": record(video),
            "contact_sheet": record(contact_sheet),
            "metrics": record(metrics_path),
            **{label: record(path) for label, path in still_paths.items()},
        },
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "video": video,
        "contact_sheet": contact_sheet,
        "metrics": metrics_path,
        "receipt": receipt_path,
        **still_paths,
    }


def detect_tail_period(commands: tuple[str, ...], candidates: list[int]) -> int | None:
    for period in sorted(candidates):
        if period > 0 and len(commands) >= period * 3:
            tail = commands[-period:]
            if tail == commands[-2 * period : -period] == commands[-3 * period : -2 * period]:
                return period
    return None
