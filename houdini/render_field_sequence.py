"""Render selected cached Memory Field frames in one persistent Houdini session."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import hou


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("hip", type=Path)
    parser.add_argument("cache_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("frames_json", type=Path)
    args = parser.parse_args()
    frames = json.loads(args.frames_json.read_text(encoding="utf-8"))
    if not isinstance(frames, list) or not all(isinstance(frame, int) for frame in frames):
        raise RuntimeError("frame selection must be a JSON array of integers")

    hou.hipFile.load(str(args.hip.resolve()), suppress_save_prompt=True, ignore_load_warnings=False)
    cache = hou.node("/obj/field_study_geometry/cached_state")
    settings = hou.node("/stage/field_study_settings")
    render = hou.node("/stage/field_study_render")
    if cache is None or settings is None or render is None:
        raise RuntimeError("generated HIP is missing the field-study look network")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for frame in frames:
        cache_path = args.cache_dir / f"state.{frame:04d}.bgeo.sc"
        image_path = args.output_dir / f"field-study.{frame:04d}.png"
        if not cache_path.is_file():
            raise RuntimeError(f"simulation cache is missing frame {frame}: {cache_path}")
        cache.parm("file").set(str(cache_path.resolve()))
        settings.parm("picture").set(image_path.resolve().as_posix())
        hou.setFrame(frame)
        render.render(frame_range=(frame, frame, 1))
        print(f"rendered_frame: {frame}", flush=True)


if __name__ == "__main__":
    main()
