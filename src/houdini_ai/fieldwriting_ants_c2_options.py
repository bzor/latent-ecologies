from __future__ import annotations

from collections import OrderedDict

from houdini_ai.fieldwriting_ants import DirectionResult, Vec3

AgentSeed = tuple[Vec3, Vec3, Vec3]


def _radius_two_control() -> tuple[AgentSeed, ...]:
    return (
        ((2, 0, 0), (-1, 0, 0), (0, 0, 1)),
        ((-2, 0, 0), (1, 0, 0), (0, 0, 1)),
        ((0, 2, 0), (0, -1, 0), (0, 0, 1)),
        ((0, -2, 0), (0, 1, 0), (0, 0, 1)),
        ((0, 0, 2), (0, 0, -1), (0, 1, 0)),
        ((0, 0, -2), (0, 0, 1), (0, 1, 0)),
    )


def c2_compact_configurations() -> OrderedDict[str, dict[str, object]]:
    common = {
        "rule": "RLRU",
        "collision_policy": "frame-exchange",
        "schedule": "synchronous-read-intent-commit",
        "agent_count": 6,
        "seed_scale": "compact-radius-2",
    }
    return OrderedDict(
        (
            (
                "radius-2-control",
                {
                    **common,
                    "initial_agents": _radius_two_control(),
                    "parameter_edit": "none",
                    "hypothesis": "Compact octahedral control with inward headings and matched pair rolls.",
                },
            ),
            (
                "torsion-cage",
                {
                    **common,
                    "initial_agents": (
                        ((2, 0, 0), (-1, 0, 0), (0, 1, 0)),
                        ((-2, 0, 0), (1, 0, 0), (0, -1, 0)),
                        ((0, 2, 0), (0, -1, 0), (1, 0, 0)),
                        ((0, -2, 0), (0, 1, 0), (-1, 0, 0)),
                        ((0, 0, 2), (0, 0, -1), (0, 1, 0)),
                        ((0, 0, -2), (0, 0, 1), (0, -1, 0)),
                    ),
                    "parameter_edit": "opposed body-frame roll on each radius-2 axis pair",
                    "hypothesis": "Opposed rolls should convert the compact core into a chiral volumetric cage.",
                },
            ),
            (
                "split-core",
                {
                    **common,
                    "initial_agents": (
                        ((2, 0, 0), (-1, 0, 0), (0, 0, 1)),
                        ((-2, 0, 1), (1, 0, 0), (0, 0, 1)),
                        ((0, 2, 0), (0, -1, 0), (1, 0, 0)),
                        ((1, -2, 0), (0, 1, 0), (0, 0, 1)),
                        ((0, 0, 2), (0, 0, -1), (0, 1, 0)),
                        ((0, 1, -2), (0, 0, 1), (1, 0, 0)),
                    ),
                    "parameter_edit": "offset one member of each opposing pair by one cell around the core",
                    "hypothesis": "A one-cell helical stagger should distribute transactions through a split compact nucleus.",
                },
            ),
            (
                "orbital-cage",
                {
                    **common,
                    "initial_agents": (
                        ((2, 0, 0), (0, 1, 0), (0, 0, 1)),
                        ((-2, 0, 0), (0, -1, 0), (0, 0, 1)),
                        ((0, 2, 0), (0, 0, 1), (1, 0, 0)),
                        ((0, -2, 0), (0, 0, -1), (1, 0, 0)),
                        ((0, 0, 2), (1, 0, 0), (0, 1, 0)),
                        ((0, 0, -2), (-1, 0, 0), (0, 1, 0)),
                    ),
                    "parameter_edit": "tangent heading circulation around the radius-2 octahedron",
                    "hypothesis": "Tangential starts should produce recurrent frame exchange around a balanced cubic envelope.",
                },
            ),
        )
    )


def c2_prewarmed_configurations() -> OrderedDict[str, dict[str, object]]:
    compact = c2_compact_configurations()
    common = {
        "rule": "RLRU",
        "collision_policy": "frame-exchange",
        "schedule": "synchronous-read-intent-commit",
        "agent_count": 6,
        "seed_scale": "compact-radius-2",
        "prewarm_steps": 600,
        "capture_steps": 1_800,
    }
    return OrderedDict(
        (
            ("torsion-cage", {**compact["torsion-cage"], **common}),
            (
                "torsion-split",
                {
                    **common,
                    "initial_agents": (
                        ((2, 0, 0), (-1, 0, 0), (0, 1, 0)),
                        ((-2, 0, 1), (1, 0, 0), (0, -1, 0)),
                        ((0, 2, 0), (0, -1, 0), (1, 0, 0)),
                        ((1, -2, 0), (0, 1, 0), (-1, 0, 0)),
                        ((0, 0, 2), (0, 0, -1), (0, 1, 0)),
                        ((0, 1, -2), (0, 0, 1), (0, -1, 0)),
                    ),
                    "parameter_edit": "opposed body-frame roll plus one-cell helical pair staggering",
                    "hypothesis": "Combining torsion and split-core offsets should braid separated fans through a displaced transaction nucleus.",
                },
            ),
            (
                "orbital-shear",
                {
                    **common,
                    "initial_agents": (
                        ((2, 0, 0), (0, 1, 0), (0, 0, 1)),
                        ((-2, 0, 1), (0, -1, 0), (0, 0, 1)),
                        ((0, 2, 0), (0, 0, 1), (1, 0, 0)),
                        ((1, -2, 0), (0, 0, -1), (1, 0, 0)),
                        ((0, 0, 2), (1, 0, 0), (0, 1, 0)),
                        ((0, 1, -2), (-1, 0, 0), (0, 1, 0)),
                    ),
                    "parameter_edit": "tangent heading circulation plus one-cell helical pair staggering",
                    "hypothesis": "Shearing the orbital cage should break cubic symmetry while retaining recurrent frame exchange.",
                },
            ),
        )
    )


def prewarmed_snapshot_window(result: DirectionResult, *, start_step: int) -> DirectionResult:
    snapshots = tuple(snapshot for snapshot in result.snapshots if snapshot.step >= start_step)
    if not snapshots or snapshots[0].step != start_step:
        raise ValueError("start_step must match a stored true snapshot")
    metrics = dict(result.metrics)
    metrics.update(
        {
            "prewarm_steps": start_step,
            "capture_start_step": start_step,
            "capture_end_step": result.steps,
            "capture_snapshot_count": len(snapshots),
        }
    )
    return DirectionResult(
        system=result.system,
        steps=result.steps,
        trajectories=result.trajectories,
        field=result.field,
        snapshots=snapshots,
        metrics=metrics,
    )
