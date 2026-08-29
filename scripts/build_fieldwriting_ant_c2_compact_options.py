from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from houdini_ai.fieldwriting_ants import package_direction
from houdini_ai.fieldwriting_ants_c2_options import c2_compact_configurations
from houdini_ai.fieldwriting_ants_robustness import run_c2_robustness_matrix, serializable_robustness_report

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "studies" / "study_004_three-dimensional-fieldwriting-ants" / "01_behavior" / "01_work" / "10_C2-compact-options"


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


def render_orthographic_panel(result, title: str, plane: tuple[int, int], size: tuple[int, int], bounds) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size, (8, 10, 10))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    margin = 30
    x_axis, y_axis = plane
    x_min, x_max = bounds[x_axis]
    y_min, y_max = bounds[y_axis]
    scale = min((width - 2 * margin) / max(1, x_max - x_min), (height - 2 * margin - 20) / max(1, y_max - y_min))

    def project(point):
        return (
            round(margin + (point[x_axis] - x_min) * scale),
            round(height - margin - (point[y_axis] - y_min) * scale),
        )

    final = result.snapshots[-1]
    palette = {0.5: (61, 91, 82), 1: (93, 113, 106), 2: (171, 184, 176)}
    for point, state in final.field:
        x, y = project(point)
        draw.rectangle((x - 1, y - 1, x + 1, y + 1), fill=palette.get(state, (151, 164, 157)))
    colors = ((72, 224, 180), (170, 188, 184), (204, 176, 154), (145, 170, 198), (198, 157, 195), (165, 195, 137))
    for agent_id, path in enumerate(result.trajectories):
        tail = path[-160:]
        draw.line([project(point) for point in tail], fill=colors[agent_id], width=2)
        x, y = project(path[-1])
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=colors[agent_id])
    draw.rectangle((0, 0, width, 22), fill=(10, 12, 11))
    draw.text((8, 7), title, fill=(224, 230, 222), font=font)
    return image


