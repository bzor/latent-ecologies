from __future__ import annotations

import math
from collections.abc import Mapping

from houdini_ai.fieldwriting_ants import (
    DirectionResult,
    Vec3,
    simulate_chiral_highway_pair,
    simulate_collision_colony,
    summarize_direction,
)

AgentFrame = tuple[Vec3, Vec3, Vec3]
PairInitialState = tuple[AgentFrame, AgentFrame]
ColonyInitialState = tuple[AgentFrame, ...]


def serializable_robustness_report(report: Mapping[str, object]) -> dict[str, object]:
    serialized = dict(report)
    serialized["variants"] = [
        {key: value for key, value in variant.items() if key != "result"}
        for variant in report["variants"]
    ]
    return serialized


def _path_distance(path: tuple[Vec3, ...]) -> int:
    return sum(
        abs(b[0] - a[0]) + abs(b[1] - a[1]) + abs(b[2] - a[2])
        for a, b in zip(path, path[1:])
    )


def _variant_record(variant_id: str, result: DirectionResult) -> dict[str, object]:
    summary = summarize_direction(result)
    distances = [_path_distance(path) for path in result.trajectories]
    endpoint_separation = math.dist(result.trajectories[0][-1], result.trajectories[1][-1])
    return {
        "id": variant_id,
        "initial_agents": result.metrics["initial_agents"],
        "initial_separation": result.metrics["initial_separation"],
        "collisions": result.metrics["collisions"],
        "shared_rewrites": result.metrics["shared_rewrites"],
        "path_distances": distances,
        "path_balance": min(distances) / max(distances) if max(distances) else 1.0,
        "endpoint_separation": endpoint_separation,
        "axis_spans": summary["axis_spans"],
        "nonplanarity_ratio": summary["nonplanarity_ratio"],
        "field_cells": summary["field_cells"],
        "state_sha256": summary["state_sha256"],
        "result": result,
    }


def run_a3_robustness_matrix(
    configurations: Mapping[str, PairInitialState],
    *,
    steps: int,
    snapshot_interval: int,
    rule: str = "RLRUUUL",
) -> dict[str, object]:
    variants = []
    for variant_id, initial_agents in configurations.items():
        result = simulate_chiral_highway_pair(
            rule,
            steps=steps,
            snapshot_interval=snapshot_interval,
            initial_agents=initial_agents,
        )
        variants.append(_variant_record(variant_id, result))
    return {
        "schema_version": 1,
        "branch": "A3",
        "rule": rule,
        "mirrored_rule": rule.translate(str.maketrans({"L": "R", "R": "L"})),
        "steps": steps,
        "schedule": "synchronous-read-intent-commit",
        "variant_count": len(variants),
        "variants": variants,
    }


def run_c2_robustness_matrix(
    configurations: Mapping[str, ColonyInitialState],
    *,
    steps: int,
    snapshot_interval: int,
    rule: str = "RLRU",
) -> dict[str, object]:
    variants = []
    for variant_id, initial_agents in configurations.items():
        forward_order = tuple(range(len(initial_agents)))
        reverse_order = tuple(reversed(forward_order))
        forward = simulate_collision_colony(
            rule,
            steps=steps,
            snapshot_interval=snapshot_interval,
            collision_policy="frame-exchange",
            initial_agents=initial_agents,
            transaction_order=forward_order,
        )
        reverse = simulate_collision_colony(
            rule,
            steps=steps,
            snapshot_interval=snapshot_interval,
            collision_policy="frame-exchange",
            initial_agents=initial_agents,
            transaction_order=reverse_order,
        )
        summary = summarize_direction(forward)
        distances = [_path_distance(path) for path in forward.trajectories]
        variants.append(
            {
                "id": variant_id,
                "initial_agents": initial_agents,
                "collisions": forward.metrics["collisions"],
                "contested_cells": forward.metrics["contested_cells"],
                "frame_exchanges": forward.metrics["frame_exchanges"],
                "transaction_order_invariant": (
                    forward.field == reverse.field and forward.trajectories == reverse.trajectories
                ),
                "path_distances": distances,
                "path_balance": min(distances) / max(distances) if max(distances) else 1.0,
                "axis_spans": summary["axis_spans"],
                "nonplanarity_ratio": summary["nonplanarity_ratio"],
                "field_cells": summary["field_cells"],
                "state_sha256": summary["state_sha256"],
                "result": forward,
            }
        )
    return {
        "schema_version": 1,
        "branch": "C2",
        "rule": rule,
        "collision_policy": "frame-exchange",
        "schedule": "synchronous-read-intent-commit",
        "order_sensitivity_test": "forward-versus-reverse-intent-enumeration",
        "steps": steps,
        "variant_count": len(variants),
        "variants": variants,
    }
