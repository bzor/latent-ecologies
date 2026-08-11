from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .doctor import inspect_workstation
from .jobs import job_status, load_job, prepare_job, set_stage_state
from .pipeline import run_composite, run_encode, run_lookdev, run_milestone3, run_package, run_render, run_simulation


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "study.schema.json"


def validate_manifest(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"manifest not found: {path}"]
    except OSError as exc:
        return [f"could not read manifest {path}: {exc}"]
    except json.JSONDecodeError as exc:
        return [f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"]

    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
    except (OSError, json.JSONDecodeError, SchemaError) as exc:
        return [f"could not load study schema {SCHEMA_PATH}: {exc}"]

    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.absolute_path)):
        location = ".".join(str(part) for part in error.absolute_path) or "manifest"
        errors.append(f"{location}: {error.message}")
    if errors:
        return errors

    simulation = data["simulation"]
    if simulation["frame_end"] < simulation["frame_start"]:
        errors.append("simulation.frame_end must not precede frame_start")
    return errors


def command_validate(args: argparse.Namespace) -> int:
    path = Path(args.manifest).resolve()
    errors = validate_manifest(path)
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1
    print(f"OK {path}")
    return 0


def command_doctor(_: argparse.Namespace) -> int:
    print(f"project: {ROOT}")
    print(f"python: {sys.version.split()[0]}")
    lines, errors = inspect_workstation()
    for line in lines:
        print(line)
    for error in errors:
        print(f"ERROR {error}")
    return 1 if errors else 0


def _job_from_args(args: argparse.Namespace):
    return load_job(ROOT, Path(args.manifest))


def _print_job(job, receipts) -> None:
    print(f"job: {job.job_id}")
    print(f"workspace: {job.directory}")
    print(f"source: {job.source_state}")
    for receipt in receipts:
        state = receipt.get("state", "pending")
        reason = "reusable" if state == "complete" else "will run" if state in {"pending", "stale", "failed"} else state
        print(f"{receipt['stage']}: {state} ({reason})")


def command_plan(args: argparse.Namespace) -> int:
    errors = validate_manifest(Path(args.manifest).resolve())
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1
    job = _job_from_args(args)
    _print_job(job, prepare_job(job))
    print("plan only: no Houdini process was started")
    return 0


def command_status(args: argparse.Namespace) -> int:
    errors = validate_manifest(Path(args.manifest).resolve())
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1
    job = _job_from_args(args)
    _print_job(job, job_status(job))
    return 0


def command_run(args: argparse.Namespace) -> int:
    errors = validate_manifest(Path(args.manifest).resolve())
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1
    job = _job_from_args(args)
    prepare_job(job)
    set_stage_state(job, "validate", "running")
    set_stage_state(job, "validate", "complete", summary="study manifest passed schema and semantic validation")
    print(f"job: {job.job_id}")
    print("validate: complete")
    try:
        for message in run_milestone3(job):
            print(message)
        print(run_simulation(job))
        print(run_lookdev(job))
        print(run_render(job))
        print(run_composite(job))
        print(run_encode(job))
        print(run_package(job))
    except RuntimeError as exc:
        print(f"ERROR {exc}")
        return 1
    print("publication: draft package complete; external posting remains approval-gated")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="houdini-ai")
    subparsers = parser.add_subparsers(required=True)
    doctor = subparsers.add_parser("doctor", help="report local pipeline tools")
    doctor.set_defaults(func=command_doctor)
    validate = subparsers.add_parser("validate", help="validate a study manifest")
    validate.add_argument("manifest")
    validate.set_defaults(func=command_validate)
    for name, handler, help_text in (
        ("plan", command_plan, "create or refresh a job plan without launching Houdini"),
        ("run", command_run, "run implemented stages for a study job"),
        ("status", command_status, "show stage states for a study job"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("manifest")
        command.set_defaults(func=handler)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
