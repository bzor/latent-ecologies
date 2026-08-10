"""Build and render the Milestone 1 headless Karma diagnostic scene."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import hou

ROOT = Path(os.environ.get("HDAI_PROJECT_ROOT", Path.cwd())).resolve()
sys.path.insert(0, str(ROOT / "src"))

from houdini_ai.diagnostic import build_receipt, validate_diagnostic_png, write_receipt  # noqa: E402


def set_parm(node: hou.Node, name: str, value: object) -> None:
    parm = node.parm(name)
    if parm is None:
        raise RuntimeError(f"{node.path()} has no parameter named {name}")
    parm.set(value)


def main() -> None:
    root = ROOT
    output_dir = root / "work" / "diagnostics"
    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = output_dir / "karma-headless.0001.png"
    hip_path = output_dir / "karma-headless.hiplc"
    receipt_path = output_dir / "karma-headless.receipt.json"

    stage = hou.node("/stage")
    if stage is None:
        raise RuntimeError("Houdini scene has no /stage LOP network")

    sphere = stage.createNode("sphere", "diagnostic_sphere")
    set_parm(sphere, "primpath", "/diagnostic/sphere")
    for channel, value in zip(("xn__primvarsdisplayColor_p8ar", "xn__primvarsdisplayColor_p8ag", "xn__primvarsdisplayColor_p8ab"), (0.12, 0.42, 0.8)):
        set_parm(sphere, channel, value)

    camera = stage.createNode("camera", "diagnostic_camera")
    camera.setInput(0, sphere)
    set_parm(camera, "primpath", "/cameras/diagnostic")
    set_parm(camera, "tz", 8.0)

    light = stage.createNode("distantlight::2.0", "diagnostic_light")
    light.setInput(0, camera)
    set_parm(light, "primpath", "/lights/diagnostic")
    set_parm(light, "rx", -35.0)
    set_parm(light, "ry", 25.0)

    settings = stage.createNode("karmarendersettings", "diagnostic_settings")
    settings.setInput(0, light)
    set_parm(settings, "camera", "/cameras/diagnostic")
    set_parm(settings, "picture", image_path.as_posix())
    set_parm(settings, "res_mode", "autoheight")
    set_parm(settings, "resolutionx", 320)
    set_parm(settings, "samplesperpixel", 4)

    render = stage.createNode("usdrender_rop", "diagnostic_render")
    render.setInput(0, settings)
    set_parm(render, "renderer", "Karma CPU")
    set_parm(render, "soho_foreground", True)
    set_parm(render, "mkpath", True)

    stage.layoutChildren()
    hou.hipFile.save(str(hip_path))
    render.render(frame_range=(1, 1, 1))

    image_metadata = validate_diagnostic_png(image_path)
    receipt = build_receipt(
        root,
        image_path,
        hip_path,
        image_metadata,
        {
            "build": hou.applicationVersionString(),
            "license": hou.licenseCategory().name(),
            "renderer": "Karma CPU",
        },
    )
    write_receipt(receipt_path, receipt)
    print(f"diagnostic_hip: {hip_path}")
    print(f"diagnostic_image: {image_path}")
    print(f"diagnostic_bytes: {image_path.stat().st_size}")
    print(f"diagnostic_receipt: {receipt_path}")


if __name__ == "__main__":
    main()
