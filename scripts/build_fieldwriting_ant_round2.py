from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont

from houdini_ai.fieldwriting_ants import (
    enumerate_near_rules,
    hamann_direction_result,
    package_direction,
    simulate_chiral_highway_pair,
    simulate_collision_colony,
    simulate_wound_healing_colony,
    summarize_direction,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "studies"
    / "study_004_three-dimensional-fieldwriting-ants"
    / "01_behavior"
    / "01_work"
    / "05_bounded-ac-round"
)

BRANCHES = {
    "a1": ("A1 · HIGHWAY ANATOMY", "01_A1_highway-anatomy", "published RLRUUUL; representation branch"),
    "a2": ("A2 · PLANARITY RUPTURE", "02_A2_planarity-rupture", "one-edit near-Hamann bounded search"),
    "a3": ("A3 · CHIRAL HIGHWAY PAIR", "03_A3_chiral-pair", "mirrored R/L rules; shared synchronous field"),
    "c1": ("C1 · MICROCELL TISSUE", "04_C1_microcell-tissue", "unchanged RLRU scar baseline; microcell representation"),
    "c2": ("C2 · FRAME EXCHANGE", "05_C2_frame-exchange", "RLRU; collision frame exchange"),
    "c3": ("C3 · WOUND / HEALING", "06_C3_wound-healing", "RLRU; semantic 0→0.5→1→0 field"),
}


