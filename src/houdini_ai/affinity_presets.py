"""Validated handoff from browser affinity candidates to Python/VEX run preparation."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .nonlocal_affinity import AffinityConfig, AffinityParameters
from .studio_schema import validate_record


_REWIRE_GATE_DENOMINATOR = 1000


def affinity_config_from_preset(
    preset: dict[str, Any],
    *,
    agent_count: int,
    dimensions: int,
    steps: int,
) -> AffinityConfig:
    """Create a production config from an inert candidate without authorizing execution.

    The browser's Mulberry32 initialization is preview-only. Production preparation uses
    the canonical Python stochastic receipt and VEX integration while preserving the
    candidate's seed, force law, and per-step rewiring probability.
    """

    validation_value = deepcopy(preset)
    validation_value.setdefault("id", "affinity-preset-portable")
    validation_value.setdefault("state", "candidate")
    validation_value.setdefault("visibility", "private")
    validation_value.setdefault("created_at", "1970-01-01T00:00:00+00:00")
    errors = validate_record("affinity-preset", validation_value)
    if errors:
        raise ValueError("invalid affinity preset: " + "; ".join(errors))
    if preset["production_hint"]["execution_authorized"] is not False:
        raise ValueError("affinity preset must not authorize execution")
    if not isinstance(agent_count, int) or agent_count < 2:
        raise ValueError("agent_count must be an integer of at least 2")
    if not isinstance(dimensions, int) or dimensions < 1:
        raise ValueError("dimensions must be a positive integer")
    if not isinstance(steps, int) or steps < 0:
        raise ValueError("steps must be a nonnegative integer")

    parameters = preset["parameters"]
    probability = float(preset["rewiring"]["probability_per_simulation_step"])
    exclusive_max = round(probability * _REWIRE_GATE_DENOMINATOR) + 1
    exclusive_max = max(1, min(_REWIRE_GATE_DENOMINATOR + 1, exclusive_max))
    return AffinityConfig(
        seed=int(preset["seed"]),
        agent_count=agent_count,
        steps=steps,
        dimensions=dimensions,
        rewire_gate_denominator=_REWIRE_GATE_DENOMINATOR,
        rewire_gate_exclusive_max=exclusive_max,
        rewires_per_event=int(preset["rewiring"]["rewires_per_event"]),
        parameters=AffinityParameters(
            contraction=float(parameters["contraction"]),
            attraction=float(parameters["attraction"]),
            repulsion=float(parameters["repulsion"]),
            softening=float(parameters["softening"]),
        ),
    )


def load_affinity_preset(
    path: Path,
    *,
    agent_count: int,
    dimensions: int,
    steps: int,
) -> AffinityConfig:
    """Load a saved Studio or downloaded candidate and prepare its production config."""

    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("affinity preset must be a JSON object")
    return affinity_config_from_preset(value, agent_count=agent_count, dimensions=dimensions, steps=steps)
