from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw


STATE_COLORS = {
    "low-field": (24, 32, 38),
    "attractive": (45, 180, 110),
    "saturated": (235, 82, 72),
    "healed": (90, 145, 240),
}


def render_temporal_frames(
    metrics: Mapping[str, Any],
    config: Mapping[str, Any],
    output_dir: Path,
    size: tuple[int, int] = (360, 540),
    hold_frames: int = 1,
) -> list[Path]:
    """Render cheap diagnostic frames directly from stored review samples."""
    output_dir.mkdir(parents=True, exist_ok=True)
    width, height = size
    gx, gy = (int(value) for value in metrics["grid"])
    system = config["system"]
    attraction = float(system["attraction_threshold"])
    saturation = float(system["saturation_threshold"])
    domain_width = float(system["domain_width"])
    domain_height = float(system["domain_height"])
    previous = [0.0] * (gx * gy)
    paths: list[Path] = []

    for record in metrics["review"]:
        field = [float(value) for value in record["field"]]
        provisional = record.get("provisional_matrix")
        collagen = record.get("mature_collagen")
        contraction = record.get("contraction")
        wound = record.get("wound_signal")
        crosslink = record.get("crosslink")
        fibrotic_signal = record.get("fibrotic_signal")
        biological = metrics.get("mutation") in {"fibrotic-remodeling", "wound-contractile-remodeling", "purse-string-closure", "collagen-crosslink-weave", "keloid-signal-bloom"}
        image = Image.new("RGB", (gx, gy))
        pixels = image.load()
        for py in range(gy):
            cy = py
            for px in range(gx):
                cx = px
                index = cy * gx + cx
                value = field[index]
                if biological and isinstance(provisional, list) and isinstance(collagen, list):
                    p = min(1.0, float(provisional[index]) / max(saturation, 1e-6))
                    c = min(1.0, float(collagen[index]) / max(saturation, 1e-6))
                    if metrics.get("mutation") == "keloid-signal-bloom":
                        s = min(1.0, float(fibrotic_signal[index])) if isinstance(fibrotic_signal, list) else 0.0
                        pixels[px, py] = (
                            round(min(255, 15 + 210 * c + 170 * s)),
                            round(min(255, 18 + 45 * c + 190 * s)),
                            round(max(0, min(255, 28 + 105 * c - 50 * s))),
                        )
                    elif metrics.get("mutation") == "collagen-crosslink-weave":
                        x = min(1.0, float(crosslink[index]) / 0.4) if isinstance(crosslink, list) else 0.0
                        pixels[px, py] = (
                            round(min(255, 12 + 70 * c + 220 * x)),
                            round(min(255, 18 + 110 * c + 170 * x)),
                            round(max(0, min(255, 26 + 210 * c * (1.0 - 0.8 * x)))),
                        )
                    elif metrics.get("mutation") in {"wound-contractile-remodeling", "purse-string-closure"}:
                        k = min(1.0, float(contraction[index])) if isinstance(contraction, list) else 0.0
                        w = min(1.0, float(wound[index])) if isinstance(wound, list) else 0.0
                        if metrics.get("mutation") == "purse-string-closure":
                            edge = math.exp(-((w - 0.38) / 0.20) ** 2)
                            pixels[px, py] = (
                                round(min(255, 10 + 220 * c + 40 * k)),
                                round(min(255, 16 + 45 * c + 30 * edge)),
                                round(min(255, 28 + 100 * c + 150 * k + 50 * w)),
                            )
                        else:
                            pixels[px, py] = (
                                round(min(255, 12 + 30 * p + 190 * c + 50 * k)),
                                round(min(255, 20 + 170 * p + 45 * c)),
                                round(min(255, 28 + 65 * p + 80 * c + 140 * k + 20 * w)),
                            )
                    else:
                        pixels[px, py] = (
                            round(min(255, 15 + 35 * p + 220 * c)),
                            round(min(255, 22 + 180 * p + 65 * c)),
                            round(min(255, 28 + 75 * p + 85 * c)),
                        )
                else:
                    if previous[index] >= attraction and value < attraction:
                        state = "healed"
                    elif value >= saturation:
                        state = "saturated"
                    elif value >= attraction:
                        state = "attractive"
                    else:
                        state = "low-field"
                    pixels[px, py] = STATE_COLORS[state]

        image = image.resize(size, Image.Resampling.NEAREST)
        draw = ImageDraw.Draw(image)
        direction_x = record.get("direction_x")
        direction_y = record.get("direction_y")
        if isinstance(direction_x, list) and isinstance(direction_y, list) and len(direction_x) == gx * gy and len(direction_y) == gx * gy:
            vector_color = (210, 225, 235)
            biological = metrics.get("mutation") in {"fibrotic-remodeling", "wound-contractile-remodeling", "purse-string-closure", "collagen-crosslink-weave", "keloid-signal-bloom"}
            vector_stride = 2 if biological else 1
            for cy in range(0, gy, vector_stride):
                for cx in range(0, gx, vector_stride):
                    index = cy * gx + cx
                    if biological and field[index] < attraction:
                        continue
                    dx, dy = float(direction_x[index]), float(direction_y[index])
                    length = math.hypot(dx, dy)
                    if length <= 1e-6:
                        continue
                    px = round((cx + 0.5) / gx * width)
                    py = round((cy + 0.5) / gy * height)
                    scale = min(width / gx, height / gy) * (0.28 if vector_stride > 1 else 0.18)
                    draw.line((px, py, px + dx / length * scale, py - dy / length * scale), fill=vector_color, width=1)
        if metrics.get("mutation") == "collagen-crosslink-weave" and isinstance(crosslink, list):
            marker = max(2.0, min(width / gx, height / gy) * 0.28)
            for cy in range(0, gy, 2):
                for cx in range(0, gx, 2):
                    index = cy * gx + cx
                    if float(crosslink[index]) < 0.16:
                        continue
                    px = round((cx + 0.5) / gx * width)
                    py = round((cy + 0.5) / gy * height)
                    draw.line((px - marker, py - marker, px + marker, py + marker), fill=(255, 226, 105), width=1)
                    draw.line((px - marker, py + marker, px + marker, py - marker), fill=(255, 226, 105), width=1)
        for x, y, heading in record.get("agents", []):
            px = round((float(x) / domain_width + 0.5) * width)
            py = round((0.5 - float(y) / domain_height) * height)
            dx, dy = math.cos(float(heading)) * 3, -math.sin(float(heading)) * 3
            draw.line((px - dx, py - dy, px + dx, py + dy), fill=(248, 245, 220), width=1)
        label = str(metrics.get("variant_label", metrics["mutation"]))
        draw.rectangle((2, 2, min(width - 2, 244), 15), fill=(7, 9, 12))
        draw.text((5, 3), f"{label}  f{record['frame']}", fill=(240, 240, 230))
        for _ in range(hold_frames):
            path = output_dir / f"frame-{len(paths):04d}.png"
            image.save(path)
            paths.append(path)
        previous = field
    return paths


