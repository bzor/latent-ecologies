"""Apply tightened portrait framing to the existing artist-edited Scar Tissue HIP."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import hou

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from houdini_ai.scar_tissue_edit import SHOTS, portrait_camera_at_frame

hip=(ROOT/'work/studio/handoffs/scar-tissue-abc-a-v1/scar-tissue-abc-a-handoff.hiplc').resolve()
backup=hip.with_name(f"{hip.stem}.pre-tight-portrait-{datetime.now().strftime('%Y%m%d-%H%M%S')}{hip.suffix}")
shutil.copy2(hip,backup)
hou.hipFile.load(str(hip),suppress_save_prompt=True)
camera=hou.node('/stage/CAM_EDIT_ABC_A_PORTRAIT')
if camera is None: raise RuntimeError('missing portrait camera')
for name in ('tx','ty','tz','rx','ry','focalLength'): camera.parm(name).deleteAllKeyframes()
for shot in SHOTS:
    for frame in shot['frames']:
        values=portrait_camera_at_frame(frame)
        for parm_name,source_name in (('tx','tx'),('ty','ty'),('tz','tz'),('rx','rx'),('ry','ry'),('focalLength','focal_length')):
            key=hou.Keyframe(); key.setFrame(frame); key.setValue(float(values[source_name])); key.setExpression('linear()',hou.exprLanguage.Hscript); camera.parm(parm_name).setKeyframe(key)
camera.setComment('9:16 SOCIAL MASTER — tightened full-frame portrait A/B/C/A reframing')
hou.hipFile.save(str(hip)); hou.hipFile.clear(suppress_save_prompt=True); hou.hipFile.load(str(hip),suppress_save_prompt=True)
camera=hou.node('/stage/CAM_EDIT_ABC_A_PORTRAIT')
expected={1:125,315:125,316:140,630:140,631:150,945:150,946:125,1260:125}
for frame,focal in expected.items():
    if abs(camera.parm('focalLength').evalAtFrame(frame)-focal)>1e-6:
        shutil.copy2(backup,hip); raise RuntimeError('reopen mismatch; restored backup')
report={'hip':str(hip),'backup':str(backup),'sha256':hashlib.sha256(hip.read_bytes()).hexdigest(),'portrait_focals':{'A1':125,'B':140,'C':150,'A2':125},'B_ty':[3.60,3.40]}
(hip.parent/'portrait-tight-framing-receipt.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
