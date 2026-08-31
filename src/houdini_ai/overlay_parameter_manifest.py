"""Structured parameter snapshots consumed by overlay components."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from .study_vault import parse_variation_stem, variation_file_stem


_VALUE_TYPES = (str, int, float, bool)

# A Behavior HDA reports the variation number and title KC set on it. It does not know
# which promoted behavior the Study filed it under, so a manifest carries
# behavior_number only when the asset exposes it, and defaults to the first behavior.
DEFAULT_BEHAVIOR_NUMBER = 1


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "untitled"


def manifest_behavior_number(manifest: Mapping[str, Any]) -> int:
    variation = manifest.get("variation")
    if isinstance(variation, Mapping):
        number = variation.get("behavior_number")
        if isinstance(number, int) and not isinstance(number, bool) and 1 <= number <= 999:
            return number
    return DEFAULT_BEHAVIOR_NUMBER


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
        behavior_number = variation.get("behavior_number", DEFAULT_BEHAVIOR_NUMBER)
        if (
            isinstance(behavior_number, bool)
            or not isinstance(behavior_number, int)
            or not 1 <= behavior_number <= 999
        ):
            errors.append("variation.behavior_number must be between 1 and 999")
        elif isinstance(number, int) and isinstance(title, str) and title.strip():
            # A manifest is an HDA's self-report. An asset built before the behavior
            # axis existed reports a variation-local stem, which stays acceptable as
            # input; overlay_manifest_fields upgrades it to the canonical three-axis
            # stem before anything is written into the vault.
            canonical = variation_file_stem(behavior_number, number, title)
            legacy = f"var_{number:03d}_{_slug(title)}"
            if variation.get("file_stem") not in {canonical, legacy}:
                errors.append(
                    "variation.file_stem does not match its behavior number, number, and title"
                )

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


def overlay_manifest_fields(
    manifest: Mapping[str, Any], behavior_number: int | None = None
) -> dict[str, Any]:
    """Map a validated manifest to structured and legacy overlay fields.

    ``behavior_number`` supplies the Study's behavior identity for an asset whose
    Overlay Detail folder does not expose one. It recomposes the canonical stem, so
    the sidecar written into the vault always carries the full three-axis identity
    even when the manifest came from an older HDA.
    """
    parameters = [dict(parameter) for parameter in manifest["parameters"]]
    variation = dict(manifest["variation"])
    behavior = manifest_behavior_number(manifest) if behavior_number is None else behavior_number
    stem = variation_file_stem(behavior, int(variation["number"]), str(variation["title"]))
    variation["behavior_number"] = behavior
    variation["file_stem"] = stem
    slug = parse_variation_stem(stem)["slug"]
    return {
        "variation": {
            "id": f"variation-bhvr{behavior:03d}-{int(variation['number']):03d}-{slug}",
            "number": variation["number"],
            "behavior_number": behavior,
            "title": variation["title"],
            "slug": slug,
            "file_stem": stem,
        },
        "parameter_manifest": {
            "schema_version": manifest["schema_version"],
            "variation": variation,
            "source": dict(manifest["source"]),
        },
        "overlay_parameters": parameters,
        "params": [[parameter["label"], _display_value(parameter["value"])] for parameter in parameters],
    }


HEADLESS_BINDING = "headless-clean-load"


def bind_headless_overlay_manifest(
    manifest_path: Path,
    hip_path: Path,
    pre_load_sha256: str,
) -> dict[str, Any]:
    """Bind a headless manifest export to the locked HIP's on-disk checksum.

    ``hou.hipFile.hasUnsavedChanges()`` reports true in hython immediately after a
    clean load, so an HDA export can never bind the checksum itself in a headless
    session. The driver that loaded the scene holds the missing evidence: it hashed
    the HIP before loading, made no scene mutations before exporting, and the file
    is unchanged afterwards. This function verifies that claim against the on-disk
    file and rewrites the manifest with the bound checksum and its provenance.
    """
    import hashlib

    manifest = load_overlay_parameter_manifest(manifest_path)
    errors = validate_overlay_parameter_manifest(manifest)
    if errors:
        raise ValueError("manifest is invalid: " + "; ".join(errors))

    digest = "sha256:" + hashlib.sha256(Path(hip_path).read_bytes()).hexdigest()
    if not pre_load_sha256.startswith("sha256:"):
        pre_load_sha256 = "sha256:" + pre_load_sha256
    if digest != pre_load_sha256:
        raise ValueError(
            f"HIP changed on disk between load and binding: {pre_load_sha256} became {digest}"
        )

    source = dict(manifest["source"])
    recorded = Path(str(source["hip_path"]))
    if recorded.resolve() != Path(hip_path).resolve():
        raise ValueError(
            f"manifest was exported from {recorded}, not the HIP being bound ({hip_path})"
        )

    existing = source.get("hip_sha256")
    if existing is not None:
        if existing != digest:
            raise ValueError(
                f"manifest already binds {existing}, which does not match the on-disk HIP {digest}"
            )
        return manifest

    source["hip_sha256"] = digest
    source["hip_dirty"] = False
    source["checksum_binding"] = HEADLESS_BINDING
    bound = dict(manifest)
    bound["source"] = source
    temporary = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    temporary.write_text(json.dumps(bound, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(manifest_path)
    return bound