def encode_mp4(
    frames: Sequence[Path],
    output_path: Path,
    fps: int = 6,
    ffmpeg_executable: str | Path | None = None,
) -> Path:
    """Encode an ordered PNG sequence with supplied or PATH-discovered FFmpeg."""
    if not frames:
        raise ValueError("cannot encode an empty frame sequence")
    executable = str(ffmpeg_executable or shutil.which("ffmpeg") or "")
    if not executable:
        raise FileNotFoundError("ffmpeg executable was not supplied or discovered")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pattern = frames[0].parent / "frame-%04d.png"
    command = [
        executable,
        "-y",
        "-loglevel",
        "error",
        "-framerate",
        str(fps),
        "-i",
        str(pattern),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    return output_path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_receipt(
    output_path: Path,
    *,
    experiment_id: str,
    mutation: str,
    files: Sequence[Path],
) -> Path:
    common_root = Path(output_path).parent
    payload = {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "mutation": mutation,
        "files": {
            path.name if path.parent == common_root else path.relative_to(common_root).as_posix(): {
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in files
        },
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def render_comparison_contact(
    entries: Sequence[Mapping[str, Any]],
    contact_path: Path,
    comparison_path: Path,
) -> dict[str, Path]:
    if len(entries) != 3:
        raise ValueError("comparison requires exactly three mutations")
    panels = [Image.open(Path(entry["image"])).convert("RGB") for entry in entries]
    panel_width, panel_height = panels[0].size
    contact = Image.new("RGB", (panel_width * 3, panel_height + 28), (8, 10, 12))
    draw = ImageDraw.Draw(contact)
    mutations = []
    for index, (entry, panel) in enumerate(zip(entries, panels)):
        if panel.size != (panel_width, panel_height):
            panel = panel.resize((panel_width, panel_height))
        x = index * panel_width
        contact.paste(panel, (x, 28))
        draw.text((x + 5, 8), str(entry["mutation"]), fill=(245, 240, 220))
        mutations.append({"mutation": entry["mutation"], "metrics": dict(entry["metrics"])})
    contact_path.parent.mkdir(parents=True, exist_ok=True)
    contact.save(contact_path)
    comparison_path.write_text(
        json.dumps({"schema_version": 1, "mutations": mutations}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {"contact": contact_path, "comparison": comparison_path}
