from __future__ import annotations

from typing import Any

CAMERA_PRESETS = {
    "tight-isometric": {"tx": 7.8, "ty": 11.5, "tz": 15.8, "rx": -34.0, "ry": 25.5, "focal_length": 64.0},
    "low-grazing": {"tx": 7.8, "ty": 3.8, "tz": 15.8, "rx": -15.0, "ry": 25.5, "focal_length": 64.0},
    "intimate-tracking": {"tx": 6.1, "ty": 5.1, "tz": 13.9, "rx": -21.5, "ry": 25.5, "focal_length": 68.0},
}

SHOTS: list[dict[str, Any]] = [
    {"label": "A1", "camera": "A", "preset": "tight-isometric", "frames": [1, 315], "motion": {"tx": [7.62, 7.98], "ty": [11.5, 11.5], "tz": [15.92, 15.68]}},
    {"label": "B", "camera": "B", "preset": "low-grazing", "frames": [316, 630], "motion": {"tx": [7.8, 7.8], "ty": [3.88, 3.68], "tz": [16.05, 15.45]}},
    {"label": "C", "camera": "C", "preset": "intimate-tracking", "frames": [631, 945], "motion": {"tx": [5.92, 6.30], "ty": [5.1, 5.1], "tz": [13.9, 13.82]}},
    {"label": "A2", "camera": "A", "preset": "tight-isometric", "frames": [946, 1260], "motion": {"tx": [7.98, 7.62], "ty": [11.5, 11.5], "tz": [15.68, 15.92]}},
]

PORTRAIT_FOCAL_LENGTHS = {"A1": 125.0, "B": 140.0, "C": 150.0, "A2": 125.0}
PORTRAIT_VIEW_CONTROLS = {
    "A": {"tx": 7.8, "ty": 11.5, "tz": 15.8, "rx": -34.0, "ry": 25.5},
    "B": {"tx": 7.8, "ty": 3.5, "tz": 15.75, "rx": -15.0, "ry": 25.5},
    "C": {"tx": 6.11, "ty": 5.1, "tz": 13.86, "rx": -21.5, "ry": 25.5},
}


def frame_dimensions(width: int, portrait: bool = False) -> tuple[int, int]:
    return width, round(width * 16 / 9) if portrait else round(width * 9 / 16)


def camera_at_frame(frame: int) -> dict[str, float | str]:
    if frame < 1 or frame > 1260:
        raise ValueError(f"frame outside A-B-C-A edit: {frame}")
    shot = next(item for item in SHOTS if item["frames"][0] <= frame <= item["frames"][1])
    start, end = shot["frames"]
    amount = (frame - start) / max(1, end - start)
    preset = CAMERA_PRESETS[shot["preset"]]
    result: dict[str, float | str] = {"shot": shot["label"]}
    for name in ("tx", "ty", "tz"):
        first, last = shot["motion"][name]
        result[name] = first + (last - first) * amount
    for name in ("rx", "ry", "focal_length"):
        result[name] = preset[name]
    return result


def portrait_camera_at_frame(frame: int) -> dict[str, float | str | list[int]]:
    result: dict[str, float | str | list[int]] = dict(camera_at_frame(frame))
    shot = str(result["shot"])
    result["focal_length"] = PORTRAIT_FOCAL_LENGTHS[shot]
    result["aspect_ratio"] = [9, 16]
    if shot == "B":
        result["ty"] = float(result["ty"]) - 0.28
    return result


def portrait_control_at_frame(frame: int) -> str:
    shot = str(portrait_camera_at_frame(frame)["shot"])
    return "A" if shot in {"A1", "A2"} else shot


def portrait_stage_control_path(view: str) -> str:
    if view not in PORTRAIT_VIEW_CONTROLS:
        raise ValueError(f"unknown portrait view control: {view}")
    return f"/stage/PORTRAIT_VIEW_{view}_CTRL"


def portrait_controlled_camera_at_frame(frame: int) -> dict[str, float | str | list[int]]:
    direct = portrait_camera_at_frame(frame)
    control_name = portrait_control_at_frame(frame)
    control = PORTRAIT_VIEW_CONTROLS[control_name]
    result = dict(direct)
    for name in ("tx", "ty", "tz", "rx", "ry"):
        drift = float(direct[name]) - control[name]
        result[name] = control[name] + drift
    result["control"] = control_name
    return result
