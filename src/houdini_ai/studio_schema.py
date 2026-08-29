"""Draft 2020-12 validation for core Studio records."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource

_SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "schemas" / "studio"
_KINDS = (
    "idea", "direction", "proposal", "experiment", "artifact", "component", "specimen", "editorial", "note",
    "session", "study", "conversation-binding", "activity", "site-inclusion", "publication-manifest",
    "seed-inclusion", "seed-publication-manifest", "affinity-preset", "look-direction-brief",
    "prototype-preset",
)


@lru_cache(maxsize=1)
def _validators() -> dict[str, Draft202012Validator]:
    schemas: dict[str, dict[str, Any]] = {}
    for path in _SCHEMA_ROOT.glob("*.schema.json"):
        schemas[path.name] = json.loads(path.read_text(encoding="utf-8"))

    registry = Registry()
    for name, schema in schemas.items():
        resource = Resource.from_contents(schema)
        registry = registry.with_resource(schema["$id"], resource)
        registry = registry.with_resource((_SCHEMA_ROOT / name).as_uri(), resource)

    validators: dict[str, Draft202012Validator] = {}
    for kind in _KINDS:
        schema = schemas[f"{kind}.schema.json"]
        Draft202012Validator.check_schema(schema)
        validators[kind] = Draft202012Validator(schema, registry=registry)
    return validators


def _error_path(error: Any) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    if path:
        return path
    if error.validator == "required":
        missing = error.message.split("'")[1]
        return missing
    if error.validator == "additionalProperties":
        unexpected = error.message.split("'")[1]
        return unexpected
    return "$"


def validate_record(kind: str, value: object) -> list[str]:
    """Return deterministic, path-specific errors without modifying *value*."""

    if kind not in _KINDS:
        return [f"kind: unknown studio record kind {kind!r}"]
    try:
        errors = _validators()[kind].iter_errors(value)
        return [f"{_error_path(error)}: {error.message}" for error in sorted(errors, key=lambda item: list(item.path))]
    except (OSError, ValueError, SchemaError) as error:
        return [f"schema: {error}"]
