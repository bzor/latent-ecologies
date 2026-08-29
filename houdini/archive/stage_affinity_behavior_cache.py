"""Stage a contiguous canonical Look cache from promoted affinity Behavior."""

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

from houdini_ai.nonlocal_affinity import relationship_digest
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


def stage(
    root: Path,
    preset_path: Path,
    prepared_path: Path,
    metrics_path: Path,
    manifest_path: Path,
    component_path: Path,
    selection_dir: Path,
    *,
    frame_start: int,
    frame_end: int,
    horizon: int,
) -> dict[str, Any]:
    root = root.resolve()
    paths = [preset_path, prepared_path, metrics_path, manifest_path, component_path, selection_dir]
    preset_path, prepared_path, metrics_path, manifest_path, component_path, selection_dir = [path.resolve() for path in paths]
    if frame_start < 2 or frame_end < frame_start or horizon < frame_end - 1:
        raise ValueError("cache range must map to valid frame-1 simulation steps within the replay horizon")
    target = selection_dir / "cache_sequence"
    source_path = selection_dir / "look-source.json"
    if target.exists() or source_path.exists():
        raise RuntimeError("canonical selected cache output already exists; refusing to overwrite")

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    component = json.loads(component_path.read_text(encoding="utf-8"))
    preset = json.loads(preset_path.read_text(encoding="utf-8"))
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    if component.get("id") != "component-behavior-2e6832d7d826" or component.get("state") != "promoted":
        raise ValueError("selected component is not the promoted Study 003 Behavior")
    if metrics.get("state_authority") != "vex-geometry" or manifest.get("state_authority") != "vex-geometry":
        raise ValueError("canonical source is not VEX-authoritative")
    if metrics.get("agent_count") != 100000 or manifest.get("population_count") != 100000:
        raise ValueError("canonical promoted population must remain 100000")
    expected_hashes = {
        preset_path: metrics["preset_sha256"],
        prepared_path: metrics["prepared_sha256"],
        metrics_path: manifest["files"]["metrics.json"]["sha256"],
        prepared_path: manifest["files"]["prepared-parallel-cohort.json"]["sha256"],
    }
    for path, expected in expected_hashes.items():
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"canonical source hash mismatch for {path}: {actual} != {expected}")
    source_final = metrics_path.parent / "final-state.0960.bgeo.sc"
    if sha256(source_final) != manifest["files"][source_final.name]["sha256"]:
        raise ValueError("promoted final cache bytes do not match the frozen manifest")

    config = _config_from_validated_preset(preset, agent_count=100000, dimensions=3, steps=horizon)
    events_by_step: dict[int, list[dict[str, int]]] = {}
    for event in prepared["rewire_events"]:
        events_by_step.setdefault(int(event["step"]), []).append(event)
    staging = selection_dir / f".cache_sequence.staging-{uuid.uuid4().hex}"
    cache_dir = staging / "cache"
    cache_dir.mkdir(parents=True)
    transient = staging / "state.transient.bgeo.sc"
    started = time.perf_counter()
    cache_records: list[dict[str, Any]] = []
    scheduled_updates: list[dict[str, int]] = []
    vex_errors: list[str] = []
    try:
        geometry = _initial_geometry(prepared)
        hou.hipFile.clear(suppress_save_prompt=True)
        network = hou.node("/obj").createNode("geo", "canonical_affinity_cache_replay")
        for child in network.children():
            child.destroy()
        source = network.createNode("file", "PREVIOUS_VEX_STATE")
        update = network.createNode("attribwrangle", "VEX_AUTHORITATIVE_STEP")
        update.setInput(0, source)
        update.parm("class").set("point")
        vex_path = Path(__file__).resolve().parent / "vex" / "nonlocal_affinity_production_step.vfl"
        update.parm("snippet").set(vex_path.read_text(encoding="utf-8"))
        for name in ("contraction", "attraction", "repulsion", "softening"):
            _add_float_parm(update, name, float(getattr(config.parameters, name)))

        for step in range(1, horizon + 1):
            events = events_by_step.get(step, [])
            _apply_events(geometry, events)
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
                raise RuntimeError(f"step {step}: replay topology changed")
            geometry = cooked.freeze()
            frame = step + 1
            if frame_start <= frame <= frame_end:
                output = cache_dir / f"state.{frame:04d}.bgeo.sc"
                geometry.saveToFile(native(output))
                record = {
                    "frame": frame,
                    "simulation_step": step,
                    "path": relative(root, target / "cache" / output.name),
                    "bytes": output.stat().st_size,
                    "sha256": sha256(output),
                }
                cache_records.append(record)
                if events:
                    scheduled_updates.append({"frame": frame, "simulation_step": step, "updates": len(events)})

        final_digest = _geometry_digest(geometry)
        final_friends = list(geometry.pointIntAttribValues("friend"))
        final_enemies = list(geometry.pointIntAttribValues("enemy"))
        final_relationship_digest = relationship_digest(final_friends, final_enemies)
        expected_final_digest = metrics["final_state_sha256"]
        expected_relationship_digest = metrics["final_relationship_sha256"]
        if final_digest != expected_final_digest or final_relationship_digest != expected_relationship_digest:
            raise RuntimeError(
                f"960-step replay diverged from promoted state: {final_digest}/{final_relationship_digest}"
            )
        expected_frames = list(range(frame_start, frame_end + 1))
        if [record["frame"] for record in cache_records] != expected_frames:
            raise RuntimeError("staged cache sequence is not contiguous")
        transient.unlink(missing_ok=True)
        receipt = {
            "schema_version": 1,
            "operation": "stage-promoted-affinity-look-cache",
            "study_id": "study-003-nonlocal-affinity-dance",
            "component_id": component["id"],
            "component_content_hash": component["content_hash"],
            "state_authority": "vex-geometry",
            "engine": "hython-vex-rotating-cache",
            "agent_count": 100000,
            "dimensions": 3,
            "fps": 30,
            "frame_range": [frame_start, frame_end],
            "frame_count": len(cache_records),
            "simulation_step_range": [frame_start - 1, frame_end - 1],
            "frame_to_simulation_step": "frame - 1",
            "replay_horizon_steps": horizon,
            "identity": "stable point number with constant 100000-point topology",
            "point_attributes": ["P", "enemy", "friend"],
            "preset_id": metrics["preset_id"],
            "preset_sha256": sha256(preset_path),
            "prepared_sha256": sha256(prepared_path),
            "vex_sha256": sha256(vex_path),
            "promoted_final_cache_sha256": sha256(source_final),
            "expected_final_state_sha256": expected_final_digest,
            "final_state_sha256": final_digest,
            "final_relationship_sha256": final_relationship_digest,
            "matches_promoted_960_step_state": True,
            "vex_cook_count": horizon,
            "vex_errors": vex_errors,
            "scheduled_rewire_updates_in_visible_sequence": scheduled_updates,
            "cache_files": cache_records,
            "elapsed_seconds": time.perf_counter() - started,
        }
        (staging / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(staging, target)
        look_source = {
            "id": component["id"],
            "component_kind": "behavior",
            "state": "promoted",
            "content_hash": component["content_hash"],
            "cache_paths": [record["path"] for record in cache_records],
            "extensions": {
                "studio/cache-receipt": relative(root, target / "receipt.json"),
                "studio/frame-range": f"{frame_start}-{frame_end}",
                "studio/frame-to-simulation-step": "frame - 1",
                "studio/identity": "stable-point-number",
            },
        }
        temporary_source = source_path.with_name(f".{source_path.name}.{uuid.uuid4().hex}.tmp")
        temporary_source.write_text(json.dumps(look_source, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary_source, source_path)
        print(json.dumps({
            "cache_count": len(cache_records),
            "frame_range": [frame_start, frame_end],
            "bytes": sum(record["bytes"] for record in cache_records),
            "elapsed_seconds": receipt["elapsed_seconds"],
            "matches_promoted_960_step_state": True,
            "receipt": relative(root, target / "receipt.json"),
            "look_source": relative(root, source_path),
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
    parser.add_argument("prepared", type=Path)
    parser.add_argument("metrics", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("component", type=Path)
    parser.add_argument("selection_dir", type=Path)
    parser.add_argument("--frame-start", type=int, default=201)
    parser.add_argument("--frame-end", type=int, default=650)
    parser.add_argument("--horizon", type=int, default=960)
    args = parser.parse_args()
    stage(
        args.root, args.preset, args.prepared, args.metrics, args.manifest, args.component,
        args.selection_dir, frame_start=args.frame_start, frame_end=args.frame_end,
        horizon=args.horizon,
    )


if __name__ == "__main__":
    main()
