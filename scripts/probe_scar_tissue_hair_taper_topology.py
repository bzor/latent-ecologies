import json
import sys
from pathlib import Path

import hou

hip = Path(sys.argv[1]).resolve()
hou.hipFile.load(str(hip), suppress_save_prompt=True)
geo = hou.node("/obj/scar_tissue_grid_look")
source = geo.node("direction_hairs")
wire = geo.node("hair_radius")
taper = geo.createNode("attribwrangle", "PROBE_hair_taper")
taper.setInput(0, source)
taper.parm("class").set("point")
taper.parm("snippet").set(
    "int vertex = pointvertex(0, @ptnum);\n"
    "int primitive = vertexprim(0, vertex);\n"
    "int index = vertexprimindex(0, vertex);\n"
    "int count = primvertexcount(0, primitive);\n"
    "float u = count > 1 ? float(index) / float(count - 1) : 0.0;\n"
    "f@pscale = lerp(1.0, 0.0, u);"
)
wire.setInput(0, taper)
wire.parm("usescaleattrib").set("attrib")
wire.parm("scaleattrib").set("pscale")
hou.setFrame(473)
source_geo = taper.geometry()
wire_geo = wire.geometry()
first_prim = source_geo.prims()[0]
source_points = list(first_prim.points())
source_scales = [float(point.attribValue("pscale")) for point in source_points]
root = tuple(float(value) for value in source_points[0].position())
tip = tuple(float(value) for value in source_points[-1].position())
wire_positions = [tuple(float(value) for value in point.position()) for point in wire_geo.points()]

def distances(target):
    return sorted(
        sum((position[axis] - target[axis]) ** 2 for axis in range(3)) ** 0.5
        for position in wire_positions
    )[:12]

print(json.dumps({
    "source_points": len(source_geo.points()),
    "source_primitives": len(source_geo.prims()),
    "wire_points": len(wire_geo.points()),
    "wire_primitives": len(wire_geo.prims()),
    "points_per_curve_average": len(wire_geo.points()) / len(source_geo.prims()),
    "first_curve_source_scales": source_scales,
    "root": root,
    "tip": tip,
    "closest_wire_distances_to_root": distances(root),
    "closest_wire_distances_to_tip": distances(tip),
    "taper_errors": list(taper.errors()),
    "wire_errors": list(wire.errors()),
}, indent=2))
