"""Render a resumable contiguous range of the final portrait sequence."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path

import hou

ROOT = Path(__file__).resolve().parents[1]
HIP = ROOT / "work/studio/handoffs/scar-tissue-abc-a-v1/scar-tissue-abc-a-handoff.hiplc"
OUTPUT = HIP.parent / "portrait-frames"
TEMP_OUTPUT = OUTPUT / ".render-temp"
MINIMUM_EXR_BYTES = 1_000_000
MINIMUM_PNG_BYTES = 100_000
OUTPUT_RESOLUTION = (1080, 1920)
TONEMAP_FILTER = (
    "zscale=transfer=linear,tonemap=tonemap=hable,"
    "zscale=transfer=bt709,format=rgb24"
)


def frame_path(frame: int) -> Path:
    return OUTPUT / f"scar-tissue-portrait-{frame:04d}.png"


def temporary_exr_path(frame: int) -> Path:
    return TEMP_OUTPUT / f"scar-tissue-portrait-{frame:04d}.exr"


def complete(frame: int) -> bool:
    path = frame_path(frame)
    return path.is_file() and path.stat().st_size >= MINIMUM_PNG_BYTES


def exr_complete(frame: int) -> bool:
    path = temporary_exr_path(frame)
    return path.is_file() and path.stat().st_size >= MINIMUM_EXR_BYTES


def convert_to_png(ffmpeg: str, frame: int) -> None:
    source = temporary_exr_path(frame)
    target = frame_path(frame)
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-vf",
            TONEMAP_FILTER,
            "-frames:v",
            "1",
            str(target),
        ],
        check=True,
    )
    if not complete(frame):
        raise RuntimeError(f"tonemapped PNG was not created: {frame}")
    source.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    args = parser.parse_args()
    if not 1 <= args.start <= args.end <= 1260:
        raise ValueError("range must be within frames 1–1260")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    TEMP_OUTPUT.mkdir(parents=True, exist_ok=True)

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to create tonemapped PNG frames")

    missing = [frame for frame in range(args.start, args.end + 1) if not complete(frame)]
    report = {
        "hip": str(HIP),
        "requested_range": [args.start, args.end],
        "existing_complete_frames": (args.end - args.start + 1) - len(missing),
        "missing_frames": missing,
        "output_format": "PNG",
        "output_resolution": list(OUTPUT_RESOLUTION),
        "source_transfer": "linear",
        "tonemap": "Hable",
        "output_transfer": "BT.709",
        "temporary_exr_policy": "delete after verified PNG conversion",
        "started_at_unix": time.time(),
        "frames": [],
    }
    receipt = OUTPUT / f"range-{args.start:04d}-{args.end:04d}-receipt.json"
    receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not missing:
        report["completed"] = True
        report["completed_at_unix"] = time.time()
        receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return

    hou.hipFile.load(str(HIP), suppress_save_prompt=True)
    settings = hou.node("/stage/portrait_9x16_settings")
    render = hou.node("/stage/portrait_9x16_render")
    if settings is None or render is None:
        raise RuntimeError("missing final portrait branch")
    settings.parm("resolutionx").set(OUTPUT_RESOLUTION[0])
    actual_resolution = (
        settings.parm("resolutionx").eval(),
        settings.parm("resolutiony").eval(),
    )
    if actual_resolution != OUTPUT_RESOLUTION:
        raise RuntimeError(
            f"unexpected derived portrait resolution: {actual_resolution}"
        )

    for frame in missing:
        started = time.perf_counter()
        reused_temporary_exr = exr_complete(frame)
        if not reused_temporary_exr:
            temporary_exr = temporary_exr_path(frame)
            settings.parm("picture").set(str(temporary_exr))
            hou.setFrame(frame)
            render.render(frame_range=(frame, frame, 1))
            if not exr_complete(frame):
                raise RuntimeError(f"temporary EXR was not created: {frame}")
        convert_to_png(ffmpeg, frame)
        elapsed = time.perf_counter() - started
        frame_report = {
            "frame": frame,
            "output": str(frame_path(frame)),
            "bytes": frame_path(frame).stat().st_size,
            "elapsed_seconds": elapsed,
            "reused_temporary_exr": reused_temporary_exr,
        }
        report["frames"].append(frame_report)
        report["updated_at_unix"] = time.time()
        receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(frame_report), flush=True)

    report["completed"] = True
    report["completed_at_unix"] = time.time()
    receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
