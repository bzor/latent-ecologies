from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Sequence

from .diagnostic import validate_diagnostic_png
from .doctor import discover_tools
from .jobs import Job, job_status, set_stage_state
from .simulation import create_review_bundle, sha256_path, validate_metrics


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_matches(job: Job, stage: str, path: Path) -> bool:
    receipt = next(item for item in job_status(job) if item["stage"] == stage)
    artifact = receipt.get("artifact", {})
    return (
        receipt.get("state") == "complete"
        and receipt.get("input_digest") == job.input_digest
        and path.is_file()
        and artifact.get("sha256") == _sha256(path)
    )


def _run_logged(command: Sequence[str], log_path: Path, env: dict[str, str], timeout: int = 180) -> None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        log_path.write_text(str(exc) + "\n", encoding="utf-8")
        raise RuntimeError(str(exc)) from exc
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    log_path.write_text(output + ("\n" if output else ""), encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"command exited {result.returncode}; see {log_path}")


def run_milestone3(job: Job) -> list[str]:
    hython = next(tool for tool in discover_tools() if tool.name == "hython").path
    if hython is None:
        raise RuntimeError("hython is required; run houdini-ai doctor for setup guidance")

    config_path = job.directory / "effective-config.json"
    hip_path = job.directory / "artifacts" / "scene" / "memory-field.hiplc"
    frame = int(job.effective_config["study"]["simulation"]["frame_start"])
    image_path = job.directory / "artifacts" / "frames" / f"diagnostic.{frame:04d}.png"
    script = job.root / "houdini" / "build_study_scene.py"
    temp_dir = job.directory / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    image_path.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["HDAI_PROJECT_ROOT"] = str(job.root)
    env["HOUDINI_TEMP_DIR"] = str(temp_dir)
    messages: list[str] = []

    if _artifact_matches(job, "build", hip_path):
        messages.append("build: complete (reused verified HIP)")
    else:
        set_stage_state(job, "build", "running")
        command = (str(hython), str(script), "build", str(config_path), str(hip_path), str(image_path))
        try:
            _run_logged(command, job.directory / "logs" / "build.log", env)
            if not hip_path.is_file() or hip_path.stat().st_size < 1024:
                raise RuntimeError(f"generated HIP is missing or suspiciously small: {hip_path}")
            set_stage_state(
                job,
                "build",
                "complete",
                command=list(command),
                log="logs/build.log",
                artifact={"path": hip_path.relative_to(job.root).as_posix(), "sha256": _sha256(hip_path)},
            )
            messages.append("build: complete")
        except Exception as exc:
            set_stage_state(job, "build", "failed", error=str(exc), log="logs/build.log")
            raise

    if _artifact_matches(job, "probe", image_path):
        validate_diagnostic_png(image_path, expected_size=_expected_size(job))
        messages.append("probe: complete (reused verified PNG)")
    else:
        set_stage_state(job, "probe", "running")
        command = (str(hython), str(script), "probe", str(hip_path), str(frame))
        try:
            _run_logged(command, job.directory / "logs" / "probe.log", env)
            metadata = validate_diagnostic_png(image_path, expected_size=_expected_size(job))
            set_stage_state(
                job,
                "probe",
                "complete",
                command=list(command),
                log="logs/probe.log",
                artifact={
                    "path": image_path.relative_to(job.root).as_posix(),
                    "sha256": _sha256(image_path),
                    **metadata,
                },
            )
            messages.append("probe: complete")
        except Exception as exc:
            set_stage_state(job, "probe", "failed", error=str(exc), log="logs/probe.log")
            raise
    return messages


def _expected_size(job: Job) -> tuple[int, int]:
    render = job.effective_config["study"]["render"]
    return int(render["width"]), int(render["height"])


