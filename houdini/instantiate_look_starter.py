"""Instantiate an artist-ready Look starter HIP from a look-setup template and a promoted behavior HDA.

Implements the live-HDA handoff contract from docs/ARTIST_LED_LOOK_HANDOFF.md:
the promoted behavior enters Look Development as a re-simmable HDA node wired
into the look template's simulation entry point. The template's legacy cache
File SOP is left in place but disconnected as a fallback reference.

Run under hython:

    hython houdini/instantiate_look_starter.py \
        --hda studies/<study>/01_behavior/03_promoted/<asset>.hda \
        --output studies/<study>/02_look/look.hiplc
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import hou

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROJECT_CONFIG = PROJECT_ROOT / "config" / "project.json"
FALLBACK_FPS = 30

DEFAULT_TEMPLATE_DIR = Path(__file__).resolve().parent / "look_setups" / "basic"
SIM_CONTAINER = "/obj/PLAYGROUND_SIM"
SIM_ENTRY = "/obj/PLAYGROUND_SIM/ENSURE_POINT_VISIBILITY"
LEGACY_CACHE_SOURCE = "/obj/PLAYGROUND_SIM/SOURCE_PROMOTED_SIMULATION"
SIM_OUTPUT = "/obj/PLAYGROUND_SIM/OUT_SIMULATION"
RENDER_PICTURE_PARM = "/stage/RENDER_KARMA_SETTINGS/picture"
HDA_NODE_NAME = "PROMOTED_BEHAVIOR"


def project_default_fps() -> int:
    """The project-wide delivery frame rate from config/project.json."""
    try:
        return int(json.loads(PROJECT_CONFIG.read_text(encoding="utf-8"))["default_fps"])
    except (OSError, KeyError, ValueError, TypeError):
        return FALLBACK_FPS


def native(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def node_errors(root: hou.Node) -> list[str]:
    errors: list[str] = []
    for child in (root, *root.allSubChildren()):
        errors.extend(f"{child.path()}: {error}" for error in child.errors())
    return errors


def sop_definition_in_file(hda_path: Path) -> hou.HDADefinition:
    definitions = [
        definition
        for definition in hou.hda.definitionsInFile(native(hda_path))
        if definition.nodeTypeCategory() == hou.sopNodeTypeCategory()
    ]
    if not definitions:
        raise ValueError(f"no SOP HDA definition found in {hda_path}")
    if len(definitions) > 1:
        names = [definition.nodeTypeName() for definition in definitions]
        raise ValueError(f"expected exactly one SOP definition, found {names}")
    return definitions[0]


def missing_external_dependencies(setup: dict[str, Any]) -> list[str]:
    return [
        dependency
        for dependency in setup.get("external_dependencies", [])
        if not Path(dependency).exists()
    ]


def instantiate(
    template_dir: Path,
    hda_path: Path,
    output_hip: Path,
    render_picture: str | None,
    cook_frames: list[int],
    force: bool,
    frame_range: tuple[int, int] | None = None,
    fps: int | None = None,
) -> dict[str, Any]:
    setup = json.loads((template_dir / "setup.json").read_text(encoding="utf-8"))
    template_hip = template_dir / setup["template"]["path"]
    if not template_hip.exists():
        raise FileNotFoundError(f"template HIP not found: {template_hip}")
    if not hda_path.exists():
        raise FileNotFoundError(f"behavior HDA not found: {hda_path}")
    if output_hip.exists() and not force:
        raise FileExistsError(
            f"{output_hip} already exists; refusing to overwrite a possibly artist-owned "
            "file without --force"
        )

    template_sha = sha256_file(template_hip)
    recorded_sha = setup["template"].get("sha256")
    template_drift = recorded_sha is not None and template_sha != recorded_sha

    output_hip.parent.mkdir(parents=True, exist_ok=True)
    hda_copy = output_hip.parent / hda_path.name
    if hda_copy.resolve() != hda_path.resolve():
        shutil.copy2(hda_path, hda_copy)
    shutil.copy2(template_hip, output_hip)

    definition = sop_definition_in_file(hda_copy)
    type_name = definition.nodeTypeName()

    hou.hipFile.load(native(output_hip), suppress_save_prompt=True, ignore_load_warnings=True)
    hou.hda.installFile(native(hda_copy))

    container = hou.node(SIM_CONTAINER)
    entry = hou.node(SIM_ENTRY)
    legacy_source = hou.node(LEGACY_CACHE_SOURCE)
    if container is None or entry is None:
        raise RuntimeError(f"template does not match contract: missing {SIM_CONTAINER} or {SIM_ENTRY}")

    behavior = container.node(HDA_NODE_NAME) or container.createNode(type_name, HDA_NODE_NAME)
    entry.setInput(0, behavior)
    if legacy_source is not None:
        legacy_source.setDisplayFlag(False)
        legacy_source.setRenderFlag(False)
        legacy_source.setComment(
            "Legacy cache fallback. The live handoff is the PROMOTED_BEHAVIOR HDA; "
            "rewire ENSURE_POINT_VISIBILITY back here only if a baked cache is required."
        )
        legacy_source.setGenericFlag(hou.nodeFlag.DisplayComment, True)
        behavior.setPosition(legacy_source.position() + hou.Vector2(3.0, 0.0))

    if render_picture:
        picture = hou.parm(RENDER_PICTURE_PARM)
        if picture is None:
            raise RuntimeError(f"template does not match contract: missing {RENDER_PICTURE_PARM}")
        picture.set(render_picture)

    # The look templates carry whatever frame rate the source experiment used, so the
    # project delivery rate is set explicitly rather than inherited.
    target_fps = project_default_fps() if fps is None else fps
    template_fps = hou.fps()
    if target_fps and float(target_fps) != float(template_fps):
        hou.setFps(float(target_fps))

    if frame_range is not None:
        start, end = frame_range
        if end <= start:
            raise ValueError(f"invalid frame range: {frame_range}")
        hou.playbar.setFrameRange(start, end)
        hou.playbar.setPlaybackRange(start, end)

    hou.hipFile.save(native(output_hip))

    hou.hipFile.clear(suppress_save_prompt=True)
    hou.hipFile.load(native(output_hip), suppress_save_prompt=True, ignore_load_warnings=True)
    reopened_container = hou.node(SIM_CONTAINER)
    output_node = hou.node(SIM_OUTPUT)
    if reopened_container is None or output_node is None:
        raise RuntimeError("reopened starter is missing its simulation network")
    cooks: list[dict[str, Any]] = []
    for frame in cook_frames:
        hou.setFrame(frame)
        output_node.cook(force=True)
        geometry = output_node.geometry()
        cooks.append(
            {
                "frame": frame,
                "points": len(geometry.points()) if geometry is not None else None,
                "errors": node_errors(reopened_container),
            }
        )
    failed = [cook for cook in cooks if not cook["points"] or cook["errors"]]

    receipt = {
        "schema_version": 1,
        "state": "artist-ready-starter",
        "contract": "live-hda",
        "setup_id": setup["id"],
        "template": {
            "path": native(template_hip),
            "sha256": template_sha,
            "drifted_from_setup_record": template_drift,
        },
        "behavior_hda": {
            "source_path": native(hda_path),
            "study_copy": native(hda_copy),
            "sha256": sha256_file(hda_copy),
            "node_type": type_name,
            "node_path": f"{SIM_CONTAINER}/{HDA_NODE_NAME}",
        },
        "legacy_cache_fallback": LEGACY_CACHE_SOURCE if legacy_source is not None else None,
        "starter_hip": {
            "path": native(output_hip),
            "bytes": output_hip.stat().st_size,
            "sha256": sha256_file(output_hip),
        },
        "render_picture": render_picture or hou.parm(RENDER_PICTURE_PARM).evalAsString(),
        "frame_range": list(frame_range) if frame_range is not None else None,
        "fps": hou.fps(),
        "template_fps": template_fps,
        "fps_source": "explicit" if fps is not None else "config/project.json default_fps",
        "houdini_version": hou.applicationVersionString(),
        "reopen_cooks": cooks,
        "reopen_passed": not failed,
        "missing_external_dependencies": missing_external_dependencies(setup),
        "note": (
            "Frame 1 is the HDA's initial state; the simulation is live and re-simmable. "
            "The template playback range is inherited from the setup and may need adjusting "
            "to the behavior's own timing. The frame rate is set to the project delivery rate "
            "rather than inherited from the template."
        ),
    }
    receipt_path = output_hip.with_suffix(".starter-receipt.json")
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    if failed:
        raise RuntimeError(f"reopen verification failed: {failed}")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template-dir", type=Path, default=DEFAULT_TEMPLATE_DIR)
    parser.add_argument("--hda", type=Path, required=True, help="promoted behavior HDA file")
    parser.add_argument("--output", type=Path, required=True, help="starter HIP path, normally <study>/02_look/look.hiplc")
    parser.add_argument("--render-picture", help="study-local render output path for the Karma picture parm")
    parser.add_argument("--cook-frames", type=int, nargs="+", default=[1, 2])
    parser.add_argument("--force", action="store_true", help="overwrite an existing output HIP")
    parser.add_argument(
        "--frame-range", type=int, nargs=2, metavar=("START", "END"),
        help="playback/global frame range to set on the starter HIP",
    )
    parser.add_argument(
        "--fps", type=int,
        help="frame rate for the starter HIP; defaults to default_fps in config/project.json",
    )
    args = parser.parse_args()
    instantiate(
        args.template_dir.resolve(),
        args.hda.resolve(),
        args.output.resolve(),
        args.render_picture,
        args.cook_frames,
        args.force,
        tuple(args.frame_range) if args.frame_range else None,
        args.fps,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
