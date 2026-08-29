"""Contained, read-only discovery of reviewable Studio artifacts."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .studio_store import StudioStore


_KIND_BY_SUFFIX = {
    ".mp4": "video",
    ".mov": "video",
    ".webm": "video",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".hip": "scene",
    ".hiplc": "scene",
    ".hipnc": "scene",
    ".json": "document",
    ".md": "document",
    ".txt": "document",
    ".zip": "package",
}
_JOB_OUTPUT_ROOTS = frozenset(("review", "lookdev", "package", "publish", "render"))
_STUDIO_OUTPUT_ROOTS = frozenset(
    ("handoffs", "probes", "chromatic", "cinematography", "motion-checks", "specimen-outputs", "field-station")
)
_TEMP_SUFFIXES = frozenset((".tmp", ".part", ".partial", ".lock"))
_EXCLUDED_DIRECTORIES = frozenset(("motion-frames", "hips", "cache"))
_DISCOVERABLE_KINDS = frozenset(("video", "image", "package"))
_FRAME_NUMBER = re.compile(r"(\d+)(?=\.[^.]+$)")
_CATALOG_CACHE_LOCK = threading.RLock()
_CATALOG_TARGETS: dict[Path, dict[str, Path]] = {}


class ArtifactCatalogError(ValueError):
    pass


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _catalog_id(relative: str) -> str:
    return "catalog-" + hashlib.sha256(relative.encode("utf-8")).hexdigest()[:20]


def _safe_file(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size <= 0:
        return False
    if path.suffix.lower() not in _KIND_BY_SUFFIX or path.suffix.lower() in _TEMP_SUFFIXES:
        return False
    lowered = path.name.lower()
    if path.name.startswith(".") or lowered in {"effective-config.json", ".env"}:
        return False
    if any(part.startswith(".") for part in path.parts):
        return False
    return not any(token in lowered for token in (".tmp", ".partial", ".lock"))


def _discoverable_file(path: Path) -> bool:
    return _safe_file(path) and _KIND_BY_SUFFIX[path.suffix.lower()] in _DISCOVERABLE_KINDS


def _stage(relative: str) -> str:
    parts = Path(relative).parts
    if len(parts) >= 3 and parts[0:2] == ("work", "jobs"):
        return parts[3] if len(parts) > 3 else "job"
    if len(parts) >= 3 and parts[0:2] == ("work", "studio"):
        return "handoff" if parts[2] == "handoffs" else parts[2].removesuffix("s")
    if len(parts) >= 4 and parts[0] == "studies" and parts[1].startswith("study_"):
        if parts[2] in {"03_specimen", "04_delivery"}:
            return re.sub(r"^[0-9]{2}_", "", parts[2])
        return re.sub(r"^[0-9]{2}_", "", parts[3])
    return "unknown"


def _inferred_track(relative: str) -> str | None:
    lowered = relative.lower()
    for token, track in (
        ("chromatic", "chromatic"),
        ("cinematography", "cinematography"),
        ("motion-check", "cinematography"),
        ("look", "look"),
        ("behavior", "behavior"),
        ("scar-tissue", "behavior"),
    ):
        if token in lowered:
            return track
    return None


def _inferred_project(relative: str) -> tuple[str, str]:
    lowered = relative.lower()
    for token, project_id, title in (
        ("pilot-study-003", "study-003-nonlocal-affinity-dance", "Study 003 | Nonlocal affinity graph dynamics"),
        ("study-003-affinity", "study-003-nonlocal-affinity-dance", "Study 003 | Nonlocal affinity graph dynamics"),
        ("nonlocal-affinity", "study-003-nonlocal-affinity-dance", "Study 003 | Nonlocal affinity graph dynamics"),
        ("scar-tissue", "study-002-scar-tissue", "Study 002 | Directional refractory path memory"),
        ("001-memory-field", "study-001-memory-field", "Study 001 | Refractory field memory"),
        ("002-mass-flow", "legacy-mass-flow", "Legacy | Mass flow"),
    ):
        if token in lowered:
            return project_id, title
    return "legacy-studio", "Legacy Studio"


def _job_project(job: Path) -> tuple[str, str]:
    config = job / "effective-config.json"
    try:
        value = json.loads(config.read_text(encoding="utf-8"))
        study = value.get("study", {}) if isinstance(value, dict) else {}
        project_id, title = study.get("id"), study.get("title")
        if isinstance(project_id, str) and project_id and isinstance(title, str) and title:
            return project_id, title
    except (OSError, json.JSONDecodeError):
        pass
    return _inferred_project(job.as_posix())


def _file_entry(root: Path, path: Path) -> dict[str, Any]:
    relative = _relative(root, path)
    stat = path.stat()
    kind = _KIND_BY_SUFFIX[path.suffix.lower()]
    return {
        "id": _catalog_id(relative),
        "path": relative,
        "name": path.stem.replace("-", " ").replace("_", " "),
        "stage": _stage(relative),
        "track": _inferred_track(relative),
        "validation": "discovered",
        "artifact_id": None,
        "experiment_id": None,
        "component_ids": [],
        "specimen_ids": [],
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "media": {
            "kind": kind,
            "extension": path.suffix.lower(),
            "mime": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        },
        "url": f"/catalog-media/{_catalog_id(relative)}",
        "_target": path.resolve(),
    }


def _sequence_entry(root: Path, directory: Path, frames: list[tuple[int, Path]]) -> dict[str, Any]:
    relative = _relative(root, directory)
    ordered = sorted(frames)
    stat = directory.stat()
    return {
        "id": _catalog_id(relative),
        "path": relative,
        "name": directory.name.replace("-", " ").replace("_", " "),
        "stage": _stage(relative),
        "track": _inferred_track(relative),
        "validation": "discovered",
        "artifact_id": None,
        "experiment_id": None,
        "component_ids": [],
        "specimen_ids": [],
        "size": sum(path.stat().st_size for _, path in ordered),
        "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "media": {
            "kind": "sequence",
            "extension": ordered[0][1].suffix.lower(),
            "mime": mimetypes.guess_type(ordered[0][1].name)[0] or "application/octet-stream",
            "frame_count": len(ordered),
            "first_frame": ordered[0][0],
            "last_frame": ordered[-1][0],
        },
        "url": f"/catalog-media/{_catalog_id(relative)}",
        "_target": ordered[0][1].resolve(),
    }


def _scan_tree(
    root: Path,
    base: Path,
    entries: dict[str, dict[str, Any]],
    project: tuple[str, str] | None = None,
) -> None:
    if not base.is_dir() or not _inside(base, root):
        return
    sequence_directories: set[Path] = set()
    for directory in sorted((path for path in base.rglob("*") if path.is_dir()), key=lambda path: len(path.parts)):
        if not _inside(directory, base) or any(part in _EXCLUDED_DIRECTORIES for part in directory.parts):
            continue
        frames: list[tuple[int, Path]] = []
        for child in directory.iterdir():
            if not _inside(child, base) or not _safe_file(child) or _KIND_BY_SUFFIX.get(child.suffix.lower()) != "image":
                continue
            match = _FRAME_NUMBER.search(child.name)
            if match:
                frames.append((int(match.group(1)), child))
        if len(frames) >= 2:
            entry = _sequence_entry(root, directory, frames)
            project_id, project_title = project or _inferred_project(entry["path"])
            entry.update({"project_id": project_id, "project_title": project_title})
            entries[entry["path"]] = entry
            sequence_directories.add(directory.resolve())
    for path in base.rglob("*"):
        if not _inside(path, base) or any(part in _EXCLUDED_DIRECTORIES for part in path.parts) or not _discoverable_file(path):
            continue
        resolved = path.resolve()
        if any(parent in sequence_directories for parent in resolved.parents):
            continue
        entry = _file_entry(root, path)
        project_id, project_title = project or _inferred_project(entry["path"])
        entry.update({"project_id": project_id, "project_title": project_title})
        entries.setdefault(entry["path"], entry)


def _registered_records(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    store = StudioStore(root)
    artifacts, _ = store.list("artifacts")
    components, _ = store.list("components")
    specimens, _ = store.list("specimens")
    return (
        [record for record in artifacts if record.get("decision") != "archive"],
        [record for record in components if record.get("state") != "archived"],
        [record for record in specimens if record.get("state") != "archived"],
    )


def _approved_path(root: Path, relative: str) -> Path | None:
    candidate = (root / Path(relative.replace("\\", "/"))).resolve()
    if not _inside(candidate, root) or not candidate.is_file():
        return None
    parts = Path(relative.replace("\\", "/")).parts
    job = len(parts) >= 5 and parts[:2] == ("work", "jobs") and parts[3] in _JOB_OUTPUT_ROOTS
    studio = len(parts) >= 5 and parts[:2] == ("work", "studio") and parts[2] in _STUDIO_OUTPUT_ROOTS
    sectioned_vault = (
        len(parts) >= 6
        and parts[0] == "studies"
        and parts[1].startswith("study_")
        and re.fullmatch(r"0[1-6]_[a-z-]+", parts[2]) is not None
        and parts[3] in {"02_review", "03_selected"}
    )
    flat_vault = (
        len(parts) >= 4
        and parts[0] == "studies"
        and parts[1].startswith("study_")
        and parts[2] in {"03_specimen", "04_delivery"}
    )
    return candidate if (job or studio or sectioned_vault or flat_vault) and _safe_file(candidate) else None


def _study_vault_project(study_directory: Path) -> tuple[str, str]:
    manifest = study_directory / "00_study" / "study.json"
    try:
        value = json.loads(manifest.read_text(encoding="utf-8"))
        study_id, title = value.get("id"), value.get("title")
        if isinstance(study_id, str) and study_id and isinstance(title, str) and title:
            return study_id, title
    except (OSError, json.JSONDecodeError, AttributeError):
        pass
    return _inferred_project(study_directory.as_posix())


def _archived_work_roots(root: Path) -> tuple[str, ...]:
    """Read reset manifests and return normalized work roots hidden from live review."""

    studies = root / "studies"
    archived: set[str] = set()
    if not studies.is_dir():
        return ()
    for manifest in studies.glob("study_*/99_archive/**/archive-manifest.json"):
        try:
            value = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        roots = value.get("archived_work_roots", []) if isinstance(value, dict) else []
        if not isinstance(roots, list):
            continue
        for relative in roots:
            if not isinstance(relative, str):
                continue
            normalized = Path(relative.replace("\\", "/")).as_posix().rstrip("/")
            if normalized.startswith("work/") and ".." not in Path(normalized).parts:
                archived.add(normalized)
    return tuple(sorted(archived))


def _is_archived_path(relative: str, archived_roots: tuple[str, ...]) -> bool:
    normalized = Path(relative.replace("\\", "/")).as_posix().rstrip("/")
    return any(normalized == root or normalized.startswith(root + "/") for root in archived_roots)


def _catalog_entries(root: Path) -> list[dict[str, Any]]:
    root = Path(root).resolve()
    entries: dict[str, dict[str, Any]] = {}
    archived_roots = _archived_work_roots(root)
    jobs = root / "work" / "jobs"
    if jobs.is_dir():
        for job in jobs.iterdir():
            relative_job = _relative(root, job)
            if not job.is_dir() or not _inside(job, jobs) or _is_archived_path(relative_job, archived_roots):
                continue
            for output in _JOB_OUTPUT_ROOTS:
                _scan_tree(root, job / output, entries, _job_project(job))
    studio = root / "work" / "studio"
    for output in _STUDIO_OUTPUT_ROOTS:
        relative_output = _relative(root, studio / output)
        if not _is_archived_path(relative_output, archived_roots):
            _scan_tree(root, studio / output, entries)
    studies = root / "studies"
    if studies.is_dir():
        for study in studies.iterdir():
            if not study.is_dir() or not study.name.startswith("study_") or not _inside(study, studies):
                continue
            project = _study_vault_project(study)
            for phase in study.iterdir():
                if not phase.is_dir() or re.fullmatch(r"0[1-6]_[a-z-]+", phase.name) is None:
                    continue
                if phase.name == "01_behavior":
                    for section in ("02_review", "03_selected"):
                        _scan_tree(root, phase / section, entries, project)
                elif phase.name in {"03_specimen", "04_delivery"}:
                    _scan_tree(root, phase, entries, project)

    entries = {
        relative: entry
        for relative, entry in entries.items()
        if not _is_archived_path(relative, archived_roots)
    }

    artifacts, components, specimens = _registered_records(root)
    components_by_ref: dict[str, list[str]] = {}
    for component in components:
        reference = component.get("source_artifact_ref")
        component_id = component.get("id")
        if isinstance(reference, str) and isinstance(component_id, str):
            components_by_ref.setdefault(reference, []).append(component_id)
    specimen_by_component: dict[str, list[str]] = {}
    for specimen in specimens:
        specimen_id = specimen.get("id")
        component_ids = specimen.get("component_ids")
        if isinstance(specimen_id, str) and isinstance(component_ids, list):
            for component_id in component_ids:
                if isinstance(component_id, str):
                    specimen_by_component.setdefault(component_id, []).append(specimen_id)

    for artifact in artifacts:
        relative = artifact.get("path")
        expected = artifact.get("sha256")
        if (
            artifact.get("decision") == "archive"
            or not isinstance(relative, str)
            or not isinstance(expected, str)
            or _is_archived_path(relative, archived_roots)
        ):
            continue
        path = _approved_path(root, relative)
        if path is None:
            continue
        actual = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        if artifact.get("verified") is not True or actual != expected:
            continue
        entry = entries.get(relative) or _file_entry(root, path)
        if "project_id" not in entry:
            project_id, project_title = _inferred_project(relative)
            entry.update({"project_id": project_id, "project_title": project_title})
        component_ids = sorted(set(components_by_ref.get(relative, [])))
        specimen_ids = sorted({item for component_id in component_ids for item in specimen_by_component.get(component_id, [])})
        entry.update(
            {
                "track": artifact.get("track") or entry["track"],
                "validation": "verified",
                "artifact_id": artifact.get("id"),
                "experiment_id": artifact.get("experiment_id"),
                "component_ids": component_ids,
                "specimen_ids": specimen_ids,
            }
        )
        entries[relative] = entry
    return sorted(entries.values(), key=lambda item: (item["stage"], item["path"]))


def build_artifact_catalog(root: Path) -> list[dict[str, Any]]:
    """Return safe public metadata for all contained, reviewable artifacts."""

    resolved_root = Path(root).resolve()
    entries = _catalog_entries(resolved_root)
    with _CATALOG_CACHE_LOCK:
        _CATALOG_TARGETS[resolved_root] = {item["id"]: Path(item["_target"]).resolve() for item in entries}
    return [{key: value for key, value in item.items() if key != "_target"} for item in entries]


def resolve_catalog_media(root: Path, artifact_id: str) -> Path:
    """Resolve an opaque catalog ID back to its contained current media target."""

    if not re.fullmatch(r"catalog-[a-f0-9]{20}", artifact_id):
        raise FileNotFoundError("catalog artifact not found")
    resolved_root = Path(root).resolve()
    with _CATALOG_CACHE_LOCK:
        target = _CATALOG_TARGETS.get(resolved_root, {}).get(artifact_id)
    if target is not None and target.is_file() and _inside(target, resolved_root):
        return target
    build_artifact_catalog(resolved_root)
    with _CATALOG_CACHE_LOCK:
        target = _CATALOG_TARGETS.get(resolved_root, {}).get(artifact_id)
    if target is not None and target.is_file() and _inside(target, resolved_root):
        return target
    raise FileNotFoundError("catalog artifact not found")
