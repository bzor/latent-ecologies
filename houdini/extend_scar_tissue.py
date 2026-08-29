"""Continue a VEX-authoritative Scar Tissue cache without restarting it."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import hou

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from houdini_ai.behavior_lab import config_from_experiment  # noqa: E402
from simulate_scar_tissue import MUTATION_IDS, state_digest  # noqa: E402


def configure_update(config: dict) -> tuple[hou.Node, hou.Node]:
    network = hou.node("/obj").createNode("geo", "scar_tissue_vex_continuation")
    for child in network.children():
        child.destroy()
    source = network.createNode("file", "CACHE_previous_authoritative_state")
    update = network.createNode("attribwrangle", "VEX_advance_state_one_frame")
    update.setInput(0, source)
    update.parm("class").set("detail")
    vex_source = (ROOT / "houdini/vex/scar_tissue_stateful.vfl").read_text(encoding="utf-8")
    update.parm("snippet").set(vex_source)
    system = config["system"]
    values = {
        "agent_count": int(system["agent_count"]), "grid_width": int(system["grid_width"]),
        "grid_height": int(system["grid_height"]), "current_frame": int(config["frame_start"]),
        "start_frame": int(config["frame_start"]), "mutation": MUTATION_IDS[system["mutation"]],
        "seed": int(config["seed"]), "refractory_frames": 4, "fps": float(config["fps"]),
        "domain_width": float(system["domain_width"]), "domain_height": float(system["domain_height"]),
        "scar_decay": float(system["decay"]), "healing_decay": min(float(system["decay"]), 0.92),
        "deposit_amount": float(system["deposit"]), "attraction_threshold": float(system["attraction_threshold"]),
        "saturation_threshold": float(system["saturation_threshold"]), "field_strength": float(system["field_strength"]),
        "wander_strength": 0.025, "speed": float(system["speed"]),
    }
    group = update.parmTemplateGroup()
    for name, value in values.items():
        template = hou.IntParmTemplate(name, name, 1, default_value=(value,)) if isinstance(value, int) else hou.FloatParmTemplate(name, name, 1, default_value=(value,))
        group.append(template)
    update.setParmTemplateGroup(group)
    for name, value in values.items():
        update.parm(name).set(value)
    source.setPosition(hou.Vector2(0, 0))
    update.setPosition(hou.Vector2(3, 0))
    return source, update


def extend(experiment_path: Path, output: Path, start: int, end: int) -> None:
    if start <= 1 or end < start:
        raise ValueError("continuation requires 1 < start-frame <= end-frame")
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    config = config_from_experiment(experiment)
    cache = output / "cache"
    source_frame = start - 1
    source_path = cache / f"vex-state.{source_frame:04d}.bgeo.sc"
    if not source_path.is_file():
        raise FileNotFoundError(f"missing authoritative source cache: {source_path}")
    collisions = [cache / f"vex-state.{frame:04d}.bgeo.sc" for frame in range(start, end + 1)]
    existing = [path for path in collisions if path.exists()]
    if existing:
        raise FileExistsError(f"refusing to overwrite continuation cache: {existing[0]}")

    hou.hipFile.clear(suppress_save_prompt=True)
    source, update = configure_update(config)
    source.parm("file").set(str(source_path.resolve()))
    hashes: dict[str, str] = {}
    final_geometry = None
    previous = source_path
    for frame in range(start, end + 1):
        source.parm("file").set(str(previous.resolve()))
        source.parm("reload").pressButton()
        update.parm("current_frame").set(frame)
        try:
            update.cook(force=True)
        except hou.OperationFailed as exc:
            raise RuntimeError(f"Stateful VEX continuation failed at frame {frame}: {'; '.join(update.errors()) or exc}") from exc
        errors = list(update.errors())
        if errors:
            raise RuntimeError(f"Stateful VEX continuation failed at frame {frame}: {'; '.join(errors)}")
        final_geometry = update.geometry()
        if final_geometry is None:
            raise RuntimeError(f"Stateful VEX continuation produced no geometry at frame {frame}")
        target = cache / f"vex-state.{frame:04d}.bgeo.sc"
        final_geometry.saveToFile(str(target))
        hashes[target.name] = hashlib.sha256(target.read_bytes()).hexdigest()
        previous = target

    assert final_geometry is not None
    reloaded = hou.Geometry()
    reloaded.loadFromFile(str(previous))
    source.parm("file").set(str(previous.resolve()))
    source.setDisplayFlag(True); source.setRenderFlag(True)
    update.setDisplayFlag(False); update.setRenderFlag(False)
    hip = output / "scar-tissue-continuation.hiplc"
    hou.hipFile.save(str(hip))
    count = int(config["system"]["agent_count"])
    metrics = {
        "schema_version": 1, "operation": "vex-authoritative-continuation",
        "experiment_id": config["id"], "source_frame": source_frame,
        "source_cache_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "frame_start": start, "frame_end": end, "vex_cook_count": end - start + 1,
        "engine": "houdini-vex-authoritative", "state_authority": "vex-geometry",
        "verification_scope": "continued from prior serialized VEX geometry without reinitialization",
        "state_sha256": state_digest(reloaded, count), "state_digest_source": "reloaded-final-cache",
        "final_cache": previous.name, "final_cache_sha256": hashes[previous.name],
        "cache_sha256": hashes, "vex_errors": [],
        "hip": {"path": hip.name, "bytes": hip.stat().st_size, "sha256": hashlib.sha256(hip.read_bytes()).hexdigest()},
    }
    (output / "continuation-metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output.resolve())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--start-frame", type=int, required=True)
    parser.add_argument("--end-frame", type=int, required=True)
    args = parser.parse_args()
    extend(args.experiment.resolve(), args.output.resolve(), args.start_frame, args.end_frame)


if __name__ == "__main__":
    main()
