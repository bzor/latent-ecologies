from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from PIL import Image, ImageDraw, ImageFilter


LOOKS = ("fibrous-memory", "etched-substrate", "membrane-stress")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _coordinates(index: int, grid: tuple[int, int], size: tuple[int, int]) -> tuple[float, float]:
    gx, gy = grid
    width, height = size
    x, y = index % gx, index // gx
    return ((x + 0.5) / gx * width, (y + 0.5) / gy * height)


def _fibrous(record: Mapping[str, Any], grid: tuple[int, int], size: tuple[int, int]) -> Image.Image:
    image = Image.new("RGB", size, (8, 10, 12))
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    lines = ImageDraw.Draw(glow)
    cell = min(size[0] / grid[0], size[1] / grid[1])
    for index, value in enumerate(record["field"]):
        if value < 0.04:
            continue
        x, y = _coordinates(index, grid, size)
        dx, dy = record["direction_x"][index], record["direction_y"][index]
        length = math.hypot(dx, dy)
        if length < 1e-6:
            continue
        scale = cell * (0.8 + min(2.2, value * 2.0))
        dx, dy = dx / length * scale, dy / length * scale
        alpha = min(235, 45 + int(value * 150))
        lines.line((x - dx, y + dy, x + dx, y - dy), fill=(205, 218, 198, alpha), width=max(1, round(cell * 0.18)))
    blurred = glow.filter(ImageFilter.GaussianBlur(max(1.0, cell * 0.55)))
    image = Image.alpha_composite(image.convert("RGBA"), blurred)
    return Image.alpha_composite(image, glow).convert("RGB")


def _etched(record: Mapping[str, Any], grid: tuple[int, int], size: tuple[int, int]) -> Image.Image:
    gx, gy = grid
    field = record["field"]
    low = Image.new("L", (gx, gy))
    low.putdata([max(0, min(255, round(value * 150))) for value in field])
    relief = low.resize(size, Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(1.2))
    image = Image.new("RGB", size, (192, 187, 169))
    pixels = image.load(); values = relief.load()
    for y in range(size[1]):
        for x in range(size[0]):
            center = values[x, y]
            left = values[max(0, x - 2), y]
            above = values[x, max(0, y - 2)]
            shade = max(-70, min(55, (left - center) + (above - center)))
            depth = center * 0.42
            pixels[x, y] = tuple(max(0, min(255, int(base + shade - depth))) for base in (202, 195, 174))
    edges = relief.filter(ImageFilter.FIND_EDGES)
    ink = Image.new("RGB", size, (45, 47, 43))
    return Image.composite(ink, image, edges.point(lambda value: min(180, value * 2)))


def _membrane(record: Mapping[str, Any], grid: tuple[int, int], size: tuple[int, int]) -> Image.Image:
    gx, gy = grid
    low = Image.new("L", (gx, gy))
    low.putdata([max(0, min(255, round(value * 180))) for value in record["field"]])
    field = low.resize(size, Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(3.5))
    image = Image.new("RGB", size)
    pixels = image.load(); values = field.load()
    for y in range(size[1]):
        for x in range(size[0]):
            value = values[x, y] / 255.0
            gxv = values[min(size[0] - 1, x + 2), y] - values[max(0, x - 2), y]
            gyv = values[x, min(size[1] - 1, y + 2)] - values[x, max(0, y - 2)]
            stress = min(1.0, math.hypot(gxv, gyv) / 65.0)
            pixels[x, y] = (
                int(11 + value * 42 + stress * 95),
                int(18 + value * 78 + stress * 38),
                int(29 + value * 102 + stress * 118),
            )
    highlights = ImageDraw.Draw(image, "RGBA")
    cell = min(size[0] / gx, size[1] / gy)
    for index, idle in enumerate(record["idle"]):
        if idle < 16 or record["field"][index] < 0.03:
            continue
        x, y = _coordinates(index, grid, size)
        radius = cell * min(1.8, 0.35 + idle / 80.0)
        highlights.ellipse((x - radius, y - radius, x + radius, y + radius), outline=(150, 220, 255, 75), width=1)
    return image


def build_lookdev_probes(
    behavior: Mapping[str, Any],
    metrics: Mapping[str, Any],
    output_dir: Path,
    *,
    size: tuple[int, int] = (540, 810),
) -> dict[str, Any]:
    if behavior.get("component_kind") != "behavior" or behavior.get("state") != "promoted":
        raise ValueError("a promoted behavior component is required")
    review = metrics.get("review")
    grid_value = metrics.get("grid")
    if not isinstance(review, list) or not review or not isinstance(grid_value, list) or len(grid_value) != 2:
        raise ValueError("behavior metrics require review state and grid")
    record = review[-1]
    grid = (int(grid_value[0]), int(grid_value[1]))
    output_dir.mkdir(parents=True, exist_ok=True)
    renderers = {"fibrous-memory": _fibrous, "etched-substrate": _etched, "membrane-stress": _membrane}
    looks: dict[str, str] = {}
    for name, renderer in renderers.items():
        path = output_dir / f"{name}.png"
        renderer(record, grid, size).save(path)
        looks[name] = path.name
    comparison = Image.new("RGB", (size[0] * 3, size[1] + 34), (12, 15, 18))
    draw = ImageDraw.Draw(comparison)
    for index, name in enumerate(LOOKS):
        comparison.paste(Image.open(output_dir / looks[name]).convert("RGB"), (index * size[0], 34))
        draw.text((index * size[0] + 10, 10), name, fill=(235, 238, 240))
    comparison_path = output_dir / "comparison.png"
    comparison.save(comparison_path)
    files = [output_dir / value for value in looks.values()] + [comparison_path]
    receipt = {
        "schema_version": 1,
        "source_behavior_component_id": behavior["id"],
        "source_behavior_content_hash": behavior["content_hash"],
        "source_state_sha256": metrics.get("state_sha256"),
        "looks": looks,
        "files": {path.name: {"bytes": path.stat().st_size, "sha256": _sha256(path)} for path in files},
    }
    (output_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt
