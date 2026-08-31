import hou
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HIP=ROOT/'work/studio/handoffs/scar-tissue-abc-a-v1/scar-tissue-abc-a-handoff.hiplc'; OUT=HIP.parent
hou.hipFile.load(str(HIP),suppress_save_prompt=True); stage=hou.node('/stage'); base=stage.node('CAM_EDIT_ABC_A_PORTRAIT')
candidates=[('a',125,3.9,-15),('b',140,3.9,-15),('c',140,3.5,-15),('d',155,3.5,-15),('e',140,3.2,-12),('f',155,3.2,-12)]
for label,focal,ty,rx in candidates:
 c=hou.copyNodesTo((base,),stage)[0]; c.setName('b_candidate_'+label); c.parm('primpath').set('/cameras/b_candidate_'+label)
 for n in ('tx','ty','tz','rx','ry','focalLength'): c.parm(n).deleteAllKeyframes()
 for n,v in [('tx',7.8),('ty',ty),('tz',15.75),('rx',rx),('ry',25.5),('focalLength',focal)]: c.parm(n).set(v)
 s=hou.copyNodesTo((stage.node('portrait_9x16_settings'),),stage)[0]; s.setName('b_settings_'+label); s.setInput(0,c); s.parm('camera').set('/cameras/b_candidate_'+label); s.parm('resolutionx').set(540); s.parm('samplesperpixel').set(8); s.parm('picture').set(str(OUT/f'portrait-b-candidate-{label}.png'))
 r=hou.copyNodesTo((stage.node('portrait_9x16_render'),),stage)[0]; r.setName('b_render_'+label); r.setInput(0,s); hou.setFrame(473); r.render(frame_range=(473,473,1))
