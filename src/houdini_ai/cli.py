from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .doctor import inspect_workstation
from .jobs import job_status, load_job, prepare_job, set_stage_state
from .mass_flow import run_mass_flow_probe
from .pipeline import run_composite, run_encode, run_lookdev, run_milestone3, run_package, run_render, run_simulation
from .storage import ALL_CATEGORIES, DEFAULT_CATEGORIES, apply_cleanup, format_bytes, plan_cleanup, storage_report


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
    report = storage_report(ROOT)
    if report["level"] != "ok":
        print(f"WARNING storage is {report['level']}: {format_bytes(report['work_size'])} in work, {format_bytes(report['disk_free'])} free")
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


def command_scale_probe(args: argparse.Namespace) -> int:
    errors = validate_manifest(Path(args.manifest).resolve())
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1
    job = _job_from_args(args)
    report = storage_report(ROOT)
    if report["level"] != "ok":
        print(f"WARNING storage is {report['level']}: {format_bytes(report['work_size'])} in work, {format_bytes(report['disk_free'])} free")
    prepare_job(job)
    print(f"job: {job.job_id}")
    try:
        print(run_mass_flow_probe(job))
    except RuntimeError as exc:
        print(f"ERROR {exc}")
        return 1
    return 0


def command_storage(_: argparse.Namespace) -> int:
    report = storage_report(ROOT)
    print(f"work: {format_bytes(report['work_size'])} across {report['work_files']:,} files [{report['level']}]")
    print(f"disk free: {format_bytes(report['disk_free'])} (minimum {format_bytes(report['minimum_free_bytes'])})")
    print(f"budgets: warning {format_bytes(report['warning_bytes'])}; critical {format_bytes(report['critical_bytes'])}")
    for job in report["jobs"]:
        flags = []
        if job.latest:
            flags.append("latest")
        if job.retention_protected:
            flags.append("protected")
        if job.package_complete:
            flags.append("packaged")
        print(f"{format_bytes(job.size):>10}  {job.job_id}  [{', '.join(flags) or 'reproducible'}]")
    return 1 if report["level"] == "critical" else 0


def command_clean(args: argparse.Namespace) -> int:
    categories = args.category or list(DEFAULT_CATEGORIES)
    items = plan_cleanup(ROOT, categories)
    total = sum(item.size for item in items)
    print(f"cleanup mode: {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"categories: {', '.join(categories)}")
    for item in items:
        print(f"{format_bytes(item.size):>10}  {item.category:<20} {item.path.relative_to(ROOT)}")
    print(f"total reclaimable: {format_bytes(total)} across {len(items)} targets")
    if args.apply:
        reclaimed = apply_cleanup(ROOT, items)
        print(f"reclaimed: {format_bytes(reclaimed)}")
    else:
        print("no files were removed; pass --apply to execute this exact category plan")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="houdini-ai")
    subparsers = parser.add_subparsers(required=True)
    doctor = subparsers.add_parser("doctor", help="report local pipeline tools")
    doctor.set_defaults(func=command_doctor)
    validate = subparsers.add_parser("validate", help="validate a study manifest")
    validate.add_argument("manifest")
    validate.set_defaults(func=command_validate)
    storage = subparsers.add_parser("storage", help="report generated-work usage and retention state")
    storage.set_defaults(func=command_storage)
    clean = subparsers.add_parser("clean", help="plan or apply bounded generated-work cleanup")
    clean.add_argument("--category", action="append", choices=ALL_CATEGORIES)
    clean.add_argument("--apply", action="store_true", help="execute the cleanup plan; default is dry-run")
    clean.set_defaults(func=command_clean)
    for name, handler, help_text in (
        ("plan", command_plan, "create or refresh a job plan without launching Houdini"),
        ("run", command_run, "run implemented stages for a study job"),
        ("status", command_status, "show stage states for a study job"),
        ("scale-probe", command_scale_probe, "run the Phase 2 high-density agent capability probe"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("manifest")
        command.set_defaults(func=handler)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
