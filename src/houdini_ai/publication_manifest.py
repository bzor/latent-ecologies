"""Deterministic allowlisted projection for living public Studies."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .artifact_catalog import build_artifact_catalog
from .studio_schema import validate_record
from .studio_store import StudioStore


_PUBLIC_STATES = frozenset(("site-live", "archive-keep"))


def _validate(kind: str, record: dict[str, Any]) -> None:
    errors = validate_record(kind, record)
    if errors:
        raise ValueError("; ".join(errors))


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_publication_manifest(store: StudioStore, root: Path, study_id: str) -> dict[str, Any]:
    root = Path(root).resolve()
    study = store.read("studies", study_id)
    _validate("study", study)

    inclusions, inclusion_errors = store.list("site-inclusions")
    if inclusion_errors:
        raise ValueError("; ".join(error["error"] for error in inclusion_errors))
    selected: list[dict[str, Any]] = []
    for inclusion in inclusions:
        _validate("site-inclusion", inclusion)
        if inclusion.get("study_id") == study_id and inclusion.get("state") in _PUBLIC_STATES:
            selected.append(inclusion)

    catalog = build_artifact_catalog(root)
    items: list[dict[str, Any]] = []
    for inclusion in selected:
        if inclusion.get("rights_status") != "cleared":
            raise ValueError(f"publication requires recorded rights clearance: {inclusion['id']}")
        if inclusion.get("ever_public") is not True or not inclusion.get("first_published_at"):
            raise ValueError(f"public inclusion has inconsistent exposure history: {inclusion['id']}")
        artifact_id = str(inclusion["artifact_id"])
        artifact = store.read("artifacts", artifact_id)
        _validate("artifact", artifact)
        if artifact.get("sha256") != inclusion.get("source_sha256"):
            raise ValueError(f"checksum changed since site inclusion: {artifact_id}")
        matches = [
            entry for entry in catalog
            if entry.get("artifact_id") == artifact_id and entry.get("validation") == "verified"
        ]
        if len(matches) != 1:
            raise ValueError(f"publication requires one currently verified artifact: {artifact_id}")
        entry = matches[0]
        if entry.get("project_id") != study_id:
            raise ValueError(f"artifact belongs to a different Study: {artifact_id}")
        media = entry.get("media")
        if not isinstance(media, dict):
            raise ValueError(f"artifact has no public media metadata: {artifact_id}")
        extension = media.get("extension")
        mime = media.get("mime")
        kind = media.get("kind")
        size = entry.get("size")
        if not isinstance(extension, str) or not isinstance(mime, str) or not isinstance(kind, str) or not isinstance(size, int):
            raise ValueError(f"artifact media metadata is invalid: {artifact_id}")
        digest = str(artifact["sha256"]).split(":", 1)[1]
        items.append(
            {
                "inclusion_id": inclusion["id"],
                "artifact_id": artifact_id,
                "source_sha256": artifact["sha256"],
                "state": inclusion["state"],
                "title": inclusion["public_title"],
                "caption": inclusion["public_caption"],
                "role": inclusion["role"],
                "section": inclusion["section"],
                "order": inclusion["order"],
                "alt_text": inclusion["alt_text"],
                "media": {
                    "kind": kind,
                    "extension": extension,
                    "mime": mime,
                    "size": size,
                    "public_path": f"media/{digest}{extension}",
                },
            }
        )

    items.sort(key=lambda item: (str(item["section"]), int(item["order"]), str(item["inclusion_id"])))
    content = {
        "schema_version": 1,
        "mode": "archive" if study["state"] == "archived" else "living",
        "study": {
            "id": study["id"],
            "title": study["title"],
            "state": study["state"],
            "current_phase": study["current_phase"],
        },
        "items": items,
    }
    digest = _canonical_digest(content)
    manifest = {
        **content,
        "id": f"publication-manifest-{digest[:20]}",
        "content_sha256": f"sha256:{digest}",
    }
    _validate("publication-manifest", manifest)
    return manifest
