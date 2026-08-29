"""Deterministic reference model for the Nonlocal Affinity Dance baseline."""

from __future__ import annotations

import math
import hashlib
import json
import random
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class AffinityParameters:
    contraction: float = 0.995
    attraction: float = 0.02
    repulsion: float = 0.01
    softening: float = 0.01


@dataclass(frozen=True)
class AffinityState:
    positions: tuple[tuple[float, ...], ...]
    friends: tuple[int, ...]
    enemies: tuple[int, ...]


@dataclass(frozen=True)
class RewireEvent:
    point: int
    friend: int
    enemy: int


@dataclass(frozen=True)
class AffinityConfig:
    seed: int
    agent_count: int
    steps: int
    dimensions: int = 2
    rewire_gate_denominator: int = 1000
    rewire_gate_exclusive_max: int = 100
    rewires_per_event: int = 1
    parameters: AffinityParameters = AffinityParameters()


def baseline_config(*, seed: int = 122095, agent_count: int = 1000, steps: int = 240) -> AffinityConfig:
    return AffinityConfig(seed=seed, agent_count=agent_count, steps=steps)


def _validate_state(state: AffinityState) -> tuple[int, int]:
    count = len(state.positions)
    if count == 0:
        raise ValueError("affinity state requires at least one point")
    dimensions = len(state.positions[0])
    if dimensions < 1 or any(len(position) != dimensions for position in state.positions):
        raise ValueError("all affinity positions must share a nonzero dimensionality")
    if len(state.friends) != count or len(state.enemies) != count:
        raise ValueError("friend and enemy arrays must match the point count")
    if any(index < 0 or index >= count for index in (*state.friends, *state.enemies)):
        raise ValueError("friend and enemy indices must reference existing points")
    if any(not math.isfinite(value) for position in state.positions for value in position):
        raise ValueError("affinity positions must be finite")
    return count, dimensions


def _softened_direction(origin: tuple[float, ...], target: tuple[float, ...], softening: float) -> tuple[float, ...]:
    offset = tuple(target[axis] - origin[axis] for axis in range(len(origin)))
    denominator = softening + math.sqrt(sum(value * value for value in offset))
    return tuple(value / denominator for value in offset)


def step_state(
    state: AffinityState,
    parameters: AffinityParameters,
    rewire: RewireEvent | Sequence[RewireEvent] | None = None,
) -> AffinityState:
    """Advance every point synchronously by the source equation."""

    count, dimensions = _validate_state(state)
    if parameters.softening <= 0.0:
        raise ValueError("softening must be positive")
    positions = state.positions
    friends = list(state.friends)
    enemies = list(state.enemies)
    rewires = () if rewire is None else (rewire,) if isinstance(rewire, RewireEvent) else tuple(rewire)
    for event in rewires:
        if not isinstance(event, RewireEvent):
            raise TypeError("rewire batches must contain RewireEvent values")
        if any(index < 0 or index >= count for index in (event.point, event.friend, event.enemy)):
            raise ValueError("rewire indices must reference existing points")
        friends[event.point] = event.friend
        enemies[event.point] = event.enemy
    updated: list[tuple[float, ...]] = []
    for point, position in enumerate(positions):
        toward = _softened_direction(position, positions[friends[point]], parameters.softening)
        away = _softened_direction(position, positions[enemies[point]], parameters.softening)
        updated.append(tuple(
            parameters.contraction * position[axis]
            + parameters.attraction * toward[axis]
            - parameters.repulsion * away[axis]
            for axis in range(dimensions)
        ))
    return AffinityState(tuple(updated), tuple(friends), tuple(enemies))


def _initialize(config: AffinityConfig, rng: random.Random) -> AffinityState:
    if config.agent_count < 1 or config.steps < 0 or config.dimensions < 1:
        raise ValueError("agent_count and dimensions must be positive and steps must be nonnegative")
    positions = tuple(
        tuple(rng.uniform(-1.0, 1.0) for _ in range(config.dimensions))
        for _ in range(config.agent_count)
    )
    friends = tuple(rng.randrange(config.agent_count) for _ in range(config.agent_count))
    enemies = tuple(rng.randrange(config.agent_count) for _ in range(config.agent_count))
    return AffinityState(positions, friends, enemies)


