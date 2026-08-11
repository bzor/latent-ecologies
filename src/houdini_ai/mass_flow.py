from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw, ImageFilter

from .doctor import discover_tools
from .jobs import Job, job_status, set_stage_state


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_mass_flow_metrics(path: Path, config: Mapping[str, Any]) -> dict[str, Any]:
    try:
        metrics = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"mass-flow metrics are unreadable: {path}: {exc}") from exc
    study = config.get("study", config)
    simulation = study["simulation"]
    system = simulation["rule_genome"]["system"]
    if metrics.get("agent_count") != system["agent_count"]:
        raise RuntimeError("mass-flow metrics report the wrong population")
    if metrics.get("frame_start") != simulation["frame_start"]:
        raise RuntimeError("mass-flow metrics start at the wrong frame")
    if metrics.get("frame_end") > simulation["frame_end"]:
        raise RuntimeError("mass-flow metrics extend beyond the configured range")
    checkpoints = metrics.get("checkpoints", [])
    if not checkpoints or checkpoints[0].get("frame") != simulation["frame_start"]:
        raise RuntimeError("mass-flow metrics have no valid initial checkpoint")
    half_width = system["domain_width"] * 0.5
    half_height = system["domain_height"] * 0.5
    half_depth = system.get("domain_depth", 0.0) * 0.5
    for checkpoint in checkpoints:
        if checkpoint.get("agent_count") != system["agent_count"]:
            raise RuntimeError(f"checkpoint {checkpoint.get('frame')} lost agents")
        bounds = checkpoint.get("bounds", [])
        max_x = bounds[3] if len(bounds) == 6 else bounds[2] if len(bounds) == 4 else float("inf")
        max_y = bounds[4] if len(bounds) == 6 else bounds[3] if len(bounds) == 4 else float("inf")
        if len(bounds) not in (4, 6) or bounds[0] < -half_width - 1e-3 or max_x > half_width + 1e-3:
            raise RuntimeError(f"checkpoint {checkpoint.get('frame')} escaped horizontal bounds")
        if bounds[1] < -half_height - 1e-3 or max_y > half_height + 1e-3:
            raise RuntimeError(f"checkpoint {checkpoint.get('frame')} escaped vertical bounds")
        if len(bounds) == 6 and (bounds[2] < -half_depth - 1e-3 or bounds[5] > half_depth + 1e-3):
            raise RuntimeError(f"checkpoint {checkpoint.get('frame')} escaped depth bounds")
        if checkpoint.get("max_speed", 0) > system["max_speed"] + 1e-3:
            raise RuntimeError(f"checkpoint {checkpoint.get('frame')} exceeded maximum speed")
    return metrics


