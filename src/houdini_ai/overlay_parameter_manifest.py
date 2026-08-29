"""Structured parameter snapshots consumed by overlay components."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping


_VALUE_TYPES = (str, int, float, bool)


def _variation_file_stem(number: int, title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "untitled"
    return f"var_{number:03d}_{slug}"


def validate_overlay_parameter_manifest(manifest: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    variation = manifest.get("variation")
    if not isinstance(variation, Mapping):
        errors.append("variation must be an object")
    else:
        number = variation.get("number")
        title = variation.get("title")
        if not isinstance(number, int) or not 1 <= number <= 999:
            errors.append("variation.number must be between 1 and 999")
        if not isinstance(title, str) or not title.strip():
            errors.append("variation.title must be a non-empty string")
        if isinstance(number, int) and isinstance(title, str) and title.strip():
            if variation.get("file_stem") != _variation_file_stem(number, title):
                errors.append("variation.file_stem does not match its number and title")

    source = manifest.get("source")
    if not isinstance(source, Mapping):
        errors.append("source must be an object")
    else:
        for field in ("hip_path", "node_path", "asset_type"):
            if not isinstance(source.get(field), str) or not str(source[field]).strip():
                errors.append(f"source.{field} must be a non-empty string")
        if not isinstance(source.get("hip_dirty"), bool):
            errors.append("source.hip_dirty must be boolean")
        if not isinstance(source.get("frame"), (int, float)):
            errors.append("source.frame must be numeric")
        checksum = source.get("hip_sha256")
        if checksum is not None and (
            not isinstance(checksum, str) or re.fullmatch(r"sha256:[a-f0-9]{64}", checksum) is None
        ):
            errors.append("source.hip_sha256 must be null or a sha256 digest")

    parameters = manifest.get("parameters")
    if not isinstance(parameters, list) or not parameters:
        errors.append("parameters must be a non-empty list")
        return errors

    seen: set[str] = set()
    for index, parameter in enumerate(parameters):
        prefix = f"parameters[{index}]"
        if not isinstance(parameter, Mapping):
            errors.append(f"{prefix} must be an object")
            continue
        key = parameter.get("key")
        if not isinstance(key, str) or re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+", key) is None:
            errors.append(f"{prefix}.key must be a stable dotted key")
        elif key in seen:
            errors.append(f"duplicate parameter key {key!r}")
        else:
            seen.add(key)
        for field in ("label", "parameter", "type", "units"):
            if not isinstance(parameter.get(field), str) or not str(parameter[field]).strip():
                errors.append(f"{prefix}.{field} must be a non-empty string")
        value = parameter.get("value")
        if not isinstance(value, _VALUE_TYPES) or value is None:
            errors.append(f"{prefix}.value must be a scalar")
        if not isinstance(parameter.get("animated"), bool):
            errors.append(f"{prefix}.animated must be boolean")
        comparison = parameter.get("comparison_range")
        if comparison is not None and (
            not isinstance(comparison, list)
            or len(comparison) != 2
            or any(not isinstance(item, (int, float)) for item in comparison)
            or comparison[0] >= comparison[1]
        ):
            errors.append(f"{prefix}.comparison_range must be [minimum, maximum] with minimum below maximum")
    return errors


def load_overlay_parameter_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_overlay_parameter_manifest(manifest)
    if errors:
        raise ValueError(f"{path}: " + "; ".join(errors))
    return manifest


def _display_value(value: object) -> str:
    if isinstance(value, bool):
        return "on" if value else "off"
    if isinstance(value, float):
        return format(value, ".8g")
    return str(value)


def overlay_manifest_fields(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Map a validated manifest to structured and legacy overlay fields."""
    parameters = [dict(parameter) for parameter in manifest["parameters"]]
    variation = dict(manifest["variation"])
    slug = str(variation["file_stem"]).split("_", 2)[2]
    return {
        "variation": {
            "id": f"variation-{int(variation['number']):03d}-{slug}",
            "number": variation["number"],
            "title": variation["title"],
            "slug": slug,
            "file_stem": variation["file_stem"],
        },
        "parameter_manifest": {
            "schema_version": manifest["schema_version"],
            "variation": variation,
            "source": dict(manifest["source"]),
        },
        "overlay_parameters": parameters,
        "params": [[parameter["label"], _display_value(parameter["value"])] for parameter in parameters],
    }
