from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Mapping

from PIL import Image, ImageDraw

from .doctor import discover_tools
from .jobs import Job


def artifact_sdf(x: float, y: float, relic: Mapping[str, float]) -> float:
    distance = math.hypot(x, y) - relic["relic_hub_radius"]
    arm_start = relic["relic_hub_radius"] * 0.45
    half_length = relic["relic_arm_length"] * 0.5
    center = arm_start + half_length
    for index in range(3):
        angle = relic["relic_orientation"] + index * math.tau / 3.0
        along = x * math.cos(angle) + y * math.sin(angle) - center
        lateral = -x * math.sin(angle) + y * math.cos(angle)
        qx = abs(along) - half_length
        qy = abs(lateral) - relic["relic_arm_half_width"]
        distance = min(distance, math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0))
    return distance


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_metrics(path: Path, config: Mapping[str, Any], frame_end: int | None = None) -> dict[str, Any]:
    try:
        frames = json.loads(path.read_text(encoding="utf-8"))["frames"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise RuntimeError(f"simulation metrics are unreadable: {path}: {exc}") from exc
    study = config["study"]
    simulation = study["simulation"]
    system = simulation["rule_genome"]["system"]
    expected_end = frame_end or simulation["frame_end"]
    expected_frames = list(range(simulation["frame_start"], expected_end + 1))
    if [record.get("frame") for record in frames] != expected_frames:
        raise RuntimeError("simulation metrics do not contain the expected contiguous frame range")
    half_width = system["domain"]["domain_width"] * 0.5
    half_height = system["domain"]["domain_height"] * 0.5
    relic = system["relic"]
    for record in frames:
        if len(record.get("agents", [])) != system["agent_count"]:
            raise RuntimeError(f"frame {record['frame']} has the wrong agent count")
        for agent in record["agents"]:
            x, y, _ = agent["position"]
            values = (*agent["position"], *agent["velocity"], agent["relic_distance"])
            if not all(math.isfinite(value) for value in values):
                raise RuntimeError(f"frame {record['frame']} contains non-finite agent data")
            if abs(x) > half_width + 1e-4 or abs(y) > half_height + 1e-4:
                raise RuntimeError(f"frame {record['frame']} has an agent outside the domain")
            if artifact_sdf(x, y, relic) < -1e-3:
                raise RuntimeError(f"frame {record['frame']} has an agent inside the relic")
    near_samples = 0
    clockwise_samples = 0
    sectors: set[int] = set()
    approaches = 0
    previous_near: dict[int, bool] = {}
    for record in frames:
        for fallback_id, agent in enumerate(record["agents"]):
            agent_id = agent.get("id", fallback_id)
            near = agent["relic_distance"] < 1.0
            if near and previous_near.get(agent_id) is False:
                approaches += 1
            previous_near[agent_id] = near
            if near:
                near_samples += 1
                x, y, _ = agent["position"]
                vx, vy, _ = agent["velocity"]
                clockwise_samples += x * vy - y * vx < 0
                sectors.add(int((math.atan2(y, x) + math.pi) / math.tau * 12) % 12)
    return {
        "frame_count": len(frames),
        "agent_count": system["agent_count"],
        "final_resource": frames[-1]["resource_total"],
        "final_inhibition": frames[-1]["inhibition_mean"],
        "mean_speed": sum(record["mean_speed"] for record in frames) / len(frames),
        "max_speed": max(record["max_speed"] for record in frames),
        "boundary_contacts": sum(record["boundary_contacts"] for record in frames),
        "relic_approaches": approaches,
        "near_relic_agent_frames": near_samples,
        "perimeter_sectors_visited": len(sectors),
        "clockwise_near_relic_fraction": clockwise_samples / near_samples if near_samples else 0.0,
        "resource_consumed": frames[0]["resource_total"] - frames[-1]["resource_total"],
        "inhibition_change": frames[-1]["inhibition_mean"] - frames[0]["inhibition_mean"],
    }


def _to_pixel(x: float, y: float, width: int, height: int, domain_width: float, domain_height: float) -> tuple[int, int]:
    return round((x / domain_width + 0.5) * width), round((0.5 - y / domain_height) * height)


def _render_frame(record: Mapping[str, Any], system: Mapping[str, Any], size: tuple[int, int], instrument: bool) -> Image.Image:
    width, height = size
    field = record.get("field")
    grid_width, grid_height = system["grid_width"], system["grid_height"]
    if field:
        pixels = []
        for resource, inhibition in zip(field["resource"], field["inhibition"]):
            pixels.append((round(8 + resource * 35 + inhibition * 145), round(13 + resource * 105), round(18 + resource * 150), 255))
        background = Image.new("RGBA", (grid_width, grid_height))
        background.putdata(pixels)
        image = background.resize(size, Image.Resampling.BILINEAR)
    else:
        image = Image.new("RGBA", size, (7, 11, 15, 255))
    draw = ImageDraw.Draw(image, "RGBA")
    domain = system["domain"]
    scale = width / domain["domain_width"]
    for agent in record["agents"]:
        x, y, _ = agent["position"]
        px, py = _to_pixel(x, y, width, height, domain["domain_width"], domain["domain_height"])
        draw.ellipse((px - 2, py - 2, px + 2, py + 2), fill=(220, 244, 238, 245))
        if instrument and agent["id"] % 4 == 0:
            for key, color in (
                ("resource_steer", (83, 230, 175, 210)),
                ("inhibition_steer", (244, 151, 65, 210)),
                ("relic_avoidance", (218, 104, 220, 210)),
            ):
                vx, vy, _ = agent[key]
                draw.line((px, py, px + vx * scale * 0.35, py - vy * scale * 0.35), fill=color, width=1)
    draw.text((10, 8), f"frame {record['frame']:04d}", fill=(225, 235, 232, 230))
    return image


def create_review_bundle(job: Job, metrics_path: Path) -> dict[str, str]:
    data = json.loads(metrics_path.read_text(encoding="utf-8"))
    frames = data["frames"]
    system = job.effective_config["study"]["simulation"]["rule_genome"]["system"]
    review_dir = job.directory / "review"
    frames_dir = review_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    field_records = [record for record in frames if "field" in record]
    render = job.effective_config["study"]["render"]
    portrait = render["height"] > render["width"]
    panel_size = (180, 320) if portrait else (320, 180)
    panels = [_render_frame(record, system, panel_size, False) for record in field_records]
    contact_size = (540, 640) if portrait else (960, 360)
    contact = Image.new("RGBA", contact_size, (5, 7, 10, 255))
    positions = (
        ((0, 0), (180, 0), (360, 0), (90, 320), (270, 320))
        if portrait
        else ((0, 0), (320, 0), (640, 0), (160, 180), (480, 180))
    )
    for panel, position in zip(panels, positions):
        contact.alpha_composite(panel, position)
    contact_path = review_dir / "contact-sheet.png"
    contact.save(contact_path)
    instrument_path = review_dir / "instrument-frame.png"
    _render_frame(field_records[-1], system, (render["width"], render["height"]), True).save(instrument_path)

    preview_size = (360, 640) if portrait else (640, 360)
    for index, record in enumerate(frames[::3]):
        nearest = min(field_records, key=lambda candidate: abs(candidate["frame"] - record["frame"]))
        preview_record = {**record, "field": nearest["field"]}
        _render_frame(preview_record, system, preview_size, False).save(frames_dir / f"preview.{index:04d}.png")
    ffmpeg = next(tool.path for tool in discover_tools() if tool.name == "ffmpeg")
    preview_path = review_dir / "preview.mp4"
    if ffmpeg:
        result = subprocess.run(
            (
                str(ffmpeg), "-y", "-framerate", "10", "-i", str(frames_dir / "preview.%04d.png"),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(preview_path),
            ),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        (review_dir / "preview-encode.log").write_text(result.stderr, encoding="utf-8")
        if result.returncode != 0:
            raise RuntimeError(f"preview encoding failed; see {review_dir / 'preview-encode.log'}")

    summary = validate_metrics(metrics_path, job.effective_config)
    summary_path = review_dir / "metrics-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    first, last = frames[0], frames[-1]
    report = (
        "# Memory Field simulation review\n\n"
        f"- Frames: {first['frame']}–{last['frame']}\n"
        f"- Agents: {summary['agent_count']}\n"
        f"- Mean speed: {summary['mean_speed']:.3f}\n"
        f"- Peak speed: {summary['max_speed']:.3f}\n"
        f"- Resource remaining: {summary['final_resource']:.3f}\n"
        f"- Mean inhibition: {summary['final_inhibition']:.5f}\n"
        f"- Boundary contacts: {summary['boundary_contacts']}\n"
        f"- Relic approaches: {summary['relic_approaches']}\n"
        f"- Perimeter sectors visited: {summary['perimeter_sectors_visited']}/12\n"
        f"- Clockwise near-relic motion: {summary['clockwise_near_relic_fraction']:.1%}\n"
        f"- Resource consumed: {summary['resource_consumed']:.3f}\n"
    )
    report_path = review_dir / "metrics-report.md"
    report_path.write_text(report, encoding="utf-8")
    return {
        "contact_sheet": contact_path.relative_to(job.root).as_posix(),
        "instrument_frame": instrument_path.relative_to(job.root).as_posix(),
        "preview": preview_path.relative_to(job.root).as_posix() if preview_path.is_file() else "unavailable",
        "metrics_summary": summary_path.relative_to(job.root).as_posix(),
        "metrics_report": report_path.relative_to(job.root).as_posix(),
    }
