"""Canonical study card: the systematized text identity of a Study.

One JSON file at `<study>/00_study/study-card.json` holds the words the overlay
(and any other packaging) draws from: number, title, short and long summaries,
bullets, and headline parameters. These fields follow docs/TECHNICAL_VOICE.md:
mechanism-first titles, defined claims, explicit provenance, and no unsupported
scientific or anthropomorphic framing. The card is seeded from the Seed record at
promotion, maintained conversationally through Hermes, and merged into the
overlay `study.json` sidecar by `houdini/export_overlay_study.py` (CLI flags
override card fields).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .display_text import validate_display_text
from .study_vault import parse_variation_stem, variation_file_stem

STUDY_CARD_NAME = "study-card.json"

_REQUIRED = (
    "schema_version",
    "study_id",
    "variation_id",
    "variation_number",
    "variation_title",
    "variation_slug",
    "variation_file_stem",
    "number",
    "title",
)
_OPTIONAL_STRINGS = ("overlay_id", "subtitle", "summary", "source", "date", "credits")


def validate_study_card(card: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in _REQUIRED:
        if key not in card:
            errors.append(f"study card is missing {key!r}")
    if errors:
        return errors
    if card["schema_version"] != 1:
        errors.append("study card schema_version must be 1")
    if not isinstance(card["study_id"], str) or not card["study_id"].startswith("study-"):
        errors.append("study_id must be a canonical 'study-…' record id")
    if not isinstance(card["number"], int) or card["number"] < 1:
        errors.append("number must be a positive integer")
    if not isinstance(card["title"], str) or not card["title"].strip():
        errors.append("title must be a non-empty string")
    variation_number = card["variation_number"]
    variation_title = card["variation_title"]
    if not isinstance(variation_number, int) or not 1 <= variation_number <= 999:
        errors.append("variation_number must be between 1 and 999")
    if not isinstance(variation_title, str) or not variation_title.strip():
        errors.append("variation_title must be a non-empty string")
    elif isinstance(variation_number, int) and 1 <= variation_number <= 999:
        behavior_number = card.get("variation_behavior_number", 1)
        if (
            isinstance(behavior_number, bool)
            or not isinstance(behavior_number, int)
            or not 1 <= behavior_number <= 999
        ):
            errors.append("variation_behavior_number must be between 1 and 999")
        else:
            expected_stem = variation_file_stem(behavior_number, variation_number, variation_title)
            expected_slug = parse_variation_stem(expected_stem)["slug"]
            expected_id = f"variation-bhvr{behavior_number:03d}-{variation_number:03d}-{expected_slug}"
            if card["variation_file_stem"] != expected_stem:
                errors.append("variation_file_stem does not match variation number and title")
            if card["variation_slug"] != expected_slug:
                errors.append("variation_slug does not match variation title")
            if card["variation_id"] != expected_id:
                errors.append("variation_id does not match variation number and title")
    for key in _OPTIONAL_STRINGS:
        if key in card and not isinstance(card[key], str):
            errors.append(f"{key} must be a string")
    for key in ("title", *_OPTIONAL_STRINGS):
        value = card.get(key)
        if isinstance(value, str):
            errors.extend(validate_display_text(value, key))
    bullets = card.get("bullets", [])
    if not isinstance(bullets, list) or any(not isinstance(item, str) or not item.strip() for item in bullets):
        errors.append("bullets must be a list of non-empty strings")
    elif isinstance(bullets, list):
        for index, item in enumerate(bullets):
            errors.extend(validate_display_text(item, f"bullets[{index}]"))
    params = card.get("params", [])
    if not isinstance(params, list) or any(
        not isinstance(pair, (list, tuple)) or len(pair) != 2 or not all(isinstance(part, str) for part in pair)
        for pair in params
    ):
        errors.append("params must be a list of [label, value] string pairs")
    elif isinstance(params, list):
        for row_index, pair in enumerate(params):
            for column_index, item in enumerate(pair):
                errors.extend(validate_display_text(item, f"params[{row_index}][{column_index}]"))
    return errors


def load_study_card(path: Path) -> dict[str, Any]:
    card = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_study_card(card)
    if errors:
        raise ValueError(f"{path}: " + "; ".join(errors))
    return card


def overlay_fields(card: Mapping[str, Any]) -> dict[str, Any]:
    """Map a study card onto the flat study.json sidecar fields."""
    return {
        "id": card.get("overlay_id") or f"STUDY-{int(card['number']):03d}",
        "number": card["number"],
        "title": card["title"],
        "subtitle": card.get("subtitle", ""),
        "summary": card.get("summary", ""),
        "bullets": list(card.get("bullets", [])),
        "params": [list(pair) for pair in card.get("params", [])],
        "source": card.get("source", ""),
        "date": card.get("date", ""),
        "credits": card.get("credits", ""),
        "variation": {
            "id": card["variation_id"],
            "number": card["variation_number"],
            "title": card["variation_title"],
            "slug": card["variation_slug"],
            "file_stem": card["variation_file_stem"],
        },
    }


def card_from_records(
    study_record: Mapping[str, Any],
    seed_record: Mapping[str, Any] | None = None,
    variation_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Scaffold an initial card from canonical Study, Seed, and variation records."""
    seed = seed_record or {}
    variation = variation_record or {
        "id": "variation-bhvr001-001-primary-treatment",
        "number": 1,
        "behavior_number": 1,
        "title": "Primary Treatment",
        "slug": "primary-treatment",
        "file_stem": "bhvr_001_var_001_primary-treatment",
    }
    study_id = str(study_record.get("id", ""))
    digits = "".join(char for char in study_id if char.isdigit())
    card = {
        "schema_version": 1,
        "study_id": study_id,
        "variation_id": variation["id"],
        "variation_number": variation["number"],
        "variation_behavior_number": variation.get("behavior_number", 1),
        "variation_title": variation["title"],
        "variation_slug": variation["slug"],
        "variation_file_stem": variation["file_stem"],
        "number": int(digits[:3]) if digits else 0,
        "title": str(study_record.get("title") or seed.get("title") or study_id),
        "subtitle": str(seed.get("short_summary", "")),
        "summary": str(seed.get("long_summary", "")),
        "bullets": [],
        "params": [],
        "source": "",
        "date": "",
        "credits": "",
    }
    errors = validate_study_card(card)
    if errors:
        raise ValueError("; ".join(errors))
    return card
