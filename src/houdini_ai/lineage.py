"""Validation helpers for Studio record lineage."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

from .studio_store import StudioStore


class LineageError(ValueError):
    pass


_COLLECTION_BY_PREFIX = {
    "idea": "ideas",
    "proposal": "proposals",
    "experiment": "experiments",
    "component": "components",
    "editorial": "editorial",
    "artifact": "artifacts",
    "job": "jobs",
}
_ALLOWED_EDGES = {
    ("idea", "proposal"),
    ("proposal", "experiment"),
    ("experiment", "artifact"),
    ("artifact", "component"),
    ("component", "component"),
    ("artifact", "editorial"),
}


def record_kind(record_id: str) -> str:
    kind = record_id.split("-", 1)[0]
    if kind not in _COLLECTION_BY_PREFIX:
        raise LineageError(f"unknown record type: {record_id}")
    return kind


def validate_edge(store: StudioStore, source_id: str, target_id: str) -> None:
    source_kind = record_kind(source_id)
    target_kind = record_kind(target_id)
    if (source_kind, target_kind) not in _ALLOWED_EDGES:
        raise LineageError(f"lineage edge not allowed: {source_kind} -> {target_kind}")
    for kind, record_id in ((source_kind, source_id), (target_kind, target_id)):
        try:
            store.read(_COLLECTION_BY_PREFIX[kind], record_id)
        except FileNotFoundError as error:
            raise LineageError(f"missing referenced record: {record_id}") from error


def promotion_chain(store: StudioStore, artifact: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return a complete promotion chain after checking identity, state, and track."""

    experiment_id = artifact.get("experiment_id")
    if not isinstance(experiment_id, str):
        raise LineageError("artifact source experiment is required")
    try:
        experiment = store.read("experiments", experiment_id)
    except FileNotFoundError as error:
        raise LineageError(f"missing referenced record: {experiment_id}") from error
    proposal_id = experiment.get("proposal_id")
    if not isinstance(proposal_id, str):
        raise LineageError("experiment source proposal is required")
    try:
        proposal = store.read("proposals", proposal_id)
    except FileNotFoundError as error:
        raise LineageError(f"missing referenced record: {proposal_id}") from error
    idea_id = proposal.get("idea_id")
    if not isinstance(idea_id, str):
        raise LineageError("proposal source idea is required")
    try:
        idea = store.read("ideas", idea_id)
    except FileNotFoundError as error:
        raise LineageError(f"missing referenced record: {idea_id}") from error

    expected_states = (("idea", idea, "proposed"), ("proposal", proposal, "approved"), ("experiment", experiment, "completed"))
    for kind, record, expected in expected_states:
        if record.get("state") != expected:
            raise LineageError(f"{kind} lifecycle is incompatible with promotion: expected {expected}")
    tracks = {artifact.get("track"), experiment.get("track"), proposal.get("track"), idea.get("track")}
    if len(tracks) != 1 or not isinstance(artifact.get("track"), str):
        raise LineageError("promotion lineage track mismatch")
    return idea, proposal, experiment


def stable_content_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def assert_acyclic(edges: Iterable[tuple[str, str]]) -> None:
    graph: dict[str, set[str]] = {}
    for source, target in edges:
        graph.setdefault(source, set()).add(target)
        graph.setdefault(target, set())
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise LineageError("lineage cycle detected")
        if node in visited:
            return
        visiting.add(node)
        for child in graph[node]:
            visit(child)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)
