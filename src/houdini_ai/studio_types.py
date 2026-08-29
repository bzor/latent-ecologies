"""Shared, stable vocabulary for Studio records and workflows."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

TRACKS: Final = ("behavior", "look", "chromatic", "cinematography", "specimen", "field-station")
DECISIONS: Final = ("keep", "iterate", "mutate", "hold", "archive", "reject", "promote")
VISIBILITIES: Final = ("private", "public-candidate")
COST_TIERS: Final = ("tiny", "probe", "study", "specimen", "external")

EDITORIAL_DESTINATIONS: Final = ("web", "x", "instagram", "youtube")
EDITORIAL_ROLES: Final = (
    "field-observation",
    "research-note",
    "theory",
    "failure",
    "process",
    "specimen",
    "download",
)
EDITORIAL_READINESS: Final = (
    "needs-edit",
    "needs-caption",
    "needs-a11y",
    "ready-for-approval",
    "approved",
    "published",
)
EDITORIAL_TAGS: Final = frozenset(
    [*(f"publish:{value}" for value in EDITORIAL_DESTINATIONS)]
    + [*(f"role:{value}" for value in EDITORIAL_ROLES)]
    + [*(f"visibility:{value}" for value in VISIBILITIES)]
    + [*(f"readiness:{value}" for value in EDITORIAL_READINESS)]
)

LIFECYCLE_TRANSITIONS: Final = {
    "idea": {
        "inbox": frozenset(("scoped", "archived", "rejected")),
        "scoped": frozenset(("proposed", "archived", "rejected")),
        "proposed": frozenset(("archived", "rejected")),
        "archived": frozenset(),
        "rejected": frozenset(),
    },
    "proposal": {
        "proposed": frozenset(("approved", "held", "rejected", "archived")),
        "approved": frozenset(("implemented", "archived")),
        "held": frozenset(("proposed", "archived", "rejected")),
        "implemented": frozenset(("archived",)),
        "rejected": frozenset(),
        "archived": frozenset(),
    },
    "direction": {
        "candidate": frozenset(("selected", "held", "rejected", "archived")),
        "selected": frozenset(("held", "rejected", "archived")),
        "held": frozenset(("selected", "rejected", "archived")),
        "rejected": frozenset(("selected", "held", "archived")),
        "archived": frozenset(),
    },
    "experiment": {
        "draft": frozenset(("approved", "archived")),
        "approved": frozenset(("running", "archived")),
        "running": frozenset(("completed", "failed")),
        "completed": frozenset(("archived",)),
        "failed": frozenset(("approved", "archived")),
        "archived": frozenset(),
    },
    "component": {
        "promoted": frozenset(("superseded", "archived")),
        "superseded": frozenset(("archived",)),
        "archived": frozenset(),
    },
    "specimen": {
        "draft": frozenset(("approved", "archived", "rejected")),
        "approved": frozenset(("rendering", "archived")),
        "rendering": frozenset(("completed", "failed")),
        "completed": frozenset(("archived",)),
        "failed": frozenset(("approved", "archived")),
        "rejected": frozenset(),
        "archived": frozenset(),
    },
    "editorial": {
        "draft": frozenset(("ready-for-approval", "archived")),
        "ready-for-approval": frozenset(("approved", "draft", "archived")),
        "approved": frozenset(("published", "draft", "archived")),
        "published": frozenset(("archived",)),
        "archived": frozenset(),
    },
}


def validate_track(value: object) -> bool:
    """Return whether *value* is a canonical Studio track name."""

    return isinstance(value, str) and value in TRACKS


def can_transition(kind: str, current: str, target: str) -> bool:
    """Return whether the lifecycle table explicitly permits a transition."""

    return target in LIFECYCLE_TRANSITIONS.get(kind, {}).get(current, frozenset())


def effective_visibility(visibility: str, tags: Iterable[str] = ()) -> str:
    """Resolve visibility, with any private signal taking precedence."""

    tag_set = set(tags)
    if visibility == "private" or "visibility:private" in tag_set:
        return "private"
    return visibility


def validate_editorial_tags(tags: Iterable[str]) -> list[str]:
    """Return deterministic errors for unknown or duplicate editorial tags."""

    errors: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        if tag in seen:
            errors.append(f"duplicate tag: {tag}")
        elif tag not in EDITORIAL_TAGS:
            errors.append(f"unknown editorial tag: {tag}")
        seen.add(tag)
    return errors


def cost_tier_rank(tier: str) -> int:
    """Return a tier's strict ordering rank, rejecting unknown tiers."""

    try:
        return COST_TIERS.index(tier)
    except ValueError as error:
        raise ValueError(f"unknown cost tier: {tier}") from error
