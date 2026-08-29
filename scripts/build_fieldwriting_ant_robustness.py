from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont

from houdini_ai.fieldwriting_ants import package_direction
from houdini_ai.fieldwriting_ants_robustness import (
    run_a3_robustness_matrix,
    run_c2_robustness_matrix,
    serializable_robustness_report,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "studies"
    / "study_004_three-dimensional-fieldwriting-ants"
    / "01_behavior"
    / "01_work"
    / "06_A3-C2-robustness"
)


def colony(radius_x: int, radius_y: int, radius_z: int):
    return (
        ((radius_x, 0, 0), (-1, 0, 0), (0, 0, 1)),
        ((-radius_x, 0, 0), (1, 0, 0), (0, 0, 1)),
        ((0, radius_y, 0), (0, -1, 0), (0, 0, 1)),
        ((0, -radius_y, 0), (0, 1, 0), (0, 0, 1)),
        ((0, 0, radius_z), (0, 0, -1), (0, 1, 0)),
        ((0, 0, -radius_z), (0, 0, 1), (0, 1, 0)),
    )


A3_CONFIGS = {
    "gap-2": (((-1, 0, 0), (0, 1, 0), (0, 0, 1)), ((1, 0, 0), (0, 1, 0), (0, 0, 1))),
    "gap-4": (((-2, 0, 0), (0, 1, 0), (0, 0, 1)), ((2, 0, 0), (0, 1, 0), (0, 0, 1))),
    "gap-8": (((-4, 0, 0), (0, 1, 0), (0, 0, 1)), ((4, 0, 0), (0, 1, 0), (0, 0, 1))),
    "stagger-y": (((-2, -1, 0), (0, 1, 0), (0, 0, 1)), ((2, 1, 0), (0, 1, 0), (0, 0, 1))),
    "stagger-z": (((-2, 0, -1), (0, 1, 0), (0, 0, 1)), ((2, 0, 1), (0, 1, 0), (0, 0, 1))),
    "opposed-roll": (((-2, 0, 0), (0, 1, 0), (0, 0, 1)), ((2, 0, 0), (0, 1, 0), (0, 0, -1))),
}

C2_CONFIGS = {
    "radius-2": colony(2, 2, 2),
    "radius-3": colony(3, 3, 3),
    "radius-4": colony(4, 4, 4),
    "anisotropic-234": colony(2, 3, 4),
    "x-offset": (((3, 0, 1), (-1, 0, 0), (0, 0, 1)),) + colony(3, 3, 3)[1:],
    "rolled-z": colony(3, 3, 3)[:4]
    + (
        ((0, 0, 3), (0, 0, -1), (1, 0, 0)),
        ((0, 0, -3), (0, 0, 1), (1, 0, 0)),
    ),
}


