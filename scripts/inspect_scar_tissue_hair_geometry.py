import json
import sys
from pathlib import Path

import hou

hip = Path(sys.argv[1]).resolve()
hou.hipFile.load(str(hip), suppress_save_prompt=True)
geo = hou.node("/obj/scar_tissue_grid_look")
hair = geo.node("direction_hairs")
wire = geo.node("hair_radius")
out = geo.node("OUT_DIRECTION_HAIRS")
hou.setFrame(473)
source_geo = hair.geometry()
wire_geo = wire.geometry()
wire_positions = [tuple(float(value) for value in point.position()) for point in wire_geo.points()[:25]]
ring_radii = []
for start in range(0, 25, 5):
    ring = wire_positions[start:start + 5]
    center = tuple(sum(point[axis] for point in ring) / len(ring) for axis in range(3))
    ring_radii.append(max(sum((point[axis] - center[axis]) ** 2 for axis in range(3)) ** 0.5 for point in ring))
report = {
    "nodes": {
        node.name(): {
            "type": node.type().name(),
            "input": node.input(0).path() if node.input(0) else None,
            "output": [item.path() for item in node.outputs()],
            "position": list(node.position()),
            "errors": list(node.errors()),
        }
        for node in (hair, wire, out)
    },
    "polywire_parameters": [
        {
            "name": parm.name(),
            "label": parm.parmTemplate().label(),
            "value": parm.evalAsString(),
        }
        for parm in wire.parms()
    ],
    "scale_attribute_menu": {
        "items": list(wire.parm("usescaleattrib").parmTemplate().menuItems()),
        "labels": list(wire.parm("usescaleattrib").parmTemplate().menuLabels()),
    },
    "source": {
        "points": len(source_geo.points()),
        "primitives": len(source_geo.prims()),
        "point_attributes": [attrib.name() for attrib in source_geo.pointAttribs()],
    },
    "wire": {
        "points": len(wire_geo.points()),
        "primitives": len(wire_geo.prims()),
        "bounds": list(wire_geo.boundingBox().minvec()) + list(wire_geo.boundingBox().maxvec()),
        "first_curve_ring_radii": ring_radii,
    },
}
print(json.dumps(report, indent=2))