def determinism_signature(metrics: Mapping[str, Any]) -> str:
    stable = {
        "agent_count": metrics["agent_count"],
        "frame_start": metrics["frame_start"],
        "frame_end": metrics["frame_end"],
        "state_sha256": metrics["state_sha256"],
        "checkpoints": [
            {
                key: round(value, 6) if isinstance(value, float) else
                [round(item, 6) for item in value] if isinstance(value, list) else value
                for key, value in checkpoint.items() if key != "elapsed_seconds"
            }
            for checkpoint in metrics["checkpoints"]
        ],
    }
    return hashlib.sha256(json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def materially_equivalent_metrics(a: Mapping[str, Any], b: Mapping[str, Any], tolerance: float = 1e-4) -> bool:
    for key in ("agent_count", "frame_start", "frame_end", "seed"):
        if a.get(key) != b.get(key):
            return False
    checkpoints_a, checkpoints_b = a.get("checkpoints", []), b.get("checkpoints", [])
    if len(checkpoints_a) != len(checkpoints_b):
        return False
    for left, right in zip(checkpoints_a, checkpoints_b):
        for key in ("frame", "agent_count"):
            if left.get(key) != right.get(key):
                return False
        for key in ("mean_speed", "max_speed"):
            if abs(float(left[key]) - float(right[key])) > tolerance:
                return False
        if len(left["bounds"]) != len(right["bounds"]):
            return False
        if any(abs(float(x) - float(y)) > tolerance for x, y in zip(left["bounds"], right["bounds"])):
            return False
    return True


def render_mass_flow_review(review_path: Path, config: Mapping[str, Any], output_dir: Path) -> dict[str, str]:
    data = json.loads(review_path.read_text(encoding="utf-8"))
    study = config.get("study", config)
    system = study["simulation"]["rule_genome"]["system"]
    width, height = int(study["render"]["width"]), int(study["render"]["height"])
    domain_width, domain_height = system["domain_width"], system["domain_height"]
    output_dir.mkdir(parents=True, exist_ok=True)
    palette = ((108, 225, 255), (255, 143, 92), (192, 150, 255))

    def render_frame(record: Mapping[str, Any], size: tuple[int, int]) -> Image.Image:
        frame_width, frame_height = size
        base = Image.new("RGB", size, (4, 7, 12))
        glow = Image.new("RGBA", size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow, "RGBA")
        sharp = Image.new("RGBA", size, (0, 0, 0, 0))
        sharp_draw = ImageDraw.Draw(sharp, "RGBA")
        for x, y, speed, phase in record["points"]:
            px = round((x / domain_width + 0.5) * frame_width)
            py = round((0.5 - y / domain_height) * frame_height)
            color = palette[phase]
            alpha = min(220, round(70 + speed / system["max_speed"] * 150))
            glow_draw.ellipse((px - 2, py - 2, px + 2, py + 2), fill=(*color, alpha // 2))
            sharp_draw.point((px, py), fill=(*color, alpha))
        base = Image.alpha_composite(base.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(2.2)))
        base = Image.alpha_composite(base, sharp)
        draw = ImageDraw.Draw(base, "RGBA")
        draw.text((12, 10), f"MASS FLOW  /  FRAME {record['frame']:04d}", fill=(224, 234, 239, 220))
        return base

    frames = data["frames"]
    selected_indices = sorted({0, len(frames) // 3, len(frames) * 2 // 3, len(frames) - 1})
    selected = [frames[index] for index in selected_indices]
    tile_size = (width // 2, height // 2)
    contact = Image.new("RGBA", (width, height), (2, 4, 8, 255))
    for index, record in enumerate(selected):
        tile = render_frame(record, tile_size)
        contact.alpha_composite(tile, ((index % 2) * tile_size[0], (index // 2) * tile_size[1]))
    contact_path = output_dir / "contact-sheet.png"
    contact.convert("RGB").save(contact_path)
    final_path = output_dir / "final-frame.png"
    render_frame(frames[-1], (width, height)).convert("RGB").save(final_path)

    trail_base = Image.new("RGB", (width, height), (3, 6, 11))
    trail_glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    trail_sharp = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(trail_glow, "RGBA")
    sharp_draw = ImageDraw.Draw(trail_sharp, "RGBA")

    def pixel(point: Sequence[float]) -> tuple[int, int]:
        return round((point[0] / domain_width + 0.5) * width), round((0.5 - point[1] / domain_height) * height)

    history_count = min(len(record["points"]) for record in frames)
    for point_index in range(history_count):
        phase = int(frames[-1]["points"][point_index][3])
        color = palette[phase]
        for history_index in range(1, len(frames)):
            previous = frames[history_index - 1]["points"][point_index]
            current = frames[history_index]["points"][point_index]
            if abs(current[0] - previous[0]) > domain_width * 0.5 or abs(current[1] - previous[1]) > domain_height * 0.5:
                continue
            alpha = round(28 + history_index / max(1, len(frames) - 1) * 112)
            segment = (*pixel(previous), *pixel(current))
            glow_draw.line(segment, fill=(*color, alpha), width=4)
            sharp_draw.line(segment, fill=(*color, min(210, alpha + 38)), width=1)
        endpoint = pixel(frames[-1]["points"][point_index])
        sharp_draw.ellipse((endpoint[0] - 1, endpoint[1] - 1, endpoint[0] + 1, endpoint[1] + 1), fill=(*color, 205))
    trail_image = Image.alpha_composite(trail_base.convert("RGBA"), trail_glow.filter(ImageFilter.GaussianBlur(3.5)))
    trail_image = Image.alpha_composite(trail_image, trail_sharp)
    trail_draw = ImageDraw.Draw(trail_image, "RGBA")
    trail_draw.text((18, 16), "MASS FLOW  /  DERIVED TRAILS", fill=(229, 237, 241, 220))
    trail_draw.text((18, 34), f"{history_count:,} REPRESENTATIVES  /  {len(frames)} CHECKPOINTS", fill=(139, 155, 166, 210))
    trails_path = output_dir / "derived-trails.png"
    trail_image.convert("RGB").save(trails_path)
    return {"contact_sheet": str(contact_path), "final_frame": str(final_path), "derived_trails": str(trails_path)}


def render_mass_flow_animation(review_path: Path, config: Mapping[str, Any], output_dir: Path) -> Path:
    data = json.loads(review_path.read_text(encoding="utf-8"))
    study = config.get("study", config)
    system = study["simulation"]["rule_genome"]["system"]
    width, height = int(study["render"]["width"]), int(study["render"]["height"])
    domain_width, domain_height = system["domain_width"], system["domain_height"]
    palette = ((67, 196, 229), (224, 105, 54), (150, 102, 224))
    frames_dir = output_dir / "motion-frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for stale_frame in frames_dir.glob("motion.*.jpg"):
        stale_frame.unlink()
    records = data["frames"][1:]  # Drop the irregular frame-1 seed checkpoint; regular samples play at 6 fps.

    def pixel(point: Sequence[float]) -> tuple[int, int]:
        return round((point[0] / domain_width + 0.5) * width), round((0.5 - point[1] / domain_height) * height)

    representative_stride = max(1, len(records[0]["points"]) // 3000)
    history_length = int(system.get("trail_history_checkpoints", 5))
    for frame_index, record in enumerate(records, 1):
        image = Image.new("RGB", (width, height), (3, 6, 11))
        glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        sharp = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        glow_draw, sharp_draw = ImageDraw.Draw(glow, "RGBA"), ImageDraw.Draw(sharp, "RGBA")
        history_start = max(1, frame_index - history_length)
        for point_index in range(0, len(record["points"]), representative_stride):
            phase = int(record["points"][point_index][3])
            color = palette[phase]
            for history_index in range(history_start, frame_index):
                previous = records[history_index - 1]["points"][point_index]
                current = records[history_index]["points"][point_index]
                if abs(current[0] - previous[0]) > domain_width * 0.5 or abs(current[1] - previous[1]) > domain_height * 0.5:
                    continue
                segment = (*pixel(previous), *pixel(current))
                alpha = round(35 + (history_index - history_start + 1) / history_length * 120)
                glow_draw.line(segment, fill=(*color, alpha), width=4)
                sharp_draw.line(segment, fill=(*color, min(220, alpha + 45)), width=1)
        image = Image.alpha_composite(image.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(3.0)))
        image = Image.alpha_composite(image, sharp)
        ImageDraw.Draw(image).text((18, 16), f"MASS FLOW  /  {record['frame']:04d}", fill=(225, 235, 240, 220))
        image.convert("RGB").save(frames_dir / f"motion.{frame_index:04d}.jpg", quality=92)
    ffmpeg = next(tool.path for tool in discover_tools() if tool.name == "ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to encode the Mass Flow preview")
    duration_seconds = len(records) / 6
    duration_label = f"{duration_seconds:g}".replace(".", "p")
    output = output_dir / f"mass-flow-{duration_label}s-preview.mp4"
    command = [str(ffmpeg), "-y", "-framerate", "6", "-i", str(frames_dir / "motion.%04d.jpg"), "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
    if result.returncode:
        raise RuntimeError(f"Mass Flow preview encode failed: {result.stderr[-1000:]}")
    return output


def _run(command: Sequence[str], log_path: Path, env: dict[str, str], timeout: int = 900) -> None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        log_path.write_text(str(exc) + "\n", encoding="utf-8")
        raise RuntimeError(str(exc)) from exc
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    log_path.write_text(output + ("\n" if output else ""), encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"mass-flow subprocess exited {result.returncode}; see {log_path}")


def run_mass_flow_probe(job: Job) -> str:
    if job.effective_config["study"]["id"] != "002-mass-flow":
        raise RuntimeError("scale-probe currently requires Study 002")
    receipt = next(item for item in job_status(job) if item["stage"] == "simulate")
    metrics_path = job.directory / "simulation" / "mass-flow-metrics.json"
    review_path = job.directory / "simulation" / "mass-flow-review.json"
    if (
        receipt.get("state") == "complete"
        and receipt.get("input_digest") == job.input_digest
        and metrics_path.is_file()
        and receipt.get("metrics_sha256") == sha256_path(metrics_path)
        and review_path.is_file()
    ):
        validate_mass_flow_metrics(metrics_path, job.effective_config)
        render_mass_flow_review(review_path, job.effective_config, job.directory / "review")
        render_mass_flow_animation(review_path, job.effective_config, job.directory / "review")
        return "scale-probe: complete (reused verified cache)"

    hython = next(tool.path for tool in discover_tools() if tool.name == "hython")
    if hython is None:
        raise RuntimeError("hython is required; run houdini-ai doctor")
    script = job.root / "houdini" / "simulate_mass_flow.py"
    config_path = job.directory / "effective-config.json"
    simulation_dir = job.directory / "simulation"
    simulation_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["HDAI_PROJECT_ROOT"] = str(job.root)
    env["HOUDINI_TEMP_DIR"] = str(job.directory / "temp")
    (job.directory / "temp").mkdir(parents=True, exist_ok=True)
    set_stage_state(job, "simulate", "running")

    def invoke(label: str, config: Path, frame_end: int | None) -> tuple[Path, Path]:
        metrics = simulation_dir / f"{label}-metrics.json"
        review = simulation_dir / f"{label}-review.json"
        command = [str(hython), str(script), str(config), str(simulation_dir / f"{label}-cache"), str(metrics), str(review)]
        if frame_end is not None:
            command.extend(("--frame-end", str(frame_end)))
        _run(command, job.directory / "logs" / f"mass-flow-{label}.log", env)
        return metrics, review

    try:
        start = job.effective_config["study"]["simulation"]["frame_start"]
        smoke_end = start + 7
        smoke_a, _ = invoke("smoke-a", config_path, smoke_end)
        smoke_b, _ = invoke("smoke-b", config_path, smoke_end)
        a = validate_mass_flow_metrics(smoke_a, job.effective_config)
        b = validate_mass_flow_metrics(smoke_b, job.effective_config)
        if not materially_equivalent_metrics(a, b):
            raise RuntimeError("same-seed mass-flow smoke probes were not deterministic")
        variant = json.loads(json.dumps(job.effective_config))
        variant["study"]["seed"] += 1
        variant_path = simulation_dir / "changed-seed-config.json"
        variant_path.write_text(json.dumps(variant, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        variant_metrics, _ = invoke("changed-seed", variant_path, smoke_end)
        changed = validate_mass_flow_metrics(variant_metrics, variant)
        if determinism_signature(a) == determinism_signature(changed):
            raise RuntimeError("changed seed did not produce a distinct mass-flow probe")
        full_metrics, full_review = invoke("mass-flow", config_path, None)
        if full_metrics != metrics_path:
            metrics_path.write_bytes(full_metrics.read_bytes())
        if full_review != review_path:
            review_path.write_bytes(full_review.read_bytes())
        metrics = validate_mass_flow_metrics(metrics_path, job.effective_config)
        review = render_mass_flow_review(review_path, job.effective_config, job.directory / "review")
        preview = render_mass_flow_animation(review_path, job.effective_config, job.directory / "review")
        set_stage_state(
            job, "simulate", "complete", metrics="simulation/mass-flow-metrics.json",
            metrics_sha256=sha256_path(metrics_path), review=review,
            preview=str(preview),
            deterministic=True, changed_seed_distinct=True,
            agent_count=metrics["agent_count"], elapsed_seconds=metrics["elapsed_seconds"],
            agent_frames_per_second=metrics["agent_frames_per_second"],
        )
        return f"scale-probe: complete ({metrics['agent_count']:,} agents)"
    except Exception as exc:
        set_stage_state(job, "simulate", "failed", error=str(exc), log="logs/mass-flow-*.log")
        raise
