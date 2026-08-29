from __future__ import annotations

import json
import os
import re
import threading
import uuid
from pathlib import Path
from typing import Any


_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,79}")
_WRITE_LOCK = threading.RLock()


class StudioStore:
    """Contained JSON record storage rooted beneath ``work/studio``."""

    def __init__(self, root: Path):
        if root is None:
            raise TypeError("root must be explicitly supplied")
        self.root = Path(root).resolve()
        self.directory = self.root / "work" / "studio"

    def _path(self, collection: str, record_id: str) -> Path:
        if not _ID_PATTERN.fullmatch(collection):
            raise ValueError("invalid collection")
        if not _ID_PATTERN.fullmatch(record_id):
            raise ValueError("invalid record_id")
        path = self.directory / collection / f"{record_id}.json"
        try:
            path.resolve().relative_to(self.directory.resolve())
        except ValueError as error:
            raise ValueError("record path escapes store root") from error
        return path

    def create(self, collection: str, record_id: str, value: dict[str, Any]) -> dict[str, Any]:
        path = self._path(collection, record_id)
        with _WRITE_LOCK:
            if path.exists():
                raise FileExistsError(f"record already exists: {record_id}")
            self._write(path, value)
        return value

    def update(self, collection: str, record_id: str, value: dict[str, Any]) -> dict[str, Any]:
        path = self._path(collection, record_id)
        with _WRITE_LOCK:
            if not path.is_file():
                raise FileNotFoundError(f"record does not exist: {record_id}")
            self._write(path, value)
        return value

    def read(self, collection: str, record_id: str) -> dict[str, Any]:
        path = self._path(collection, record_id)
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"record is not a JSON object: {record_id}")
        return value

    def list(self, collection: str) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        directory = self._path(collection, "placeholder").parent
        records: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        if not directory.is_dir():
            return records, errors
        for path in sorted(directory.iterdir()):
            if not path.is_file() or path.suffix not in {".json", ".tmp"}:
                continue
            try:
                if path.suffix == ".json" and not _ID_PATTERN.fullmatch(path.stem):
                    raise ValueError("malformed record filename")
                value = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(value, dict):
                    raise ValueError("record is not a JSON object")
                if path.suffix == ".tmp":
                    raise ValueError("interrupted temporary record")
                records.append(value)
            except (OSError, ValueError, json.JSONDecodeError) as error:
                errors.append({"path": str(path), "error": str(error)})
        return records, errors

    @staticmethod
    def _write(path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("x", encoding="utf-8") as handle:
                json.dump(value, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
