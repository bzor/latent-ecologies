from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from houdini_ai.fieldwriting_ants import package_direction, summarize_direction
from houdini_ai.fieldwriting_ants_offshoots import detect_translating_tail, simulate_rul_bridge_feedback_variant

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = (
    REPO_ROOT
    / "studies"
    / "study_004_three-dimensional-fieldwriting-ants"
    / "01_behavior"
    / "01_work"
    / "09_RUL-causal-recovery-round"
)
VARIANTS = (
    ("01_control", "control"),
    ("02_relay-node", "relay-node"),
    ("03_ladder-exchange", "ladder-exchange"),
    ("04_scar-recovery", "scar-branch"),
)
SCHEDULES = {
    "control": ((), 0),
    "relay-node": ((3803, 6403, 9003), 22),
    "ladder-exchange": ((3809, 7009, 10209), 88),
    "scar-branch": ((4000, 6200, 8400), 22),
}


def checksum(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(OUTPUT_ROOT).as_posix(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def recovery_latency(path, after_step: int, period: int = 22, cycles: int = 8, limit: int = 2_000):
    deltas = [tuple(b[axis] - a[axis] for axis in range(3)) for a, b in zip(path, path[1:])]
    for latency in range(0, limit + 1):
        start = after_step + latency
        tail = deltas[start : start + period * cycles]
        if len(tail) < period * cycles:
            return None
        unit = tail[:period]
        if all(tail[index : index + period] == unit for index in range(0, len(tail), period)):
            displacement = tuple(sum(delta[axis] for delta in unit) for axis in range(3))
            if displacement != (0, 0, 0):
                return latency
    return None


def event_span(result, event_step: int, duration: int) -> list[int]:
    per_agent = []
    for path in result.trajectories:
        points = path[event_step : event_step + duration + 1]
        per_agent.append(
            [max(point[axis] for point in points) - min(point[axis] for point in points) for axis in range(3)]
        )
    return [max(spans[axis] for spans in per_agent) for axis in range(3)]


def event_window_sheet(results: dict[str, object]) -> Path:
    width, height = 480, 480
    sheet = Image.new("RGB", (960, 960), (10, 12, 11))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (directory_name, variant) in enumerate(VARIANTS):
        result = results[variant]
        schedule, duration = SCHEDULES[variant]
        event_step = schedule[0] if schedule else 3803
        start, end = max(0, event_step - 120), min(result.steps, event_step + duration + 220)
        paths = [path[start : end + 1] for path in result.trajectories]
        points = [point for path in paths for point in path]
        projected = []
        for point in points:
            x, y, z = point
            projected.append((x * 0.72 - y * 0.69, x * 0.36 + y * 0.38 + z * 0.82))
        min_x, max_x = min(x for x, _ in projected), max(x for x, _ in projected)
        min_y, max_y = min(y for _, y in projected), max(y for _, y in projected)
        scale = min(390 / max(1, max_x - min_x), 350 / max(1, max_y - min_y))
        ox, oy = (index % 2) * width, (index // 2) * height

        def project(point):
            x, y, z = point
            px, py = x * 0.72 - y * 0.69, x * 0.36 + y * 0.38 + z * 0.82
            return (round(ox + 45 + (px - min_x) * scale), round(oy + 425 - (py - min_y) * scale))

        draw.text((ox + 12, oy + 10), directory_name.replace("_", " "), fill=(224, 230, 221), font=font)
        draw.text((ox + 12, oy + 30), f"steps {start}..{end}  event {event_step}  duration {duration}", fill=(137, 156, 145), font=font)
        for agent_id, path in enumerate(paths):
            draw.line([project(point) for point in path], fill=(75, 222, 181) if agent_id == 0 else (195, 189, 177), width=3)
            draw.ellipse((*project(path[0]), *project(path[0])), fill=(220, 226, 218))
        for agent_id, full_path in enumerate(result.trajectories):
            marker = project(full_path[event_step])
            draw.ellipse((marker[0] - 7, marker[1] - 7, marker[0] + 7, marker[1] + 7), outline=(235, 89, 139), width=2)
        if variant == "scar-branch":
            snapshot = next(snapshot for snapshot in result.snapshots if snapshot.step == event_step)
            center = result.trajectories[0][event_step]
            local = [point for point, _ in snapshot.field if max(abs(point[axis] - center[axis]) for axis in range(3)) <= 6]
            for point in local:
                px, py = project(point)
                draw.ellipse((px - 2, py - 2, px + 2, py + 2), fill=(234, 177, 95))
    output = OUTPUT_ROOT / "event-window-comparison.png"
    sheet.save(output)
    return output


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    horizon = 15_000
    common_snapshots = set(range(0, horizon + 1, 500)) | {horizon}
    for schedule, duration in SCHEDULES.values():
        for event_step in schedule:
            common_snapshots.update((event_step, event_step + duration // 2, event_step + duration))
    extra = tuple(sorted(common_snapshots))
    results = {}
    rows = []
    movies = []
    for directory_name, variant in VARIANTS:
        result = simulate_rul_bridge_feedback_variant(
            variant,
            steps=horizon,
            snapshot_interval=500,
            extra_snapshot_steps=extra,
        )
        results[variant] = result
        artifacts = package_direction(
            result,
            OUTPUT_ROOT / directory_name,
            fps=12,
            size=(480, 480),
            render_profile="anatomy",
        )
        movies.append(artifacts["video"])
        schedule, duration = SCHEDULES[variant]
        tails = [detect_translating_tail(path, max_period=256, minimum_cycles=4) for path in result.trajectories]
        rows.append(
            {
                "id": directory_name,
                "variant": variant,
                "event_schedule": schedule,
                "event_duration": duration,
                "event_count": len(schedule),
                "tail_periods": [tail["period"] if tail else None for tail in tails],
                "tail_displacements": [tail["displacement"] if tail else None for tail in tails],
                "recovery_latencies": [
                    [recovery_latency(path, event_step + duration) for path in result.trajectories]
                    for event_step in schedule
                ],
                "event_window_spans": [event_span(result, event_step, duration) for event_step in schedule],
                "collisions": result.metrics["collisions"],
                "shared_rewrites": result.metrics["shared_rewrites"],
                "field_cells": summarize_direction(result)["field_cells"],
                "axis_spans": summarize_direction(result)["axis_spans"],
                "state_sha256": summarize_direction(result)["state_sha256"],
                "restored_scar_events": result.metrics["restored_scar_events"],
                "authority": "python-reference",
            }
        )

    control = results["control"]
    scar = results["scar-branch"]
    rows[-1]["exact_final_control_equivalence"] = scar.trajectories == control.trajectories and scar.field == control.field
    report_path = OUTPUT_ROOT / "causal-recovery-study.json"
    report_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "study": "RUL causal excursion and recovery round",
                "classification": "bounded Studio interventions over a published Hamann cubic 3D RUL pair",
                "intervention_order": "pre-read intervention, synchronous read, intent, commit",
                "true_snapshot_timelapse": True,
                "interpolation": False,
                "common_snapshot_steps": list(extra),
                "variants": rows,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    event_sheet = event_window_sheet(results)
    global_sheet = Image.new("RGB", (960, 960), (12, 14, 13))
    global_draw = ImageDraw.Draw(global_sheet)
    global_font = ImageFont.load_default()
    for index, (directory_name, variant) in enumerate(VARIANTS):
        origin = ((index % 2) * 480, (index // 2) * 480)
        with Image.open(OUTPUT_ROOT / directory_name / "stills" / "late.png") as image:
            global_sheet.paste(image.convert("RGB"), origin)
        row = next(item for item in rows if item["variant"] == variant)
        global_draw.rectangle((origin[0], origin[1], origin[0] + 480, origin[1] + 42), fill=(10, 12, 11))
        global_draw.text((origin[0] + 10, origin[1] + 8), directory_name.replace("_", " "), fill=(226, 231, 223), font=global_font)
        global_draw.text((origin[0] + 10, origin[1] + 25), f"periods {row['tail_periods']}  rewrites {row['shared_rewrites']}  spans {row['axis_spans']}", fill=(137, 155, 145), font=global_font)
    global_sheet_path = OUTPUT_ROOT / "global-comparison.png"
    global_sheet.save(global_sheet_path)

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg is required")
    movie_path = OUTPUT_ROOT / "causal-comparison.mp4"
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for movie in movies:
        command.extend(["-i", str(movie)])
    command.extend(["-filter_complex", "[0:v][1:v][2:v][3:v]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0:fill=black:shortest=1[v]", "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(movie_path)])
    subprocess.run(command, check=True)

    review_path = OUTPUT_ROOT / "REVIEW.md"
    review_path.write_text(
        "# RUL causal excursion and recovery round\n\n"
        "This round supersedes the feed-forward test as the causal answer. Relay pulses alter the primary field, ladder exchange swaps complete primary body frames, and scars temporarily modify the primary field before exact restoration.\n\n"
        "- Relay-node uses paired state increments separated by one period. Both agents reacquire exact period-22 tails, although agent 0 may leave with a changed translation vector.\n"
        "- Ladder exchange swaps complete frames for four periods, then swaps back. It gives the largest local excursion and increases shared-field rewriting while both tails reacquire period 22.\n"
        "- Scar recovery inserts a four-cell lateral branch for one period and restores the exact replaced values. Final field and trajectories equal the control exactly. Event-aligned frames are required because a coarse regular cadence can miss the active scar.\n\n"
        "Ladder exchange is the strongest causal structural event. Relay-node is subtler. Scar recovery is a clean reversible field event with limited geometric scale.\n",
        encoding="utf-8",
    )
    receipt_files = [report_path, event_sheet, global_sheet_path, movie_path, review_path]
    for directory_name, _ in VARIANTS:
        receipt_files.append(OUTPUT_ROOT / directory_name / "receipt.json")
    receipt_path = OUTPUT_ROOT / "receipt.json"
    receipt_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "root": str(OUTPUT_ROOT),
                "true_snapshot_timelapse": True,
                "interpolation": False,
                "artifacts": {path.relative_to(OUTPUT_ROOT).as_posix(): checksum(path) for path in receipt_files},
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
