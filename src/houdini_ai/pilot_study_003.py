"""Idempotent canonical bootstrap for Pilot Study 003."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .directions import create_direction, decide_direction, derive_probe_proposal
from .studio_api import REGISTERED_PROPOSAL_RUNNERS, StudioAPI
from .studio_sessions import activate_session, create_session
from .studio_store import StudioStore

SOURCE_URL = "https://community.wolfram.com/groups/-/m/t/122095"
_ROLE_KEY = "studio/pilot-study-003-role"
_DIRECTION_ORDER = ("faithful-baseline", "graph-choreography", "encounter-memory")


def _records(store: StudioStore, collection: str) -> list[dict[str, Any]]:
    records, errors = store.list(collection)
    if errors:
        raise ValueError("; ".join(error["error"] for error in errors))
    return records


def _by_role(store: StudioStore, collection: str, role: str) -> dict[str, Any] | None:
    matches = [
        record for record in _records(store, collection)
        if record.get("extensions", {}).get(_ROLE_KEY) == role
    ]
    if len(matches) > 1:
        raise ValueError(f"duplicate Pilot Study 003 {collection} role: {role}")
    return matches[0] if matches else None


def _direction_value(role: str, prior: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if role == "faithful-baseline":
        return {
            "title": "Faithful Nonlocal Signed Graph",
            "premise": "A directed nonlocal friend/enemy graph can continuously organize spatial form without nearest-neighbor flocking.",
            "mechanism": (
                "Initialize 1000 points in 2D with one independently drawn friend and enemy index. Synchronously update "
                "x_next = 0.995*x + 0.02*phi(friend-x) - 0.01*phi(enemy-x), where "
                "phi(d)=d/(0.01+norm(d)); occasionally rewire one point with independent random draws."
            ),
            "expected_emergent_behavior": (
                "Compact rotating cliques, follower tails, partial loops, and continuing structural reorganization should emerge "
                "without local-neighbor queries."
            ),
            "cheapest_informative_probe": (
                "Compare a seeded tiny Python reference with a three-step live VEX cook, then inspect a short fixed-camera point motion check."
            ),
            "risks": [
                "Incorrect update ordering could produce an asynchronous system unlike the source.",
                "A visually plausible result could conceal different rewiring semantics.",
            ],
            "conceptual_distinction": "This is the immutable source-faithful calibration branch, not a parameter or presentation variation.",
            "sibling_relations": [],
            "extensions": {
                _ROLE_KEY: role,
                "studio/source-url": SOURCE_URL,
                "studio/reference-policy": "fidelity-gate-then-independent-departure",
            },
        }
    faithful = prior["faithful-baseline"]
    if role == "graph-choreography":
        return {
            "title": "Graph Choreography",
            "premise": "Designed relationship motifs can choreograph transitions while preserving the original spatial force law.",
            "mechanism": (
                "Keep the baseline pull/push response but replace random relationship topology with explicit rings, chains, cliques, "
                "and scheduled graph transitions."
            ),
            "expected_emergent_behavior": "Legible formations should assemble, deform, exchange members, and transition between graph-authored spatial phrases.",
            "cheapest_informative_probe": "Run three fixed graph motifs with identical initial positions and compare topology and trajectory diagnostics.",
            "risks": ["Over-designed topology may become mechanical rather than emergent."],
            "conceptual_distinction": "This changes relationship topology while holding the source force law stable.",
            "sibling_relations": [{"direction_id": faithful["id"], "relationship": "replaces random topology with designed motifs"}],
            "extensions": {_ROLE_KEY: role},
        }
    choreography = prior["graph-choreography"]
    return {
        "title": "Encounter Memory",
        "premise": "Relationship history can become persistent agent state that changes future affinity and aversion.",
        "mechanism": (
            "Keep one friend and enemy per point, but replace random rewiring with bounded memory of encounters, accumulated affinity, "
            "fatigue, and possible role reversal."
        ),
        "expected_emergent_behavior": "Temporary alliances, betrayal waves, territorial memory, and path-dependent reorganizations should develop.",
        "cheapest_informative_probe": "Compare random rewiring with one encounter-memory threshold using the same seed and force law.",
        "risks": ["Memory may freeze the graph or produce undifferentiated churn without carefully bounded state."],
        "conceptual_distinction": "This changes why topology evolves, not merely how frequently random rewiring occurs.",
        "sibling_relations": [
            {"direction_id": faithful["id"], "relationship": "replaces stochastic rewiring with historical causation"},
            {"direction_id": choreography["id"], "relationship": "emergent topology rather than authored topology"},
        ],
        "extensions": {_ROLE_KEY: role},
    }


def bootstrap_pilot_study_003(root: Path) -> dict[str, Any]:
    """Create the accepted seed, directions, session, and inert probe proposal once."""

    root = Path(root).resolve()
    api = StudioAPI(root)
    store = api.store

    idea = _by_role(store, "ideas", "seed")
    if idea is None:
        idea = api.capture_idea({
            "title": "Nonlocal Affinity Dance",
            "raw_text": (
                "Faithfully reproduce Simon Woods' nonlocal friend/enemy particle dance once, preserve it as a baseline, "
                "then use it as a launchpad for independent animation systems rather than a rigid aesthetic reference."
            ),
            "track": "behavior",
            "source_urls": [SOURCE_URL],
            "questions": ["How does a mutable network of attraction and aversion write itself into spatial form?"],
            "constraints": [
                "Prove the original 2D synchronous mechanism before adding new causal rules.",
                "Keep representation, look, palette, and cinematography out of behavior approval.",
                "Evaluate descendants on their own temporal identity after fidelity is established.",
            ],
            "extensions": {
                _ROLE_KEY: "seed",
                "studio/source-author": "Simon Woods",
                "studio/source-title": "Dancing with friends and enemies: boids' swarm intelligence",
                "studio/source-role": "faithful-launchpad",
            },
        })

    directions: dict[str, dict[str, Any]] = {}
    for role in _DIRECTION_ORDER:
        record = _by_role(store, "directions", role)
        if record is None:
            record = create_direction(store, str(idea["id"]), _direction_value(role, directions))
            record = decide_direction(store, str(record["id"]), "select" if role == "faithful-baseline" else "hold")
        directions[role] = record

    proposal = _by_role(store, "proposals", "faithful-probe")
    if proposal is None:
        proposal = derive_probe_proposal(
            store,
            str(directions["faithful-baseline"]["id"]),
            {
                "outputs": ["reference-metrics.json", "vex-parity.json", "motion-check.mp4", "receipt.json"],
                "stop_conditions": [
                    "Stop on non-finite positions, invalid relationship indices, or VEX compile/cook errors.",
                    "Stop if the same-seed Python and VEX tracer states differ beyond the declared tolerance.",
                    "Stop before presentation rendering or any unrecorded causal additions.",
                ],
                "runner": "behavior.probe",
                "cost_tier": "probe",
                "extensions": {
                    _ROLE_KEY: "faithful-probe",
                    "studio/execution-authority": "separate-approval-required",
                },
            },
            registered_runners=REGISTERED_PROPOSAL_RUNNERS,
        )

    sessions = [record for record in _records(store, "sessions") if record.get("project_slug") == "pilot-study-003"]
    if len(sessions) > 1:
        raise ValueError("duplicate Pilot Study 003 sessions")
    if sessions:
        session = sessions[0]
        activate_session(store, str(session["id"]))
    else:
        session = create_session(store, {
            "title": "Pilot Study 003 | Nonlocal affinity graph dynamics",
            "project_slug": "pilot-study-003",
            "current_phase": "directions",
            "intent": (
                "Prove the source-faithful nonlocal affinity mechanism, freeze it as an ancestor, then depart into independently "
                "judged experimental animation systems."
            ),
            "selected_branch_id": directions["faithful-baseline"]["id"],
            "approved_selection_ids": [directions["faithful-baseline"]["id"]],
            "idea_id": idea["id"],
            "unresolved_questions": ["Does the faithful implementation preserve continuing reorganization rather than settling into a static graph drawing?"],
            "blockers": ["The bounded faithful probe proposal has not yet been approved for runner execution."],
            "recommended_next_action": "Build and verify the deterministic Python reference before approving live Houdini execution.",
            "extensions": {_ROLE_KEY: "session"},
        }, activate=True)

    return {
        "idea": store.read("ideas", str(idea["id"])),
        "directions": [directions[role] for role in _DIRECTION_ORDER],
        "proposal": proposal,
        "session": session,
    }