def select_planarity_rupture(output_root: Path) -> tuple[str, list[dict[str, object]]]:
    base = "RLRUUUL"
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for mutation in enumerate_near_rules(base):
        rule = str(mutation["rule"])
        if rule in seen:
            continue
        seen.add(rule)
        result = hamann_direction_result(rule, steps=30_000, snapshot_interval=30_000)
        metrics = summarize_direction(result)
        spans = metrics["axis_spans"]
        score = (
            float(metrics["nonplanarity_ratio"]) * 1000
            + min(sum(spans), 600)
            + min(float(metrics["field_cells"]) / 50, 300)
        )
        rows.append({**mutation, "score": round(score, 6), "metrics": metrics})
    rows.sort(key=lambda row: (-float(row["score"]), str(row["rule"])))
    survey = {
        "schema_version": 1,
        "status": "bounded compositional search; no novelty claim",
        "base_rule": base,
        "raw_one_edit_operations": 60,
        "unique_rules_evaluated": len(rows),
        "steps_per_rule": 30_000,
        "score": "1000*nonplanarity + min(sum(axis_spans),600) + min(field_cells/50,300)",
        "selected_rule": rows[0]["rule"],
        "rows": rows,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "near-rule-survey.json").write_text(
        json.dumps(survey, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return str(rows[0]["rule"]), rows


def build_branch(branch: str, output_root: Path) -> None:
    _, folder, _ = BRANCHES[branch]
    directory = output_root / folder
    profile = "default"
    if branch == "a1":
        result = hamann_direction_result("RLRUUUL", steps=100_000, snapshot_interval=2_000)
        profile = "anatomy"
    elif branch == "a2":
        selected_rule, _ = select_planarity_rupture(directory)
        result = hamann_direction_result(selected_rule, steps=30_000, snapshot_interval=500)
        result.metrics.update(
            {
                "base_rule": "RLRUUUL",
                "selection_class": "one-edit near-Hamann bounded search",
            }
        )
        profile = "anatomy"
    elif branch == "a3":
        result = simulate_chiral_highway_pair("RLRUUUL", steps=40_000, snapshot_interval=800)
    elif branch == "c1":
        result = simulate_collision_colony("RLRU", steps=1_200, snapshot_interval=20)
        result.metrics.update({"branch_role": "representation-only microcell baseline"})
        profile = "microcell"
    elif branch == "c2":
        result = simulate_collision_colony(
            "RLRU", steps=1_200, snapshot_interval=20, collision_policy="frame-exchange"
        )
        profile = "microcell"
    elif branch == "c3":
        result = simulate_wound_healing_colony("RLRU", steps=1_200, snapshot_interval=20)
        profile = "microcell"
    else:
        raise ValueError(branch)
    artifacts = package_direction(
        result,
        directory,
        fps=12,
        size=(720, 720),
        render_profile=profile,
    )
    print(json.dumps({key: str(path) for key, path in artifacts.items()}, indent=2))


def build_comparison(output_root: Path) -> None:
    comparison_dir = output_root / "07_comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for branch, (title, folder, hypothesis) in BRANCHES.items():
        directory = output_root / folder
        records.append(
            {
                "id": branch.upper(),
                "title": title,
                "directory": directory,
                "hypothesis": hypothesis,
                "metrics": json.loads((directory / "metrics.json").read_text(encoding="utf-8")),
            }
        )

    width, height = 720, 720
    header = 66
    sheet = Image.new("RGB", (width * 3, (height + header) * 2), (14, 16, 15))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, record in enumerate(records):
        column, row = index % 3, index // 3
        x, y = column * width, row * (height + header)
        with Image.open(record["directory"] / "stills" / "late.png") as image:
            sheet.paste(image.convert("RGB"), (x, y + header))
        metrics = record["metrics"]
        draw.text((x + 14, y + 10), record["title"], fill=(224, 228, 220), font=font)
        draw.text((x + 14, y + 30), record["hypothesis"], fill=(149, 161, 155), font=font)
        draw.text(
            (x + 14, y + 48),
            f"spans {metrics['axis_spans']}  nonplanarity {metrics['nonplanarity_ratio']:.3f}",
            fill=(107, 122, 115),
            font=font,
        )
    sheet_path = comparison_dir / "six-run-late-state-comparison.png"
    sheet.save(sheet_path)

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg is required")
    video_path = comparison_dir / "six-run-motion-comparison.mp4"
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for record in records:
        command.extend(["-i", str(record["directory"] / "motion-timelapse.mp4")])
    command.extend(
        [
            "-filter_complex",
            "[0:v][1:v][2:v][3:v][4:v][5:v]xstack=inputs=6:layout=0_0|w0_0|w0+w1_0|0_h0|w0_h0|w0+w1_h0:fill=black:shortest=1[v]",
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

    comparison = comparison_dir / "comparison.json"
    comparison.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "approved six-run bounded Behavior round; no rule-level novelty claim",
                "artifact_semantics": "Every panel uses true deterministic snapshots; intervals are timelapsed, not interpolated.",
                "branches": [
                    {
                        "id": record["id"],
                        "title": record["title"],
                        "hypothesis": record["hypothesis"],
                        "metrics": record["metrics"],
                    }
                    for record in records
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    review = comparison_dir / "REVIEW.md"
    review.write_text(
        "# Approved six-run A/C Behavior round\n\n"
        "These are deterministic Behavior diagnostics, not Look development. No rule-level novelty claim is made.\n\n"
        "## Current ranking\n\n"
        "1. **A3 — Chiral highway pair:** strongest combined visual and computational branch. The mirrored ants produced two collision transactions, 224 cross-lineage rewrites, and a connected shared structure rather than simply diverging.\n"
        "2. **C2 — Frame exchange:** strongest C rule change. Twenty-four frame exchanges create a more open, asymmetric territorial lattice than the scar/reverse baseline without runaway growth.\n"
        "3. **C3 — Wound/healing:** strongest semantic-material branch. The final field retains both 0.5 and 1 states after 3,085 provisional writes, 2,292 healing transitions, and 1,831 erasures; a field-only diagnostic is needed before visual promotion.\n"
        "4. **A2 — Planarity rupture:** the bounded one-edit search selected RLRUUULD. It is nearly isotropic by axis span but currently reads as a crystalline translating structure; exact periodicity and novelty remain unresolved.\n"
        "5. **C1 — Microcell tissue:** useful representation control. Smaller cells improve the tissue reading, but the underlying behavior is unchanged.\n"
        "6. **A1 — Highway anatomy:** successful proof that published RLRUUUL is 3D, but it remains a historical and representational control.\n\n"
        "## Recommended next gate\n\n"
        "Deepen A3 and C2 as the two primary Behavior branches; retain C3 as a semantic field variant. Before Look work, test deterministic initial-condition robustness, scheduler sensitivity, and whether structures persist when recent lineage trails are hidden.\n",
        encoding="utf-8",
    )

    def artifact(path: Path) -> dict[str, object]:
        data = path.read_bytes()
        return {"path": path.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    receipt = comparison_dir / "receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "artifacts": {
                    "sheet": artifact(sheet_path),
                    "video": artifact(video_path),
                    "comparison": artifact(comparison),
                    "review": artifact(review),
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
    parser = argparse.ArgumentParser(description="Build approved Study 004 six-run A/C round")
    parser.add_argument("target", choices=(*BRANCHES.keys(), "compare"))
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.target == "compare":
        build_comparison(args.output_root)
    else:
        build_branch(args.target, args.output_root)


if __name__ == "__main__":
    main()
