"""Run the approved 5k Canvas-identity → planar VEX → shallow-3D ladder."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from houdini_ai.affinity_presets import load_affinity_preset
from houdini_ai.doctor import discover_tools
from houdini_ai.nonlocal_affinity import lift_prepared_to_3d, prepare_canvas_run
from houdini_ai.studio_api import StudioAPI
from houdini_ai.studio_schema import validate_record
from houdini_ai.studio_store import StudioStore


EXPERIMENT_ID = "experiment-study-003-affinity-identity-ladder-v1"
BRANCHES = (
    ("tight-swirls", "affinity-preset-32e76e5d39d0"),
    ("wide-swirls-outliers", "affinity-preset-32f02869ab53"),
    ("cohesive-swirl", "affinity-preset-9e33c556dc55"),
)
AGENT_COUNT = 5000
STEPS = 240
DEPTH = 0.15


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
            "question": "Where does Canvas morphology diverge: runtime handoff or the controlled 2D-to-3D lift?",
            "hypothesis": "Exact Mulberry32 graph/event replay will recover Canvas morphology in planar VEX; adding only shallow deterministic Z will isolate dimensional change without reseeding.",
            "mechanism": "Recreate each 5k Canvas initial state and event schedule exactly; replay it in planar VEX; preserve XY, graph, and events while adding bounded Z depth 0.15 for a second VEX replay.",
            "outputs": ["three exact planar VEX replays", "three graph-identical shallow-3D replays", "30fps all-point comparisons", "parity and receipt manifest"],
            "stop_conditions": ["Canvas oracle mismatch", "relationship mismatch", "VEX error", "reference tolerance failure", "non-finite geometry"],
            "runner": "behavior.nonlocal_affinity_3d",
            "cost_tier": "study",
            "direction_ids": ["direction-fbe9c254e174"],
            "extensions": {"bzor.systems/explicit-user-approval": "KC selected the controlled identity ladder diagnostic."},
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
                "preset_ids": [preset_id for _slug, preset_id in BRANCHES],
                "agent_count": AGENT_COUNT,
                "steps": STEPS,
                "planar_rng": "mulberry32-v1",
                "shallow_3d_depth": DEPTH,
                "review_interval": 1,
                "trails": "canvas-display-diagnostic-only",
            },
            "visibility": "private",
        })
    if experiment["state"] not in {"draft", "running"}:
        raise RuntimeError(f"identity ladder is not runnable from state {experiment['state']}")
    extensions = dict(experiment.get("extensions", {}))
    extensions["bzor.systems/output-root"] = output_root.relative_to(root).as_posix()
    running = {**experiment, "state": "running", "extensions": extensions}
    errors = validate_record("experiment", running)
    if errors:
        raise RuntimeError("; ".join(errors))
    store.update("experiments", EXPERIMENT_ID, running)
    return store


def verify_output(directory: Path, prepared_path: Path, dimensions: int) -> dict[str, Any]:
    metrics = json.loads((directory / "metrics.json").read_text(encoding="utf-8"))
    if metrics["agent_count"] != AGENT_COUNT or metrics["steps"] != STEPS or metrics["dimensions"] != dimensions:
        raise RuntimeError(f"{directory}: run dimensions mismatch")
    if metrics["prepared_source"] != "external-receipt" or metrics["prepared_sha256"] != sha(prepared_path):
        raise RuntimeError(f"{directory}: prepared receipt mismatch")
    if metrics["vex_errors"] or not metrics["reference_material_tolerance_passed"] or not metrics["relationship_indices_match"]:
        raise RuntimeError(f"{directory}: VEX parity failed")
    if metrics["review_sample_steps"] != list(range(STEPS + 1)):
        raise RuntimeError(f"{directory}: dense review schedule incomplete")
    if any(checkpoint["invalid_values"] for checkpoint in metrics["checkpoints"]):
        raise RuntimeError(f"{directory}: non-finite geometry")
    return {
        "metrics": (directory / "metrics.json").relative_to(directory.parents[2]).as_posix(),
        "metrics_sha256": sha(directory / "metrics.json"),
        "final_state_sha256": metrics["final_state_sha256"],
        "maximum_position_error": metrics["maximum_position_error"],
        "mean_position_error": metrics["mean_position_error"],
        "p99_position_error": metrics["p99_position_error"],
        "comparison_tolerance": metrics["comparison_tolerance"],
        "strict_max_tolerance_passed": metrics["reference_tolerance_passed"],
        "material_tolerance_passed": metrics["reference_material_tolerance_passed"],
        "rewire_count": metrics["rewire_count"],
    }


def run(root: Path) -> dict[str, Any]:
    root = root.resolve()
    output_root = root / "work/studies/study-003-nonlocal-affinity-dance/20-behavior/comparisons/affinity-identity-ladder-v1"
    output_root.mkdir(parents=True, exist_ok=True)
    store = ensure_lifecycle(root, output_root)
    hython = next((tool.path for tool in discover_tools() if tool.name == "hython"), None)
    if hython is None:
        raise RuntimeError("Houdini hython is unavailable")
    runner = root / "houdini/simulate_nonlocal_affinity_3d.py"
    results: dict[str, dict[str, Any]] = {"planar": {}, "shallow_3d": {}}
    for slug, preset_id in BRANCHES:
        preset_path = root / "work/studio/affinity-presets" / f"{preset_id}.json"
        preset = json.loads(preset_path.read_text(encoding="utf-8"))
        planar_config = load_affinity_preset(preset_path, agent_count=AGENT_COUNT, dimensions=2, steps=STEPS)
        planar_prepared = prepare_canvas_run(
            planar_config,
            rewire_probability=float(preset["rewiring"]["probability_per_simulation_step"]),
        )
        planar_receipt = output_root / "receipts" / f"{slug}-canvas-planar.json"
        shallow_receipt = output_root / "receipts" / f"{slug}-canvas-shallow-3d.json"
        write_json(planar_receipt, planar_prepared)
        write_json(shallow_receipt, lift_prepared_to_3d(planar_prepared, seed=planar_config.seed, depth=DEPTH))
        for stage, dimensions, receipt in (
            ("planar", 2, planar_receipt),
            ("shallow-3d", 3, shallow_receipt),
        ):
            directory = output_root / stage / slug
            directory.mkdir(parents=True, exist_ok=True)
            command = [
                str(hython), str(runner), str(preset_path), str(directory),
                "--agent-count", str(AGENT_COUNT), "--dimensions", str(dimensions),
                "--steps", str(STEPS), "--checkpoint-interval", "12",
                "--review-interval", "1", "--review-count", str(AGENT_COUNT),
                "--prepared", str(receipt), "--compare-reference",
            ]
            print(f"run identity ladder: {stage}/{slug}", flush=True)
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
                raise RuntimeError(f"{stage}/{slug} failed: {completed.stderr[-2000:]}")
            key = "planar" if dimensions == 2 else "shallow_3d"
            results[key][slug] = verify_output(directory, receipt, dimensions)
    manifest = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "agent_count": AGENT_COUNT,
        "steps": STEPS,
        "source_rng": "mulberry32-v1",
        "graph_identity": "initial XY, friend/enemy indices, and ordered rewire events preserved",
        "shallow_3d_depth": DEPTH,
        "stages": results,
        "scaling_status": "not-run",
    }
    manifest_path = output_root / "identity-ladder-manifest.json"
    write_json(manifest_path, manifest)
    experiment = store.read("experiments", EXPERIMENT_ID)
    extensions = dict(experiment.get("extensions", {}))
    extensions["bzor.systems/identity-manifest"] = manifest_path.relative_to(root).as_posix()
    completed_record = {**experiment, "state": "completed", "extensions": extensions}
    errors = validate_record("experiment", completed_record)
    if errors:
        raise RuntimeError("; ".join(errors))
    store.update("experiments", EXPERIMENT_ID, completed_record)
    print(json.dumps({"experiment_id": EXPERIMENT_ID, "output_root": str(output_root)}, sort_keys=True))
    return manifest


if __name__ == "__main__":
    run(Path.cwd())
