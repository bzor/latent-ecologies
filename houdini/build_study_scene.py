"""Build or probe-render the generated Study 001 Solaris/Karma scene."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import hou


def set_parm(node: hou.Node, name: str, value: object) -> None:
    parm = node.parm(name)
    if parm is None:
        raise RuntimeError(f"{node.path()} has no parameter named {name}")
    parm.set(value)


def build(config_path: Path, hip_path: Path, image_path: Path) -> None:
    effective = json.loads(config_path.read_text(encoding="utf-8"))
    study = effective["study"]
    simulation = study["simulation"]
    render_config = study["render"]

    hou.hipFile.clear(suppress_save_prompt=True)
    hou.setFps(simulation["fps"])
    hou.playbar.setFrameRange(simulation["frame_start"], simulation["frame_end"])
    hou.playbar.setPlaybackRange(simulation["frame_start"], simulation["frame_end"])
    hou.setFrame(simulation["frame_start"])

    stage = hou.node("/stage")
    if stage is None:
        raise RuntimeError("Houdini scene has no /stage LOP network")

    sphere = stage.createNode("sphere", "memory_field_subject")
    set_parm(sphere, "primpath", "/memory_field/subject")
    color_parms = (
        "xn__primvarsdisplayColor_p8ar",
        "xn__primvarsdisplayColor_p8ag",
        "xn__primvarsdisplayColor_p8ab",
    )
    for channel, value in zip(color_parms, (0.12, 0.42, 0.8)):
        set_parm(sphere, channel, value)

    camera = stage.createNode("camera", "static_observation_camera")
    camera.setInput(0, sphere)
    set_parm(camera, "primpath", "/cameras/static_observation")
    set_parm(camera, "tz", 8.0)

    light = stage.createNode("distantlight::2.0", "field_study_light")
    light.setInput(0, camera)
    set_parm(light, "primpath", "/lights/field_study")
    set_parm(light, "rx", -35.0)
    set_parm(light, "ry", 25.0)

    settings = stage.createNode("karmarendersettings", "karma_settings")
    settings.setInput(0, light)
    set_parm(settings, "camera", "/cameras/static_observation")
    set_parm(settings, "picture", image_path.as_posix())
    set_parm(settings, "res_mode", "manual")
    set_parm(settings, "resolutionx", render_config["width"])
    # Karma derives Y from X by default and locks the expression-backed channel.
    # Unlock it so the versioned manifest remains authoritative for both axes.
    settings.parm("resolutiony").lock(False)
    set_parm(settings, "resolutiony", render_config["height"])
    set_parm(settings, "samplesperpixel", 4)

    render = stage.createNode("usdrender_rop", "diagnostic_render")
    render.setInput(0, settings)
    set_parm(render, "renderer", "Karma CPU")
    set_parm(render, "soho_foreground", True)
    set_parm(render, "mkpath", True)

    stage.layoutChildren()
    hip_path.parent.mkdir(parents=True, exist_ok=True)
    hou.hipFile.save(str(hip_path))
    print(f"hip: {hip_path}")


def probe(hip_path: Path, frame: int) -> None:
    hou.hipFile.load(str(hip_path), suppress_save_prompt=True, ignore_load_warnings=False)
    render = hou.node("/stage/diagnostic_render")
    if render is None:
        raise RuntimeError("generated HIP has no /stage/diagnostic_render node")
    render.render(frame_range=(frame, frame, 1))
    print(f"probe_frame: {frame}")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("config", type=Path)
    build_parser.add_argument("hip", type=Path)
    build_parser.add_argument("image", type=Path)
    probe_parser = subparsers.add_parser("probe")
    probe_parser.add_argument("hip", type=Path)
    probe_parser.add_argument("frame", type=int)
    args = parser.parse_args()
    if args.__dict__.get("config") is not None:
        build(args.config.resolve(), args.hip.resolve(), args.image.resolve())
    else:
        probe(args.hip.resolve(), args.frame)


if __name__ == "__main__":
    main()
