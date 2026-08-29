"""Run the approved 960-step Parallel-cohort endurance check."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from houdini_ai.doctor import discover_tools
from houdini_ai.nonlocal_affinity import final_prepared_relationships, relationship_digest
from houdini_ai.nonlocal_affinity_review import render_single_review

AGENT_COUNT = 100000
STEPS = 960
CHECKPOINT_INTERVAL = 24
REVIEW_INTERVAL = 4
REVIEW_COUNT = 20000
APPROVAL_MESSAGE_ID = "1538663472307642562"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def analyze(metrics: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    checkpoints = metrics["checkpoints"]
    radial = [(int(item["step"]), float(item["radial_mean"])) for item in checkpoints]
    minimum_step, minimum_radius = min(radial, key=lambda item: item[1])
    maximum_after_minimum = max((item for item in radial if item[0] >= minimum_step), key=lambda item: item[1])
    frames = review["frames"]
    late_frames = [frame for frame in frames if int(frame["step"]) >= 720]
    late_displacements: list[float] = []
    for previous, current in zip(late_frames, late_frames[1:]):
        for before, after in zip(previous["points"], current["points"]):
            late_displacements.append(sum((float(a) - float(b)) ** 2 for a, b in zip(after, before)) ** 0.5)
    late_displacements.sort()
    mean_late_displacement = sum(late_displacements) / max(1, len(late_displacements))
    p95_late_displacement = late_displacements[round((len(late_displacements) - 1) * 0.95)] if late_displacements else 0.0
    final_radius = radial[-1][1]
    return {
        "collapse": {
            "initial_radial_mean": radial[0][1],
            "minimum_radial_mean": minimum_radius,
            "minimum_step": minimum_step,
            "fractional_change_initial_to_minimum": minimum_radius / radial[0][1] - 1.0,
        },
        "expansion_after_collapse": {
            "maximum_radial_mean": maximum_after_minimum[1],
            "maximum_step": maximum_after_minimum[0],
            "fractional_change_minimum_to_maximum": maximum_after_minimum[1] / minimum_radius - 1.0,
            "final_radial_mean": final_radius,
        },
        "continued_reorganization_720_to_960": {
            "sample_interval_steps": REVIEW_INTERVAL,
            "transition_count": max(0, len(late_frames) - 1),
            "mean_sampled_point_displacement_per_interval": mean_late_displacement,
            "p95_sampled_point_displacement_per_interval": p95_late_displacement,
            "active": mean_late_displacement > 1e-6,
        },
        "finite_geometry": all(int(item["invalid_values"]) == 0 for item in checkpoints),
    }


def run(root: Path) -> dict[str, Any]:
    root = root.resolve()
    cohort_root = root / "work/studies/study-003-nonlocal-affinity-dance/20-behavior/comparisons/affinity-cohort-100k-v1"
    prepared_path = cohort_root / "receipts/tight-swirls-parallel-cohort-100k.json"
    preset_path = root / "work/studio/affinity-presets/affinity-preset-32e76e5d39d0.json"
    output_root = root / "work/studies/study-003-nonlocal-affinity-dance/20-behavior/endurance/parallel-cohort-100k-960-v1"
    simulation = output_root / "simulation"
    review_output = output_root / "review"
    if (output_root / "endurance-receipt.json").exists():
        raise RuntimeError(f"endurance output already exists: {output_root}")
    simulation.mkdir(parents=True, exist_ok=True)
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    expected_friends, expected_enemies = final_prepared_relationships(prepared)
    expected_relationship_sha = relationship_digest(expected_friends, expected_enemies)
    hython = next((tool.path for tool in discover_tools() if tool.name == "hython"), None)
    if hython is None:
        raise RuntimeError("Houdini hython is unavailable")
    command = [
        str(hython), str(root / "houdini/simulate_nonlocal_affinity_3d.py"),
        str(preset_path), str(simulation),
        "--agent-count", str(AGENT_COUNT), "--dimensions", "3", "--steps", str(STEPS),
        "--checkpoint-interval", str(CHECKPOINT_INTERVAL),
        "--review-interval", str(REVIEW_INTERVAL), "--review-count", str(REVIEW_COUNT),
        "--prepared", str(prepared_path),
    ]
    completed = subprocess.run(
        command, capture_output=True, text=True, check=False,
        env={**os.environ, "PYTHONPATH": str(root / "src"), "HOUDINI_TEMP_DIR": str(simulation / "temp")},
    )
    (simulation / "stdout.log").write_text(completed.stdout, encoding="utf-8")
    (simulation / "stderr.log").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"endurance simulation failed: {completed.stderr[-3000:]}")
    metrics_path = simulation / "metrics.json"
    review_path = simulation / "review.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    review = json.loads(review_path.read_text(encoding="utf-8"))
    expected_review_steps = list(range(0, STEPS + 1, REVIEW_INTERVAL))
    if metrics["vex_errors"] or metrics["vex_cook_count"] != STEPS:
        raise RuntimeError("VEX endurance execution failed verification")
    if metrics["final_relationship_sha256"] != expected_relationship_sha:
        raise RuntimeError("Parallel topology changed unexpectedly")
    if metrics["review_sample_steps"] != expected_review_steps:
        raise RuntimeError("endurance review schedule is incomplete")
    if any(int(item["invalid_values"]) for item in metrics["checkpoints"]):
        raise RuntimeError("endurance geometry contains non-finite values")
    analysis = analyze(metrics, review)
    media = render_single_review(
        simulation, review_output, title="Shallow-3D Parallel cohorts",
        fps=24, hold_frames=1, point_size=1, trail_alpha=0.18,
        population_count=AGENT_COUNT, video_name="parallel-cohort-100k-960-endurance.mp4",
    )
    receipt = {
        "schema_version": 1,
        "study": "Study 003 — Non-Local Affinity",
        "decision": "Behavior Decision 01",
        "authorization": {
            "scope": "Parallel-cohort endurance check only",
            "discord_message_id": APPROVAL_MESSAGE_ID,
            "look_development_authorized": False,
            "publication_authorized": False,
        },
        "engine": metrics["engine"],
        "state_authority": metrics["state_authority"],
        "population_count": AGENT_COUNT,
        "steps": STEPS,
        "review_policy": f"{REVIEW_COUNT} stratified points; stride 5 retains four cohort members per anchor; every {REVIEW_INTERVAL} genuine steps",
        "vex_cook_count": metrics["vex_cook_count"],
        "vex_errors": metrics["vex_errors"],
        "prepared_sha256": sha(prepared_path),
        "expected_final_relationship_sha256": expected_relationship_sha,
        "measured_final_relationship_sha256": metrics["final_relationship_sha256"],
        "topology_retained": metrics["final_relationship_sha256"] == expected_relationship_sha,
        "final_state_sha256": metrics["final_state_sha256"],
        "final_cache_sha256": metrics["cache_sha256"][f"state.{STEPS:04d}.bgeo.sc"],
        "hip_sha256": sha(simulation / metrics["hip"]),
        "metrics_sha256": sha(metrics_path),
        "review_source_sha256": sha(review_path),
        "elapsed_seconds": metrics["elapsed_seconds"],
        "analysis": analysis,
        "media": media,
    }
    receipt_path = output_root / "endurance-receipt.json"
    write_json(receipt_path, receipt)
    print(json.dumps({"output_root": str(output_root), "receipt": str(receipt_path), "video": str(review_output / media["video"])}, sort_keys=True))
    return receipt


if __name__ == "__main__":
    run(Path.cwd())