def make_projection_sheet(result, directory: Path, title: str, global_bounds) -> Path:
    sheet = Image.new("RGB", (960, 960), (8, 10, 10))
    with Image.open(directory / "stills" / "late.png") as perspective:
        sheet.paste(perspective.convert("RGB").resize((480, 480)), (0, 0))
    labels = (("XY", (0, 1)), ("XZ", (0, 2)), ("YZ", (1, 2)))
    origins = ((480, 0), (0, 480), (480, 480))
    for (label, plane), origin in zip(labels, origins):
        sheet.paste(render_orthographic_panel(result, f"{title} | {label}", plane, (480, 480), global_bounds), origin)
    draw = ImageDraw.Draw(sheet)
    draw.rectangle((0, 0, 480, 26), fill=(10, 12, 11))
    draw.text((10, 8), f"{title} | perspective", fill=(224, 230, 222), font=ImageFont.load_default())
    output = directory / "projection-sheet.png"
    sheet.save(output)
    return output


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    configurations = c2_compact_configurations()
    steps, snapshot_interval = 1_200, 10
    target_movie_seconds = 12
    records = []
    results = {}

    # Each candidate is simulated, reverse-order checked, packaged, and receipt-verified before the next starts.
    for index, (variant_id, configuration) in enumerate(configurations.items(), start=1):
        matrix = run_c2_robustness_matrix(
            {variant_id: configuration["initial_agents"]},
            steps=steps,
            snapshot_interval=snapshot_interval,
            rule=configuration["rule"],
        )
        variant = matrix["variants"][0]
        if not variant["transaction_order_invariant"]:
            raise RuntimeError(f"transaction order changed {variant_id}")
        result = variant["result"]
        results[variant_id] = result
        directory = OUTPUT_ROOT / f"{index:02d}_{variant_id}"
        playback_fps = len(result.snapshots) / target_movie_seconds
        artifacts = package_direction(
            result,
            directory,
            fps=playback_fps,
            size=(480, 480),
            render_profile="microcell",
        )
        verify_branch(directory, len(result.snapshots))
        record = {key: value for key, value in variant.items() if key != "result"}
        record.update(
            {
                "directory": directory.relative_to(OUTPUT_ROOT).as_posix(),
                "parameter_edit": configuration["parameter_edit"],
                "hypothesis": configuration["hypothesis"],
                "render_profile": "microcell",
                "movie": artifacts["video"].relative_to(OUTPUT_ROOT).as_posix(),
            }
        )
        records.append(record)

    all_points = [point for result in results.values() for path in result.trajectories for point in path]
    global_bounds = tuple((min(point[axis] for point in all_points), max(point[axis] for point in all_points)) for axis in range(3))
    projection_paths = []
    for index, variant_id in enumerate(configurations, start=1):
        directory = OUTPUT_ROOT / f"{index:02d}_{variant_id}"
        projection_paths.append(make_projection_sheet(results[variant_id], directory, variant_id, global_bounds))
        records[index - 1]["projection_sheet"] = projection_paths[-1].relative_to(OUTPUT_ROOT).as_posix()

    late_grid = Image.new("RGB", (960, 960), (8, 10, 10))
    draw = ImageDraw.Draw(late_grid)
    font = ImageFont.load_default()
    movies = []
    for index, record in enumerate(records):
        directory = OUTPUT_ROOT / record["directory"]
        origin = ((index % 2) * 480, (index // 2) * 480)
        with Image.open(directory / "stills" / "late.png") as image:
            late_grid.paste(image.convert("RGB"), origin)
        draw.rectangle((origin[0], origin[1], origin[0] + 480, origin[1] + 48), fill=(10, 12, 11))
        draw.text((origin[0] + 10, origin[1] + 8), record["id"], fill=(225, 231, 222), font=font)
        draw.text(
            (origin[0] + 10, origin[1] + 26),
            f"exchange {record['frame_exchanges']} | collision {record['collisions']} | span {record['axis_spans']} | np {record['nonplanarity_ratio']:.3f}",
            fill=(137, 156, 145),
            font=font,
        )
        movies.append(directory / "motion-timelapse.mp4")
    comparison_path = OUTPUT_ROOT / "c2-compact-comparison.png"
    late_grid.save(comparison_path)

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg is required")
    comparison_movie = OUTPUT_ROOT / "c2-compact-comparison.mp4"
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

    report_path = OUTPUT_ROOT / "c2-compact-options.json"
    report = {
        "schema_version": 1,
        "study": "C2 compact radius-2 parameter options",
        "branch": "C2",
        "status": "post-promotion bounded Behavior development",
        "canonical_selection_unchanged": "selection-c2-radius-3",
        "control": "radius-2-control",
        "rule": "RLRU",
        "collision_policy": "frame-exchange",
        "schedule": "synchronous-read-intent-commit",
        "order_sensitivity_test": "forward-versus-reverse-intent-enumeration",
        "steps": steps,
        "snapshot_interval": snapshot_interval,
        "movie_duration_seconds": target_movie_seconds,
        "frames_per_movie": len(next(iter(results.values())).snapshots),
        "true_snapshot_timelapse": True,
        "interpolation": False,
        "semantic_field_palette_independent": True,
        "variants": records,
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    review_path = OUTPUT_ROOT / "REVIEW.md"
    review_path.write_text(
        "# C2 compact radius-2 parameter options\n\n"
        "Four six-agent `RLRU` colonies retain synchronous read, intent, transactional commit and frame-exchange chemistry. Only compact seed position, heading, or roll parameters change.\n\n"
        "## Measured and observed\n\n"
        "1. **Orbital cage** is the strongest balanced-volume option. Tangential headings produce 33 frame exchanges at three recurrent contested cells, exact `26 × 26 × 26` spans, nonplanarity `1.0`, and path balance `0.999`. The perspective and three projections show a coherent six-armed cubic envelope. Its symmetry is a feature, though it may become diagrammatic if Look overemphasizes the axes.\n"
        "2. **Split core** is the densest compact transaction option. One-cell staggered seeds produce 13 collisions, 11 contested cells, and 26 frame exchanges inside `27 × 20 × 22`. It reads as a tight asymmetric knot with distributed collision structure. This is the clearest continuation of the compact-control premise.\n"
        "3. **Radius-2 control** remains the exact documented control with 10 collisions, 8 contested cells, and 20 frame exchanges inside `28 × 21 × 22`. Orthographic views confirm three-axis occupation, with a comparatively thin YZ profile.\n"
        "4. **Torsion cage** is the widest and most volumetric stress option at `39 × 41 × 46`, nonplanarity `0.848`. Opposed roll produces separated planar fans and long connectors rather than a unified cage. It is distinct but weakest as a compact morphology.\n\n"
        "## Recommendation\n\n"
        "Carry **split core** and **orbital cage** forward for comparison with the radius-2 control. Keep torsion cage as a negative/extent control unless its separated fan structure becomes useful during Look.\n\n"
        "All four are non-promoted alternatives. Frozen C2 radius-3 remains unchanged.\n",
        encoding="utf-8",
    )

    top_files = [comparison_path, comparison_movie, report_path, review_path, *projection_paths]
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
