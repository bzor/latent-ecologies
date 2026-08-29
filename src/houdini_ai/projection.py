from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from pathlib import PurePosixPath
from typing import Any, Mapping

from .studio_schema import validate_record
from .studio_store import StudioStore


CLAIM_STATUSES = {"measured", "derived", "observed", "hypothesized"}
_SHA256 = re.compile(r"[a-f0-9]{64}")
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[/\\]")
_URI_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def _relative_public_path(value: object) -> str:
    path = str(value)
    candidate = PurePosixPath(path.replace("\\", "/"))
    if (
        not path
        or candidate.is_absolute()
        or _WINDOWS_ABSOLUTE.match(path)
        or _URI_SCHEME.match(path)
        or ".." in candidate.parts
    ):
        raise ValueError("artifact path must be a contained relative path")
    return candidate.as_posix()


def project_editorial_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Return the public subset of one explicitly approved editorial record."""
    if record.get("visibility") != "public-candidate":
        raise ValueError("private or unknown visibility cannot be projected")
    if record.get("readiness") != "approved":
        raise ValueError("editorial record must be approved before projection")
    license_name = record.get("license")
    if not isinstance(license_name, str) or not license_name.strip():
        raise ValueError("editorial record requires an explicit license")

    record_id = _relative_public_path(record.get("id"))
    if "/" in record_id:
        raise ValueError("record id must be a contained relative name")

    artifacts = []
    for source in record.get("artifacts", []):
        if not isinstance(source, Mapping):
            raise ValueError("artifact must be an object")
        checksum = str(source.get("sha256", ""))
        if not _SHA256.fullmatch(checksum):
            raise ValueError("artifact requires a valid sha256")
        artifacts.append(
            {
                "id": str(source.get("id", "")),
                "path": _relative_public_path(source.get("path")),
                "sha256": checksum,
                "role": str(source.get("role", "")),
                "download": bool(source.get("download", False)),
            }
        )
    if not artifacts:
        raise ValueError("editorial record requires at least one artifact")

    claims = []
    for source in record.get("claims", []):
        status = str(source.get("status", "")) if isinstance(source, Mapping) else ""
        if status not in CLAIM_STATUSES:
            raise ValueError("invalid claim status")
        text = str(source.get("text", "")).strip()
        if not text:
            raise ValueError("claim text is required")
        claims.append({"status": status, "text": text})

    return deepcopy(
        {
            "id": record_id,
            "title": str(record.get("title", "")),
            "summary": str(record.get("summary", "")),
            "license": license_name,
            "artifacts": artifacts,
            "claims": claims,
        }
    )


def project_canonical_editorial(store: StudioStore, editorial_id: str) -> dict[str, Any]:
    """Convert approved canonical records to the public contract without publishing."""

    editorial = store.read("editorial", editorial_id)
    if editorial.get("state") != "approved" or editorial.get("approved") is not True:
        raise ValueError("editorial record must be approved before projection")
    editorial_errors = validate_record("editorial", editorial)
    if editorial_errors:
        raise ValueError("invalid canonical editorial record: " + "; ".join(editorial_errors))

    artifacts, listing_errors = store.list("artifacts")
    if listing_errors:
        raise ValueError("artifact store contains unreadable records")
    artifacts_by_path = {artifact.get("path"): artifact for artifact in artifacts}
    projected_artifacts: list[dict[str, Any]] = []
    roles = editorial.get("roles", [])
    for index, reference in enumerate(editorial["artifact_refs"]):
        artifact = artifacts_by_path.get(reference)
        if artifact is None:
            raise ValueError(f"referenced artifact record is missing: {reference}")
        artifact_errors = validate_record("artifact", artifact)
        if artifact_errors:
            raise ValueError("invalid verified artifact: " + "; ".join(artifact_errors))
        artifact_path = (store.root / str(artifact["path"])).resolve()
        try:
            artifact_path.relative_to(store.root)
        except ValueError as error:
            raise ValueError("verified artifact escapes project root") from error
        if not artifact_path.is_file():
            raise ValueError(f"verified artifact is missing: {reference}")
        actual_sha256 = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        if actual_sha256 != str(artifact["sha256"]).removeprefix("sha256:"):
            raise ValueError(f"verified artifact checksum mismatch: {reference}")
        role = roles[index] if index < len(roles) else (roles[0] if roles else "field-observation")
        projected_artifacts.append(
            {
                "id": artifact["id"],
                "path": artifact["path"],
                "sha256": str(artifact["sha256"]).removeprefix("sha256:"),
                "role": role,
                "download": role == "download",
            }
        )

    public_input = {
        "id": editorial_id.removeprefix("editorial-"),
        "visibility": editorial["visibility"],
        "readiness": editorial["state"],
        "title": editorial.get("title", ""),
        "summary": editorial.get("summary", ""),
        "license": editorial.get("license", ""),
        "claims": editorial.get("claims", []),
        "artifacts": projected_artifacts,
    }
    return project_editorial_record(public_input)
