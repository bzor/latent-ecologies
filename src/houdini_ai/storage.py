from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_CATEGORIES = ("stale-jobs", "smoke-caches", "temp")
ALL_CATEGORIES = (*DEFAULT_CATEGORIES, "packaged-sequences")


def directory_size(path: Path) -> tuple[int, int]:
    size = 0
    count = 0
    if not path.exists():
        return size, count
    for item in path.rglob("*"):
        if item.is_file():
            try:
                size += item.stat().st_size
                count += 1
            except OSError:
                continue
    return size, count


@dataclass(frozen=True)
class JobStorage:
    path: Path
    job_id: str
    study_id: str
    size: int
    files: int
    latest: bool
    retention_protected: bool
    package_complete: bool


@dataclass(frozen=True)
class CleanupItem:
    category: str
    path: Path
    size: int
    reason: str


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def inventory_jobs(root: Path) -> list[JobStorage]:
    jobs_dir = root.resolve() / "work" / "jobs"
    raw = []
    for path in jobs_dir.iterdir() if jobs_dir.is_dir() else ():
        if not path.is_dir():
            continue
        effective = _read_json(path / "effective-config.json")
        study = effective.get("study", {})
        study_id = str(study.get("id", path.name.split("-s", 1)[0]))
        status = study.get("status")
        publication = study.get("publication", {})
        protected = status == "selected" or publication.get("state") in {"approved", "published"}
        package = _read_json(path / "receipts" / "package.json")
        size, files = directory_size(path)
        raw.append((path, study_id, protected, package.get("state") == "complete", size, files))
    newest: dict[str, Path] = {}
    for path, study_id, *_ in raw:
        if study_id not in newest or path.stat().st_mtime > newest[study_id].stat().st_mtime:
            newest[study_id] = path
    return [
        JobStorage(path, path.name, study_id, size, files, newest.get(study_id) == path, protected, package_complete)
        for path, study_id, protected, package_complete, size, files in raw
    ]


def storage_report(root: Path) -> dict:
    root = root.resolve()
    jobs = inventory_jobs(root)
    work_size, work_files = directory_size(root / "work")
    config = _read_json(root / "config" / "project.json").get("storage", {})
    warning = float(config.get("warning_gb", 20.0)) * 1024**3
    critical = float(config.get("critical_gb", 50.0)) * 1024**3
    minimum_free = float(config.get("minimum_free_gb", 100.0)) * 1024**3
    disk = shutil.disk_usage(root)
    level = "critical" if work_size >= critical or disk.free < minimum_free else "warning" if work_size >= warning else "ok"
    return {
        "work_size": work_size,
        "work_files": work_files,
        "level": level,
        "warning_bytes": int(warning),
        "critical_bytes": int(critical),
        "disk_free": disk.free,
        "minimum_free_bytes": int(minimum_free),
        "jobs": sorted(jobs, key=lambda item: item.size, reverse=True),
    }


def plan_cleanup(root: Path, categories: Iterable[str] = DEFAULT_CATEGORIES) -> list[CleanupItem]:
    root = root.resolve()
    requested = set(categories)
    unknown = requested - set(ALL_CATEGORIES)
    if unknown:
        raise ValueError(f"unknown cleanup categories: {', '.join(sorted(unknown))}")
    items: list[CleanupItem] = []
    for job in inventory_jobs(root):
        if "stale-jobs" in requested and not job.latest and not job.retention_protected:
            items.append(CleanupItem("stale-jobs", job.path, job.size, "superseded reproducible job"))
            continue
        if job.retention_protected:
            continue
        if "smoke-caches" in requested:
            patterns = ("simulation/smoke-*-cache", "simulation/changed-seed-cache")
            for pattern in patterns:
                for path in job.path.glob(pattern):
                    size, _ = directory_size(path)
                    if size:
                        items.append(CleanupItem("smoke-caches", path, size, "determinism gate cache"))
        if "temp" in requested:
            path = job.path / "temp"
            size, _ = directory_size(path)
            if size:
                items.append(CleanupItem("temp", path, size, "recreatable process scratch"))
        if "packaged-sequences" in requested and job.package_complete:
            path = job.path / "render" / "frames"
            size, _ = directory_size(path)
            if size:
                items.append(CleanupItem("packaged-sequences", path, size, "sequence retained in verified package outputs"))
    return sorted(items, key=lambda item: item.size, reverse=True)


def apply_cleanup(root: Path, items: Iterable[CleanupItem]) -> int:
    root = root.resolve()
    jobs_root = (root / "work" / "jobs").resolve()
    reclaimed = 0
    for item in items:
        target = item.path.resolve()
        if target == jobs_root or jobs_root not in target.parents:
            raise RuntimeError(f"refusing cleanup outside the job workspace: {target}")
        if target.exists():
            reclaimed += item.size
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
    return reclaimed


def format_bytes(value: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"
