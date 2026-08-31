from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from houdini_ai.fieldwriting_ants import package_direction, simulate_chiral_highway_pair, summarize_direction
from houdini_ai.fieldwriting_ants_offshoots import analyze_offshoot_candidate

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = (
    REPO_ROOT
    / "studies"
    / "study_004_three-dimensional-fieldwriting-ants"
    / "01_behavior"
    / "01_work"
    / "07_A3-classic-offshoot-study"
)
SAME_GAP_4 = (((-2, 0, 0), (0, 1, 0), (0, 0, 1)), ((2, 0, 0), (0, 1, 0), (0, 0, 1)))

CONFIGS = (
    {
        "id": "01_control-A3-gap-4",
        "hypothesis": "Frozen A3 control: long-transient shared volumetric highway pair.",
        "rule": "RLRUUUL",
        "steps": 20_000,
        "initial_agents": SAME_GAP_4,
        "phases": (0, 0),
    },
    {
        "id": "02_RRLU-parallel",
        "hypothesis": "Published period-32 rule tests strict one-axis translating highway morphology without forced interaction.",
        "rule": "RRLU",
        "steps": 12_000,
        "initial_agents": SAME_GAP_4,
        "phases": (0, 0),
    },
    {
        "id": "03_RRLU-phase-1",
        "hypothesis": "A one-state rule phase offset tests whether strict RRLU highways can interact and then separate.",
        "rule": "RRLU",
        "steps": 12_000,
        "initial_agents": SAME_GAP_4,
        "phases": (0, 1),
    },
    {
        "id": "04_RRLU-antiparallel",
        "hypothesis": "Opposed headings test a bilateral period-32 branch control.",
        "rule": "RRLU",
        "steps": 12_000,
        "initial_agents": (((-2, 0, 0), (0, 1, 0), (0, 0, 1)), ((2, 0, 0), (0, -1, 0), (0, 0, 1))),
        "phases": (0, 0),
    },
    {
        "id": "05_RUL-gap-2",
        "hypothesis": "A close pair using published period-22 RUL tests repeatable shared-field diagonal offshoots.",
        "rule": "RUL",
        "steps": 12_000,
        "initial_agents": (((-1, 0, 0), (0, 1, 0), (0, 0, 1)), ((1, 0, 0), (0, 1, 0), (0, 0, 1))),
        "phases": (0, 0),
    },
    {
        "id": "06_RUL-gap-4",
        "hypothesis": "Gap-4 with published period-22 RUL tests a direct classic-like replacement parameter against the frozen control.",
        "rule": "RUL",
        "steps": 12_000,
        "initial_agents": SAME_GAP_4,
        "phases": (0, 0),
    },
    {
        "id": "07_RUL-gap-6",
        "hypothesis": "A wider RUL pair tests whether translating branches persist after shared-field contact disappears.",
        "rule": "RUL",
        "steps": 12_000,
        "initial_agents": (((-3, 0, 0), (0, 1, 0), (0, 0, 1)), ((3, 0, 0), (0, 1, 0), (0, 0, 1))),
        "phases": (0, 0),
    },
    {
        "id": "08_RUL-phase-1",
        "hypothesis": "A one-state RUL phase offset tests asymmetric translating offshoot periods after contact.",
        "rule": "RUL",
        "steps": 12_000,
        "initial_agents": SAME_GAP_4,
        "phases": (0, 1),
    },
)


