from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from houdini_ai.fieldwriting_ants import package_direction
from houdini_ai.fieldwriting_ants_c2_options import (
    c2_compact_configurations,
    c2_prewarmed_configurations,
    prewarmed_snapshot_window,
)
from houdini_ai.fieldwriting_ants_robustness import run_c2_robustness_matrix
from build_fieldwriting_ant_c2_compact_options import make_projection_sheet

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "studies" / "study_004_three-dimensional-fieldwriting-ants" / "01_behavior" / "01_work" / "11_C2-prewarmed-options"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_branch(directory: Path, expected_frames: int) -> None:
    receipt = json.loads((directory / "receipt.json").read_text(encoding="utf-8"))
    if len(receipt["frames"]) != expected_frames:
        raise RuntimeError(f"wrong frame count in {directory}")
    for record in list(receipt["frames"]) + list(receipt["artifacts"].values()):
        path = directory / record["path"]
        if not path.is_file() or path.stat().st_size != record["bytes"] or sha256(path) != record["sha256"]:
            raise RuntimeError(f"failed receipt check: {path}")


def build_variant(variant_id, configuration, *, total_steps, snapshot_interval, prewarm_steps, directory):
    matrix = run_c2_robustness_matrix(
        {variant_id: configuration["initial_agents"]},
        steps=total_steps,
        snapshot_interval=snapshot_interval,
        rule="RLRU",
    )
    record = matrix["variants"][0]
    if not record["transaction_order_invariant"]:
        raise RuntimeError(f"transaction order changed {variant_id}")
    full_result = record["result"]
    review_result = (
        prewarmed_snapshot_window(full_result, start_step=prewarm_steps)
        if prewarm_steps
        else full_result
    )
    if len(review_result.snapshots) != 121:
        raise RuntimeError(f"expected 121 true snapshots for {variant_id}")
    artifacts = package_direction(
        review_result,
        directory,
        fps=len(review_result.snapshots) / 12,
        size=(480, 480),
        render_profile="microcell",
    )
    verify_branch(directory, 121)
    serializable = {key: value for key, value in record.items() if key != "result"}
    serializable.update(
        {
            "directory": directory.relative_to(OUTPUT_ROOT).as_posix(),
            "parameter_edit": configuration["parameter_edit"],
            "hypothesis": configuration["hypothesis"],
            "total_simulation_steps": total_steps,
            "prewarm_steps": prewarm_steps,
            "capture_start_step": prewarm_steps,
            "capture_end_step": total_steps,
            "captured_simulation_steps": total_steps - prewarm_steps,
            "snapshot_interval": snapshot_interval,
            "captured_true_snapshots": len(review_result.snapshots),
            "movie_duration_seconds": 12,
            "movie": artifacts["video"].relative_to(OUTPUT_ROOT).as_posix(),
        }
    )
    return review_result, serializable


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    compact = c2_compact_configurations()
    prewarmed = c2_prewarmed_configurations()
    specifications = (
        ("radius-2-control", compact["radius-2-control"], 1_200, 10, 0),
        ("torsion-cage-prewarmed", prewarmed["torsion-cage"], 2_400, 15, 600),
        ("torsion-split-prewarmed", prewarmed["torsion-split"], 2_400, 15, 600),
        ("orbital-shear-prewarmed", prewarmed["orbital-shear"], 2_400, 15, 600),
    )
    results = {}
    records = []
    movies = []

    # Sequential execution: each branch passes reverse-order and receipt checks before the next starts.
    for index, (display_id, configuration, total_steps, interval, prewarm) in enumerate(specifications, start=1):
        simulation_id = display_id.replace("-prewarmed", "")
        directory = OUTPUT_ROOT / f"{index:02d}_{display_id}"
        result, record = build_variant(
            simulation_id,
            configuration,
            total_steps=total_steps,
            snapshot_interval=interval,
            prewarm_steps=prewarm,
            directory=directory,
        )
        record["id"] = display_id
        record["simulation_id"] = simulation_id
        record["playback_step_rate_relative_to_control"] = record["captured_simulation_steps"] / 1_200
        results[display_id] = result
        records.append(record)
        movies.append(directory / "motion-timelapse.mp4")

    all_points = [point for result in results.values() for path in result.trajectories for point in path]
    global_bounds = tuple((min(point[axis] for point in all_points), max(point[axis] for point in all_points)) for axis in range(3))
    projection_paths = []
    for index, (display_id, *_rest) in enumerate(specifications, start=1):
        directory = OUTPUT_ROOT / f"{index:02d}_{display_id}"
        path = make_projection_sheet(results[display_id], directory, display_id, global_bounds)
        projection_paths.append(path)
        records[index - 1]["projection_sheet"] = path.relative_to(OUTPUT_ROOT).as_posix()

    comparison = Image.new("RGB", (960, 960), (8, 10, 10))
    draw = ImageDraw.Draw(comparison)
    font = ImageFont.load_default()
    for index, record in enumerate(records):
        directory = OUTPUT_ROOT / record["directory"]
        origin = ((index % 2) * 480, (index // 2) * 480)
        with Image.open(directory / "stills" / "late.png") as image:
            comparison.paste(image.convert("RGB"), origin)
        draw.rectangle((origin[0], origin[1], origin[0] + 480, origin[1] + 52), fill=(10, 12, 11))
        draw.text((origin[0] + 10, origin[1] + 8), record["id"], fill=(225, 231, 222), font=font)
        draw.text(
            (origin[0] + 10, origin[1] + 26),
            f"window {record['capture_start_step']}..{record['capture_end_step']} | {record['captured_simulation_steps']} steps/12s | exchange {record['frame_exchanges']}",
            fill=(137, 156, 145),
            font=font,
        )
        draw.text(
            (origin[0] + 10, origin[1] + 39),
            f"collision {record['collisions']} | span {record['axis_spans']} | np {record['nonplanarity_ratio']:.3f}",
            fill=(137, 156, 145),
            font=font,
        )
    comparison_still = OUTPUT_ROOT / "c2-prewarmed-comparison.png"
    comparison.save(comparison_still)

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg is required")
    comparison_movie = OUTPUT_ROOT / "c2-prewarmed-comparison.mp4"
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for movie in movies:
        command.extend(["-i", str(movie)])
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
            str(comparison_movie),
        ]
    )
    subprocess.run(command, check=True)

    report_path = OUTPUT_ROOT / "c2-prewarmed-options.json"
    report_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "study": "C2 prewarmed compact options",
                "branch": "C2",
                "status": "post-promotion bounded Behavior development",
                "canonical_selection_unchanged": "selection-c2-radius-3",
                "retained_working_reference": "radius-2-control",
                "rule": "RLRU",
                "collision_policy": "frame-exchange",
                "schedule": "synchronous-read-intent-commit",
                "order_sensitivity_test": "forward-versus-reverse-intent-enumeration",
                "movie_duration_seconds": 12,
                "captured_true_snapshots_per_movie": 121,
                "prewarmed_candidate_steps": 600,
                "prewarmed_capture_steps": 1_800,
                "prewarmed_step_rate_relative_to_control": 1.5,
                "interpolation": False,
                "variants": records,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    review_path = OUTPUT_ROOT / "REVIEW.md"
    review_path.write_text(
        "# C2 prewarmed compact options\n\n"
        "The radius-2 control is retained unchanged at steps 0 through 1,200. The other three movies begin from a hidden 600-step prewarm and capture steps 600 through 2,400. Each 12-second candidate therefore shows 1,800 true simulation steps, 1.5 times the control step rate. All movies contain 121 true snapshots without interpolation.\n\n"
        "## Measured and observed\n\n"
        "1. `torsion-split-prewarmed` is the strongest compact continuation. Combining opposed rolls with the one-cell stagger consolidates the long torsion rays into a dense asymmetric `31 × 23 × 33` structure with 16 frame exchanges. Perspective shows several articulated lobes while common-scale orthographic views retain a compact nucleus.\n"
        "2. `torsion-cage-prewarmed` matures into a clear central hub with three long translating arms rather than the earlier separated local fans. It reaches `102 × 76 × 112` with 18 frame exchanges. This is coherent but strongly anisotropic and no longer compact.\n"
        "3. `orbital-shear-prewarmed` produces a balanced `66 × 66 × 66` extent and nonplanarity `1.0`, but most growth resolves into one long bundled corridor with a terminal interaction mass. It is reproducible and volumetric by span, though weaker as a collision tissue.\n\n"
        "The retained `radius-2-control` remains the exact compact reference with state hash `992fc62e45e85eec6b383735f79357fb44be42609df9d1e5865fff35ab7d2525`.\n\n"
        "All candidates remain non-promoted working alternatives. Frozen C2 radius-3 is unchanged.\n",
        encoding="utf-8",
    )

    top_files = [comparison_still, comparison_movie, report_path, review_path, *projection_paths]
    receipt_path = OUTPUT_ROOT / "receipt.json"
    receipt_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "true_snapshot_timelapse": True,
                "interpolation": False,
                "artifacts": {
                    path.relative_to(OUTPUT_ROOT).as_posix(): {
                        "path": path.relative_to(OUTPUT_ROOT).as_posix(),
                        "bytes": path.stat().st_size,
                        "sha256": sha256(path),
                    }
                    for path in top_files
                },
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
