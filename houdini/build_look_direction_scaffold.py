"""Build a deterministic parent-owned scaffold for one Look direction worker."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import hou

_CACHE_FRAME = re.compile(r"(\d{3,6})(?=\.(?:bgeo|vdb)(?:\.sc)?$)", re.IGNORECASE)


def native(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def set_parm(node: hou.Node, name: str, value: object) -> None:
    parm = node.parm(name)
    if parm is None:
        raise RuntimeError(f"{node.path()} has no parameter named {name}")
    parm.set(value)


def cache_expression(path: Path) -> str:
    return _CACHE_FRAME.sub(lambda match: f"$F{len(match.group(1))}", native(path))


def build(packet_path: Path, output_dir: Path, project_root: Path) -> None:
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    review = packet["review_contract"]
    scene_path = (output_dir / packet["workspace_layout"]["scene_stem"]).with_suffix(".hip")
    if scene_path.exists() or scene_path.is_symlink():
        raise RuntimeError(f"refusing to overwrite existing direction scaffold: {scene_path}")
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    (output_dir / "00_design").mkdir(parents=True, exist_ok=True)
    (output_dir / "02_probes").mkdir(parents=True, exist_ok=True)

    cache_records = packet["source_cache_receipt"]
    if not cache_records:
        raise RuntimeError("direction scaffold requires frozen Behavior caches")
    first_cache = (project_root / cache_records[0]["path"]).resolve()
    if not first_cache.is_file() or sha256(first_cache) != cache_records[0]["sha256"]:
        raise RuntimeError("direction scaffold source cache does not match the frozen receipt")
    frames = [
        int(match.group(1))
        for record in cache_records
        if (match := _CACHE_FRAME.search(str(record["path"]))) is not None
    ]

    hou.hipFile.clear(suppress_save_prompt=True)
    hou.playbar.setFrameRange(min(frames), max(frames))
    hou.playbar.setPlaybackRange(min(frames), max(frames))
    hou.setFrame(min(frames))

    geo = hou.node("/obj").createNode("geo", "LOOK_DIRECTION")
    for child in geo.children():
        child.destroy()
    source = geo.createNode("file", "SOURCE_FROZEN_CACHE")
    set_parm(source, "file", cache_expression(first_cache))
    look_input = geo.createNode("null", "LOOK_INPUT")
    look_input.setInput(0, source)
    output = geo.createNode("null", "OUT_FINAL")
    output.setInput(0, look_input)
    output.setDisplayFlag(True)
    output.setRenderFlag(True)
    source.setPosition(hou.Vector2((0, 6)))
    look_input.setPosition(hou.Vector2((0, 3)))
    output.setPosition(hou.Vector2((0, -6)))
    source.cook(force=True)
    if source.geometry() is None or not source.geometry().points():
        raise RuntimeError("direction scaffold frozen cache cooked no points")

    stage = hou.node("/stage")
    for child in stage.children():
        child.destroy()
    paths = review["required_scene_nodes"]
    imp = stage.createNode("sopimport", Path(paths["look_import"]).name)
    set_parm(imp, "soppath", output.path())
    set_parm(imp, "enable_pathprefix", 1)
    set_parm(imp, "pathprefix", "/World/Look")

    library = stage.createNode("materiallibrary", Path(paths["material_library"]).name)
    library.setInput(0, imp)
    set_parm(library, "matpathprefix", "/materials/")
    shader = library.createNode("mtlxstandard_surface", "LOOK_SHADER")
    material = library.createNode("mtlxsurfacematerial", "LOOK_MATERIAL")
    material.setInput(0, shader)
    set_parm(shader, "base_colorr", 0.45)
    set_parm(shader, "base_colorg", 0.48)
    set_parm(shader, "base_colorb", 0.52)
    set_parm(shader, "specular_roughness", 0.42)

    assign = stage.createNode("assignmaterial", Path(paths["material_assignment"]).name)
    assign.setInput(0, library)
    set_parm(assign, "nummaterials", 1)
    set_parm(assign, "primpattern1", "/World/Look/**")
    set_parm(assign, "matspecpath1", "/materials/LOOK_MATERIAL")

    neutral = stage.createNode("camera", Path(paths["neutral_camera"]).name)
    neutral.setInput(0, assign)
    set_parm(neutral, "primpath", "/World/Cameras/Neutral")
    for name, value in review["neutral_camera_parameters"].items():
        set_parm(neutral, name, value)

    hero = stage.createNode("camera", Path(paths["hero_camera"]).name)
    hero.setInput(0, neutral)
    set_parm(hero, "primpath", "/World/Cameras/Hero")
    for name, value in review["neutral_camera_parameters"].items():
        set_parm(hero, name, value)

    dome = stage.createNode("domelight::3.0", Path(paths["neutral_dome"]).name)
    dome.setInput(0, hero)
    set_parm(dome, "primpath", "/World/Lights/NeutralDome")
    for name, value in review["neutral_dome_parameters"].items():
        set_parm(dome, name, value)

    key = stage.createNode("distantlight::2.0", Path(paths["hero_key"]).name)
    key.setInput(0, hero)
    set_parm(key, "primpath", "/World/Lights/Key")
    set_parm(key, "ry", 35.0)
    set_parm(key, "xn__inputsintensity_i0a", 4.0)
    fill = stage.createNode("distantlight::2.0", Path(paths["hero_fill"]).name)
    fill.setInput(0, key)
    set_parm(fill, "primpath", "/World/Lights/Fill")
    set_parm(fill, "ry", -45.0)
    set_parm(fill, "xn__inputsintensity_i0a", 1.5)
    rim = stage.createNode("distantlight::2.0", Path(paths["hero_rim"]).name)
    rim.setInput(0, fill)
    set_parm(rim, "primpath", "/World/Lights/Rim")
    set_parm(rim, "ry", 155.0)
    set_parm(rim, "xn__inputsintensity_i0a", 3.0)

    selector = stage.createNode("switch", Path(paths["lighting_selector"]).name)
    selector.setInput(0, dome)
    selector.setInput(1, rim)
    set_parm(selector, "input", 0)
    settings = stage.createNode("karmarendersettings", Path(paths["render_settings"]).name)
    settings.setInput(0, selector)
    set_parm(settings, "primpath", "/Render/Look")
    set_parm(settings, "camera", "/World/Cameras/Hero")
    set_parm(settings, "picture", native(output_dir / "02_probes" / "scaffold.$F4.png"))
    for name, value in review["neutral_render_parameters"].items():
        set_parm(settings, name, value)
    set_parm(settings, "resolutionx", review["resolution"][0])
    if settings.parm("resolutiony").evalAsInt() != review["resolution"][1]:
        raise RuntimeError("locked Karma aspect does not resolve to the contracted resolution height")
    set_parm(settings, "samplesperpixel", review["samples_per_pixel"])
    set_parm(settings, "pathtracedsamples", review["path_traced_samples"])
    render = stage.createNode("usdrender_rop", Path(paths["render_output"]).name)
    render.setInput(0, settings)
    set_parm(render, "renderer", "BRAY_HdKarma")
    set_parm(render, "loppath", settings.path())
    set_parm(render, "rendersettings", "/Render/Look")

    chain = [imp, library, assign, neutral, hero, dome, key, fill, rim, selector, settings, render]
    for index, node in enumerate(chain):
        node.setPosition(hou.Vector2((0, 18 - index * 3)))
    library.layoutChildren()

    protected_paths = {
        "source_file": source.path(),
        "look_input": look_input.path(),
        "final_output": output.path(),
        **paths,
    }
    attempt_id = packet.get("attempt_id", "unmaterialized-scaffold-probe")
    protected: dict[str, dict[str, str]] = {}
    for role, node_path in protected_paths.items():
        protected_node = hou.node(node_path)
        if protected_node is None:
            raise RuntimeError(f"parent scaffold lost protected node {node_path}")
        scaffold_id = hashlib.sha256(f"{attempt_id}|{node_path}".encode()).hexdigest()
        protected_node.setUserData("parent_scaffold_id", scaffold_id)
        protected[role] = {
            "path": node_path,
            "type": protected_node.type().name(),
            "scaffold_id": scaffold_id,
        }
    hou.hipFile.save(native(scene_path))

    receipt = {
        "schema_version": 1,
        "owner": "parent-deterministic-scaffold",
        "direction_id": packet["direction"]["id"],
        "attempt_id": attempt_id,
        "scene_path": scene_path.relative_to(output_dir).as_posix(),
        "scene_sha256_before_worker": sha256(scene_path),
        "source_cache_expression": cache_expression(first_cache),
        "protected_nodes": protected,
        "locked_neutral_contract": {
            "camera": review["neutral_camera_parameters"],
            "dome": review["neutral_dome_parameters"],
            "render_settings": review["neutral_render_parameters"],
        },
    }
    (output_dir / "00_design" / "PARENT_SCAFFOLD.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    build(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
