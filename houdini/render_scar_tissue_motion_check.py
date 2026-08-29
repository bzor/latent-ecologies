"""Render lightweight flat Scar Tissue motion checks from authoritative caches."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import hou
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))

from houdini_ai.scar_tissue_edit import camera_at_frame, frame_dimensions, portrait_camera_at_frame  # noqa: E402
from render_scar_tissue_grid_look import CAMERAS, derive_frame

WIDTH, DEPTH = 9.0, 13.5


def rotate_x(point: tuple[float, float, float], angle: float) -> tuple[float, float, float]:
    x, y, z = point; c, s = math.cos(angle), math.sin(angle)
    return x, y * c - z * s, y * s + z * c


def rotate_y(point: tuple[float, float, float], angle: float) -> tuple[float, float, float]:
    x, y, z = point; c, s = math.cos(angle), math.sin(angle)
    return x * c + z * s, y, -x * s + z * c


def project(point: tuple[float, float, float], camera: dict[str, float], width: int, height: int) -> tuple[float, float, float] | None:
    relative = (point[0] - camera["tx"], point[1] - camera["ty"], point[2] - camera["tz"])
    relative = rotate_y(relative, math.radians(-camera["ry"]))
    relative = rotate_x(relative, math.radians(-camera["rx"]))
    depth = -relative[2]
    if depth <= 0.05:
        return None
    focal_pixels = width * camera["focal_length"] / 36.0
    return width * 0.5 + relative[0] * focal_pixels / depth, height * 0.5 - relative[1] * focal_pixels / depth, depth


def load(path: Path) -> hou.Geometry:
    geometry = hou.Geometry(); geometry.loadFromFile(str(path)); return geometry


def rgb(value: tuple[float, float, float]) -> tuple[int, int, int]:
    return tuple(round(max(0.0, min(1.0, channel)) * 255) for channel in value)


def draw_line(draw: ImageDraw.ImageDraw, positions: list[tuple[float, float, float]], camera: dict[str, float], width: int, height: int, color: tuple[int, int, int], line_width: int) -> None:
    projected = [project(position, camera, width, height) for position in positions]
    points = [(item[0], item[1]) for item in projected if item is not None]
    if len(points) >= 2:
        draw.line(points, fill=color, width=line_width, joint="curve")


def render_frame(output: Path, derived: Path, frame: int, camera_name: str, width: int, edit_camera: bool = False, portrait_edit: bool = False) -> Path:
    _, height = frame_dimensions(width, portrait_edit)
    camera = portrait_camera_at_frame(frame) if portrait_edit else camera_at_frame(frame) if edit_camera else CAMERAS[camera_name]
    image = Image.new("RGB", (width, height), (8, 12, 20)); draw = ImageDraw.Draw(image)
    field = load(derived / f"field.{frame:04d}.bgeo.sc")
    cells = []
    for point in field.points():
        x, y, z = (float(value) for value in point.position())
        scale = tuple(float(value) for value in point.attribValue("scale")); color = rgb(tuple(float(value) for value in point.attribValue("Cd")))
        projected = project((x, y + scale[1] * 0.5, z), camera, width, height)
        if projected: cells.append((projected[2], projected, scale, color))
    for _, projected, scale, color in sorted(cells, reverse=True):
        size = max(1, round(width * scale[0] / max(projected[2], 1.0) * 1.25))
        height_px = max(1, round(width * scale[1] / max(projected[2], 1.0) * 1.45))
        x, y = projected[0], projected[1]
        base = tuple(round(channel * 0.35) for channel in color)
        draw.rectangle((x - size, y, x + size, y + height_px), fill=base)
        draw.rectangle((x - size, y - max(1, size // 2), x + size, y), fill=color)

    hairs = load(derived / f"hairs.{frame:04d}.bgeo.sc")
    for primitive in hairs.prims():
        draw_line(draw, [tuple(float(v) for v in vertex.point().position()) for vertex in primitive.vertices()], camera, width, height, (22, 207, 178), 1)
    trails = load(derived / f"trails.{frame:04d}.bgeo.sc")
    for primitive in trails.prims():
        draw_line(draw, [tuple(float(v) for v in vertex.point().position()) for vertex in primitive.vertices()], camera, width, height, (112, 170, 255), 1)
    for filename in (f"trail-starts.{frame:04d}.bgeo.sc", f"agents.{frame:04d}.bgeo.sc"):
        for point in load(derived / filename).points():
            projected = project(tuple(float(v) for v in point.position()), camera, width, height)
            if projected:
                x, y = projected[0], projected[1]; draw.ellipse((x - 1.5, y - 1.5, x + 1.5, y + 1.5), fill=(170, 205, 255))
    path = output / "frames" / f"motion.{frame:04d}.png"; image.save(path, optimize=True); return path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cache_dir", type=Path); parser.add_argument("metrics", type=Path); parser.add_argument("output", type=Path)
    parser.add_argument("--frames", default="1,6,11,16,21,26,31,36,41,46,51,56")
    parser.add_argument("--camera", choices=tuple(CAMERAS), default="tight-isometric")
    parser.add_argument("--edit-camera", action="store_true")
    parser.add_argument("--portrait-edit", action="store_true")
    parser.add_argument("--reuse-derived", action="store_true")
    parser.add_argument("--derived-dir", type=Path)
    parser.add_argument("--width", type=int, default=480); parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args(); frames = [int(value) for value in args.frames.split(",")]
    args.output.mkdir(parents=True, exist_ok=True); (args.output / "frames").mkdir(exist_ok=True)
    metrics = json.loads(args.metrics.read_text(encoding="utf-8")); derived = (args.derived_dir or args.output).resolve()
    if not args.reuse_derived:
        for frame in frames:
            derive_frame(args.cache_dir.resolve(), frame, metrics, args.output.resolve())
    else:
        for frame in frames:
            required = [derived / f"{prefix}.{frame:04d}.bgeo.sc" for prefix in ("field", "hairs", "agents", "trail-starts", "trails")]
            missing = [path for path in required if not path.is_file()]
            if missing:
                raise FileNotFoundError(f"missing derived motion geometry: {missing[0]}")
    hip = args.output / "scar-tissue-motion-check.hiplc"
    hou.hipFile.clear(suppress_save_prompt=True)
    geo = hou.node("/obj").createNode("geo", "SCAR_TISSUE_MOTION_CHECK_SOURCE")
    for child in geo.children(): child.destroy()
    file_node = geo.createNode("file", "AUTHORITATIVE_CACHE"); file_node.parm("file").set(str(args.cache_dir.resolve() / "vex-state.$F4.bgeo.sc"))
    file_node.setPosition(hou.Vector2(0, 0)); geo.setPosition(hou.Vector2(0, 0)); hou.hipFile.save(str(hip))
    rendered = [] if args.build_only else [render_frame(args.output.resolve(), derived, frame, args.camera, args.width, args.edit_camera, args.portrait_edit) for frame in frames]
    receipt = {
        "schema_version": 1, "operation": "motion-check", "render_engine": "software-flat-proxy",
        "opengl_status": "unavailable-headless-vulkan-crash", "source_authority": "vex-geometry-cache",
        "source_cache": args.cache_dir.resolve().as_posix(), "source_behavior_component_id": "component-behavior-b3bcc837c3e2",
        "source_look_component_id": "component-look-6013004ba32c", "source_palette_component_id": "component-palette-a52433fdb147",
        "frames": frames, "camera": "A-B-C-A-portrait-edit" if args.portrait_edit else "A-B-C-A-edit" if args.edit_camera else args.camera,
        "camera_parameters": "animated-from-shared-portrait-contract" if args.portrait_edit else "animated-from-shared-edit-contract" if args.edit_camera else CAMERAS[args.camera],
        "aspect_ratio": [9, 16] if args.portrait_edit else [16, 9], "width": args.width, "height": frame_dimensions(args.width, args.portrait_edit)[1],
        "display_mode": "flat-software-proxy", "karma_invoked": False,
        "hip": {"path": hip.name, "bytes": hip.stat().st_size, "sha256": sha(hip)},
        "rendered_frames": [{"path": path.relative_to(args.output.resolve()).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)} for path in rendered],
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output.resolve())


if __name__ == "__main__": main()
