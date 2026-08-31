"""Add a root-to-point taper to direction hairs in the artist-edited HIP."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

import hou

ALLOWED_PATHS = {
    "/obj/scar_tissue_grid_look/direction_hairs",
    "/obj/scar_tissue_grid_look/hair_root_to_point_taper",
    "/obj/scar_tissue_grid_look/hair_radius",
    "/obj/scar_tissue_grid_look/OUT_DIRECTION_HAIRS",
}
HAIR_ROOT_SCALE = 1.0
HAIR_TIP_SCALE = 0.0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_snapshot() -> list[dict[str, object]]:
    records = []
    for root_path in ("/obj/scar_tissue_grid_look", "/stage", "/stage/neutral_look_materials"):
        root = hou.node(root_path)
        if root is None:
            continue
        for node in (root, *root.allSubChildren()):
            if node.path() in ALLOWED_PATHS or node.name() == "attribvop1":
                continue
            parms = []
            for parm in node.parms():
                try:
                    raw = repr(parm.rawValue())
                except hou.Error:
                    raw = "<unavailable>"
                keys = [(key.frame(), key.asCode()) for key in parm.keyframes()]
                parms.append((parm.name(), raw, keys))
            inputs = [
                (index, source.path() if source else None)
                for index, source in enumerate(node.inputs())
            ]
            records.append({
                "path": node.path(),
                "type": node.type().name(),
                "parms": sorted(parms),
                "inputs": inputs,
            })
    return sorted(records, key=lambda record: str(record["path"]))


def fingerprint(records: list[dict[str, object]]) -> str:
    payload = json.dumps(records, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def install_taper() -> None:
    geo = hou.node("/obj/scar_tissue_grid_look")
    source = geo.node("direction_hairs")
    wire = geo.node("hair_radius")
    output = geo.node("OUT_DIRECTION_HAIRS")
    if None in (geo, source, wire, output):
        raise RuntimeError("missing direction-hair SOP chain")
    if geo.node("hair_root_to_point_taper") is not None:
        raise RuntimeError("hair taper already exists")

    taper = geo.createNode("attribwrangle", "hair_root_to_point_taper")
    taper.setInput(0, source)
    taper.parm("class").set("point")
    taper.parm("snippet").set(
        "int vertex = pointvertex(0, @ptnum);\n"
        "int primitive = vertexprim(0, vertex);\n"
        "int index = vertexprimindex(0, vertex);\n"
        "int count = primvertexcount(0, primitive);\n"
        "float u = count > 1 ? float(index) / float(count - 1) : 0.0;\n"
        f"f@pscale = lerp({HAIR_ROOT_SCALE}, {HAIR_TIP_SCALE}, u);"
    )
    wire.setInput(0, taper)
    wire.parm("usescaleattrib").set("attrib")
    wire.parm("scaleattrib").set("pscale")

    taper.setPosition(hou.Vector2((7, -3)))
    wire.setPosition(hou.Vector2((7, -6)))
    output.setPosition(hou.Vector2((7, -9)))
    box = next((item for item in geo.networkBoxes() if item.comment() == "DIRECTION HAIRS"), None)
    if box is not None:
        box.addItem(taper)
        box.fitAroundContents()


def taper_audit() -> dict[str, object]:
    hou.setFrame(473)
    geo = hou.node("/obj/scar_tissue_grid_look")
    taper = geo.node("hair_root_to_point_taper")
    wire = geo.node("hair_radius")
    source_geo = taper.geometry()
    wire_geo = wire.geometry()
    scales = [float(point.attribValue("pscale")) for point in source_geo.points()]
    first_curve_points = list(source_geo.prims()[0].points())
    first_curve_scales = [float(point.attribValue("pscale")) for point in first_curve_points]
    root = tuple(float(value) for value in first_curve_points[0].position())
    tip = tuple(float(value) for value in first_curve_points[-1].position())
    positions = [tuple(float(value) for value in point.position()) for point in wire_geo.points()]

    def closest_distances(target: tuple[float, float, float]) -> list[float]:
        return sorted(
            sum((position[axis] - target[axis]) ** 2 for axis in range(3)) ** 0.5
            for position in positions
        )[:5]

    return {
        "taper_node": taper.path(),
        "wire_input": wire.input(0).path(),
        "pscale_min": min(scales),
        "pscale_max": max(scales),
        "first_curve_pscale": first_curve_scales,
        "closest_root_vertex_distances": closest_distances(root),
        "closest_tip_vertex_distances": closest_distances(tip),
        "wire_points": len(wire_geo.points()),
        "wire_primitives": len(wire_geo.prims()),
        "errors": list(taper.errors()) + list(wire.errors()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("hip", type=Path)
    args = parser.parse_args()
    hip = args.hip.resolve()
    backup = hip.with_name(
        f"{hip.stem}.pre-pointed-hairs-{datetime.now().strftime('%Y%m%d-%H%M%S')}{hip.suffix}"
    )
    shutil.copy2(hip, backup)
    original_sha = sha256(hip)

    hou.hipFile.load(str(hip), suppress_save_prompt=True)
    before_records = protected_snapshot()
    before_fingerprint = fingerprint(before_records)
    install_taper()
    after_records = protected_snapshot()
    if fingerprint(after_records) != before_fingerprint:
        diagnostics = hip.parent / "pointed-hair-protected-mismatch-before-save.json"
        diagnostics.write_text(
            json.dumps({"before": before_records, "after": after_records}, indent=2, default=str),
            encoding="utf-8",
        )
        raise RuntimeError("hair edit changed protected scene data before save")
    hou.hipFile.save(str(hip))

    hou.hipFile.clear(suppress_save_prompt=True)
    hou.hipFile.load(str(hip), suppress_save_prompt=True)
    reopened_records = protected_snapshot()
    if fingerprint(reopened_records) != before_fingerprint:
        diagnostics = hip.parent / "pointed-hair-protected-mismatch.json"
        diagnostics.write_text(
            json.dumps({"before": before_records, "reopened": reopened_records}, indent=2, default=str),
            encoding="utf-8",
        )
        shutil.copy2(backup, hip)
        raise RuntimeError("protected scene data changed after reopen; restored backup")

    audit = taper_audit()
    if audit["errors"] or abs(audit["pscale_min"] - HAIR_TIP_SCALE) > 1e-6 or abs(audit["pscale_max"] - HAIR_ROOT_SCALE) > 1e-6:
        shutil.copy2(backup, hip)
        raise RuntimeError("hair taper attributes failed; restored backup")
    scales = audit["first_curve_pscale"]
    tip_distances = audit["closest_tip_vertex_distances"]
    root_distances = audit["closest_root_vertex_distances"]
    if not all(scales[index] > scales[index + 1] for index in range(len(scales) - 1)):
        shutil.copy2(backup, hip)
        raise RuntimeError(f"hair scale does not decrease toward tip: {scales}; restored backup")
    if max(tip_distances) > 1e-6 or min(root_distances) < 0.0049:
        shutil.copy2(backup, hip)
        raise RuntimeError(
            f"cooked endpoint did not collapse cleanly: root={root_distances}, tip={tip_distances}; restored backup"
        )

    report = {
        "hip": str(hip),
        "backup": str(backup),
        "original_sha256": original_sha,
        "updated_sha256": sha256(hip),
        "protected_scene_fingerprint": before_fingerprint,
        "protected_scene_preserved": True,
        "hair_radius_profile": "linear-root-to-point",
        **audit,
    }
    receipt = hip.parent / "pointed-hair-receipt.json"
    receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
