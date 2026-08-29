import hashlib
import json
import sys
from array import array
from pathlib import Path

import hou

hda = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
hou.hipFile.clear(suppress_save_prompt=True)
hou.hda.installFile(str(hda).replace('\\', '/'))
g = hou.node('/obj').createNode('geo', 'CONTROL_AUDIT')
for child in g.children():
    child.destroy()
node = g.createNode('bzor::nonlocal_affinity_parallel::1.0', 'NONLOCAL_AFFINITY_PARALLEL')

def pdigest():
    values = node.geometry().pointFloatAttribValues('P')
    return hashlib.sha256(array('q', (round(v * 10_000_000) for v in values)).tobytes()).hexdigest()

hou.setFrame(25)
node.cook(force=True)
default_digest = pdigest()
node.parm('attraction').set(0.03)
node.parm('reset_simulation').pressButton()
node.cook(force=True)
variation_digest = pdigest()
node.parm('attraction').set(0.02)
node.parm('depth_scale').set(0.0)
node.parm('reset_simulation').pressButton()
hou.setFrame(1)
node.cook(force=True)
zs = node.geometry().pointFloatAttribValues('P')[2::3]
errors = [f'{child.path()}: {error}' for child in (node, *node.allSubChildren()) for error in child.errors()]
result = {
    'schema_version': 1,
    'asset_type': node.type().name(),
    'point_count': len(node.geometry().points()),
    'default_frame_25_position_sha256': default_digest,
    'attraction_0_03_frame_25_position_sha256': variation_digest,
    'dynamics_control_changes_state': default_digest != variation_digest,
    'depth_zero_max_abs_z_at_initial_state': max((abs(v) for v in zs), default=0.0),
    'depth_control_flattens_initial_state': max((abs(v) for v in zs), default=0.0) <= 1e-8,
    'reset_button_exercised': True,
    'node_errors': errors,
}
if not result['dynamics_control_changes_state'] or not result['depth_control_flattens_initial_state'] or errors:
    raise RuntimeError(json.dumps(result, sort_keys=True))
out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps(result, sort_keys=True))
