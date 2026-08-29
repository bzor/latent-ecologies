from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping

from PIL import Image, ImageDraw

from houdini_ai.behavior_package import encode_mp4


def _world_to_screen(x: float, y: float, width: int, height: int, panel_width: int) -> tuple[int, int]:
    px = round(panel_width * (0.5 + x / 4.0))
    py = round(height * (0.5 - y / 13.0))
    return px, py


def _render_zipper_frame(
    metrics: Mapping[str, Any],
    review_index: int,
    size: tuple[int, int],
) -> Image.Image:
    width, height = size
    kymo_width = max(80, width // 5)
    panel_width = width - kymo_width
    record = metrics["review"][review_index]
    image = Image.new("RGB", size, (7, 10, 15))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, panel_width, height), fill=(9, 12, 18))
    points = record["points"]

    for primitive in record["primitives"]:
        ids = primitive["points"]
        if len(ids) != 2:
            continue
        pa, pb = points[ids[0]]["P"], points[ids[1]]["P"]
        a = _world_to_screen(float(pa[0]), float(pa[1]), width, height, panel_width)
        b = _world_to_screen(float(pb[0]), float(pb[1]), width, height, panel_width)
        if int(primitive["kind"]) == 0:
            tension = min(1.0, float(primitive.get("tension", 0.0)) * 2.0)
            color = (
                round(82 + 165 * tension),
                round(88 - 38 * tension),
                round(100 + 120 * tension),
            )
            draw.line((*a, *b), fill=color, width=2)
        else:
            bond = min(1.0, float(primitive.get("bond", 0.0)))
            if bond <= 0.02:
                continue
            latched = int(primitive.get("latched", 0))
            color = (255, 220, 80) if latched else (235, 145, 35)
            draw.line((*a, *b), fill=color, width=1 + round(3 * bond))

    for point in points:
        px, py = _world_to_screen(float(point["P"][0]), float(point["P"][1]), width, height, panel_width)
        activator = min(1.0, float(point.get("activator", 0.0)))
        myosin = min(1.0, float(point.get("myosin", 0.0)))
        radius = 2 + round(3 * myosin)
        if activator > 0.02:
            color = (
                round(40 * (1.0 - activator)),
                round(100 + 150 * activator),
                round(135 + 120 * activator),
            )
        else:
            color = (150 + round(80 * myosin), 135, 165 + round(70 * myosin))
        draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=color)
        if int(point.get("fused", 0)):
            draw.ellipse((px - radius - 2, py - radius - 2, px + radius + 2, py + radius + 2), outline=(255, 220, 75), width=2)

    draw.rectangle((panel_width, 0, width - 1, height - 1), fill=(5, 8, 12), outline=(55, 70, 82))
    history = metrics["review"][: review_index + 1]
    bank_points = [point for point in points if int(point.get("bank", 0)) < 0]
    edge_count = max(1, len(bank_points))
    for row, historic in enumerate(history):
        y0 = round(row / max(1, len(history)) * height)
        y1 = max(y0 + 1, round((row + 1) / max(1, len(history)) * height))
        historic_bank = [point for point in historic["points"] if int(point.get("bank", 0)) < 0]
        for point in historic_bank:
            index = int(point["edge_index"])
            x0 = panel_width + round(index / edge_count * kymo_width)
            x1 = panel_width + round((index + 1) / edge_count * kymo_width)
            a = min(1.0, float(point.get("activator", 0.0)))
            if a > 0.02:
                draw.rectangle((x0, y0, max(x0, x1), y1), fill=(15, round(80 + 170 * a), round(110 + 145 * a)))
    draw.text((panel_width + 4, 4), "EDGE PULSE\nHISTORY", fill=(205, 220, 225))
    label = str(metrics.get("variant_label", "EXCITABLE PURSE-STRING ZIPPER"))
    draw.rectangle((2, 2, min(panel_width - 2, 310), 18), fill=(4, 6, 9))
    draw.text((6, 5), f"{label}  f{record['frame']}", fill=(238, 238, 228))
    return image