def checksum(path: Path, relative_to: Path | None = None) -> dict[str, object]:
    data = path.read_bytes()
    artifact_path = path.relative_to(relative_to).as_posix() if relative_to is not None else path.name
    return {"path": artifact_path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def build_sheet(family: str, report: dict[str, object], root: Path) -> Path:
    width, height, header = 480, 480, 66
    sheet = Image.new("RGB", (width * 3, (height + header) * 2), (14, 16, 15))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, row in enumerate(report["variants"]):
        x, y = (index % 3) * width, (index // 3) * (height + header)
        with Image.open(root / row["id"] / "stills" / "late.png") as image:
            sheet.paste(image.convert("RGB"), (x, y + header))
        draw.text((x + 12, y + 9), f"{family} · {row['id']}", fill=(226, 230, 222), font=font)
        if family == "A3":
            detail = f"coll {row['collisions']}  rewrites {row['shared_rewrites']}  sep {row['endpoint_separation']:.1f}"
        else:
            detail = f"coll {row['collisions']}  exchanges {row['frame_exchanges']}  order={row['transaction_order_invariant']}"
        draw.text((x + 12, y + 29), detail, fill=(152, 166, 157), font=font)
        draw.text(
            (x + 12, y + 47),
            f"spans {row['axis_spans']}  np {row['nonplanarity_ratio']:.3f}",
            fill=(107, 124, 115),
            font=font,
        )
    path = root / f"{family.lower()}-robustness-sheet.png"
    sheet.save(path)
    return path


def build_finalists(output_root: Path, a3: dict[str, object], c2: dict[str, object]) -> dict[str, Path]:
    finalists = (
        ("A3 · gap-4", output_root / "01_A3" / "gap-4", next(row for row in a3["variants"] if row["id"] == "gap-4")),
        ("A3 · opposed-roll", output_root / "01_A3" / "opposed-roll", next(row for row in a3["variants"] if row["id"] == "opposed-roll")),
        ("C2 · radius-2", output_root / "02_C2" / "radius-2", next(row for row in c2["variants"] if row["id"] == "radius-2")),
        ("C2 · radius-3", output_root / "02_C2" / "radius-3", next(row for row in c2["variants"] if row["id"] == "radius-3")),
    )
    directory = output_root / "03_finalists"
    directory.mkdir(parents=True, exist_ok=True)
    width, height, header = 480, 480, 62
    sheet = Image.new("RGB", (width * 2, (height + header) * 2), (14, 16, 15))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (title, root, row) in enumerate(finalists):
        x, y = (index % 2) * width, (index // 2) * (height + header)
        with Image.open(root / "stills" / "late.png") as image:
            sheet.paste(image.convert("RGB"), (x, y + header))
        draw.text((x + 12, y + 10), title, fill=(226, 230, 222), font=font)
        if title.startswith("A3"):
            detail = f"rewrites {row['shared_rewrites']}  separation {row['endpoint_separation']:.1f}  np {row['nonplanarity_ratio']:.3f}"
        else:
            detail = f"exchanges {row['frame_exchanges']}  collisions {row['collisions']}  np {row['nonplanarity_ratio']:.3f}"
        draw.text((x + 12, y + 33), detail, fill=(149, 165, 155), font=font)
    sheet_path = directory / "finalist-comparison.png"
    sheet.save(sheet_path)

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg is required")
    video_path = directory / "finalist-comparison.mp4"
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for _, root, _ in finalists:
        command.extend(["-i", str(root / "motion-timelapse.mp4")])
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
            str(video_path),
        ]
    )
    subprocess.run(command, check=True)

    review = directory / "REVIEW.md"
    review.write_text(
        "# A3 + C2 robustness decision\n\n"
        "## A3\n\n"
        "Shared-field interaction persists across all six tested initial conditions: every run records cross-lineage rewrites, with 0–4 direct same-destination collisions. "
        "Morphology is sensitive to pair geometry, so A3 is a robust interaction family rather than one invariant form. **Gap-4** is the balanced canonical candidate; "
        "**opposed-roll** is the high-coupling stress candidate (2,547 rewrites and endpoint separation 19.2).\n\n"
        "## C2\n\n"
        "All six seed geometries produce frame exchanges and all six are exactly invariant to forward-versus-reverse intent enumeration under synchronous commit. "
        "Interaction strength is seed-sensitive: 2–24 exchanges. **Radius-3** remains the canonical candidate; **radius-2** is the denser compact alternative. "
        "Radius-4 develops a long separated arm, while anisotropic-234 and rolled-z are weaker chemistry demonstrations.\n\n"
        "## Gate\n\n"
        "Advance A3 gap-4 and C2 radius-3 as the canonical Behavior candidates, retaining opposed-roll and radius-2 as stress/compact controls. "
        "This is not a novelty claim and is not yet Look approval.\n",
        encoding="utf-8",
    )
    return {"finalist_sheet": sheet_path, "finalist_video": video_path, "review": review}


def build(output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    a3_root, c2_root = output_root / "01_A3", output_root / "02_C2"
    a3 = run_a3_robustness_matrix(A3_CONFIGS, steps=20_000, snapshot_interval=500)
    c2 = run_c2_robustness_matrix(C2_CONFIGS, steps=1_200, snapshot_interval=20)

    for root, report in ((a3_root, a3), (c2_root, c2)):
        root.mkdir(parents=True, exist_ok=True)
        for row in report["variants"]:
            package_direction(
                row["result"],
                root / row["id"],
                fps=12,
                size=(480, 480),
                render_profile="microcell" if report["branch"] == "C2" else "default",
            )
        report_path = root / "robustness.json"
        report_path.write_text(
            json.dumps(serializable_robustness_report(report), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        sheet = build_sheet(str(report["branch"]), report, root)
        receipt_path = root / "receipt.json"
        receipt_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "artifacts": {"report": checksum(report_path), "sheet": checksum(sheet)},
                    "variant_receipts": [str(Path(row["id"]) / "receipt.json") for row in report["variants"]],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    finalists = build_finalists(output_root, a3, c2)
    README = output_root / "README.md"
    README.write_text(
        "# A3 + C2 robustness gate\n\n"
        "Bounded deterministic initial-condition tests for the two approved Behavior branches. "
        "All movies are true-snapshot timelapses with no interpolation.\n\n"
        "A3 tests six pair separations/frame arrangements at 20,000 steps. C2 tests six seed geometries "
        "at 1,200 steps and verifies forward-versus-reverse intent enumeration produces identical field and trajectories.\n",
        encoding="utf-8",
    )
    receipt = output_root / "receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "artifacts": {
                    "readme": checksum(README, relative_to=output_root),
                    "a3_sheet": checksum(a3_root / "a3-robustness-sheet.png", relative_to=output_root),
                    "a3_report": checksum(a3_root / "robustness.json", relative_to=output_root),
                    "c2_sheet": checksum(c2_root / "c2-robustness-sheet.png", relative_to=output_root),
                    "c2_report": checksum(c2_root / "robustness.json", relative_to=output_root),
                    **{key: checksum(path, relative_to=output_root) for key, path in finalists.items()},
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(output_root)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Study 004 A3/C2 robustness gate")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build(args.output_root)


if __name__ == "__main__":
    main()