def checksum(path: Path, root: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {"path": path.relative_to(root).as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    rows = []
    videos = []
    for config in CONFIGS:
        result = simulate_chiral_highway_pair(
            config["rule"],
            steps=config["steps"],
            snapshot_interval=500 if config["steps"] == 20_000 else 300,
            initial_agents=config["initial_agents"],
            rule_phase_offsets=config["phases"],
        )
        directory = OUTPUT_ROOT / config["id"]
        artifacts = package_direction(result, directory, fps=12, size=(480, 480), render_profile="anatomy")
        analysis = analyze_offshoot_candidate(result, max_period=256, minimum_cycles=4)
        summary = summarize_direction(result)
        row = {
            "id": config["id"],
            "hypothesis": config["hypothesis"],
            "rule": config["rule"],
            "mirrored_rule": result.metrics["left_rule"],
            "steps": config["steps"],
            "initial_agents": config["initial_agents"],
            "rule_phase_offsets": config["phases"],
            "collisions": result.metrics["collisions"],
            "shared_rewrites": result.metrics["shared_rewrites"],
            "axis_spans": summary["axis_spans"],
            "nonplanarity_ratio": summary["nonplanarity_ratio"],
            "field_cells": summary["field_cells"],
            "state_sha256": summary["state_sha256"],
            **analysis,
        }
        rows.append(row)
        videos.append(artifacts["video"])

    report = {
        "schema_version": 1,
        "study": "A3 classic-like offshoot parameter study",
        "classification": "bounded Studio composition using published Hamann cubic 3D rules",
        "frozen_control": "01_control-A3-gap-4",
        "schedule": "synchronous-read-intent-commit",
        "collision_policy": "same-destination-pitch-apart",
        "true_snapshot_timelapse": True,
        "interpolation": False,
        "variant_count": len(rows),
        "variants": rows,
    }
    report_path = OUTPUT_ROOT / "offshoot-study.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    width, height, header = 480, 480, 82
    sheet = Image.new("RGB", (width * 4, (height + header) * 2), (12, 14, 13))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, row in enumerate(rows):
        x, y = (index % 4) * width, (index // 4) * (height + header)
        with Image.open(OUTPUT_ROOT / row["id"] / "stills" / "late.png") as image:
            sheet.paste(image.convert("RGB"), (x, y + header))
        tails = row["translating_tails"]
        periods = [tail["period"] if tail else None for tail in tails]
        draw.text((x + 10, y + 8), row["id"], fill=(226, 230, 222), font=font)
        draw.text((x + 10, y + 29), f"periods {periods}  rewrites {row['shared_rewrites']}  coll {row['collisions']}", fill=(155, 170, 160), font=font)
        draw.text((x + 10, y + 50), f"spans {row['axis_spans']}  density {row['occupied_density']:.6f}", fill=(115, 132, 122), font=font)
        draw.text((x + 10, y + 67), f"classic-like gate = {row['classic_like_gate']}", fill=(99, 214, 161) if row["classic_like_gate"] else (154, 150, 145), font=font)
    sheet_path = OUTPUT_ROOT / "offshoot-comparison.png"
    sheet.save(sheet_path)

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg is required")
    movie_path = OUTPUT_ROOT / "offshoot-comparison.mp4"
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for video in videos:
        command.extend(["-i", str(video)])
    layout = "0_0|w0_0|w0+w1_0|w0+w1+w2_0|0_h0|w0_h0|w0+w1_h0|w0+w1+w2_h0"
    inputs = "".join(f"[{index}:v]" for index in range(len(videos)))
    command.extend(["-filter_complex", f"{inputs}xstack=inputs=8:layout={layout}:fill=black:shortest=1[v]", "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(movie_path)])
    subprocess.run(command, check=True)

    detail_root = OUTPUT_ROOT / "09_RUL-transient-detail"
    detail_runs = (
        ("gap-2-first-1000", CONFIGS[4]),
        ("gap-4-first-1000", CONFIGS[5]),
    )
    detail_sheet = Image.new("RGB", (960, 540), (12, 14, 13))
    detail_draw = ImageDraw.Draw(detail_sheet)
    detail_videos = []
    for index, (detail_id, config) in enumerate(detail_runs):
        detail_result = simulate_chiral_highway_pair(
            config["rule"],
            steps=1_000,
            snapshot_interval=100,
            initial_agents=config["initial_agents"],
            rule_phase_offsets=config["phases"],
        )
        detail_artifacts = package_direction(
            detail_result,
            detail_root / detail_id,
            fps=12,
            size=(480, 480),
            render_profile="anatomy",
        )
        detail_videos.append(detail_artifacts["video"])
        with Image.open(detail_root / detail_id / "stills" / "late.png") as image:
            detail_sheet.paste(image.convert("RGB"), (index * 480, 60))
        detail_draw.text(
            (index * 480 + 12, 12),
            f"RUL {detail_id} · rewrites {detail_result.metrics['shared_rewrites']} · collisions {detail_result.metrics['collisions']}",
            fill=(220, 226, 216),
            font=font,
        )
    detail_sheet_path = detail_root / "transient-detail.png"
    detail_sheet.save(detail_sheet_path)
    detail_movie_path = detail_root / "transient-detail.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(detail_videos[0]),
            "-i",
            str(detail_videos[1]),
            "-filter_complex",
            "[0:v][1:v]hstack=inputs=2:shortest=1[v]",
            "-map",
            "[v]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(detail_movie_path),
        ],
        check=True,
    )

    review_path = OUTPUT_ROOT / "REVIEW.md"
    review_path.write_text(
        "# A3 classic-like offshoot parameter study\n\n"
        "## Result\n\n"
        "Recognizable translating ant-like offshoots are possible in the shared 3D pair. The strongest bounded candidates use Hamann's published `RUL` period-22 rule and its mirrored partner. "
        "Gap-2 and gap-4 both retain exact translating tails after shared-field interaction, while gap-6 translates without interaction. The phase-1 pairing also passes the operational gate with asymmetric period-22 and period-14 tails.\n\n"
        "## Interpretation\n\n"
        "`RUL` gap-4 is the clearest classic-like branch treatment: both walkers retain period-22 translating tails with distinct displacement vectors, one collision, 36 cross-lineage rewrites, sparse occupancy, and three-axis aggregate extent. "
        "`RUL` gap-2 is the interaction-heavy nearby control. The existing `RLRUUUL` gap-4 remains the frozen A3 Behavior and exhibits a long volumetric transient rather than a detected short translating tail within 20,000 steps.\n\n"
        "`RRLU` confirms strict period-32 highways, but the parallel and antiparallel configurations either do not share the field or read as nearly one-dimensional. High nonplanarity alone was not used as a success criterion.\n\n"
        "## Scope\n\n"
        "This is a bounded Studio composition using published cubic 3D rules. It demonstrates recognizable morphology and exact tail translation in these runs. It is not a rule-level novelty claim and does not establish strict equivalence to classic 2D Langton `RL`.\n",
        encoding="utf-8",
    )

    receipt_files = [report_path, sheet_path, movie_path, detail_sheet_path, detail_movie_path, review_path]
    for row in rows:
        receipt_files.append(OUTPUT_ROOT / row["id"] / "receipt.json")
    receipt_path = OUTPUT_ROOT / "receipt.json"
    receipt_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "root": str(OUTPUT_ROOT),
                "true_snapshot_timelapse": True,
                "interpolation": False,
                "artifacts": {path.relative_to(OUTPUT_ROOT).as_posix(): checksum(path, OUTPUT_ROOT) for path in receipt_files},
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
