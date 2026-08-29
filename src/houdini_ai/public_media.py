"""Materialize content-addressed public media without network action."""

from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path
from typing import Any

from .studio_schema import validate_record
from .studio_store import StudioStore


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def materialize_public_media(
    store: StudioStore,
    root: Path,
    manifest: dict[str, Any],
    output_directory: Path,
) -> list[dict[str, Any]]:
    errors = validate_record("publication-manifest", manifest)
    if errors:
        raise ValueError("; ".join(errors))
    root = Path(root).resolve()
    output_directory = Path(output_directory).resolve()
    public_root = (root / "work" / "public-site").resolve()
    if not _inside(output_directory, public_root):
        raise ValueError("public output must remain beneath work/public-site")

    receipts: list[dict[str, Any]] = []
    for item in manifest["items"]:
        artifact = store.read("artifacts", str(item["artifact_id"]))
        artifact_errors = validate_record("artifact", artifact)
        if artifact_errors:
            raise ValueError("; ".join(artifact_errors))
        source = (root / str(artifact["path"])).resolve()
        if not _inside(source, root) or not source.is_file():
            raise ValueError(f"public media source is missing or escapes the project: {artifact['id']}")
        expected = str(item["source_sha256"]).split(":", 1)[1]
        actual = _digest(source)
        if actual != expected or artifact.get("sha256") != item.get("source_sha256"):
            raise ValueError(f"public media checksum mismatch: {artifact['id']}")
        relative = Path(str(item["media"]["public_path"]))
        target = (output_directory / relative).resolve()
        if not _inside(target, output_directory):
            raise ValueError("public media target escapes output directory")
        if target.exists():
            if not target.is_file() or _digest(target) != expected:
                raise ValueError(f"content-addressed public target has unexpected bytes: {relative.as_posix()}")
        else:
            write_atomic(target, source.read_bytes())
        receipts.append(
            {
                "artifact_id": artifact["id"],
                "path": relative.as_posix(),
                "bytes": target.stat().st_size,
                "sha256": f"sha256:{_digest(target)}",
            }
        )
    return receipts
