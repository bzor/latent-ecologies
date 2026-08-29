"""Run and verify the approved Study 003 100k three-preset 3D comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from houdini_ai.doctor import discover_tools
from houdini_ai.studio_schema import validate_record
from houdini_ai.studio_store import StudioStore


EXPERIMENT_ID = "experiment-study-003-affinity-3d-100k-v1"
PRESETS = (
    ("tight-swirls", "affinity-preset-32e76e5d39d0"),
    ("wide-swirls-outliers", "affinity-preset-32f02869ab53"),
    ("cohesive-swirl", "affinity-preset-9e33c556dc55"),
)
AGENT_COUNT = 100_000
DIMENSIONS = 3
STEPS = 240
CHECKPOINT_INTERVAL = 12
REVIEW_COUNT = 5_000


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_checkpoint_steps() -> list[int]:
    return [0, *range(CHECKPOINT_INTERVAL, STEPS + 1, CHECKPOINT_INTERVAL)]


def verify_branch(directory: Path, preset_id: str) -> dict[str, Any]:
    metrics_path = directory / "metrics.json"
    review_path = directory / "review.json"
    preset_path = directory / "effective-preset.json"
    hip_path = directory / "nonlocal-affinity-3d.hiplc"
    if not all(path.is_file() for path in (metrics_path, review_path, preset_path, hip_path)):
        raise RuntimeError(f"{directory.name}: missing required output")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    if metrics.get("preset_id") != preset_id:
        raise RuntimeError(f"{directory.name}: preset identity mismatch")
    if metrics.get("state_authority") != "vex-geometry" or metrics.get("engine") != "hython-vex-rotating-cache":
        raise RuntimeError(f"{directory.name}: wrong execution authority")
    if (metrics.get("agent_count"), metrics.get("dimensions"), metrics.get("steps")) != (
        AGENT_COUNT, DIMENSIONS, STEPS,
    ):
        raise RuntimeError(f"{directory.name}: production dimensions mismatch")
    if metrics.get("vex_cook_count") != STEPS or metrics.get("vex_errors"):
        raise RuntimeError(f"{directory.name}: VEX execution is incomplete")
    if metrics.get("durable_checkpoint_steps") != expected_checkpoint_steps():
        raise RuntimeError(f"{directory.name}: checkpoint schedule mismatch")
    if any(checkpoint.get("invalid_values") for checkpoint in metrics.get("checkpoints", [])):
        raise RuntimeError(f"{directory.name}: non-finite geometry values")
    if metrics.get("look_status") != "deferred" or metrics.get("trails_status") != "deferred":
        raise RuntimeError(f"{directory.name}: behavior run contains premature Look decisions")
    for name, expected in metrics.get("cache_sha256", {}).items():
        path = directory / "cache" / name
        if not path.is_file() or sha256_path(path) != expected:
            raise RuntimeError(f"{directory.name}: cache checksum mismatch for {name}")
    final_path = directory / str(metrics["final_cache"])
    if not final_path.is_file() or metrics.get("state_digest_source") != "reloaded-final-cache":
        raise RuntimeError(f"{directory.name}: final cache was not reload-verified")
    review = json.loads(review_path.read_text(encoding="utf-8"))
    if [frame["step"] for frame in review.get("frames", [])] != expected_checkpoint_steps():
        raise RuntimeError(f"{directory.name}: review checkpoint mismatch")
    if any(len(frame["points"]) != REVIEW_COUNT for frame in review["frames"]):
        raise RuntimeError(f"{directory.name}: review point sample mismatch")
    return {
        "preset_id": preset_id,
        "directory": str(directory),
        "metrics_sha256": sha256_path(metrics_path),
        "review_sha256": sha256_path(review_path),
        "hip_sha256": sha256_path(hip_path),
        "final_cache": str(final_path),
        "final_cache_sha256": sha256_path(final_path),
        "final_state_sha256": metrics["final_state_sha256"],
        "rewire_count": metrics["rewire_count"],
        "elapsed_seconds": metrics["elapsed_seconds"],
        "final_checkpoint": metrics["checkpoints"][-1],
    }


def update_experiment(store: StudioStore, state: str, output_root: Path, branches: list[dict[str, Any]] | None = None) -> None:
    record = store.read("experiments", EXPERIMENT_ID)
    extensions = dict(record.get("extensions", {}))
    extensions["bzor.systems/output-root"] = str(output_root)
    if branches is not None:
        extensions["bzor.systems/verified-branches"] = [branch["preset_id"] for branch in branches]
        extensions["bzor.systems/comparison-manifest"] = str(output_root / "comparison-manifest.json")
    updated = {**record, "state": state, "extensions": extensions}
    errors = validate_record("experiment", updated)
    if errors:
        raise RuntimeError("invalid experiment transition: " + "; ".join(errors))
    store.update("experiments", EXPERIMENT_ID, updated)


def run(root: Path) -> dict[str, Any]:
    root = root.resolve()
    output_root = root / "work" / "studies" / "study-003-nonlocal-affinity-dance" / "20-behavior" / "comparisons" / "affinity-3d-100k-v1"
    output_root.mkdir(parents=True, exist_ok=True)
    store = StudioStore(root)
    experiment = store.read("experiments", EXPERIMENT_ID)
    if experiment.get("state") not in {"draft", "running"}:
        raise RuntimeError(f"experiment must be draft or running, not {experiment.get('state')}")
    proposal = store.read("proposals", str(experiment["proposal_id"]))
    if proposal.get("state") != "approved" or proposal.get("runner") != "behavior.nonlocal_affinity_3d":
        raise RuntimeError("production run requires its approved registered proposal")
    update_experiment(store, "running", output_root)
    hython = next((tool.path for tool in discover_tools() if tool.name == "hython"), None)
    if hython is None:
        raise RuntimeError("Houdini hython is unavailable")
    runner = root / "houdini" / "simulate_nonlocal_affinity_3d.py"
    branches: list[dict[str, Any]] = []
    try:
        for slug, preset_id in PRESETS:
            directory = output_root / slug
            preset_path = root / "work" / "studio" / "affinity-presets" / f"{preset_id}.json"
            try:
                branch = verify_branch(directory, preset_id)
                print(f"reuse verified branch: {slug}", flush=True)
            except (FileNotFoundError, KeyError, RuntimeError, ValueError, json.JSONDecodeError):
                directory.mkdir(parents=True, exist_ok=True)
                command = [
                    str(hython), str(runner), str(preset_path), str(directory),
                    "--agent-count", str(AGENT_COUNT),
                    "--dimensions", str(DIMENSIONS),
                    "--steps", str(STEPS),
                    "--checkpoint-interval", str(CHECKPOINT_INTERVAL),
                    "--review-count", str(REVIEW_COUNT),
                ]
                print(f"run branch: {slug}", flush=True)
                completed = subprocess.run(
                    command,
                    text=True,
                    capture_output=True,
                    check=False,
                    env={
                        **os.environ,
                        "PYTHONPATH": str(root / "src"),
                        "HOUDINI_TEMP_DIR": str(directory / "temp"),
                    },
                )
                (directory / "stdout.log").write_text(completed.stdout, encoding="utf-8")
                (directory / "stderr.log").write_text(completed.stderr, encoding="utf-8")
                if completed.returncode:
                    raise RuntimeError(f"{slug} failed with exit {completed.returncode}: {completed.stderr[-2000:]}")
                branch = verify_branch(directory, preset_id)
            branches.append(branch)
            (output_root / "progress.json").write_text(
                json.dumps({"completed": [item["preset_id"] for item in branches]}, indent=2) + "\n",
                encoding="utf-8",
            )
        manifest = {
            "schema_version": 1,
            "experiment_id": EXPERIMENT_ID,
            "state_authority": "vex-geometry",
            "agent_count": AGENT_COUNT,
            "dimensions": DIMENSIONS,
            "steps": STEPS,
            "checkpoint_interval": CHECKPOINT_INTERVAL,
            "trails_status": "deferred-to-look-development",
            "point_geometry_status": "deferred-to-look-development",
            "branches": branches,
        }
        manifest_path = output_root / "comparison-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        update_experiment(store, "completed", output_root, branches)
        print(json.dumps({"output_root": str(output_root), "branches": len(branches)}, sort_keys=True), flush=True)
        return manifest
    except Exception:
        update_experiment(store, "failed", output_root)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    run(args.root)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr, flush=True)
        raise
