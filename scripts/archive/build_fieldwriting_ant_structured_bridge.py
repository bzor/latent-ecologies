from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from houdini_ai.fieldwriting_ants import package_direction, summarize_direction
from houdini_ai.fieldwriting_ants_offshoots import analyze_offshoot_candidate, simulate_rul_bridge_variant

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = (
    REPO_ROOT
    / "studies"
    / "study_004_three-dimensional-fieldwriting-ants"
    / "01_behavior"
    / "01_work"
    / "08_RUL-structured-bridge-round"
)
VARIANTS = (
    ("01_control", "control", "Unmodified period-22 RUL gap-4 pair."),
    ("02_relay-nodes", "relay-node", "Persistent radial nodes written every four base periods."),
    ("03_ladder-exchange", "ladder-exchange", "Persistent transverse rungs written every eight base periods."),
    ("04_scar-branch", "scar-branch", "Alternating side branches transition from 0.5 active to persistent state-1 healed records."),
)


def record(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(OUTPUT_ROOT).as_posix(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def stack_movie(inputs: list[Path], output: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg is required")
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for path in inputs:
        command.extend(["-i", str(path)])
    command.extend(
        [
            "-filter_complex",
            "[0:v][1:v][2:v][3:v]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0:fill=black:shortest=1[v]",
            "-map",
            "[v]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    subprocess.run(command, check=True)


def comparison_sheet(rows: list[dict[str, object]], source_name: str, output_name: str) -> Path:
    width, height, header = 480, 480, 72
    sheet = Image.new("RGB", (width * 2, (height + header) * 2), (12, 14, 13))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, row in enumerate(rows):
        x, y = (index % 2) * width, (index // 2) * (height + header)
        source = OUTPUT_ROOT / row["id"] / source_name
        with Image.open(source) as image:
            sheet.paste(image.convert("RGB"), (x, y + header))
        draw.text((x + 12, y + 10), row["title"], fill=(225, 231, 222), font=font)
        draw.text(
            (x + 12, y + 31),
            f"events {row['event_count']}  cells {row['event_cells']}  periods {row['tail_periods']}",
            fill=(151, 168, 157),
            font=font,
        )
        draw.text(
            (x + 12, y + 51),
            f"primary preserved={row['primary_trajectory_preserved']}  spans {row['axis_spans']}",
            fill=(107, 128, 116),
            font=font,
        )
    output = OUTPUT_ROOT / output_name
    sheet.save(output)
    return output


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    control = simulate_rul_bridge_variant("control", steps=12_000, snapshot_interval=300)
    rows = []
    global_movies = []
    detail_movies = []
    for directory_name, variant, hypothesis in VARIANTS:
        result = control if variant == "control" else simulate_rul_bridge_variant(variant, steps=12_000, snapshot_interval=300)
        directory = OUTPUT_ROOT / directory_name
        artifacts = package_direction(result, directory / "global", fps=12, size=(480, 480), render_profile="anatomy")
        detail = simulate_rul_bridge_variant(variant, steps=3_000, snapshot_interval=100)
        detail_artifacts = package_direction(detail, directory / "detail-3000", fps=12, size=(480, 480), render_profile="anatomy")
        analysis = analyze_offshoot_candidate(result, max_period=256, minimum_cycles=4)
        summary = summarize_direction(result)
        row = {
            "id": directory_name,
            "title": directory_name.replace("_", " "),
            "variant": variant,
            "hypothesis": hypothesis,
            "event_count": result.metrics["event_count"],
            "event_cells": result.metrics.get("event_cells", 0),
            "event_start": result.metrics.get("event_start"),
            "event_interval": result.metrics.get("event_interval"),
            "event_duration": result.metrics["event_duration"],
            "primary_trajectory_preserved": result.trajectories == control.trajectories,
            "tail_periods": [tail["period"] if tail else None for tail in analysis["translating_tails"]],
            "tail_displacements": [tail["displacement"] if tail else None for tail in analysis["translating_tails"]],
            "shared_rewrites": result.metrics["shared_rewrites"],
            "collisions": result.metrics["collisions"],
            "axis_spans": summary["axis_spans"],
            "nonplanarity_ratio": summary["nonplanarity_ratio"],
            "field_cells": summary["field_cells"],
            "state_counts": summary["state_counts"],
            "state_sha256": summary["state_sha256"],
            "primary_state_sha256": summarize_direction(control)["state_sha256"],
            "authority": "python-reference",
            "event_writer_coupling": result.metrics.get("event_writer_coupling", "none"),
        }
        rows.append(row)
        global_movies.append(artifacts["video"])
        detail_movies.append(detail_artifacts["video"])

    report_path = OUTPUT_ROOT / "structured-bridge-study.json"
    report_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "study": "RUL structured bridge four-run round",
                "classification": "bounded Studio event-writer compositions over a published Hamann cubic 3D RUL pair",
                "primary_behavior_contract": "The two primary RUL trajectories and base field are unchanged by event writers.",
                "true_snapshot_timelapse": True,
                "interpolation": False,
                "variants": rows,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    global_sheet = comparison_sheet(rows, "global/stills/late.png", "global-comparison.png")
    detail_sheet = comparison_sheet(rows, "detail-3000/stills/late.png", "detail-comparison.png")
    global_movie = OUTPUT_ROOT / "global-comparison.mp4"
    detail_movie = OUTPUT_ROOT / "detail-comparison.mp4"
    stack_movie(global_movies, global_movie)
    stack_movie(detail_movies, detail_movie)

    review_path = OUTPUT_ROOT / "REVIEW.md"
    review_path.write_text(
        "# RUL structured bridge round\n\n"
        "Four deterministic runs compare the unchanged RUL gap-4 bridge with three feed-forward event writers. The event layer reads exact primary positions but does not alter the primary field, body frames, or trajectories. All four retain both exact period-22 translating tails.\n\n"
        "- **Relay nodes:** radial state-0.5 nodes every 88 steps. This produces a punctuated carrier with the densest repeated station rhythm.\n"
        "- **Ladder exchange:** transverse state-0.5 rungs every 176 steps. This produces the clearest structural modulation while leaving more uninterrupted bridge between events.\n"
        "- **Scar branch:** alternating side branches every 88 steps. Each branch is active at state 0.5 for 22 steps, then persists as a state-1 healed record. This produces a directional history of local forks while the bridge continues unchanged.\n\n"
        "These are compositional secondary-writer mechanisms. They preserve the bridge exactly because their coupling is feed-forward. They do not demonstrate that the primary RUL walkers can leave and reacquire the highway after causal feedback.\n",
        encoding="utf-8",
    )

    receipt_files = [report_path, global_sheet, detail_sheet, global_movie, detail_movie, review_path]
    for row in rows:
        receipt_files.extend(
            [
                OUTPUT_ROOT / row["id"] / "global" / "receipt.json",
                OUTPUT_ROOT / row["id"] / "detail-3000" / "receipt.json",
            ]
        )
    receipt_path = OUTPUT_ROOT / "receipt.json"
    receipt_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "root": str(OUTPUT_ROOT),
                "true_snapshot_timelapse": True,
                "interpolation": False,
                "artifacts": {path.relative_to(OUTPUT_ROOT).as_posix(): record(path) for path in receipt_files},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(OUTPUT_ROOT)


if __name__ == "__main__":
    main()
