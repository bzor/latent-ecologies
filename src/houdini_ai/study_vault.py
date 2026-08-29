"""Human-facing canonical directory contract for Computational Studio Studies."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Mapping


PHASE_DIRECTORIES = (
    "00_study",
    "01_behavior",
    "02_look",
    "03_specimen",
    "04_delivery",
    "90_shared",
    "99_archive",
)
PHASE_SECTIONS = (
    "00_brief",
    "01_work",
    "02_review",
    "03_selected",
)
SECTIONED_PHASE_DIRECTORIES = ("01_behavior",)
_STUDY_ID = re.compile(r"study-(?P<number>[0-9]{3})-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)")


def _variation_slug(title: str) -> str:
    if not isinstance(title, str) or not title.strip():
        raise ValueError("variation title is required")
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")
    if not slug:
        raise ValueError("variation title must contain letters or numbers")
    return slug


def variation_file_stem(number: int, title: str) -> str:
    """Return the canonical filename stem shared by Look, Specimen, and Delivery."""

    if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= 999:
        raise ValueError("variation number must be an integer from 1 to 999")
    return f"var_{number:03d}_{_variation_slug(title)}"


def add_study_variation(
    vault: Path,
    *,
    number: int,
    title: str,
    state: str = "active",
    behavior_selection_id: str | None = None,
    derived_from: str | None = None,
    make_current: bool = True,
) -> dict[str, Any]:
    """Add one stable variation identity to an initialized Study vault."""

    if state not in {"active", "held", "selected", "completed", "archived"}:
        raise ValueError("variation state is invalid")
    stem = variation_file_stem(number, title)
    slug = stem.split("_", 2)[2]
    variation_id = f"variation-{number:03d}-{slug}"
    path = Path(vault) / "00_study" / "variations.json"
    registry = json.loads(path.read_text(encoding="utf-8"))
    variations = registry.get("variations")
    if not isinstance(variations, list):
        raise ValueError("variation registry is malformed")
    if any(item.get("number") == number for item in variations if isinstance(item, dict)):
        raise ValueError(f"variation number {number:03d} already exists")
    if derived_from is not None and not any(
        item.get("id") == derived_from for item in variations if isinstance(item, dict)
    ):
        raise ValueError("derived_from must reference an existing variation")
    variation: dict[str, Any] = {
        "behavior_selection_id": behavior_selection_id,
        "derived_from": derived_from,
        "file_stem": stem,
        "id": variation_id,
        "number": number,
        "slug": slug,
        "state": state,
        "title": title.strip(),
    }
    variations.append(variation)
    variations.sort(key=lambda item: item["number"])
    if make_current:
        registry["current_variation_id"] = variation_id
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(path)
    if make_current:
        card_path = path.parent / "study-card.json"
        if card_path.is_file():
            card = json.loads(card_path.read_text(encoding="utf-8"))
            card.update(
                {
                    "variation_file_stem": variation["file_stem"],
                    "variation_id": variation["id"],
                    "variation_number": variation["number"],
                    "variation_slug": variation["slug"],
                    "variation_title": variation["title"],
                }
            )
            card_temporary = card_path.with_suffix(".json.tmp")
            card_temporary.write_text(
                json.dumps(card, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            card_temporary.replace(card_path)
    return variation


def study_directory_name(study_id: str) -> str:
    """Translate a canonical Study ID into its sortable vault directory name."""

    match = _STUDY_ID.fullmatch(study_id)
    if match is None:
        raise ValueError("study_id must match study-NNN-lowercase-slug")
    return f"study_{match.group('number')}_{match.group('slug')}"


def _write_new(path: Path, content: str) -> None:
    if path.exists():
        return
    path.write_text(content, encoding="utf-8", newline="\n")


def initialize_study_vault(root: Path, study: Mapping[str, Any]) -> Path:
    """Create an idempotent canonical Study skeleton without replacing authored files."""

    study_id = study.get("id")
    title = study.get("title")
    if not isinstance(study_id, str):
        raise ValueError("study id is required")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("study title is required")

    vault = Path(root).resolve() / "studies" / study_directory_name(study_id)
    for phase in PHASE_DIRECTORIES:
        (vault / phase).mkdir(parents=True, exist_ok=True)
    for phase in SECTIONED_PHASE_DIRECTORIES:
        for section in PHASE_SECTIONS:
            (vault / phase / section).mkdir(parents=True, exist_ok=True)

    study_directory = vault / "00_study"
    _write_new(study_directory / "study.json", json.dumps(dict(study), indent=2, sort_keys=True) + "\n")
    _write_new(
        study_directory / "README.md",
        f"# {title}\n\nCanonical private Study vault for `{study_id}`.\n",
    )
    _write_new(
        study_directory / "status.json",
        json.dumps(
            {
                "current_phase": study.get("current_phase", "seed"),
                "state": study.get("state", "active"),
                "study_id": study_id,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    _write_new(
        study_directory / "lineage.json",
        json.dumps({"edges": [], "study_id": study_id}, indent=2, sort_keys=True) + "\n",
    )
    _write_new(
        study_directory / "artifact-index.json",
        json.dumps({"artifacts": [], "study_id": study_id}, indent=2, sort_keys=True) + "\n",
    )
    _write_new(
        study_directory / "variations.json",
        json.dumps(
            {
                "current_variation_id": "variation-001-primary-treatment",
                "schema_version": 1,
                "study_id": study_id,
                "variations": [
                    {
                        "behavior_selection_id": None,
                        "derived_from": None,
                        "file_stem": "var_001_primary-treatment",
                        "id": "variation-001-primary-treatment",
                        "number": 1,
                        "slug": "primary-treatment",
                        "state": "active",
                        "title": "Primary Treatment",
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    _write_new(study_directory / "decisions.md", "# Decisions\n\n")
    return vault
