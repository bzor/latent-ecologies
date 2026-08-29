"""Run Tight Swirls as three graph-preserving 5k→100k cohort lifts."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from houdini_ai.affinity_presets import load_affinity_preset
from houdini_ai.doctor import discover_tools
from houdini_ai.nonlocal_affinity import (
    cohort_lift_prepared,
    final_prepared_relationships,
    lift_prepared_to_3d,
    prepare_canvas_run,
    relationship_digest,
)
from houdini_ai.studio_api import StudioAPI
from houdini_ai.studio_schema import validate_record
from houdini_ai.studio_store import StudioStore


EXPERIMENT_ID = "experiment-study-003-affinity-cohort-100k-v1"
PRESET_ID = "affinity-preset-32e76e5d39d0"
STRATEGIES = (
    ("parallel", "Parallel cohorts"),
    ("neighbor", "Neighbor braid"),
    ("mixed", "Mixed cohorts"),
)
ANCHOR_COUNT = 5000
COHORT_SIZE = 20
AGENT_COUNT = ANCHOR_COUNT * COHORT_SIZE
STEPS = 240
ANCHOR_DEPTH = 0.15
COHORT_RADIUS = 0.012
REVIEW_COUNT = 20000


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ensure_lifecycle(root: Path, output_root: Path) -> StudioStore:
    store = StudioStore(root)
    try:
        experiment = store.read("experiments", EXPERIMENT_ID)
    except FileNotFoundError:
        api = StudioAPI(root)
        proposal = api.create_proposal({
            "idea_id": "idea-nonlocal-affinity-dance-b774404e",
            "question": "Can the exact 5k Canvas morphology scale to 100k by lifting its graph rather than reseeding it?",
            "hypothesis": "Twenty descendants per Canvas anchor will preserve the large-scale swirl vocabulary; controlled cohort routing will determine whether density reads as layers, braid, or interwoven volume.",
            "mechanism": "Preserve the exact Tight Swirls Mulberry32 anchor graph and event history, add the approved shallow Z lift, expand every anchor and every event 20x, and compare parallel, neighbor, and mixed within-cohort edge routing.",
            "outputs": ["three 100k VEX-authoritative caches", "241-state 20k-stratified review streams", "30fps comparison", "topology and cache receipts"],
            "stop_conditions": ["macro-edge violation", "final relationship digest mismatch", "VEX error", "non-finite geometry", "incomplete review schedule"],
            "runner": "behavior.nonlocal_affinity_3d",
            "cost_tier": "study",
            "direction_ids": ["direction-fbe9c254e174"],
            "extensions": {"bzor.systems/explicit-user-approval": "KC approved proceeding with the structure-preserving 5k-to-100k lift."},
        })
        approved = api.approve_proposal(proposal["id"])
        experiment = api.create_record("experiments", {
            "schema_version": 1,
            "id": EXPERIMENT_ID,
            "proposal_id": approved["id"],
            "track": "behavior",
            "state": "draft",
            "runner": "behavior.nonlocal_affinity_3d",
            "parameters": {
                "preset_id": PRESET_ID,
                "anchor_count": ANCHOR_COUNT,
                "cohort_size": COHORT_SIZE,
                "agent_count": AGENT_COUNT,
                "steps": STEPS,
                "anchor_depth": ANCHOR_DEPTH,
                "cohort_radius": COHORT_RADIUS,
                "routing_strategies": [slug for slug, _title in STRATEGIES],
                "review_count": REVIEW_COUNT,
            },
            "visibility": "private",
        })
    if experiment["state"] not in {"draft", "running"}:
        raise RuntimeError(f"cohort experiment is not runnable from state {experiment['state']}")
    extensions = dict(experiment.get("extensions", {}))
    extensions["bzor.systems/output-root"] = output_root.relative_to(root).as_posix()
    running = {**experiment, "state": "running", "extensions": extensions}
    errors = validate_record("experiment", running)
    if errors:
        raise RuntimeError("; ".join(errors))
    store.update("experiments", EXPERIMENT_ID, running)
    return store


def verify_output(directory: Path, prepared_path: Path, expected_relationship_sha: str) -> dict[str, Any]:
    metrics_path = directory / "metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    if metrics["agent_count"] != AGENT_COUNT or metrics["dimensions"] != 3 or metrics["steps"] != STEPS:
        raise RuntimeError(f"{directory}: run dimensions mismatch")
    if metrics["prepared_source"] != "external-receipt" or metrics["prepared_sha256"] != sha(prepared_path):
        raise RuntimeError(f"{directory}: prepared receipt mismatch")
    if metrics["vex_errors"] or metrics["vex_cook_count"] != STEPS:
        raise RuntimeError(f"{directory}: VEX execution failed")
    if metrics["final_relationship_sha256"] != expected_relationship_sha:
        raise RuntimeError(f"{directory}: final relationship digest mismatch")
    if metrics["review_sample_steps"] != list(range(STEPS + 1)):
        raise RuntimeError(f"{directory}: dense review schedule incomplete")
    if any(checkpoint["invalid_values"] for checkpoint in metrics["checkpoints"]):
        raise RuntimeError(f"{directory}: non-finite geometry")
    return {
        "metrics": metrics_path.relative_to(directory.parents[1]).as_posix(),
        "metrics_sha256": sha(metrics_path),
        "prepared_sha256": sha(prepared_path),
        "expected_final_relationship_sha256": expected_relationship_sha,
        "measured_final_relationship_sha256": metrics["final_relationship_sha256"],
        "final_state_sha256": metrics["final_state_sha256"],
        "rewire_count": metrics["rewire_count"],
        "elapsed_seconds": metrics["elapsed_seconds"],
        "final_radial_mean": metrics["checkpoints"][-1]["radial_mean"],
        "final_radial_extent": metrics["checkpoints"][-1]["radial_extent"],
        "final_cache_sha256": metrics["cache_sha256"][f"state.{STEPS:04d}.bgeo.sc"],
        "hip_sha256": sha(directory / metrics["hip"]),
    }


def run(root: Path) -> dict[str, Any]:
    root = root.resolve()
    output_root = root / "work/studies/study-003-nonlocal-affinity-dance/20-behavior/comparisons/affinity-cohort-100k-v1"
    output_root.mkdir(parents=True, exist_ok=True)
    store = ensure_lifecycle(root, output_root)
    preset_path = root / "work/studio/affinity-presets" / f"{PRESET_ID}.json"
    preset = json.loads(preset_path.read_text(encoding="utf-8"))
    config = load_affinity_preset(preset_path, agent_count=ANCHOR_COUNT, dimensions=2, steps=STEPS)
    planar = prepare_canvas_run(config, rewire_probability=float(preset["rewiring"]["probability_per_simulation_step"]))
    shallow = lift_prepared_to_3d(planar, seed=config.seed, depth=ANCHOR_DEPTH)
    hython = next((tool.path for tool in discover_tools() if tool.name == "hython"), None)
    if hython is None:
        raise RuntimeError("Houdini hython is unavailable")
    runner = root / "houdini/simulate_nonlocal_affinity_3d.py"
    initial_positions_sha: str | None = None
    results: dict[str, Any] = {}
    for slug, title in STRATEGIES:
        prepared = cohort_lift_prepared(
            shallow,
            seed=config.seed,
            cohort_size=COHORT_SIZE,
            radius=COHORT_RADIUS,
            routing=slug,
        )
        positions_sha = canonical_sha(prepared["initial_positions"])
        if initial_positions_sha is None:
            initial_positions_sha = positions_sha
        elif positions_sha != initial_positions_sha:
            raise RuntimeError("strategy branches do not share identical initial positions")
        if len(prepared["initial_positions"]) != AGENT_COUNT:
            raise RuntimeError("cohort lift produced the wrong population")
        if any(int(target) // COHORT_SIZE != int(planar[edge][anchor]) for edge in ("friends", "enemies") for anchor in range(ANCHOR_COUNT) for target in prepared[edge][anchor * COHORT_SIZE:(anchor + 1) * COHORT_SIZE]):
            raise RuntimeError(f"{slug}: initial macro edge invariant failed")
        for event_index, event in enumerate(prepared["rewire_events"]):
            source_event = planar["rewire_events"][event_index // COHORT_SIZE]
            if any((int(event[field]) // COHORT_SIZE) != int(source_event[field]) for field in ("point", "friend", "enemy")):
                raise RuntimeError(f"{slug}: event macro edge invariant failed")
        final_friends, final_enemies = final_prepared_relationships(prepared)
        expected_relationship_sha = relationship_digest(final_friends, final_enemies)
        receipt = output_root / "receipts" / f"tight-swirls-{slug}-cohort-100k.json"
        write_json(receipt, prepared)
        directory = output_root / slug
        directory.mkdir(parents=True, exist_ok=True)
        command = [
            str(hython), str(runner), str(preset_path), str(directory),
            "--agent-count", str(AGENT_COUNT), "--dimensions", "3", "--steps", str(STEPS),
            "--checkpoint-interval", "12", "--review-interval", "1", "--review-count", str(REVIEW_COUNT),
            "--prepared", str(receipt),
        ]
        print(f"run cohort lift: {slug}", flush=True)
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "PYTHONPATH": str(root / "src"), "HOUDINI_TEMP_DIR": str(directory / "temp")},
        )
        (directory / "stdout.log").write_text(completed.stdout, encoding="utf-8")
        (directory / "stderr.log").write_text(completed.stderr, encoding="utf-8")
        if completed.returncode:
            raise RuntimeError(f"{slug} failed: {completed.stderr[-2000:]}")
        results[slug] = {"title": title, **verify_output(directory, receipt, expected_relationship_sha)}
    manifest = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "preset_id": PRESET_ID,
        "anchor_identity": "exact Canvas Mulberry32 positions, friend/enemy anchor graph, and ordered events",
        "anchor_count": ANCHOR_COUNT,
        "cohort_size": COHORT_SIZE,
        "agent_count": AGENT_COUNT,
        "steps": STEPS,
        "anchor_depth": ANCHOR_DEPTH,
        "cohort_radius": COHORT_RADIUS,
        "initial_positions_sha256": initial_positions_sha,
        "review_policy": f"{REVIEW_COUNT} stratified points; stride 5 retains four cohort members per anchor; every genuine state 0-{STEPS}",
        "branches": results,
    }
    manifest_path = output_root / "cohort-comparison-manifest.json"
    write_json(manifest_path, manifest)
    experiment = store.read("experiments", EXPERIMENT_ID)
    extensions = dict(experiment.get("extensions", {}))
    extensions["bzor.systems/cohort-manifest"] = manifest_path.relative_to(root).as_posix()
    completed_record = {**experiment, "state": "completed", "extensions": extensions}
    errors = validate_record("experiment", completed_record)
    if errors:
        raise RuntimeError("; ".join(errors))
    store.update("experiments", EXPERIMENT_ID, completed_record)
    print(json.dumps({"experiment_id": EXPERIMENT_ID, "output_root": str(output_root)}, sort_keys=True))
    return manifest


if __name__ == "__main__":
    run(Path.cwd())
