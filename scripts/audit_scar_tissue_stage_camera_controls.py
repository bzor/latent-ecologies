import json
import sys
from pathlib import Path

import hou

hip=Path(sys.argv[1]).resolve(); hou.hipFile.load(str(hip),suppress_save_prompt=True)
stage=hou.node('/stage'); camera=stage.node('CAM_EDIT_ABC_A_PORTRAIT'); controls={v:stage.node(f'PORTRAIT_VIEW_{v}_CTRL') for v in 'ABC'}
frames=(1,315,316,630,631,945,946,1260)
def sample(): return {f:{n:camera.parm(n).evalAtFrame(f) for n in ('tx','ty','tz','rx','ry','rz')} for f in frames}
base=sample(); b=controls['B']; original=b.parm('tx').eval(); b.parm('tx').set(original+0.5); shifted=sample(); b.parm('tx').set(original)
hou.setFrame(473); usd=stage.node('portrait_9x16_settings').stage()
report={
 'obj_controls_removed':hou.node('/obj/PORTRAIT_CAMERA_CONTROLS') is None,
 'stage_controls':{v:{'path':n.path(),'type':n.type().name(),'input':n.input(0).path() if n.input(0) else None,'position':[n.position().x(),n.position().y()],'errors':list(n.errors()),'usd_prim':str(n.parm('primpath').eval())} for v,n in controls.items()},
 'portrait_camera_input':camera.input(0).path(),
 'final_camera_prim_valid':usd.GetPrimAtPath('/cameras/portrait_abc_a').IsValid(),
 'control_prims_valid':{v:usd.GetPrimAtPath(f'/camera_controls/portrait_view_{v.lower()}').IsValid() for v in 'ABC'},
 'b_live_offset':{str(f):shifted[f]['tx']-base[f]['tx'] for f in frames},
 'camera_expressions_reference_stage':all('/stage/PORTRAIT_VIEW_' in camera.parm(n).expression() and '/obj/' not in camera.parm(n).expression() for n in ('tx','ty','tz','rx','ry','rz')),
 'portrait_resolution':[stage.node('portrait_9x16_settings').parm('resolutionx').eval(),stage.node('portrait_9x16_settings').parm('resolutiony').eval()],
 'errors':{p:list(hou.node(p).errors()) for p in ['/stage/CAM_EDIT_ABC_A_PORTRAIT','/stage/portrait_9x16_settings','/stage/portrait_9x16_render']},
}
print(json.dumps(report,indent=2))