def _cache_digest(cache_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(cache_dir.glob("state.*.bgeo.sc")):
        digest.update(path.name.encode())
        digest.update(sha256_path(path).encode())
    return digest.hexdigest()


def run_simulation(job: Job) -> str:
    receipt = next(item for item in job_status(job) if item["stage"] == "simulate")
    simulation = job.effective_config["study"]["simulation"]
    expected_count = simulation["frame_end"] - simulation["frame_start"] + 1
    metrics_path = job.directory / "simulation" / "metrics.json"
    cache_dir = job.directory / "simulation" / "cache"
    cache_files = list(cache_dir.glob("state.*.bgeo.sc"))
    if (
        receipt.get("state") == "complete"
        and receipt.get("input_digest") == job.input_digest
        and metrics_path.is_file()
        and receipt.get("metrics_sha256") == sha256_path(metrics_path)
        and len(cache_files) == expected_count
        and receipt.get("cache_sha256") == _cache_digest(cache_dir)
    ):
        validate_metrics(metrics_path, job.effective_config)
        create_review_bundle(job, metrics_path)
        return "simulate: complete (reused verified cache)"

    hython = next(tool for tool in discover_tools() if tool.name == "hython").path
    if hython is None:
        raise RuntimeError("hython is required; run houdini-ai doctor for setup guidance")
    script = job.root / "houdini" / "simulate_memory_field.py"
    hip_path = job.directory / "artifacts" / "scene" / "memory-field.hiplc"
    config_path = job.directory / "effective-config.json"
    env = dict(os.environ)
    env["HDAI_PROJECT_ROOT"] = str(job.root)
    env["HOUDINI_TEMP_DIR"] = str(job.directory / "temp")
    simulation_dir = job.directory / "simulation"
    simulation_dir.mkdir(parents=True, exist_ok=True)
    set_stage_state(job, "simulate", "running")

    def invoke(label: str, config: Path, output_cache: Path, output_metrics: Path, frame_end: int | None) -> None:
        command = [str(hython), str(script), str(hip_path), str(config), str(output_cache), str(output_metrics)]
        if frame_end is not None:
            command.extend(("--frame-end", str(frame_end)))
        _run_logged(command, job.directory / "logs" / f"simulate-{label}.log", env, timeout=300)

    try:
        smoke_end = min(simulation["frame_start"] + 23, simulation["frame_end"])
        smoke_a = simulation_dir / "smoke-a.json"
        smoke_b = simulation_dir / "smoke-b.json"
        invoke("smoke-a", config_path, simulation_dir / "smoke-a-cache", smoke_a, smoke_end)
        invoke("smoke-b", config_path, simulation_dir / "smoke-b-cache", smoke_b, smoke_end)
        validate_metrics(smoke_a, job.effective_config, smoke_end)
        validate_metrics(smoke_b, job.effective_config, smoke_end)
        if sha256_path(smoke_a) != sha256_path(smoke_b):
            raise RuntimeError("same-seed smoke simulations produced different metrics")

        variant = json.loads(json.dumps(job.effective_config))
        variant["study"]["seed"] += 1
        variant_path = simulation_dir / "changed-seed-config.json"
        variant_path.write_text(json.dumps(variant, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        variant_metrics = simulation_dir / "changed-seed.json"
        invoke("changed-seed", variant_path, simulation_dir / "changed-seed-cache", variant_metrics, smoke_end)
        validate_metrics(variant_metrics, variant, smoke_end)
        if sha256_path(smoke_a) == sha256_path(variant_metrics):
            raise RuntimeError("changed seed did not produce a distinct simulation")

        invoke("full", config_path, cache_dir, metrics_path, None)
        summary = validate_metrics(metrics_path, job.effective_config)
        if len(list(cache_dir.glob("state.*.bgeo.sc"))) != expected_count:
            raise RuntimeError("full simulation cache is incomplete")
        review = create_review_bundle(job, metrics_path)
        set_stage_state(
            job,
            "simulate",
            "complete",
            metrics="simulation/metrics.json",
            metrics_sha256=sha256_path(metrics_path),
            cache="simulation/cache",
            cache_sha256=_cache_digest(cache_dir),
            smoke_deterministic=True,
            changed_seed_distinct=True,
            summary=summary,
            review=review,
        )
        return "simulate: complete"
    except Exception as exc:
        set_stage_state(job, "simulate", "failed", error=str(exc), log="logs/simulate-*.log")
        raise


def run_lookdev(job: Job) -> str:
    look_dir = job.directory / "lookdev"
    receipt_path = look_dir / "receipt.json"
    frames = (
        int(job.effective_config["study"]["simulation"]["frame_start"]),
        round(
            (
                job.effective_config["study"]["simulation"]["frame_start"]
                + job.effective_config["study"]["simulation"]["frame_end"]
            )
            / 2
        ),
        int(job.effective_config["study"]["simulation"]["frame_end"]),
    )
    images = [look_dir / f"field-study.{frame:04d}.png" for frame in frames]
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        receipt = {}
    if receipt.get("input_digest") == job.input_digest and all(
        image.is_file() and receipt.get("images", {}).get(image.name) == sha256_path(image) for image in images
    ):
        for image in images:
            validate_diagnostic_png(image, expected_size=_expected_size(job))
        return "lookdev: complete (reused verified stills)"

    hython = next(tool for tool in discover_tools() if tool.name == "hython").path
    if hython is None:
        raise RuntimeError("hython is required; run houdini-ai doctor for setup guidance")
    look_dir.mkdir(parents=True, exist_ok=True)
    hip_path = job.directory / "artifacts" / "scene" / "memory-field.hiplc"
    script = job.root / "houdini" / "render_field_study.py"
    env = dict(os.environ)
    env["HDAI_PROJECT_ROOT"] = str(job.root)
    env["HOUDINI_TEMP_DIR"] = str(job.directory / "temp")
    for frame, image in zip(frames, images):
        cache = job.directory / "simulation" / "cache" / f"state.{frame:04d}.bgeo.sc"
        command = (str(hython), str(script), str(hip_path), str(cache), str(image), str(frame))
        _run_logged(command, job.directory / "logs" / f"lookdev-{frame:04d}.log", env, timeout=300)
        validate_diagnostic_png(image, expected_size=_expected_size(job))
    instrument_source = job.directory / "review" / "instrument-frame.png"
    instrument_target = look_dir / "instrument-frame.png"
    if instrument_source.is_file():
        instrument_target.write_bytes(instrument_source.read_bytes())
    receipt = {
        "receipt_version": 1,
        "input_digest": job.input_digest,
        "frames": list(frames),
        "images": {image.name: sha256_path(image) for image in images},
        "instrument": instrument_target.name if instrument_target.is_file() else "unavailable",
        "depth_of_field": False,
        "camera": "static-observation",
        "look": "field-study",
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return "lookdev: complete"
