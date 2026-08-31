from __future__ import annotations

import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .artifact_catalog import build_artifact_catalog
from .directions import create_direction, decide_direction, derive_probe_proposal, merge_directions, mutate_direction
from .process_notes import capture_note
from .promotions import promote_artifact as promote_verified_artifact
from .proposals import create_proposal as create_bounded_proposal
from .review_inbox import build_review_inbox
from .studio_schema import validate_record
from .studio_store import StudioStore
from .studio_types import can_transition, effective_visibility, validate_editorial_tags


COLLECTION_KINDS = {
    "affinity-presets": "affinity-preset",
    "ideas": "idea",
    "directions": "direction",
    "proposals": "proposal",
    "experiments": "experiment",
    "components": "component",
    "specimens": "specimen",
    "editorial": "editorial",
}
INITIAL_STATES = {
    "ideas": "inbox",
    "proposals": "proposed",
    "experiments": "draft",
    "specimens": "draft",
    "editorial": "draft",
}
REGISTERED_PROPOSAL_RUNNERS = frozenset((
    "behavior.nonlocal_affinity_3d",
    "behavior.probe",
    "behavior.scar_probe",
    "behavior.scar_tissue_probe",
    "look.scar_tissue_probe",
))
FORBIDDEN_PARAMETER_KEYS = frozenset(("command", "cmd", "shell", "executable", "script"))


