"""Render a cached Memory Field frame through the Karma field-study look."""

from __future__ import annotations

import argparse
from pathlib import Path

import hou


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("hip", type=Path)
    parser.add_argument("cache", type=Path)
    parser.add_argument("image", type=Path)
    parser.add_argument("frame", type=int)
    args = parser.parse_args()
    hou.hipFile.load(str(args.hip.resolve()), suppress_save_prompt=True, ignore_load_warnings=False)
    cache = hou.node("/obj/field_study_geometry/cached_state")
    settings = hou.node("/stage/field_study_settings")
    render = hou.node("/stage/field_study_render")
    if cache is None or settings is None or render is None:
        raise RuntimeError("generated HIP is missing the field-study look network")
    cache.parm("file").set(str(args.cache.resolve()))
    settings.parm("picture").set(args.image.resolve().as_posix())
    args.image.resolve().parent.mkdir(parents=True, exist_ok=True)
    hou.setFrame(args.frame)
    render.render(frame_range=(args.frame, args.frame, 1))
    print(f"field_study_frame: {args.frame}")
    print(f"field_study_image: {args.image.resolve()}")


if __name__ == "__main__":
    main()
