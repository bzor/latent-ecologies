"""Export a study.json sidecar for the design-overlay generator from a HIP.

Implements the "Houdini exporter" stage of design-overlay-generator/DESIGN.md:

- study text identity merged from the canonical study card
  (`00_study/study-card.json`; CLI flags override card fields);
- per-frame subject bbox projected through the render camera into normalized
  screen space (origin top-left, matching the overlay canvas);
- per-frame screen-space **point tracks** for overlay callouts: points flagged
  in the HIP via a point group (default `overlay_track`, optional string
  attrib `track_label` for names) and/or point numbers passed on the CLI —
  each track records screen position, camera depth, and optionally sampled
  point float attributes as normalized value series;
- optional scalar series from float detail attributes on the subject SOP.

Assumes constant point topology across the frame range (true for the studio's
cache sequences and live HDAs); tracks follow point numbers, not ids.

Run under hython with PYTHONPATH=src against the locked Look HIP snapshot:

    hython houdini/export_overlay_study.py look.hiplc \
        --sop /obj/PLAYGROUND_SIM/OUT_SIMULATION --camera /obj/main_cam \
        --start 205 --end 650 --card studies/<study>/00_study/study-card.json \
        --track 1234=leader --track-value speed --out study.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import hou

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from houdini_ai.study_card import load_study_card, overlay_fields  # noqa: E402
from houdini_ai.overlay_parameter_manifest import (  # noqa: E402
    load_overlay_parameter_manifest,
    overlay_manifest_fields,
)


def _camera_ndc(camera: hou.ObjNode, position: hou.Vector3, frame: float) -> tuple[float, float, float]:
    """World position -> (x, y, camera_depth) with x/y in [0,1], origin top-left."""
    to_camera = camera.worldTransformAtTime(hou.frameToTime(frame)).inverted()
    local = position * to_camera
    focal = camera.parm("focal").evalAtFrame(frame)
    aperture = camera.parm("aperture").evalAtFrame(frame)
    resx = camera.parm("resx").evalAtFrame(frame)
    resy = camera.parm("resy").evalAtFrame(frame)
    pixel_aspect = camera.parm("aspect").evalAtFrame(frame) or 1.0
    vertical_aperture = aperture * (resy / resx) / pixel_aspect
    depth = -local.z()
    if depth <= 1e-6:
        raise ValueError("point is behind the camera")
    x = (local.x() * focal) / (depth * aperture) + 0.5
    y = (local.y() * focal) / (depth * vertical_aperture) + 0.5
    return x, 1.0 - y, depth


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def frame_bbox(geometry: hou.Geometry, sop_transform: hou.Matrix4, camera: hou.ObjNode, frame: float) -> list[float] | None:
    if not geometry.points():
        return None
    bounds = geometry.boundingBox()
    corners = []
    for index in range(8):
        world = hou.Vector3(
            bounds.minvec()[0] if index & 1 == 0 else bounds.maxvec()[0],
            bounds.minvec()[1] if index & 2 == 0 else bounds.maxvec()[1],
            bounds.minvec()[2] if index & 4 == 0 else bounds.maxvec()[2],
        ) * sop_transform
        try:
            x, y, _ = _camera_ndc(camera, world, frame)
        except ValueError:
            continue
        corners.append((x, y))
    if not corners:
        return None
    xs = [corner[0] for corner in corners]
    ys = [corner[1] for corner in corners]
    return [
        _clamp(min(xs), -0.5, 1.5), _clamp(min(ys), -0.5, 1.5),
        _clamp(max(xs), -0.5, 1.5), _clamp(max(ys), -0.5, 1.5),
    ]


def collect_track_targets(
    geometry: hou.Geometry,
    group_name: str,
    label_attrib: str,
    cli_tracks: list[str],
) -> dict[str, int]:
    """Resolve {label: point_number} from the flag group and CLI entries."""
    targets: dict[str, int] = {}
    group = geometry.findPointGroup(group_name)
    has_label = geometry.findPointAttrib(label_attrib) is not None
    if group is not None:
        for point in group.points():
            label = point.stringAttribValue(label_attrib) if has_label else ""
            targets[label.strip() or f"P{point.number()}"] = point.number()
    for entry in cli_tracks:
        number_text, _, label = entry.partition("=")
        number = int(number_text)
        targets[label.strip() or f"P{number}"] = number
    return targets


def normalize(values: list[float | None]) -> list[float | None]:
    present = [value for value in values if value is not None]
    if not present:
        return values
    low, high = min(present), max(present)
    span = high - low
    return [None if value is None else (0.0 if span <= 0 else round((value - low) / span, 5)) for value in values]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hip", type=Path)
    parser.add_argument("--sop", required=True, help="subject SOP path, e.g. /obj/PLAYGROUND_SIM/OUT_SIMULATION")
    parser.add_argument("--camera", required=True, help="camera OBJ path, e.g. /obj/main_cam")
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--fps", type=int, help="defaults to the HIP fps")
    parser.add_argument("--card", type=Path, help="canonical 00_study/study-card.json (text identity source)")
    parser.add_argument("--parameter-manifest", type=Path, help="locked-HIP overlay parameter manifest")
    parser.add_argument(
        "--behavior-number", type=int,
        help="promoted behavior this variation descends from; supplies the bhvr_NNN part of the "
             "stem when the HDA does not expose one (default 1)",
    )
    parser.add_argument("--id", help="overlay id override, e.g. STUDY-003")
    parser.add_argument("--number", type=int, help="override (required when no --card)")
    parser.add_argument("--title", help="override (required when no --card)")
    parser.add_argument("--subtitle", help="override")
    parser.add_argument("--source", help="override")
    parser.add_argument("--date", help="override; ISO date recorded in the sidecar")
    parser.add_argument("--solver-name", default="POP/VEX")
    parser.add_argument("--solver-dt", default="")
    parser.add_argument("--solver-substeps", type=int, default=1)
    parser.add_argument("--solver-seed", type=int, default=0)
    parser.add_argument("--param", action="append", default=[], metavar="LABEL=VALUE", help="appended after card params")
    parser.add_argument("--series", action="append", default=[], metavar="NAME=DETAIL_ATTRIB")
    parser.add_argument("--track", action="append", default=[], metavar="POINTNUM[=LABEL]",
                        help="track a point by number without editing the HIP")
    parser.add_argument("--track-group", default="overlay_track", help="point group flagging tracked points")
    parser.add_argument("--track-label-attrib", default="track_label", help="string point attrib naming tracks")
    parser.add_argument("--track-value", action="append", default=[], metavar="ATTRIB",
                        help="float point attrib sampled per tracked point per frame")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    if args.card:
        text = overlay_fields(load_study_card(args.card))
    else:
        if args.number is None or args.title is None:
            raise SystemExit("--number and --title are required when no --card is given")
        text = {"id": "", "number": 0, "title": "", "subtitle": "", "summary": "",
                "bullets": [], "params": [], "source": "", "date": "", "credits": ""}
    for key in ("id", "number", "title", "subtitle", "source", "date"):
        override = getattr(args, key)
        if override is not None:
            text[key] = override
    manifest_fields = {}
    manifest_params: list[list[str]] = []
    if args.parameter_manifest:
        manifest_fields = overlay_manifest_fields(
            load_overlay_parameter_manifest(args.parameter_manifest), args.behavior_number
        )
        manifest_params = manifest_fields.pop("params")
        text["variation"] = manifest_fields.pop("variation")
    text["params"] = [list(pair) for pair in text["params"]] + manifest_params + [item.split("=", 1) for item in args.param]

    hou.hipFile.load(str(args.hip.resolve()).replace("\\", "/"), suppress_save_prompt=True, ignore_load_warnings=True)
    sop = hou.node(args.sop)
    camera = hou.node(args.camera)
    if sop is None or camera is None:
        raise SystemExit(f"missing node: {args.sop if sop is None else args.camera}")

    frames = list(range(args.start, args.end + 1))
    first_geometry = sop.geometryAtFrame(frames[0])
    if first_geometry is None:
        raise SystemExit(f"{args.sop} produced no geometry at frame {frames[0]}")
    targets = collect_track_targets(first_geometry, args.track_group, args.track_label_attrib, args.track)
    value_attribs = [
        name for name in args.track_value
        if first_geometry.findPointAttrib(name) is not None
    ]
    skipped_values = sorted(set(args.track_value) - set(value_attribs))

    series_specs = dict(item.split("=", 1) for item in args.series)
    series_raw: dict[str, list[float]] = {name: [] for name in series_specs}
    bbox: list[list[float]] = []
    previous = [0.25, 0.25, 0.75, 0.75]
    tracks: dict[str, dict] = {
        label: {"screen": [], "depth": [], "values": {name: [] for name in value_attribs}}
        for label in targets
    }

    for frame in frames:
        hou.setFrame(frame)
        geometry = sop.geometryAtFrame(frame)
        sop_transform = sop.parent().worldTransformAtTime(hou.frameToTime(frame))

        box = frame_bbox(geometry, sop_transform, camera, frame) if geometry is not None else None
        if box is None:
            box = previous
        bbox.append([round(value, 5) for value in box])
        previous = box

        for name, attrib in series_specs.items():
            value = 0.0
            if geometry is not None and geometry.findGlobalAttrib(attrib) is not None:
                value = float(geometry.attribValue(attrib))
            series_raw[name].append(value)

        point_count = len(geometry.points()) if geometry is not None else 0
        for label, number in targets.items():
            track = tracks[label]
            if number >= point_count:
                track["screen"].append(None)
                track["depth"].append(None)
                for name in value_attribs:
                    track["values"][name].append(None)
                continue
            point = geometry.point(number)
            world = point.position() * sop_transform
            try:
                x, y, depth = _camera_ndc(camera, world, frame)
                track["screen"].append([round(_clamp(x, -0.5, 1.5), 5), round(_clamp(y, -0.5, 1.5), 5)])
                track["depth"].append(round(depth, 5))
            except ValueError:
                track["screen"].append(None)
                track["depth"].append(None)
            for name in value_attribs:
                track["values"][name].append(float(point.floatAttribValue(name)))

    for track in tracks.values():
        track["values"] = {name: normalize(values) for name, values in track["values"].items()}

    study = {
        **text,
        **manifest_fields,
        "solver": {
            "name": args.solver_name,
            "dt": args.solver_dt,
            "substeps": args.solver_substeps,
            "seed": args.solver_seed,
        },
        "fps": args.fps or int(round(hou.fps())),
        "frames": len(frames),
        "frame_range": [args.start, args.end],
        "series": {
            name: normalize(values) for name, values in series_raw.items()
        },
        "bbox": bbox,
        "tracks": tracks,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(study, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "out": str(args.out),
        "frames": len(frames),
        "series": sorted(series_specs),
        "tracks": sorted(tracks),
        "track_values": value_attribs,
        "skipped_track_values": skipped_values,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
