from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


STAGES = ("validate", "build", "simulate", "probe", "render", "composite", "encode", "package")
STATES = {"pending", "running", "complete", "failed", "stale"}


@dataclass(frozen=True)
class Job:
    job_id: str
    root: Path
    directory: Path
    manifest_path: Path
    effective_config: Mapping[str, Any]
    input_digest: str
    source_state: str


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _git(root: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ("git", "-C", str(root), *arguments),
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def source_state(root: Path) -> str:
    revision = _git(root, "rev-parse", "HEAD")
    if revision == "unknown":
        return revision
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if not status:
        return revision
    changes = _git(root, "diff", "--binary", "HEAD")
    untracked = []
    for line in status.splitlines():
        if line.startswith("?? "):
            path = root / line[3:]
            if path.is_file():
                untracked.append((line[3:], hashlib.sha256(path.read_bytes()).hexdigest()))
    dirty_digest = hashlib.sha256(_canonical_json({"diff": changes, "untracked": untracked})).hexdigest()[:12]
    return f"{revision}+dirty.{dirty_digest}"


def load_job(root: Path, manifest_path: Path) -> Job:
    root = root.resolve()
    manifest_path = manifest_path.resolve()
    project = json.loads((root / "config" / "project.json").read_text(encoding="utf-8"))
    study = json.loads(manifest_path.read_text(encoding="utf-8"))
    revision = source_state(root)
    effective = {
        "project": project,
        "study": study,
        "source_state": revision,
        "manifest_path": manifest_path.relative_to(root).as_posix(),
    }
    digest = hashlib.sha256(_canonical_json(effective)).hexdigest()
    quality = study["presentation"]["quality"]
    job_id = f"{study['id']}-s{study['seed']}-{quality}-{digest[:12]}"
    work_dir = root / project["work_dir"] / "jobs" / job_id
    return Job(job_id, root, work_dir, manifest_path, effective, digest, revision)


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_receipt(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def receipt_path(job: Job, stage: str) -> Path:
    if stage not in STAGES:
        raise ValueError(f"unknown stage: {stage}")
    return job.directory / "receipts" / f"{stage}.json"


def prepare_job(job: Job) -> list[dict[str, Any]]:
    job.directory.mkdir(parents=True, exist_ok=True)
    (job.directory / "logs").mkdir(exist_ok=True)
    _write_json(job.directory / "effective-config.json", dict(job.effective_config))
    receipts = []
    for stage in STAGES:
        path = receipt_path(job, stage)
        receipt = _read_receipt(path)
        if receipt is None:
            receipt = {"receipt_version": 1, "stage": stage, "state": "pending", "input_digest": job.input_digest}
            _write_json(path, receipt)
        elif receipt.get("input_digest") != job.input_digest:
            receipt = {**receipt, "state": "stale", "stale_for_input_digest": job.input_digest}
            _write_json(path, receipt)
        receipts.append(receipt)
    return receipts


def set_stage_state(job: Job, stage: str, state: str, **details: Any) -> dict[str, Any]:
    if state not in STATES:
        raise ValueError(f"invalid stage state: {state}")
    path = receipt_path(job, stage)
    prior = _read_receipt(path) or {}
    receipt = {
        **prior,
        "receipt_version": 1,
        "stage": stage,
        "state": state,
        "input_digest": job.input_digest,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **details,
    }
    _write_json(path, receipt)
    return receipt


def job_status(job: Job) -> list[dict[str, Any]]:
    return [
        _read_receipt(receipt_path(job, stage))
        or {"stage": stage, "state": "pending", "input_digest": job.input_digest}
        for stage in STAGES
    ]