def _render_fascicle_frame(
    metrics: Mapping[str, Any],
    review_index: int,
    size: tuple[int, int],
) -> Image.Image:
    width, height = size
    record = metrics["review"][review_index]
    image = Image.new("RGB", size, (7, 10, 15))
    draw = ImageDraw.Draw(image)
    points = record["points"]
    fibres = {index: point for index, point in enumerate(points) if int(point.get("class", 0)) == 2}

    for primitive in record["primitives"]:
        if int(primitive.get("kind", 0)) != 2:
            continue
        bond = min(1.0, float(primitive.get("bond", 0.0)))
        if bond <= 0.018:
            continue
        ids = primitive["points"]
        if len(ids) != 2 or ids[0] not in fibres or ids[1] not in fibres:
            continue
        pa, pb = fibres[ids[0]]["P"], fibres[ids[1]]["P"]
        a = _world_to_screen(float(pa[0]), float(pa[1]), width, height, width)
        b = _world_to_screen(float(pb[0]), float(pb[1]), width, height, width)
        latched = int(primitive.get("latched", 0))
        color = (75, 225, 245) if latched else (245, 190, 55)
        draw.line((*a, *b), fill=color, width=1 + round(3 * bond))
        if latched:
            mx, my = round((a[0] + b[0]) * 0.5), round((a[1] + b[1]) * 0.5)
            radius = 2 + round(2 * bond)
            draw.ellipse((mx - radius, my - radius, mx + radius, my + radius), fill=(90, 235, 250))

    for index, fibre in fibres.items():
        px, py = _world_to_screen(float(fibre["P"][0]), float(fibre["P"][1]), width, height, width)
        direction = fibre.get("fdir", [0.0, 1.0, 0.0])
        dx, dy = float(direction[0]), -float(direction[1])
        length = max(1e-6, (dx * dx + dy * dy) ** 0.5)
        dx, dy = dx / length, dy / length
        mass = min(1.0, float(fibre.get("mass", 0.0)))
        crimp = min(1.0, float(fibre.get("crimp", 1.0)))
        tension = min(1.0, float(fibre.get("fibre_tension", 0.0)))
        half_length = 5 + round(8 * mass)
        normal = (-dy, dx)
        if crimp > 0.45:
            amplitude = 1.5 + 2.5 * crimp
            path = []
            for step in range(7):
                t = step / 6.0 * 2.0 - 1.0
                wave = (1 if step % 2 else -1) * amplitude * (1.0 - abs(t) * 0.25)
                path.append((px + dx * half_length * t + normal[0] * wave, py + dy * half_length * t + normal[1] * wave))
            shade = round(90 + 75 * mass)
            draw.line(path, fill=(shade, shade, shade + 8), width=1)
        else:
            color = (
                round(175 + 75 * tension),
                round(180 + 70 * tension),
                round(185 + 70 * tension),
            )
            width_px = 1 + min(4, round(float(fibre.get("bundle_degree", 0.0))))
            draw.line((px - dx * half_length, py - dy * half_length, px + dx * half_length, py + dy * half_length), fill=color, width=width_px)

    trail_history: dict[int, list[tuple[float, float, int, int]]] = {}
    for history_record in metrics["review"][max(0, review_index - 10):review_index + 1]:
        for history_point in history_record["points"]:
            if int(history_point.get("class", 0)) != 0 or float(history_point.get("flow_alignment", 0.0)) < 0.55:
                continue
            world_x, world_y = float(history_point["P"][0]), float(history_point["P"][1])
            sx, sy = _world_to_screen(world_x, world_y, width, height, width)
            trail_history.setdefault(int(history_point["id"]), []).append((world_x, world_y, sx, sy))
    for trail in trail_history.values():
        for previous, current in zip(trail, trail[1:]):
            if abs(current[0] - previous[0]) <= 4.0 and abs(current[1] - previous[1]) <= 6.0:
                draw.line((previous[2], previous[3], current[2], current[3]), fill=(65, 145, 170), width=1)

    for point in points:
        if int(point.get("class", 0)) != 0:
            continue
        px, py = _world_to_screen(float(point["P"][0]), float(point["P"][1]), width, height, width)
        heading = float(point.get("heading", 0.0))
        phase = int(point.get("phase", 0))
        draw.ellipse((px - 3, py - 3, px + 3, py + 3), fill=(242, 242, 230))
        draw.line((px, py, px + 7 * math.cos(heading), py - 7 * math.sin(heading)), fill=(225, 225, 215), width=1)
        anchor = int(point.get("anchor", -1))
        if phase == 2 and anchor in fibres:
            target = fibres[anchor]["P"]
            world_dx = abs(float(target[0]) - float(point["P"][0]))
            world_dy = abs(float(target[1]) - float(point["P"][1]))
            if world_dx <= 4.0 and world_dy <= 6.0:
                tx, ty = _world_to_screen(float(target[0]), float(target[1]), width, height, width)
                draw.line((px, py, tx, ty), fill=(245, 125, 35), width=2)

    label = str(metrics.get("variant_label", "TUG-AND-ZIP FASCICULATION"))
    draw.rectangle((2, 2, min(width - 2, 300), 18), fill=(4, 6, 9))
    draw.text((6, 5), f"{label}  f{record['frame']}", fill=(238, 238, 228))
    draw.text((6, height - 17), "grey: crimp  white: tension  orange: tug  cyan: latched graph", fill=(185, 195, 198))
    return image


def render_mechanics_frames(
    metrics: Mapping[str, Any],
    config: Mapping[str, Any],
    output_dir: Path,
    size: tuple[int, int] = (540, 810),
) -> list[Path]:
    del config
    output_dir.mkdir(parents=True, exist_ok=True)
    mode = str(metrics["mode"])
    paths: list[Path] = []
    for index, _record in enumerate(metrics["review"]):
        if mode == "excitable-purse-string-zipper":
            image = _render_zipper_frame(metrics, index, size)
        elif mode == "tug-zip-fasciculation":
            image = _render_fascicle_frame(metrics, index, size)
        else:
            raise NotImplementedError(mode)
        path = output_dir / f"frame-{index:04d}.png"
        image.save(path)
        paths.append(path)
    return paths


__all__ = ["encode_mp4", "render_mechanics_frames"]