class _Mulberry32:
    """Unsigned 32-bit implementation matching the Canvas JavaScript RNG."""

    def __init__(self, seed: int) -> None:
        self.state = seed & 0xFFFFFFFF

    @staticmethod
    def _imul(left: int, right: int) -> int:
        return ((left & 0xFFFFFFFF) * (right & 0xFFFFFFFF)) & 0xFFFFFFFF

    def random(self) -> float:
        self.state = (self.state + 0x6D2B79F5) & 0xFFFFFFFF
        value = self.state
        value = self._imul(value ^ (value >> 15), value | 1)
        value ^= (value + self._imul(value ^ (value >> 7), value | 61)) & 0xFFFFFFFF
        value &= 0xFFFFFFFF
        return ((value ^ (value >> 14)) & 0xFFFFFFFF) / 4294967296.0


def _state_digest(state: AffinityState) -> str:
    payload = {
        "positions": [[round(value, 12) for value in position] for position in state.positions],
        "friends": list(state.friends),
        "enemies": list(state.enemies),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def relationship_digest(friends: Sequence[int], enemies: Sequence[int]) -> str:
    """Hash relationship topology independently from floating-point positions."""

    if len(friends) != len(enemies):
        raise ValueError("friend and enemy arrays must have equal length")
    payload = {"friends": [int(value) for value in friends], "enemies": [int(value) for value in enemies]}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def final_prepared_relationships(prepared: dict[str, object]) -> tuple[list[int], list[int]]:
    """Apply an ordered prepared event schedule without integrating positions."""

    friends = [int(value) for value in prepared["friends"]]
    enemies = [int(value) for value in prepared["enemies"]]
    if len(friends) != len(enemies):
        raise ValueError("friend and enemy arrays must have equal length")
    count = len(friends)
    for event in prepared["rewire_events"]:
        point = int(event["point"])
        friend = int(event["friend"])
        enemy = int(event["enemy"])
        if any(index < 0 or index >= count for index in (point, friend, enemy)):
            raise ValueError("prepared rewire event references a missing point")
        friends[point] = friend
        enemies[point] = enemy
    return friends, enemies


def _checkpoint(step: int, state: AffinityState, prior: AffinityState | None) -> dict[str, object]:
    radii = [math.sqrt(sum(value * value for value in position)) for position in state.positions]
    displacements = [] if prior is None else [
        math.sqrt(sum((value - prior.positions[index][axis]) ** 2 for axis, value in enumerate(position)))
        for index, position in enumerate(state.positions)
    ]
    dimensions = len(state.positions[0])
    bounds = [
        [min(position[axis] for position in state.positions), max(position[axis] for position in state.positions)]
        for axis in range(dimensions)
    ]
    return {
        "step": step,
        "bounds": bounds,
        "radial_extent": max(radii),
        "radial_mean": sum(radii) / len(radii),
        "displacement_mean": sum(displacements) / len(displacements) if displacements else 0.0,
    }


def prepare_reference_run(config: AffinityConfig) -> dict[str, object]:
    """Prepare initialization and stochastic events without evolving positions."""

    if config.rewire_gate_denominator < 1 or not 1 <= config.rewire_gate_exclusive_max <= config.rewire_gate_denominator + 1:
        raise ValueError("invalid rewire gate")
    if config.rewires_per_event < 1:
        raise ValueError("rewires_per_event must be positive")
    rng = random.Random(config.seed)
    state = _initialize(config, rng)
    events: list[dict[str, int]] = []
    for step in range(1, config.steps + 1):
        if rng.randint(1, config.rewire_gate_denominator) < config.rewire_gate_exclusive_max:
            for _ in range(config.rewires_per_event):
                events.append({
                    "step": step,
                    "point": rng.randrange(config.agent_count),
                    "friend": rng.randrange(config.agent_count),
                    "enemy": rng.randrange(config.agent_count),
                })
    return {
        "initial_positions": [list(position) for position in state.positions],
        "friends": list(state.friends),
        "enemies": list(state.enemies),
        "rewire_events": events,
    }


def prepare_canvas_run(config: AffinityConfig, *, rewire_probability: float) -> dict[str, object]:
    """Recreate the browser's Mulberry32 initialization and event draw order exactly."""

    if config.dimensions != 2:
        raise ValueError("Canvas receipts require dimensions=2")
    if config.agent_count < 2 or config.steps < 0:
        raise ValueError("Canvas receipts require at least two agents and nonnegative steps")
    if not 0.0 <= rewire_probability <= 1.0:
        raise ValueError("rewire_probability must be from zero to one")
    if config.rewires_per_event < 1:
        raise ValueError("rewires_per_event must be positive")
    rng = _Mulberry32(config.seed)
    flat_positions = [rng.random() * 2.0 - 1.0 for _ in range(config.agent_count * 2)]
    positions = [flat_positions[index:index + 2] for index in range(0, len(flat_positions), 2)]
    friends = [int(rng.random() * config.agent_count) for _ in range(config.agent_count)]
    enemies = [int(rng.random() * config.agent_count) for _ in range(config.agent_count)]
    events: list[dict[str, int]] = []
    for step in range(1, config.steps + 1):
        if rng.random() < rewire_probability:
            for _ in range(config.rewires_per_event):
                events.append({
                    "step": step,
                    "point": int(rng.random() * config.agent_count),
                    "friend": int(rng.random() * config.agent_count),
                    "enemy": int(rng.random() * config.agent_count),
                })
    return {
        "initial_positions": positions,
        "friends": friends,
        "enemies": enemies,
        "rewire_events": events,
    }


def lift_prepared_to_3d(
    prepared: dict[str, object], *, seed: int, depth: float,
) -> dict[str, object]:
    """Add independent deterministic Z depth without changing the prepared XY graph or events."""

    if not math.isfinite(depth) or depth < 0.0:
        raise ValueError("depth must be finite and nonnegative")
    positions = prepared.get("initial_positions")
    if not isinstance(positions, list) or not positions or any(len(position) != 2 for position in positions):
        raise ValueError("3D lift requires a nonempty two-dimensional prepared state")
    rng = _Mulberry32(seed ^ 0x9E3779B9)
    return {
        "initial_positions": [
            [float(position[0]), float(position[1]), (rng.random() * 2.0 - 1.0) * depth]
            for position in positions
        ],
        "friends": list(prepared["friends"]),
        "enemies": list(prepared["enemies"]),
        "rewire_events": [dict(event) for event in prepared["rewire_events"]],
    }


def _cohort_route(
    anchor: int,
    target: int,
    member: int,
    cohort_size: int,
    edge_salt: int,
    routing: str,
) -> int:
    if routing == "parallel":
        return member
    value = (
        (anchor + 1) * 0x9E3779B1
        ^ (target + 1) * 0x85EBCA77
        ^ (member + 1) * 0xC2B2AE3D
        ^ edge_salt
    ) & 0xFFFFFFFF
    value ^= value >> 16
    if routing == "neighbor":
        return (member + value % 3 - 1) % cohort_size
    if routing == "mixed":
        return value % cohort_size
    raise ValueError("routing must be parallel, neighbor, or mixed")


def cohort_lift_prepared(
    prepared: dict[str, object],
    *,
    seed: int,
    cohort_size: int,
    radius: float,
    routing: str,
) -> dict[str, object]:
    """Replicate each 3D graph node while preserving every macro edge and event."""

    positions = prepared.get("initial_positions")
    friends = prepared.get("friends")
    enemies = prepared.get("enemies")
    events = prepared.get("rewire_events")
    if not isinstance(positions, list) or not positions or any(len(position) != 3 for position in positions):
        raise ValueError("cohort lift requires a nonempty three-dimensional prepared state")
    count = len(positions)
    if not isinstance(friends, list) or not isinstance(enemies, list) or len(friends) != count or len(enemies) != count:
        raise ValueError("cohort lift relationship arrays must match the anchor count")
    if not isinstance(events, list):
        raise ValueError("cohort lift requires an ordered event list")
    if cohort_size < 1:
        raise ValueError("cohort_size must be positive")
    if not math.isfinite(radius) or radius < 0.0:
        raise ValueError("radius must be finite and nonnegative")
    if routing not in {"parallel", "neighbor", "mixed"}:
        raise ValueError("routing must be parallel, neighbor, or mixed")

    rng = _Mulberry32(seed ^ 0xA511E9B3)
    lifted_positions: list[list[float]] = []
    for position in positions:
        lifted_positions.append([float(value) for value in position])
        for _member in range(1, cohort_size):
            azimuth = rng.random() * math.tau
            z_unit = rng.random() * 2.0 - 1.0
            radial = radius * (rng.random() ** (1.0 / 3.0))
            planar = math.sqrt(max(0.0, 1.0 - z_unit * z_unit))
            lifted_positions.append([
                float(position[0]) + radial * planar * math.cos(azimuth),
                float(position[1]) + radial * planar * math.sin(azimuth),
                float(position[2]) + radial * z_unit,
            ])

    lifted_friends: list[int] = []
    lifted_enemies: list[int] = []
    for anchor in range(count):
        friend_anchor = int(friends[anchor])
        enemy_anchor = int(enemies[anchor])
        for member in range(cohort_size):
            lifted_friends.append(
                friend_anchor * cohort_size
                + _cohort_route(anchor, friend_anchor, member, cohort_size, 0xF17E1D, routing)
            )
            lifted_enemies.append(
                enemy_anchor * cohort_size
                + _cohort_route(anchor, enemy_anchor, member, cohort_size, 0xE9E11D, routing)
            )

    lifted_events: list[dict[str, int]] = []
    for event in events:
        anchor = int(event["point"])
        friend_anchor = int(event["friend"])
        enemy_anchor = int(event["enemy"])
        for member in range(cohort_size):
            lifted_events.append({
                "step": int(event["step"]),
                "point": anchor * cohort_size + member,
                "friend": friend_anchor * cohort_size
                + _cohort_route(anchor, friend_anchor, member, cohort_size, 0xF17E1D, routing),
                "enemy": enemy_anchor * cohort_size
                + _cohort_route(anchor, enemy_anchor, member, cohort_size, 0xE9E11D, routing),
            })
    return {
        "initial_positions": lifted_positions,
        "friends": lifted_friends,
        "enemies": lifted_enemies,
        "rewire_events": lifted_events,
    }


def simulate_prepared(
    config: AffinityConfig,
    prepared: dict[str, object],
    *,
    engine: str = "python-prepared-replay",
) -> dict[str, object]:
    """Replay an explicitly prepared graph and event schedule through the source equation."""

    state = AffinityState(
        tuple(tuple(position) for position in prepared["initial_positions"]),
        tuple(prepared["friends"]),
        tuple(prepared["enemies"]),
    )
    checkpoint_steps = {round(config.steps * fraction / 5) for fraction in range(6)}
    checkpoints = [_checkpoint(0, state, None)]
    events = list(prepared["rewire_events"])
    events_by_step: dict[int, list[dict[str, int]]] = {}
    for event in events:
        events_by_step.setdefault(event["step"], []).append(event)
    for step in range(1, config.steps + 1):
        source_events = events_by_step.get(step, [])
        step_rewires = tuple(
            RewireEvent(point=event["point"], friend=event["friend"], enemy=event["enemy"])
            for event in source_events
        )
        prior = state
        state = step_state(state, config.parameters, step_rewires)
        if step in checkpoint_steps:
            checkpoints.append(_checkpoint(step, state, prior))
    invalid_values = sum(
        not math.isfinite(value)
        for position in state.positions
        for value in position
    )
    return {
        "engine": engine,
        "state_authority": "python-reference",
        "seed": config.seed,
        "agent_count": config.agent_count,
        "dimensions": config.dimensions,
        "steps": config.steps,
        "parameters": {
            "contraction": config.parameters.contraction,
            "attraction": config.parameters.attraction,
            "repulsion": config.parameters.repulsion,
            "softening": config.parameters.softening,
        },
        "rewire_events": events,
        "rewire_count": len(events),
        "rewires_per_event": config.rewires_per_event,
        "invalid_values": invalid_values,
        "state_sha256": _state_digest(state),
        "final_positions": [list(position) for position in state.positions],
        "friends": list(state.friends),
        "enemies": list(state.enemies),
        "checkpoints": checkpoints,
    }


def simulate_reference(config: AffinityConfig) -> dict[str, object]:
    """Run the faithful seeded CPU model and return JSON-compatible diagnostics."""

    return simulate_prepared(config, prepare_reference_run(config), engine="python-reference")
