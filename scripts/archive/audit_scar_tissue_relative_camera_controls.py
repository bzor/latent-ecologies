import json
import sys
from pathlib import Path

import hou

hip=Path(sys.argv[1]).resolve(); hou.hipFile.load(str(hip),suppress_save_prompt=True)
camera=hou.node('/stage/CAM_EDIT_ABC_A_PORTRAIT')
frames=(1,315,316,630,631,945,946,1260)
controls={'A':(1,315,946,1260),'B':(316,630),'C':(631,945)}
all_names=('tx','ty','tz','rx','ry','rz')

def sample(): return {f:{n:camera.parm(n).evalAtFrame(f) for n in all_names} for f in frames}
base=sample(); checks={}
for view,affected in controls.items():
    node=hou.node(f'/obj/PORTRAIT_CAMERA_CONTROLS/VIEW_{view}')
    original=node.parm('tx').eval(); node.parm('tx').set(original+0.75); shifted=sample(); node.parm('tx').set(original)
    checks[view]={
        'affected_shift':{str(f):shifted[f]['tx']-base[f]['tx'] for f in affected},
        'unaffected':{str(f):shifted[f]['tx']-base[f]['tx'] for f in frames if f not in affected},
    }
report={
 'controls_exist':all(hou.node(f'/obj/PORTRAIT_CAMERA_CONTROLS/VIEW_{v}') is not None for v in controls),
 'camera_keyframes':{n:len(camera.parm(n).keyframes()) for n in all_names},
 'camera_expressions':{n:camera.parm(n).expression() for n in all_names},
 'isolation':checks,
 'drifts':{
  'A1':{n:base[315][n]-base[1][n] for n in all_names},
  'B':{n:base[630][n]-base[316][n] for n in all_names},
  'C':{n:base[945][n]-base[631][n] for n in all_names},
  'A2':{n:base[1260][n]-base[946][n] for n in all_names},
 },
 'portrait_resolution':[hou.node('/stage/portrait_9x16_settings').parm('resolutionx').eval(),hou.node('/stage/portrait_9x16_settings').parm('resolutiony').eval()],
 'landscape_resolution':[hou.node('/stage/grid_look_settings').parm('resolutionx').eval(),hou.node('/stage/grid_look_settings').parm('resolutiony').eval()],
 'errors':{p:list(hou.node(p).errors()) for p in ['/obj/PORTRAIT_CAMERA_CONTROLS','/stage/CAM_EDIT_ABC_A_PORTRAIT','/stage/portrait_9x16_settings','/stage/portrait_9x16_render']},
}
print(json.dumps(report,indent=2))
