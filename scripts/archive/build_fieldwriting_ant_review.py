from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont

from houdini_ai.fieldwriting_ants import (
    detect_tail_period,
    hamann_direction_result,
    package_direction,
    simulate_collision_colony,
    simulate_langton_2d,
    simulate_shared_2d_colony,
    simulate_ring_excavator,
    summarize_direction,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "studies" / "study_004_three-dimensional-fieldwriting-ants" / "01_behavior" / "01_work"


def build_baselines(output_root: Path) -> None:
    controls = []
    for rule, steps, published_period in (
        ("RRLU", 50_000, 32),
        ("RUL", 50_000, 22),
        ("RLRUUUL", 100_000, 25_436),
    ):
        result = hamann_direction_result(rule, steps, steps)
        summary = summarize_direction(result)
        controls.append(
            {
                "rule": rule,
                "steps": steps,
                "published_period": published_period,
                "detected_tail_period": summary["detected_tail_period"],
                "pass": summary["detected_tail_period"] == published_period,
                "state_sha256": summary["state_sha256"],
                "axis_spans": summary["axis_spans"],
                "field_cells": summary["field_cells"],
            }
        )
    classic_2d = simulate_langton_2d("RL", steps=20_000)
    classic_period = detect_tail_period(classic_2d.commands, [104])
    classic_hash = hashlib.sha256(
        json.dumps(
            {"trajectory": classic_2d.trajectory, "field": classic_2d.field},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    shared_2d = simulate_shared_2d_colony("RL", steps=2_000, snapshot_interval=2_000)
    shared_summary = summarize_direction(shared_2d)
    reference_2d = {
        "classic": {
            "rule": "RL",
            "steps": 20_000,
            "published_period": 104,
            "detected_tail_period": classic_period,
            "pass": classic_period == 104,
            "state_sha256": classic_hash,
        },
        "shared_field": {
            "rule": "RL",
            "steps": 2_000,
            "schedule": shared_2d.metrics["schedule"],
            "collision_policy": shared_2d.metrics["collision_policy"],
            "collisions": shared_2d.metrics["collisions"],
            "state_sha256": shared_summary["state_sha256"],
            "pass": shared_2d.metrics["collisions"] > 0,
        },
    }
    payload = {
        "schema_version": 1,
        "formalism": "Hamann cubic heading-plus-working-plane L/R/U/D ant",
        "step_order": "read current state; increment modulo rule length; rotate body frame; move one cubic cell",
        "initial_frame": {"position": [0, 0, 0], "forward": [1, 0, 0], "up": [0, 0, 1]},
        "references_2d": reference_2d,
        "controls": controls,
        "all_pass": all(control["pass"] for control in controls)
        and all(reference["pass"] for reference in reference_2d.values()),
    }
    target = output_root / "00_historical-controls" / "historical-controls.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(target)


def build_direction(name: str, output_root: Path) -> None:
    if name == "a":
        result = hamann_direction_result("RLRUUUL", steps=100_000, snapshot_interval=2_000)
        directory = output_root / "01_frame-highway-anatomy"
    elif name == "b":
        result = simulate_ring_excavator("URDUD", steps=1_200, snapshot_interval=20, shell_radius=3)
        directory = output_root / "02_frame-covariant-excavator"
    elif name == "c":
        result = simulate_collision_colony("RLRU", steps=1_200, snapshot_interval=20)
        directory = output_root / "03_transactional-collision-scars"
    else:
        raise ValueError(name)
    artifacts = package_direction(result, directory, fps=12, size=(720, 720))
    print(json.dumps({key: str(path) for key, path in artifacts.items()}, indent=2))


def build_comparison(output_root: Path) -> None:
    comparison_dir = output_root / "04_comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)
    directions = [
        (
            "A · PUBLISHED COMPLEX HIGHWAY",
            output_root / "01_frame-highway-anatomy",
            "RLRUUUL · Hamann historical control",
            "Useful calibration; least novel behavior.",
        ),
        (
            "B · FRAME-COVARIANT EXCAVATOR",
            output_root / "02_frame-covariant-excavator",
            "URDUD · internal phase + radius-3 shell",
            "Strong architectural cavity grammar; currently regular.",
        ),
        (
            "C · TRANSACTIONAL COLLISION SCARS",
            output_root / "03_transactional-collision-scars",
            "RLRU · six synchronous shared-field walkers",
            "Strongest contribution candidate: bounded volume, lineage, and persistent conflict sites.",
        ),
    ]
    metrics = [json.loads((directory / "metrics.json").read_text(encoding="utf-8")) for _, directory, _, _ in directions]

    width, height = 720, 720
    sheet = Image.new("RGB", (width * 3, height + 72), (15, 17, 16))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for column, ((title, directory, rule, _), metric) in enumerate(zip(directions, metrics)):
        with Image.open(directory / "stills" / "late.png") as image:
            sheet.paste(image.convert("RGB"), (column * width, 72))
        x = column * width + 14
        draw.text((x, 10), title, fill=(224, 228, 220), font=font)
        draw.text((x, 30), rule, fill=(151, 163, 157), font=font)
        draw.text(
            (x, 48),
            f"spans {metric['axis_spans']}  nonplanarity {metric['nonplanarity_ratio']:.3f}",
            fill=(112, 126, 120),
            font=font,
        )
    sheet_path = comparison_dir / "late-state-comparison.png"
    sheet.save(sheet_path)

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg is required for comparison encoding")
    video_path = comparison_dir / "motion-comparison.mp4"
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for _, directory, _, _ in directions:
        command.extend(["-i", str(directory / "motion-timelapse.mp4")])
    command.extend(
        [
            "-filter_complex",
            "[0:v][1:v][2:v]hstack=inputs=3:shortest=1[v]",
            "-map",
            "[v]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(video_path),
        ]
    )
    subprocess.run(command, check=True)

    payload = {
        "schema_version": 1,
        "status": "Behavior comparison; no rule-level novelty claim",
        "direction_order": ["A", "B", "C"],
        "recommendation": "Promote C for deeper Behavior search; retain B as a second material/cavity branch; keep A as the historical calibration control.",
        "directions": [
            {
                "id": chr(ord("A") + index),
                "title": title,
                "rule": rule,
                "assessment": assessment,
                "metrics": metric,
            }
            for index, ((title, _, rule, assessment), metric) in enumerate(zip(directions, metrics))
        ],
        "artifact_semantics": "All motion panels use true deterministic snapshots; time between panels is timelapsed and not interpolated.",
    }
    comparison_json = comparison_dir / "comparison.json"
    comparison_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    readme = comparison_dir / "README.md"
    readme.write_text(
        "# Study 004 Behavior comparison\n\n"
        "These are diagnostic representations, not Look development. Semantic field states remain independent of final materials.\n\n"
        "## Current read\n\n"
        "1. **C — Transactional collision scars:** strongest candidate. It produces a bounded volumetric shared memory with six legible lineages and persistent collision sites.\n"
        "2. **B — Frame-covariant excavator:** useful secondary branch. It writes a thick body-frame shell while erasing/revisiting its centerline, but the current rule is architecturally regular.\n"
        "3. **A — Published complex highway:** required calibration and useful representational control, not a Studio novelty claim.\n\n"
        "Every movie frame is a true simulator snapshot. The movie is an explicitly sampled timelapse, not interpolated motion.\n",
        encoding="utf-8",
    )

    def record(path: Path) -> dict[str, object]:
        data = path.read_bytes()
        return {"path": path.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    receipt = comparison_dir / "receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "artifacts": {
                    "sheet": record(sheet_path),
                    "video": record(video_path),
                    "comparison": record(comparison_json),
                    "readme": record(readme),
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(comparison_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Study 004 deterministic Behavior review artifacts")
    parser.add_argument("target", choices=("baseline", "a", "b", "c", "compare", "all"))
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.target in ("baseline", "all"):
        build_baselines(args.output_root)
    for direction in ("a", "b", "c"):
        if args.target in (direction, "all"):
            build_direction(direction, args.output_root)
    if args.target in ("compare", "all"):
        build_comparison(args.output_root)


if __name__ == "__main__":
    main()
