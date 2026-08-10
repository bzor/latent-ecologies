from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from typing import Sequence

from .diagnostic import validate_diagnostic_png
from .doctor import discover_tools
from .jobs import Job, job_status, set_stage_state


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
