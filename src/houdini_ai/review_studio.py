from __future__ import annotations

import json
import mimetypes
import re
import threading
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse


MEDIA_EXTENSIONS = {".mp4": "video", ".mov": "video", ".png": "image", ".jpg": "image", ".jpeg": "image"}
SCENE_EXTENSIONS = {".hip", ".hiplc", ".hipnc"}
ARTIFACT_ROOTS = {"review", "lookdev", "package", "publish"}
DECISIONS = {"keep", "reject", "iterate", "approved-look"}
STATUSES = {"open", "acknowledged", "implemented", "resolved"}
STATUS_TRANSITIONS = {
    "open": {"acknowledged", "resolved"},
    "acknowledged": {"open", "implemented", "resolved"},
    "implemented": {"acknowledged", "resolved"},
    "resolved": {"open"},
}
_WRITE_LOCK = threading.Lock()


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _artifact_kind(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix in MEDIA_EXTENSIONS:
        return MEDIA_EXTENSIONS[suffix]
    if suffix in SCENE_EXTENSIONS:
        return "scene"
    if suffix in {".json", ".md", ".txt"}:
        return "document"
    return None


def discover_jobs(root: Path) -> list[dict[str, Any]]:
    jobs_root = root / "work" / "jobs"
    jobs = []
    if not jobs_root.is_dir():
        return jobs
    for directory in jobs_root.iterdir():
        if not directory.is_dir():
            continue
        effective = _read_json(directory / "effective-config.json")
        if not effective or not isinstance(effective.get("study"), dict):
            continue
        study = effective["study"]
        artifacts = []
        for artifact_root in sorted(ARTIFACT_ROOTS):
            base = directory / artifact_root
            if not base.is_dir():
                continue
            for path in base.rglob("*"):
                if not path.is_file() or "motion-frames" in path.parts or path.name == "derived-trails.bgeo.sc":
                    continue
                kind = _artifact_kind(path)
                if kind is None:
                    continue
                relative = path.relative_to(directory).as_posix()
                stat = path.stat()
                artifacts.append(
                    {
                        "path": relative,
                        "name": path.stem.replace("-", " ").replace("_", " "),
                        "kind": kind,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                        "url": f"/media/{quote(directory.name, safe='')}/{quote(relative, safe='/')}",
                    }
                )
        receipts = {}
        receipt_dir = directory / "receipts"
        if receipt_dir.is_dir():
            for receipt_path in receipt_dir.glob("*.json"):
                receipt = _read_json(receipt_path)
                if receipt:
                    receipts[receipt_path.stem] = receipt.get("state", "unknown")
        stat = directory.stat()
        simulation = study.get("simulation", {})
        system = simulation.get("rule_genome", {}).get("system", {})
        jobs.append(
            {
                "id": directory.name,
                "study_id": study.get("id", "unknown"),
                "title": study.get("title", study.get("id", directory.name)),
                "seed": study.get("seed"),
                "quality": study.get("presentation", {}).get("quality"),
                "source_state": effective.get("source_state", "unknown"),
                "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "receipts": receipts,
                "parameters": {
                    key: system[key]
                    for key in (
                        "agent_count", "review_agent_count", "prewarm_frames", "trail_history_checkpoints",
                        "alignment_strength", "cohesion_strength", "separation_strength", "wander_strength",
                    )
                    if key in system
                },
                "artifacts": sorted(artifacts, key=lambda item: (item["kind"], item["path"])),
            }
        )
    return sorted(jobs, key=lambda job: job["modified"], reverse=True)


class ReviewStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.directory = self.root / "work" / "reviews"

    def _path(self, study_id: str) -> Path:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", study_id):
            raise ValueError("invalid study_id")
        return self.directory / f"{study_id}.json"

    def read(self, study_id: str) -> dict[str, Any]:
        return _read_json(self._path(study_id)) or {"version": 1, "study_id": study_id, "items": []}

    def add(self, value: dict[str, Any]) -> dict[str, Any]:
        study_id = str(value.get("study_id", ""))
        job_id = str(value.get("job_id", ""))
        artifact_path = str(value.get("artifact_path", ""))
        kind = str(value.get("kind", "comment"))
        text = str(value.get("text", "")).strip()
        decision = value.get("decision")
        timecode = value.get("timecode")
        if kind not in {"comment", "decision"}:
            raise ValueError("kind must be comment or decision")
        if not text or len(text) > 2000:
            raise ValueError("text must contain 1 to 2000 characters")
        if decision is not None and decision not in DECISIONS:
            raise ValueError("invalid decision")
        if timecode is not None and (not isinstance(timecode, (int, float)) or not 0 <= timecode <= 86400):
            raise ValueError("timecode must be between 0 and 86400 seconds")
        artifact = self.root / "work" / "jobs" / job_id / artifact_path
        if not job_id or not artifact_path or not artifact.is_file() or not _inside(artifact, self.root / "work" / "jobs"):
            raise ValueError("artifact does not exist in work/jobs")
        item = {
            "id": uuid.uuid4().hex,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "study_id": study_id,
            "job_id": job_id,
            "artifact_path": artifact_path,
            "kind": kind,
            "decision": decision,
            "timecode": round(float(timecode), 3) if timecode is not None else None,
            "text": text,
            "status": "open",
        }
        with _WRITE_LOCK:
            payload = self.read(study_id)
            payload["items"].append(item)
            self._write(self._path(study_id), payload)
        return item

    def update_status(self, study_id: str, item_id: str, status: str) -> dict[str, Any]:
        if status not in STATUSES:
            raise ValueError("invalid status")
        with _WRITE_LOCK:
            payload = self.read(study_id)
            item = next((entry for entry in payload["items"] if entry.get("id") == item_id), None)
            if item is None:
                raise ValueError("review item not found")
            prior = item.get("status", "open")
            if status != prior and status not in STATUS_TRANSITIONS.get(prior, set()):
                raise ValueError(f"cannot transition review item from {prior} to {status}")
            item["status"] = status
            item["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._write(self._path(study_id), payload)
        return item

    def respond(self, study_id: str, item_id: str, value: dict[str, Any]) -> dict[str, Any]:
        text = str(value.get("text", "")).strip()
        status = str(value.get("status", "acknowledged"))
        result = value.get("result")
        if not text or len(text) > 2000:
            raise ValueError("response text must contain 1 to 2000 characters")
        if status not in STATUSES:
            raise ValueError("invalid status")
        validated_result = self._validate_result(result) if result is not None else None
        with _WRITE_LOCK:
            payload = self.read(study_id)
            item = next((entry for entry in payload["items"] if entry.get("id") == item_id), None)
            if item is None:
                raise ValueError("review item not found")
            prior = item.get("status", "open")
            if status != prior and status not in STATUS_TRANSITIONS.get(prior, set()):
                raise ValueError(f"cannot transition review item from {prior} to {status}")
            response = {
                "id": uuid.uuid4().hex,
                "author": "assistant",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "text": text,
            }
            item.setdefault("responses", []).append(response)
            item["status"] = status
            item["updated_at"] = response["created_at"]
            if validated_result is not None:
                item["result"] = validated_result
            self._write(self._path(study_id), payload)
        return item

    def _validate_result(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("result must be an object")
        commit = value.get("commit")
        job_id = value.get("job_id")
        artifact_paths = value.get("artifact_paths", [])
        if commit is not None and not re.fullmatch(r"[a-f0-9]{7,64}", str(commit)):
            raise ValueError("result commit must be a Git hash")
        if job_id is not None:
            job_dir = self.root / "work" / "jobs" / str(job_id)
            if not job_dir.is_dir() or not _inside(job_dir, self.root / "work" / "jobs"):
                raise ValueError("result job does not exist")
            if not isinstance(artifact_paths, list) or len(artifact_paths) > 20:
                raise ValueError("result artifact_paths must be a list of at most 20 paths")
            for relative in artifact_paths:
                artifact = job_dir / str(relative)
                if not artifact.is_file() or not _inside(artifact, job_dir):
                    raise ValueError(f"result artifact does not exist: {relative}")
        elif artifact_paths:
            raise ValueError("result artifacts require a job_id")
        return {
            "commit": str(commit) if commit is not None else None,
            "job_id": str(job_id) if job_id is not None else None,
            "artifact_paths": [str(path) for path in artifact_paths],
        }

    @staticmethod
    def _write(path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)


def make_handler(root: Path):
    root = root.resolve()
    website = root / "website"
    store = ReviewStore(root)

    class ReviewHandler(BaseHTTPRequestHandler):
        server_version = "HoudiniReviewStudio/0.1"

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/jobs":
                self._json({"jobs": discover_jobs(root)})
                return
            if parsed.path.startswith("/api/reviews/"):
                study_id = unquote(parsed.path.removeprefix("/api/reviews/"))
                try:
                    self._json(store.read(study_id))
                except ValueError as exc:
                    self._error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            if parsed.path.startswith("/media/"):
                self._media(parsed.path)
                return
            relative = "index.html" if parsed.path == "/" else unquote(parsed.path.lstrip("/"))
            target = (website / relative).resolve()
            if not _inside(target, website) or not target.is_file():
                self._error(HTTPStatus.NOT_FOUND, "not found")
                return
            self._file(target)

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            response_match = re.fullmatch(r"/api/reviews/([^/]+)/([a-f0-9]{32})/responses", path)
            if response_match:
                try:
                    self._json(
                        store.respond(unquote(response_match.group(1)), response_match.group(2), self._body()),
                        HTTPStatus.CREATED,
                    )
                except ValueError as exc:
                    self._error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            if path != "/api/reviews":
                self._error(HTTPStatus.NOT_FOUND, "not found")
                return
            try:
                self._json(store.add(self._body()), HTTPStatus.CREATED)
            except ValueError as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))

        def do_PATCH(self) -> None:  # noqa: N802
            match = re.fullmatch(r"/api/reviews/([^/]+)/([a-f0-9]{32})", urlparse(self.path).path)
            if not match:
                self._error(HTTPStatus.NOT_FOUND, "not found")
                return
            try:
                body = self._body()
                self._json(store.update_status(unquote(match.group(1)), match.group(2), str(body.get("status", ""))))
            except ValueError as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))

        def _body(self) -> dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise ValueError("invalid Content-Length") from exc
            if length <= 0 or length > 65536:
                raise ValueError("request body must be between 1 and 65536 bytes")
            try:
                value = json.loads(self.rfile.read(length))
            except json.JSONDecodeError as exc:
                raise ValueError("request body must be valid JSON") from exc
            if not isinstance(value, dict):
                raise ValueError("request body must be a JSON object")
            return value

        def _media(self, request_path: str) -> None:
            parts = request_path.split("/", 3)
            if len(parts) != 4:
                self._error(HTTPStatus.NOT_FOUND, "not found")
                return
            job_id, relative = unquote(parts[2]), unquote(parts[3])
            target = (root / "work" / "jobs" / job_id / relative).resolve()
            jobs_root = root / "work" / "jobs"
            if not _inside(target, jobs_root) or not target.is_file():
                self._error(HTTPStatus.NOT_FOUND, "not found")
                return
            self._file(target, allow_range=True)

        def _file(self, path: Path, allow_range: bool = False) -> None:
            size = path.stat().st_size
            start, end, status = 0, size - 1, HTTPStatus.OK
            if allow_range and self.headers.get("Range"):
                match = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers["Range"])
                if not match:
                    self._error(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE, "invalid range")
                    return
                start = int(match.group(1) or 0)
                end = min(int(match.group(2) or size - 1), size - 1)
                if start > end or start >= size:
                    self._error(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE, "range outside file")
                    return
                status = HTTPStatus.PARTIAL_CONTENT
            self.send_response(status)
            self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Accept-Ranges", "bytes")
            if status == HTTPStatus.PARTIAL_CONTENT:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            with path.open("rb") as stream:
                stream.seek(start)
                remaining = end - start + 1
                while remaining:
                    chunk = stream.read(min(1024 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)

        def _json(self, value: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(value, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _error(self, status: HTTPStatus, message: str) -> None:
            self._json({"error": message}, status)

        def log_message(self, format: str, *args: Any) -> None:
            print(f"review-studio: {self.address_string()} - {format % args}")

    return ReviewHandler


def serve(root: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), make_handler(root))
    print(f"review studio: http://{host}:{server.server_port}")
    print("feedback: work/reviews/ (local generated state)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