class StudioAPI:
    """Local application service for validated Studio records."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.store = StudioStore(self.root)

    def capture_idea(self, value: dict[str, Any]) -> dict[str, Any]:
        title = _text(value, "title", 200)
        raw_text = _text(value, "raw_text", 10_000)
        track = str(value.get("track", ""))
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48] or "untitled"
        record = {
            "schema_version": 1,
            "id": f"idea-{slug}-{uuid.uuid4().hex[:8]}",
            "title": title,
            "raw_text": raw_text,
            "track": track,
            "state": "inbox",
            "visibility": "private",
        }
        for optional in ("source_urls", "questions", "constraints", "extensions"):
            if optional in value:
                record[optional] = value[optional]
        _validate("idea", record)
        return self.store.create("ideas", record["id"], record)

    def save_affinity_preset(self, value: dict[str, Any]) -> dict[str, Any]:
        """Save an inert browser-discovered parameter candidate without authorizing execution."""

        if not isinstance(value, dict):
            raise ValueError("affinity preset must be an object")
        production_hint = value.get("production_hint")
        if not isinstance(production_hint, dict) or production_hint.get("execution_authorized") is not False:
            raise ValueError("affinity preset execution_authorized must be false")
        record = {
            **deepcopy(value),
            "id": f"affinity-preset-{uuid.uuid4().hex[:12]}",
            "state": "candidate",
            "visibility": "private",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _validate("affinity-preset", record)
        return self.store.create("affinity-presets", record["id"], record)

    def create_proposal(self, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("proposal must be an object")
        idea_id = value.get("idea_id")
        if not isinstance(idea_id, str):
            raise ValueError("proposal requires idea_id")
        idea = self.store.read("ideas", idea_id)
        canonical = {
            "schema_version": 1,
            "track": idea.get("track"),
            "state": "proposed",
            "visibility": "private",
        }
        for field, expected in canonical.items():
            if field in value and value[field] != expected:
                raise ValueError(f"proposal {field} must be {expected}")
        if "id" in value and (not isinstance(value["id"], str) or not value["id"].startswith("proposal-")):
            raise ValueError("proposal id must use the proposal- prefix")
        envelope = {"idea_id", "id", *canonical}
        details = {key: item for key, item in value.items() if key not in envelope}
        return create_bounded_proposal(
            self.store,
            idea_id,
            details,
            registered_runners=REGISTERED_PROPOSAL_RUNNERS,
        )

    def create_direction(self, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("direction must be an object")
        idea_id = value.get("idea_id")
        if not isinstance(idea_id, str):
            raise ValueError("direction requires idea_id")
        details = {key: item for key, item in value.items() if key != "idea_id"}
        return create_direction(self.store, idea_id, details)

    def decide_direction(self, direction_id: str, decision: str) -> dict[str, Any]:
        return decide_direction(self.store, direction_id, decision)

    def mutate_direction(self, direction_id: str, value: dict[str, Any]) -> dict[str, Any]:
        return mutate_direction(self.store, direction_id, value)

    def merge_directions(self, value: dict[str, Any]) -> dict[str, Any]:
        unknown = set(value) - {"source_ids", "direction"}
        if unknown:
            raise ValueError(f"unsupported merge fields: {', '.join(sorted(unknown))}")
        source_ids = value.get("source_ids")
        direction = value.get("direction")
        if not isinstance(source_ids, list) or not all(isinstance(item, str) for item in source_ids):
            raise ValueError("merge requires source_ids")
        if not isinstance(direction, dict):
            raise ValueError("merge requires a direction object")
        return merge_directions(self.store, source_ids, direction)

    def derive_direction_proposal(self, direction_id: str, value: dict[str, Any]) -> dict[str, Any]:
        return derive_probe_proposal(
            self.store, direction_id, value, registered_runners=REGISTERED_PROPOSAL_RUNNERS,
        )

    def create_record(self, collection: str, value: dict[str, Any]) -> dict[str, Any]:
        kind = _kind(collection)
        if collection == "components":
            raise ValueError("component creation requires a verified artifact; use promote_artifact")
        if collection == "directions":
            raise ValueError("directions require a dedicated creation operation")
        if not isinstance(value, dict):
            raise ValueError("record must be an object")
        record = dict(value)
        expected_state = INITIAL_STATES.get(collection)
        if expected_state is not None and record.get("state") != expected_state:
            raise ValueError(f"initial state for {collection} must be {expected_state}")
        if record.get("visibility") != "private":
            raise ValueError("new Studio records must explicitly be private")
        if collection == "experiments":
            proposal_id = record.get("proposal_id")
            if not isinstance(proposal_id, str):
                raise ValueError("experiment requires proposal_id")
            try:
                proposal = self.store.read("proposals", proposal_id)
            except FileNotFoundError as error:
                raise ValueError("experiment requires an existing approved proposal") from error
            if proposal.get("state") != "approved" or proposal.get("track") != record.get("track"):
                raise ValueError("experiment requires an approved track-compatible proposal")
            if record.get("runner") not in REGISTERED_PROPOSAL_RUNNERS:
                raise ValueError("experiment uses an unregistered runner")
            parameters = record.get("parameters")
            if not isinstance(parameters, dict) or any(str(key).lower() in FORBIDDEN_PARAMETER_KEYS for key in parameters):
                raise ValueError("experiment parameters contain forbidden execution fields")
        _validate(kind, record)
        return self.store.create(collection, str(record.get("id", "")), record)

    def list_records(self, collection: str) -> dict[str, Any]:
        _kind(collection)
        items, errors = self.store.list(collection)
        return {"items": items, "errors": errors}

    def promote_component(self, value: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("component promotion requires a verified artifact; use promote_artifact")

    def promote_artifact(
        self,
        artifact_id: str,
        component_kind: str,
        rationale: str,
        *,
        supersedes_id: str | None = None,
    ) -> dict[str, object]:
        """Promote only a verified artifact with intact local lineage."""
        return promote_verified_artifact(
            self.store,
            self.root,
            artifact_id,
            component_kind,
            rationale,
            supersedes_id=supersedes_id,
        )

    def update_editorial_tags(self, record_id: str, tags: list[str]) -> dict[str, Any]:
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError("tags must be a list of strings")
        errors = validate_editorial_tags(tags)
        if errors:
            raise ValueError("; ".join(errors))
        record = self.store.read("editorial", record_id)
        updated = {
            **record,
            "tags": list(tags),
            "destinations": [tag.split(":", 1)[1] for tag in tags if tag.startswith("publish:")],
            "roles": [tag.split(":", 1)[1] for tag in tags if tag.startswith("role:")],
            "visibility": effective_visibility(str(record.get("visibility", "private")), tags),
        }
        _validate("editorial", updated)
        return self.store.update("editorial", record_id, updated)

    def list_verified_artifacts(self) -> dict[str, Any]:
        """List promotion candidates without treating paths as authority."""
        items, errors = self.store.list("artifacts")
        return {"items": [item for item in items if item.get("verified") is True], "errors": errors}

    def artifact_catalog(self) -> dict[str, Any]:
        """Project all contained reviewable outputs into one read-only catalog."""
        return {"items": build_artifact_catalog(self.root), "errors": []}

    def session_bootstrap(self, mutation_token: str | None) -> dict[str, Any]:
        # The endpoint keeps its historical name: it bootstraps the browser's
        # mutation token; creative-session records are retired.
        return {"mutation_token": mutation_token}

    def review_inbox(self) -> dict[str, Any]:
        return build_review_inbox(self.root)

    def capture_process_note(self, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("process note must be an object")
        reference = value.get("reference_id")
        if reference is not None and not isinstance(reference, str):
            raise ValueError("reference_id must be a record id")
        return capture_note(
            self.store,
            str(value.get("text", "")),
            str(value.get("category", "")),
            str(value.get("stage", "")),
            str(value.get("track", "")),
            reference_id=reference,
        )

    def approve_proposal(self, proposal_id: str) -> dict[str, Any]:
        return self._decide_proposal(proposal_id, "approved")

    def hold_proposal(self, proposal_id: str) -> dict[str, Any]:
        return self._decide_proposal(proposal_id, "held")

    def _decide_proposal(self, proposal_id: str, state: str) -> dict[str, Any]:
        record = self.store.read("proposals", proposal_id)
        if record.get("state") != "proposed":
            raise ValueError(f"only proposed proposals can be {state}")
        updated = {**record, "state": state}
        _validate("proposal", updated)
        return self.store.update("proposals", proposal_id, updated)

    def summary(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        states: dict[str, dict[str, int]] = {}
        errors: list[dict[str, str]] = []
        for collection in COLLECTION_KINDS:
            result = self.list_records(collection)
            counts[collection] = len(result["items"])
            states[collection] = {}
            for item in result["items"]:
                state = str(item.get("state", "unknown"))
                states[collection][state] = states[collection].get(state, 0) + 1
            errors.extend(result["errors"])
        return {"visibility": "private", "counts": counts, "states": states, "errors": errors}

    def update_status(self, collection: str, record_id: str, state: str) -> dict[str, Any]:
        kind = _kind(collection)
        if collection == "experiments":
            raise ValueError("experiment lifecycle requires dedicated execution operations")
        if collection == "directions":
            raise ValueError("directions lifecycle requires dedicated operations")
        record = self.store.read(collection, record_id)
        current = str(record.get("state", ""))
        if not can_transition(kind, current, state):
            raise ValueError(f"cannot transition {kind} from {current} to {state}")
        updated = {**record, "state": state}
        _validate(kind, updated)
        return self.store.update(collection, record_id, updated)


def _kind(collection: str) -> str:
    try:
        return COLLECTION_KINDS[collection]
    except KeyError as error:
        raise ValueError("unknown Studio collection") from error


def _text(value: dict[str, Any], field: str, maximum: int) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result.strip() or len(result) > maximum:
        raise ValueError(f"{field} must contain 1 to {maximum} characters")
    return result.strip()


def _validate(kind: str, record: dict[str, Any]) -> None:
    errors = validate_record(kind, record)
    if errors:
        raise ValueError("; ".join(errors))
