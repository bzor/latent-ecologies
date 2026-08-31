"""Build corrected Study 003 caches with rewiring across the full horizon."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

import hou

from houdini_ai.nonlocal_affinity import (
    cohort_lift_prepared,
    lift_prepared_to_3d,
    prepare_canvas_run,
    relationship_digest,
)
from simulate_nonlocal_affinity_3d import (
    _add_float_parm,
    _apply_events,
    _config_from_validated_preset,
    _geometry_digest,
    _initial_geometry,
)


def native(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def run(
    root: Path,
    preset_path: Path,
    old_prepared_path: Path,
    old_metrics_path: Path,
    output: Path,
    *,
    frame_start: int = 201,
    frame_end: int = 650,
    horizon: int = 960,
) -> dict[str, Any]:
    root = root.resolve()
    preset_path = preset_path.resolve()
    old_prepared_path = old_prepared_path.resolve()
    old_metrics_path = old_metrics_path.resolve()
    output = output.resolve()
    if output.exists():
        raise RuntimeError(f"corrected selection already exists: {output}")
    if (frame_start, frame_end, horizon) != (201, 650, 960):
        raise ValueError("the corrected canonical revision is fixed to frames 201-650 and horizon 960")

    preset_raw = json.loads(preset_path.read_text(encoding="utf-8"))
    old_prepared = json.loads(old_prepared_path.read_text(encoding="utf-8"))
    old_metrics = json.loads(old_metrics_path.read_text(encoding="utf-8"))
    anchor_config = _config_from_validated_preset(
        preset_raw, agent_count=5000, dimensions=2, steps=horizon,
    )
    planar = prepare_canvas_run(
        anchor_config,
        rewire_probability=float(preset_raw["rewiring"]["probability_per_simulation_step"]),
    )
    shallow = lift_prepared_to_3d(planar, seed=anchor_config.seed, depth=0.15)
    prepared = cohort_lift_prepared(
        shallow,
        seed=anchor_config.seed,
        cohort_size=20,
        radius=0.012,
        routing="parallel",
    )
    initial_matches = all(prepared[key] == old_prepared[key] for key in ("initial_positions", "friends", "enemies"))
    old_events = old_prepared["rewire_events"]
    exact_prefix = prepared["rewire_events"][:len(old_events)] == old_events
    if not initial_matches or not exact_prefix:
        raise RuntimeError("extended schedule does not preserve the promoted initial state and event prefix")
    if len(old_events) != 4400 or len(prepared["rewire_events"]) != 16520:
        raise RuntimeError("unexpected old or extended event count")

    staging = output.with_name(f".{output.name}.staging-{uuid.uuid4().hex}")
    cache_dir = staging / "cache_sequence" / "cache"
    cache_dir.mkdir(parents=True)
    transient = staging / "state.transient.bgeo.sc"
    started = time.perf_counter()
    cache_records: list[dict[str, Any]] = []
    active_visible_steps = sorted({
        int(event["step"]) for event in prepared["rewire_events"]
        if frame_start - 1 <= int(event["step"]) <= frame_end - 1
    })
    events_by_step: dict[int, list[dict[str, int]]] = {}
    for event in prepared["rewire_events"]:
        events_by_step.setdefault(int(event["step"]), []).append(event)
    vex_errors: list[str] = []
    try:
        corrected_prepared_path = staging / "prepared-parallel-cohort-960.json"
        corrected_prepared_path.write_text(json.dumps(prepared, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        geometry = _initial_geometry(prepared)
        hou.hipFile.clear(suppress_save_prompt=True)
        network = hou.node("/obj").createNode("geo", "continuous_rewire_behavior_replay")
        for child in network.children():
            child.destroy()
        source = network.createNode("file", "PREVIOUS_VEX_STATE")
        update = network.createNode("attribwrangle", "VEX_AUTHORITATIVE_STEP")
        update.setInput(0, source)
        update.parm("class").set("point")
        vex_path = Path(__file__).resolve().parent / "vex" / "nonlocal_affinity_production_step.vfl"
        update.parm("snippet").set(vex_path.read_text(encoding="utf-8"))
        parameters = preset_raw["parameters"]
        for name in ("contraction", "attraction", "repulsion", "softening"):
            _add_float_parm(update, name, float(parameters[name]))

        prefix_state_matches = False
        old_prefix_cache = old_metrics_path.parent.parent.parent.parent.parent / "03_selected" / "selection_001" / "cache_sequence" / "cache" / "state.0236.bgeo.sc"
        # Fallback to the canonical Study path when the legacy path ancestry differs.
        old_prefix_cache = root / "studies/study_003_nonlocal-affinity-dance/01_behavior/03_selected/selection_001/cache_sequence/cache/state.0236.bgeo.sc"
        for step in range(1, horizon + 1):
            _apply_events(geometry, events_by_step.get(step, []))
            geometry.saveToFile(native(transient))
            source.parm("file").set(native(transient))
            source.parm("reload").pressButton()
            update.cook(force=True)
            errors = [str(error) for error in update.errors()]
            vex_errors.extend(f"step {step}: {error}" for error in errors)
            if errors:
                raise RuntimeError("; ".join(vex_errors))
            cooked = update.geometry()
            if cooked is None or len(cooked.points()) != 100000:
                raise RuntimeError(f"step {step}: topology changed")
            geometry = cooked.freeze()
            frame = step + 1
            if frame_start <= frame <= frame_end:
                cache_path = cache_dir / f"state.{frame:04d}.bgeo.sc"
                geometry.saveToFile(native(cache_path))
                cache_records.append({
                    "frame": frame,
                    "simulation_step": step,
                    "path": relative(root, output / "cache_sequence" / "cache" / cache_path.name),
                    "bytes": cache_path.stat().st_size,
                    "sha256": sha256(cache_path),
                })
            if step == 235:
                old_geometry = hou.Geometry()
                old_geometry.loadFromFile(native(old_prefix_cache))
                prefix_state_matches = _geometry_digest(geometry) == _geometry_digest(old_geometry)

        final_path = staging / "final-state.0960.bgeo.sc"
        geometry.saveToFile(native(final_path))
        final_digest = _geometry_digest(geometry)
        final_relationship_digest = relationship_digest(
            list(geometry.pointIntAttribValues("friend")),
            list(geometry.pointIntAttribValues("enemy")),
        )
        if not prefix_state_matches:
            raise RuntimeError("corrected replay diverged before the original schedule ended")
        if [record["frame"] for record in cache_records] != list(range(frame_start, frame_end + 1)):
            raise RuntimeError("corrected cache sequence is not contiguous")
        if active_visible_steps[-1] != frame_end - 1:
            raise RuntimeError("rewiring does not reach the final visible simulation step")
        transient.unlink(missing_ok=True)
        receipt = {
            "schema_version": 1,
            "operation": "correct-affinity-rewire-horizon",
            "correction_authorization_message_id": "1539259275254169642",
            "study_id": "study-003-nonlocal-affinity-dance",
            "state_authority": "vex-geometry",
            "engine": "hython-vex-rotating-cache",
            "agent_count": 100000,
            "dimensions": 3,
            "fps": 30,
            "frame_range": [frame_start, frame_end],
            "frame_count": len(cache_records),
            "simulation_step_range": [frame_start - 1, frame_end - 1],
            "frame_to_simulation_step": "frame - 1",
            "identity": "stable point number with constant 100000-point topology",
            "point_attributes": ["P", "enemy", "friend"],
            "original_prepared_sha256": sha256(old_prepared_path),
            "corrected_prepared_sha256": sha256(corrected_prepared_path),
            "original_event_count": len(old_events),
            "extended_event_count": len(prepared["rewire_events"]),
            "original_event_max_step": max(int(event["step"]) for event in old_events),
            "extended_event_schedule_steps": horizon,
            "extended_event_max_step": max(int(event["step"]) for event in prepared["rewire_events"]),
            "original_240_step_schedule_is_exact_prefix": exact_prefix,
            "initial_positions_and_relationships_preserved": initial_matches,
            "state_through_original_step_235_preserved": prefix_state_matches,
            "active_rewire_frames_in_visible_range": len(active_visible_steps),
            "first_visible_scheduled_rewire_frame": active_visible_steps[0] + 1,
            "last_visible_scheduled_rewire_frame": active_visible_steps[-1] + 1,
            "supersedes_component_id": "component-behavior-2e6832d7d826",
            "superseded_final_state_sha256": old_metrics["final_state_sha256"],
            "final_state_sha256": final_digest,
            "final_relationship_sha256": final_relationship_digest,
            "final_cache": "final-state.0960.bgeo.sc",
            "final_cache_bytes": final_path.stat().st_size,
            "final_cache_sha256": sha256(final_path),
            "preset_sha256": sha256(preset_path),
            "vex_sha256": sha256(vex_path),
            "vex_cook_count": horizon,
            "vex_errors": vex_errors,
            "cache_files": cache_records,
            "elapsed_seconds": time.perf_counter() - started,
        }
        receipt_path = staging / "cache_sequence" / "receipt.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        provisional_source = {
            "cache_paths": [record["path"] for record in cache_records],
            "extensions": {"studio/cache-receipt": relative(root, output / "cache_sequence" / "receipt.json")},
        }
        (staging / "cache-source.json").write_text(json.dumps(provisional_source, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(staging, output)
        print(json.dumps({
            "selection": relative(root, output),
            "cache_count": len(cache_records),
            "bytes": sum(record["bytes"] for record in cache_records),
            "extended_event_count": len(prepared["rewire_events"]),
            "last_visible_scheduled_rewire_frame": active_visible_steps[-1] + 1,
            "final_state_sha256": final_digest,
            "elapsed_seconds": receipt["elapsed_seconds"],
        }, sort_keys=True))
        return receipt
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("preset", type=Path)
    parser.add_argument("old_prepared", type=Path)
    parser.add_argument("old_metrics", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.root, args.preset, args.old_prepared, args.old_metrics, args.output)


if __name__ == "__main__":
    main()
