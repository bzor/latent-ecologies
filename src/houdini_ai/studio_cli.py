"""Argument parsing and handlers for the non-executing Studio CLI."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from urllib.parse import urlparse

from .conversation_bindings import bind_discord_thread, resolve_discord_thread
from .editorial import approve_editorial, editorial_summary, tag_artifact, untag_artifact
from .directions import DIRECTION_DECISIONS, create_direction, decide_direction, derive_probe_proposal, merge_directions, mutate_direction
from .process_notes import NOTE_CATEGORIES, NOTE_STAGES, capture_note, capture_retro, filtered_notes, write_digest
from .promotions import promote_artifact
from .proposals import approve_proposal, create_proposal
from .public_seed_bank import build_public_seed_bank
from .public_site import build_public_site
from .review_inbox import build_review_inbox
from .seed_bank import build_seed_digest, create_seed, promote_seed_to_study_command, transition_seed, update_seed
from .seed_publication import create_seed_site_draft, set_seed_rights, transition_seed_publication
from .site_inclusions import create_site_draft, set_site_rights, transition_site_inclusion
from .studio_commands import CommandContext
from .studio_schema import validate_record
from .studio_store import StudioStore
from .studio_types import DECISIONS, TRACKS
from .studies import list_studies
from .study_vault import add_study_variation, initialize_study_vault

REGISTERED_PROPOSAL_RUNNERS = frozenset(("behavior.probe", "behavior.scar_probe", "behavior.scar_tissue_probe", "look.scar_tissue_probe"))


def _store(args: argparse.Namespace) -> StudioStore:
    return StudioStore(args.studio_root)


def _print_record(record: dict[str, object], collection: str, root: Path) -> None:
    print(f"id: {record['id']}")
    print(f"path: {root / 'studio' / collection / (str(record['id']) + '.json')}")


def command_seed(args: argparse.Namespace) -> int:
    if not args.raw_text:
        raise ValueError("raw idea must not be empty")
    if args.source:
        parsed = urlparse(args.source)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source must be an http(s) URL")
    record: dict[str, object] = {
        "schema_version": 1,
        "id": f"idea-{uuid.uuid4().hex[:12]}",
        "title": args.raw_text.splitlines()[0][:120],
        "raw_text": args.raw_text,
        "track": args.track,
        "state": "inbox",
        "visibility": "private",
    }
    if args.source:
        record["source_urls"] = [args.source]
    errors = validate_record("idea", record)
    if errors:
        raise ValueError("; ".join(errors))
    _store(args).create("ideas", str(record["id"]), record)
    _print_record(record, "ideas", args.studio_root)
    return 0


def _list(args: argparse.Namespace, collection: str) -> int:
    records, errors = _store(args).list(collection)
    if errors:
        raise ValueError("; ".join(error["error"] for error in errors))
    for record in records:
        if not getattr(args, "state", None) or record.get("state") == args.state:
            print(f"{record['id']}\t{record.get('state', '')}")
    return 0


def command_show(args: argparse.Namespace) -> int:
    prefix = args.record_id.split("-", 1)[0]
    collection = {"idea": "ideas", "direction": "directions", "proposal": "proposals", "experiment": "experiments", "artifact": "artifacts", "component": "components", "editorial": "editorial"}.get(prefix)
    if collection is None:
        raise ValueError("unknown record id")
    print(json.dumps(_store(args).read(collection, args.record_id), indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def command_propose(args: argparse.Namespace) -> int:
    value = json.loads(args.proposal_json)
    if not isinstance(value, dict):
        raise ValueError("proposal-json must be an object")
    record = create_proposal(_store(args), args.idea_id, value, registered_runners=REGISTERED_PROPOSAL_RUNNERS)
    _print_record(record, "proposals", args.studio_root)
    return 0


def _json_object(raw: str, label: str) -> dict[str, object]:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def command_direction_create(args: argparse.Namespace) -> int:
    record = create_direction(_store(args), args.idea_id, _json_object(args.direction_json, "direction-json"))
    _print_record(record, "directions", args.studio_root)
    return 0


def command_directions(args: argparse.Namespace) -> int:
    records, errors = _store(args).list("directions")
    if errors:
        raise ValueError("; ".join(error["error"] for error in errors))
    for record in records:
        if (not args.idea or record.get("idea_id") == args.idea) and (not args.state or record.get("state") == args.state):
            print(f"{record['id']}\t{record['state']}\t{record['title']}")
    return 0


def command_direction_decide(args: argparse.Namespace) -> int:
    record = decide_direction(_store(args), args.direction_id, args.decision)
    print(f"id: {record['id']}")
    print(f"state: {record['state']}")
    return 0


def command_direction_mutate(args: argparse.Namespace) -> int:
    record = mutate_direction(_store(args), args.direction_id, _json_object(args.direction_json, "direction-json"))
    _print_record(record, "directions", args.studio_root)
    return 0


def command_direction_merge(args: argparse.Namespace) -> int:
    record = merge_directions(_store(args), args.direction_ids, _json_object(args.direction_json, "direction-json"))
    _print_record(record, "directions", args.studio_root)
    return 0


def command_direction_propose(args: argparse.Namespace) -> int:
    record = derive_probe_proposal(
        _store(args), args.direction_id, _json_object(args.probe_json, "probe-json"),
        registered_runners=REGISTERED_PROPOSAL_RUNNERS,
    )
    _print_record(record, "proposals", args.studio_root)
    return 0


def command_approve(args: argparse.Namespace) -> int:
    if args.record_id.startswith("proposal-"):
        record = approve_proposal(_store(args), args.record_id)
    elif args.record_id.startswith("editorial-"):
        record = approve_editorial(_store(args), args.record_id)
    else:
        raise ValueError("approval supports proposal or editorial records")
    print(f"id: {record['id']}")
    print(f"state: {record['state']}")
    return 0


MICRO_RETRO_NUDGE = "micro-retro: ask KC what dragged and what was fun; record with `studio retro`"


def command_decide(args: argparse.Namespace) -> int:
    store = _store(args)
    record = store.read("artifacts", args.artifact_id)
    updated = {**record, "decision": args.decision, "decision_note": args.note}
    store.update("artifacts", args.artifact_id, updated)
    print(f"id: {args.artifact_id}")
    print(f"decision: {args.decision}")
    print(MICRO_RETRO_NUDGE)
    return 0


def command_promote(args: argparse.Namespace) -> int:
    record = promote_artifact(_store(args), args.studio_root, args.artifact_id, args.kind, args.rationale)
    _print_record(record, "components", args.studio_root)
    print(MICRO_RETRO_NUDGE)
    return 0


def command_tag(args: argparse.Namespace) -> int:
    print(json.dumps(tag_artifact(_store(args), args.artifact_id, args.tags), sort_keys=True))
    return 0


def command_untag(args: argparse.Namespace) -> int:
    print(json.dumps(untag_artifact(_store(args), args.artifact_id, args.tag), sort_keys=True))
    return 0


def command_editorial(args: argparse.Namespace) -> int:
    for record in editorial_summary(_store(args)):
        print(f"{record['id']}\t{record['state']}\t{record['visibility']}")
    return 0


def command_note(args: argparse.Namespace) -> int:
    record = capture_note(
        _store(args), args.text, args.category, args.stage, args.track,
        reference_id=args.reference,
    )
    _print_record(record, "notes", args.studio_root)
    return 0


def command_retro(args: argparse.Namespace) -> int:
    records = capture_retro(
        _store(args), args.stage, args.track,
        dragged=args.dragged, fun=args.fun, reference_id=args.reference,
    )
    for record in records:
        _print_record(record, "notes", args.studio_root)
    return 0


def command_seed_digest(args: argparse.Namespace) -> int:
    from datetime import datetime, timezone

    today = args.date or datetime.now(timezone.utc).date().isoformat()
    print(build_seed_digest(_store(args), today=today), end="")
    return 0


def command_notes(args: argparse.Namespace) -> int:
    store = _store(args)
    if args.digest:
        print(f"path: {write_digest(store)}")
        return 0
    for record in filtered_notes(store, category=args.category, stage=args.stage, track=args.track):
        reference = f"\t{record['reference_id']}" if record.get("reference_id") else ""
        print(f"{record['id']}\t{record['created_at']}\t{record['category']}\t{record['track']}/{record['stage']}{reference}\t{str(record['text']).strip()}")
    return 0








def command_inbox(args: argparse.Namespace) -> int:
    inbox = build_review_inbox(args.studio_root)
    for item in inbox["items"]:
        print(f"{item['source_type']}\t{item['stage']}\t{item['id']}\t{item['text']}")
    return 0



def command_study_init(args: argparse.Namespace) -> int:
    study = _store(args).read("studies", args.study_id)
    vault = initialize_study_vault(args.studio_root, study)
    print(f"vault: {vault}")
    return 0


def command_study_variation_add(args: argparse.Namespace) -> int:
    study = _store(args).read("studies", args.study_id)
    vault = initialize_study_vault(args.studio_root, study)
    variation = add_study_variation(
        vault,
        number=args.number,
        title=args.title,
        behavior_number=args.behavior_number,
        state=args.state,
        behavior_selection_id=args.behavior_selection_id,
        derived_from=args.derived_from,
        make_current=not args.no_make_current,
    )
    print(f"variation: {variation['id']}")
    print(f"behavior: {variation['behavior_number']:03d}")
    print(f"file-stem: {variation['file_stem']}")
    return 0


def command_studies(args: argparse.Namespace) -> int:
    records = list_studies(_store(args))
    if args.json:
        print(json.dumps(records, indent=2, sort_keys=True))
    else:
        for record in records:
            focus = "focused" if record["is_focused"] else ""
            print(f"{record['id']}\t{record['state']}\t{focus}\t{record['title']}")
    return 0


def _read_json_input(root: Path, raw_path: str, label: str) -> object:
    path = Path(raw_path)
    if not path.is_absolute():
        path = root / path
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read {label}: {error}") from error





def command_conversation_bind(args: argparse.Namespace) -> int:
    record = bind_discord_thread(
        _store(args),
        study_id=args.study_id,
        guild_id=args.guild_id,
        parent_channel_id=args.parent_channel_id,
        thread_id=args.thread_id,
    )
    if args.json:
        print(json.dumps(record, indent=2, sort_keys=True))
    else:
        _print_record(record, "conversation-bindings", args.studio_root)
    return 0


def command_seed_conversation_bind(args: argparse.Namespace) -> int:
    record = bind_discord_thread(
        _store(args),
        seed_id=args.seed_id,
        guild_id=args.guild_id,
        parent_channel_id=args.parent_channel_id,
        thread_id=args.thread_id,
    )
    if args.json:
        print(json.dumps(record, indent=2, sort_keys=True))
    else:
        _print_record(record, "conversation-bindings", args.studio_root)
    return 0


def command_conversation_resolve(args: argparse.Namespace) -> int:
    record = resolve_discord_thread(_store(args), args.thread_id)
    if args.json:
        print(json.dumps(record, indent=2, sort_keys=True))
    else:
        if "study_id" in record:
            print(f"study: {record['study_id']}")
        else:
            print(f"seed: {record['seed_id']}")
        print(f"binding: {record['id']}")
    return 0


def _command_context(raw: str, study_id: str) -> CommandContext:
    value = _json_object(raw, "context-json")
    required = {"actor", "origin", "source_ref", "idempotency_key"}
    if set(value) != required or not all(isinstance(value[key], str) for key in required):
        raise ValueError("context-json requires actor, origin, source_ref, and idempotency_key strings")
    return CommandContext(study_id=study_id, **value)


def command_site_include(args: argparse.Namespace) -> int:
    details = _json_object(args.inclusion_json, "inclusion-json")
    required = {"public_title", "public_caption", "role", "section", "order", "alt_text"}
    if set(details) != required:
        raise ValueError("inclusion-json contains unsupported or missing fields")
    result = create_site_draft(
        _store(args),
        args.studio_root,
        _command_context(args.context_json, args.study_id),
        artifact_id=args.artifact_id,
        **details,
    )
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else f"id: {result['result']['id']}")
    return 0


def command_site_rights(args: argparse.Namespace) -> int:
    result = set_site_rights(
        _store(args),
        _command_context(args.context_json, args.study_id),
        args.inclusion_id,
        args.status,
        args.rationale,
    )
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else f"rights: {result['result']['rights_status']}")
    return 0


def command_site_transition(args: argparse.Namespace) -> int:
    result = transition_site_inclusion(
        _store(args),
        _command_context(args.context_json, args.study_id),
        args.inclusion_id,
        args.state,
    )
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else f"state: {result['result']['state']}")
    return 0


def command_public_preview(args: argparse.Namespace) -> int:
    output = Path(args.output)
    if not output.is_absolute():
        output = args.studio_root / output
    result = build_public_site(_store(args), args.studio_root, args.study_id, output)
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else f"output: {result['output']}")
    return 0


def command_seed_create(args: argparse.Namespace) -> int:
    record = create_seed(_store(args), _json_object(args.seed_json, "seed-json"))
    print(json.dumps(record, indent=2, sort_keys=True) if args.json else f"id: {record['id']}")
    return 0


def command_seed_update(args: argparse.Namespace) -> int:
    record = update_seed(_store(args), args.seed_id, _json_object(args.changes_json, "changes-json"))
    print(json.dumps(record, indent=2, sort_keys=True) if args.json else f"id: {record['id']}")
    return 0


def command_seed_transition(args: argparse.Namespace) -> int:
    record = transition_seed(_store(args), args.seed_id, args.state)
    print(json.dumps(record, indent=2, sort_keys=True) if args.json else f"state: {record['state']}")
    return 0


def command_seed_promote(args: argparse.Namespace) -> int:
    details = _json_object(args.study_json, "study-json")
    required = {"study_id", "study_title", "primary_track", "recommended_next_action"}
    if set(details) != required or not all(isinstance(details[key], str) for key in required):
        raise ValueError("study-json requires study_id, study_title, primary_track, and recommended_next_action strings")
    context_value = _json_object(args.context_json, "context-json")
    context_required = {"actor", "origin", "source_ref", "idempotency_key"}
    if set(context_value) != context_required or not all(isinstance(context_value[key], str) for key in context_required):
        raise ValueError("context-json requires actor, origin, source_ref, and idempotency_key strings")
    context = CommandContext(seed_id=args.seed_id, **context_value)
    result = promote_seed_to_study_command(_store(args), context, **details)
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else f"study: {result['result']['id']}")
    return 0


def command_seed_site_draft(args: argparse.Namespace) -> int:
    record = create_seed_site_draft(_store(args), args.seed_id, source_ref=args.source_ref)
    print(json.dumps(record, indent=2, sort_keys=True) if args.json else f"id: {record['id']}")
    return 0


def command_seed_site_rights(args: argparse.Namespace) -> int:
    record = set_seed_rights(_store(args), args.inclusion_id, args.status, args.rationale)
    print(json.dumps(record, indent=2, sort_keys=True) if args.json else f"rights: {record['rights_status']}")
    return 0


def command_seed_site_transition(args: argparse.Namespace) -> int:
    record = transition_seed_publication(
        _store(args), args.inclusion_id, args.state, actor=args.actor, source_ref=args.source_ref
    )
    print(json.dumps(record, indent=2, sort_keys=True) if args.json else f"state: {record['state']}")
    return 0


def command_seed_bank_preview(args: argparse.Namespace) -> int:
    output = Path(args.output)
    if not output.is_absolute():
        output = args.studio_root / output
    result = build_public_seed_bank(_store(args), args.studio_root, output)
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else f"output: {result['output']}")
    return 0


def add_studio_parser(subparsers: argparse._SubParsersAction, root: Path) -> None:
    studio = subparsers.add_parser("studio", help="manage local Studio records without execution")
    commands = studio.add_subparsers(required=True)

    seed = commands.add_parser("seed")
    seed.add_argument("raw_text")
    seed.add_argument("--track", choices=TRACKS, default="behavior")
    seed.add_argument("--source")
    seed.set_defaults(func=command_seed)

    seed_create = commands.add_parser("seed-create", help="capture a complete private Seed")
    seed_create.add_argument("seed_json")
    seed_create.add_argument("--json", action="store_true")
    seed_create.set_defaults(func=command_seed_create)
    seed_update = commands.add_parser("seed-update", help="update bounded Seed brainstorming fields")
    seed_update.add_argument("seed_id")
    seed_update.add_argument("changes_json")
    seed_update.add_argument("--json", action="store_true")
    seed_update.set_defaults(func=command_seed_update)
    seed_transition = commands.add_parser("seed-transition", help="transition a Seed's creative lifecycle")
    seed_transition.add_argument("seed_id")
    seed_transition.add_argument("state", choices=("incubating", "ready", "promoted", "archived"))
    seed_transition.add_argument("--json", action="store_true")
    seed_transition.set_defaults(func=command_seed_transition)
    seed_promote = commands.add_parser("seed-promote", help="promote a ready Seed into one linked Study")
    seed_promote.add_argument("seed_id")
    seed_promote.add_argument("study_json")
    seed_promote.add_argument("context_json")
    seed_promote.add_argument("--json", action="store_true")
    seed_promote.set_defaults(func=command_seed_promote)
    seed_site_draft = commands.add_parser("seed-site-draft", help="prepare a Seed as a private site draft")
    seed_site_draft.add_argument("seed_id")
    seed_site_draft.add_argument("source_ref")
    seed_site_draft.add_argument("--json", action="store_true")
    seed_site_draft.set_defaults(func=command_seed_site_draft)
    seed_site_rights = commands.add_parser("seed-site-rights", help="record Seed publication-rights status")
    seed_site_rights.add_argument("inclusion_id")
    seed_site_rights.add_argument("status", choices=("pending", "cleared", "blocked"))
    seed_site_rights.add_argument("rationale")
    seed_site_rights.add_argument("--json", action="store_true")
    seed_site_rights.set_defaults(func=command_seed_site_rights)
    seed_site_transition = commands.add_parser("seed-site-transition", help="transition explicit Seed site inclusion")
    seed_site_transition.add_argument("inclusion_id")
    seed_site_transition.add_argument("state", choices=("private", "site-draft", "site-live", "retired"))
    seed_site_transition.add_argument("actor")
    seed_site_transition.add_argument("source_ref")
    seed_site_transition.add_argument("--json", action="store_true")
    seed_site_transition.set_defaults(func=command_seed_site_transition)
    seed_bank_preview = commands.add_parser("seed-bank-preview", help="build the local read-only public Seed Bank")
    seed_bank_preview.add_argument("output")
    seed_bank_preview.add_argument("--json", action="store_true")
    seed_bank_preview.set_defaults(func=command_seed_bank_preview)

    ideas = commands.add_parser("ideas")
    ideas.add_argument("--state", default=None)
    ideas.set_defaults(func=lambda args: _list(args, "ideas"))
    direction_create = commands.add_parser("direction-create", help="create a conceptual behavior direction")
    direction_create.add_argument("idea_id")
    direction_create.add_argument("direction_json")
    direction_create.set_defaults(func=command_direction_create)
    directions = commands.add_parser("directions", help="list preserved behavior directions")
    directions.add_argument("--idea")
    directions.add_argument("--state")
    directions.set_defaults(func=command_directions)
    direction_decide = commands.add_parser("direction-decide", help="select, hold, archive, or reject a direction")
    direction_decide.add_argument("direction_id")
    direction_decide.add_argument("decision", choices=DIRECTION_DECISIONS)
    direction_decide.set_defaults(func=command_direction_decide)
    direction_mutate = commands.add_parser("direction-mutate", help="create a non-destructive conceptual mutation")
    direction_mutate.add_argument("direction_id")
    direction_mutate.add_argument("direction_json")
    direction_mutate.set_defaults(func=command_direction_mutate)
    direction_merge = commands.add_parser("direction-merge", help="create a conceptual merge with lineage")
    direction_merge.add_argument("direction_ids", nargs="+")
    direction_merge.add_argument("direction_json")
    direction_merge.set_defaults(func=command_direction_merge)
    direction_propose = commands.add_parser("direction-propose", help="derive a bounded proposed probe")
    direction_propose.add_argument("direction_id")
    direction_propose.add_argument("probe_json")
    direction_propose.set_defaults(func=command_direction_propose)
    show = commands.add_parser("show")
    show.add_argument("record_id")
    show.set_defaults(func=command_show)
    propose = commands.add_parser("propose")
    propose.add_argument("idea_id")
    propose.add_argument("proposal_json")
    propose.set_defaults(func=command_propose)
    proposals = commands.add_parser("proposals")
    proposals.add_argument("--state", default="proposed")
    proposals.set_defaults(func=lambda args: _list(args, "proposals"))
    approve = commands.add_parser("approve")
    approve.add_argument("record_id")
    approve.set_defaults(func=command_approve)
    decide = commands.add_parser("decide")
    decide.add_argument("artifact_id")
    decide.add_argument("decision", choices=DECISIONS)
    decide.add_argument("--note", required=True)
    decide.set_defaults(func=command_decide)
    promote = commands.add_parser("promote")
    promote.add_argument("artifact_id")
    promote.add_argument("--kind", required=True, choices=("behavior", "look", "palette", "shot", "sound"))
    promote.add_argument("--rationale", required=True)
    promote.set_defaults(func=command_promote)
    tag = commands.add_parser("tag")
    tag.add_argument("artifact_id")
    tag.add_argument("tags", nargs="+")
    tag.set_defaults(func=command_tag)
    untag = commands.add_parser("untag")
    untag.add_argument("artifact_id")
    untag.add_argument("tag")
    untag.set_defaults(func=command_untag)
    editorial = commands.add_parser("editorial")
    editorial.set_defaults(func=command_editorial)
    note = commands.add_parser("note", help="capture a private process observation")
    note.add_argument("text")
    note.add_argument("--category", required=True, choices=NOTE_CATEGORIES)
    note.add_argument("--stage", required=True, choices=NOTE_STAGES)
    note.add_argument("--track", required=True, choices=TRACKS)
    note.add_argument("--reference")
    note.set_defaults(func=command_note)
    seed_digest = commands.add_parser("seed-digest", help="print the Discord-postable Seed Bank digest")
    seed_digest.add_argument("--date", help="override the digest date (default: today, UTC)")
    seed_digest.set_defaults(func=command_seed_digest)
    retro = commands.add_parser("retro", help="record a gate micro-retro: what dragged, what was fun")
    retro.add_argument("--stage", required=True, choices=NOTE_STAGES)
    retro.add_argument("--track", required=True, choices=TRACKS)
    retro.add_argument("--dragged", help="KC's answer to 'what dragged?', verbatim")
    retro.add_argument("--fun", help="KC's answer to 'what was actually fun?', verbatim")
    retro.add_argument("--reference")
    retro.set_defaults(func=command_retro)
    notes = commands.add_parser("notes", help="list process observations or write a digest")
    notes.add_argument("--category", choices=NOTE_CATEGORIES)
    notes.add_argument("--stage", choices=NOTE_STAGES)
    notes.add_argument("--track", choices=TRACKS)
    notes.add_argument("--digest", action="store_true")
    notes.set_defaults(func=command_notes)
    inbox = commands.add_parser("inbox", help="list unresolved work across all Studio stages")
    inbox.set_defaults(func=command_inbox)
    study_init = commands.add_parser("study-init", help="create the canonical numbered directory contract for a Study")
    study_init.add_argument("study_id")
    study_init.set_defaults(func=command_study_init)
    study_variation_add = commands.add_parser("study-variation-add", help="register a numbered Study variation")
    study_variation_add.add_argument("study_id")
    study_variation_add.add_argument("number", type=int)
    study_variation_add.add_argument("title")
    study_variation_add.add_argument(
        "--state",
        choices=("active", "held", "selected", "completed", "archived"),
        default="active",
    )
    study_variation_add.add_argument(
        "--behavior-number",
        type=int,
        default=1,
        help="promoted behavior this variation descends from; variation numbers restart at 1 per behavior",
    )
    study_variation_add.add_argument("--behavior-selection-id")
    study_variation_add.add_argument("--derived-from")
    study_variation_add.add_argument("--no-make-current", action="store_true")
    study_variation_add.set_defaults(func=command_study_variation_add)
    studies = commands.add_parser("studies", help="list canonical Studies")
    studies.add_argument("--json", action="store_true")
    studies.set_defaults(func=command_studies)
    conversation_bind = commands.add_parser("conversation-bind", help="bind one Discord thread to a Study")
    conversation_bind.add_argument("study_id")
    conversation_bind.add_argument("--guild-id", required=True)
    conversation_bind.add_argument("--parent-channel-id", required=True)
    conversation_bind.add_argument("--thread-id", required=True)
    conversation_bind.add_argument("--json", action="store_true")
    conversation_bind.set_defaults(func=command_conversation_bind)
    seed_conversation_bind = commands.add_parser(
        "seed-conversation-bind", help="bind one Discord thread to a Seed"
    )
    seed_conversation_bind.add_argument("seed_id")
    seed_conversation_bind.add_argument("--guild-id", required=True)
    seed_conversation_bind.add_argument("--parent-channel-id", required=True)
    seed_conversation_bind.add_argument("--thread-id", required=True)
    seed_conversation_bind.add_argument("--json", action="store_true")
    seed_conversation_bind.set_defaults(func=command_seed_conversation_bind)
    conversation_resolve = commands.add_parser("conversation-resolve", help="resolve a Discord thread to its Study")
    conversation_resolve.add_argument("thread_id")
    conversation_resolve.add_argument("--json", action="store_true")
    conversation_resolve.set_defaults(func=command_conversation_resolve)
    site_include = commands.add_parser("site-include", help="prepare one verified artifact as a private site draft")
    site_include.add_argument("study_id")
    site_include.add_argument("artifact_id")
    site_include.add_argument("inclusion_json")
    site_include.add_argument("context_json")
    site_include.add_argument("--json", action="store_true")
    site_include.set_defaults(func=command_site_include)
    site_rights = commands.add_parser("site-rights", help="record publication-rights status for a site inclusion")
    site_rights.add_argument("study_id")
    site_rights.add_argument("inclusion_id")
    site_rights.add_argument("status", choices=("pending", "cleared", "blocked"))
    site_rights.add_argument("rationale")
    site_rights.add_argument("context_json")
    site_rights.add_argument("--json", action="store_true")
    site_rights.set_defaults(func=command_site_rights)
    site_transition = commands.add_parser("site-transition", help="transition an explicit site-inclusion record")
    site_transition.add_argument("study_id")
    site_transition.add_argument("inclusion_id")
    site_transition.add_argument("state", choices=("private", "site-draft", "site-live", "archive-keep", "retired"))
    site_transition.add_argument("context_json")
    site_transition.add_argument("--json", action="store_true")
    site_transition.set_defaults(func=command_site_transition)
    public_preview = commands.add_parser("public-preview", help="build a local read-only public Study preview")
    public_preview.add_argument("study_id")
    public_preview.add_argument("output")
    public_preview.add_argument("--json", action="store_true")
    public_preview.set_defaults(func=command_public_preview)

    for command in commands.choices.values():
        command.set_defaults(studio_root=root)
