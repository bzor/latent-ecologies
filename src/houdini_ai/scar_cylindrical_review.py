from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping

from PIL import Image, ImageDraw


def _project(
    position: list[float] | tuple[float, float, float],
    tube_azimuth: float,
    view: str,
) -> tuple[float, float, float]:
    x, y, z = map(float, position)
    seam = 0.10 * math.sin(y * 0.78) + 0.035 * math.sin(y * 2.17)
    local_x = x - seam
    radial = local_x * math.cos(tube_azimuth) + z * math.sin(tube_azimuth)
    depth = -local_x * math.sin(tube_azimuth) + z * math.cos(tube_azimuth)
    if view == "source":
        return seam + radial, y, depth
    yaw = math.radians(52.0)
    pitch = math.radians(19.0)
    screen_x = seam + radial * math.cos(yaw) + depth * math.sin(yaw)
    camera_depth = -radial * math.sin(yaw) + depth * math.cos(yaw)
    screen_y = y * math.cos(pitch) - camera_depth * math.sin(pitch)
    final_depth = y * math.sin(pitch) + camera_depth * math.cos(pitch)
    return screen_x, screen_y, final_depth


def _screen(projected: tuple[float, float, float], size: tuple[int, int]) -> tuple[int, int]:
    width, height = size
    return (
        round(width * (0.5 + projected[0] / 4.2)),
        round(height * (0.5 - projected[1] / 13.8)),
    )


def _project_review_point(
    point: Mapping[str, Any],
    tube_azimuth: float,
    view: str,
    tube_twist_turns: float,
) -> tuple[float, float, float]:
    position = point["P"]
    if view == "source" and abs(tube_twist_turns) > 1e-8:
        y = float(position[1])
        if "unwrapped_x" in point:
            return float(point["unwrapped_x"]), y, 0.0
        seam = 0.10 * math.sin(y * 0.78) + 0.035 * math.sin(y * 2.17)
        radius = float(point.get(
            "tube_radius", math.hypot(float(position[0]) - seam, float(position[2])),
        ))
        return seam + int(point.get("bank", 1)) * radius, y, 0.0
    return _project(position, tube_azimuth, view)


def _tube_point(radius: float, y: float, theta: float) -> list[float]:
    seam = 0.10 * math.sin(y * 0.78) + 0.035 * math.sin(y * 2.17)
    return [seam + radius * math.cos(theta), y, radius * math.sin(theta)]


def _render_view(
    metrics: Mapping[str, Any],
    review_index: int,
    view: str,
    size: tuple[int, int],
) -> Image.Image:
    record = metrics["review"][review_index]
    azimuth = float(metrics.get("tube_azimuth", 0.0))
    radius = float(metrics.get("tube_radius_initial", 1.15))
    twist_turns = float(metrics.get("tube_twist_turns", 0.0))
    image = Image.new("RGB", size, (7, 10, 15))
    draw = ImageDraw.Draw(image)

    guide = (54, 64, 91)
    axis = [_screen(_project([0.0, y, 0.0], azimuth, view), size) for y in (-5.75, 5.75)]
    draw.line((*axis[0], *axis[1]), fill=(70, 80, 105), width=1)
    for y in (-5.75, -2.875, 0.0, 2.875, 5.75):
        ring = [
            _screen(_project(_tube_point(radius, y, step / 48.0 * math.tau), azimuth, view), size)
            for step in range(49)
        ]
        draw.line(ring, fill=guide, width=1)
    for step in range(8):
        theta = step / 8.0 * math.tau
        line = [
            _screen(_project(_tube_point(radius, y, theta), azimuth, view), size)
            for y in (-5.75, 5.75)
        ]
        draw.line((*line[0], *line[1]), fill=(37, 46, 67), width=1)

    points = record["points"]
    primitives = sorted(record["primitives"], key=lambda item: sum(
        _project_review_point(points[index], azimuth, view, twist_turns)[2]
        for index in item["points"]
    ) / max(1, len(item["points"])))
    for primitive in primitives:
        ids = primitive["points"]
        if len(ids) != 2:
            continue
        pa = _screen(_project_review_point(points[ids[0]], azimuth, view, twist_turns), size)
        pb = _screen(_project_review_point(points[ids[1]], azimuth, view, twist_turns), size)
        if int(primitive.get("kind", 0)) == 1:
            bond = min(1.0, float(primitive.get("bond", 0.0)))
            if bond <= 0.02:
                continue
            color = (255, 220, 80) if int(primitive.get("latched", 0)) else (235, 145, 35)
            draw.line((*pa, *pb), fill=color, width=1 + round(3 * bond))
        else:
            tension = min(1.0, float(primitive.get("tension", 0.0)) * 2.0)
            color = (round(82 + 165 * tension), round(88 - 38 * tension), round(100 + 120 * tension))
            draw.line((*pa, *pb), fill=color, width=2)

    projected_points = sorted(
        points, key=lambda point: _project_review_point(point, azimuth, view, twist_turns)[2],
    )
    for point in projected_points:
        px, py = _screen(_project_review_point(point, azimuth, view, twist_turns), size)
        activator = min(1.0, float(point.get("activator", 0.0)))
        myosin = min(1.0, float(point.get("myosin", 0.0)))
        point_radius = 2 + round(3 * myosin)
        color = (
            (round(40 * (1.0 - activator)), round(100 + 150 * activator), round(135 + 120 * activator))
            if activator > 0.02 else
            (150 + round(80 * myosin), 135, 165 + round(70 * myosin))
        )
        draw.ellipse((px - point_radius, py - point_radius, px + point_radius, py + point_radius), fill=color)
        if int(point.get("fused", 0)):
            draw.ellipse(
                (px - point_radius - 2, py - point_radius - 2, px + point_radius + 2, py + point_radius + 2),
                outline=(255, 220, 75), width=2,
            )

    label = str(metrics.get("variant_label", "CYLINDRICAL RAPID ZIPPER"))
    title = (
        "BEHAVIOR UNWRAPPED" if view == "source" and abs(twist_turns) > 1e-8
        else ("SOURCE-ORIENTATION" if view == "source" else "OBLIQUE 3D")
    )
    draw.rectangle((2, 2, min(size[0] - 2, 420), 21), fill=(4, 6, 9))
    draw.text((7, 6), f"{label} | {title} | f{record['frame']}", fill=(238, 238, 228))
    draw.text((7, size[1] - 17), "wire: initial tube  cyan: pulse  purple: myosin  yellow: fused zipper", fill=(155, 170, 180))
    return image


def render_cylindrical_review_frames(
    metrics: Mapping[str, Any],
    output_dir: Path,
    size: tuple[int, int] = (960, 540),
) -> dict[str, list[Path]]:
    output_dir = Path(output_dir)
    result: dict[str, list[Path]] = {"source": [], "oblique": [], "combined": []}
    for family in result:
        (output_dir / family).mkdir(parents=True, exist_ok=True)
    for review_index in range(len(metrics["review"])):
        source = _render_view(metrics, review_index, "source", size)
        oblique = _render_view(metrics, review_index, "oblique", size)
        combined = Image.new("RGB", (size[0] * 2, size[1]), (7, 10, 15))
        combined.paste(source, (0, 0))
        combined.paste(oblique, (size[0], 0))
        for family, image in (("source", source), ("oblique", oblique), ("combined", combined)):
            path = output_dir / family / f"frame-{review_index:04d}.png"
            image.save(path)
            result[family].append(path)
    return result
