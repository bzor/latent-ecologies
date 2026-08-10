from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .doctor import inspect_workstation


ROOT = Path(__file__).resolve().parents[2]
REQUIRED_KEYS = {
    "schema_version",
    "id",
    "title",
    "status",
    "reproducibility",
    "seed",
    "simulation",
    "presentation",
    "render",
    "publication",
}


def validate_manifest(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"manifest not found: {path}"]
    except json.JSONDecodeError as exc:
        return [f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"]

    missing = sorted(REQUIRED_KEYS - data.keys())
    if missing:
        errors.append(f"missing required keys: {', '.join(missing)}")
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if data.get("render", {}).get("format") not in {"png", "exr"}:
        errors.append("render.format must be png or exr")
    if data.get("publication", {}).get("approval_required") is not True:
        errors.append("publication.approval_required must be true in the initial scaffold")
    simulation = data.get("simulation", {})
    if simulation.get("frame_end", 0) < simulation.get("frame_start", 1):
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="houdini-ai")
    subparsers = parser.add_subparsers(required=True)
    doctor = subparsers.add_parser("doctor", help="report local pipeline tools")
    doctor.set_defaults(func=command_doctor)
    validate = subparsers.add_parser("validate", help="validate a study manifest")
    validate.add_argument("manifest")
    validate.set_defaults(func=command_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
