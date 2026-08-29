"""Migrate portrait camera controls from OBJ Nulls to Stage Camera LOPs."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

import hou

PARAMETERS=("tx","ty","tz","rx","ry","rz")
FRAMES=(1,315,316,630,631,945,946,1260)


def sample(camera: hou.Node) -> dict[int,dict[str,float]]:
    return {frame:{name:camera.parm(name).evalAtFrame(frame) for name in PARAMETERS} for frame in FRAMES}


def replace_expression_paths(camera: hou.Node) -> None:
    for name in PARAMETERS:
        parm=camera.parm(name); expression=parm.expression()
        for view in "ABC":
            expression=expression.replace(
                f'/obj/PORTRAIT_CAMERA_CONTROLS/VIEW_{view}/{name}',
                f'/stage/PORTRAIT_VIEW_{view}_CTRL/{name}',
            )
        parm.deleteAllKeyframes(); parm.setExpression(expression,hou.exprLanguage.Hscript)


def migrate() -> dict[str,object]:
    obj=hou.node('/obj'); stage=hou.node('/stage'); camera=hou.node('/stage/CAM_EDIT_ABC_A_PORTRAIT')
    old=obj.node('PORTRAIT_CAMERA_CONTROLS') if obj else None
    source=stage.node('assign_neutral_materials') if stage else None
    if None in (obj,stage,camera,old,source): raise RuntimeError('missing existing portrait control rig')
    values={view:{name:old.node(f'VIEW_{view}').parm(name).eval() for name in PARAMETERS} for view in 'ABC'}
    previous=source; controls=[]
    for index,view in enumerate('ABC'):
        node=stage.createNode('camera',f'PORTRAIT_VIEW_{view}_CTRL'); node.setInput(0,previous); previous=node; controls.append(node)
        node.setPosition(hou.Vector2((5,-13-index*2.5))); node.setColor(hou.Color((0.78,0.42,0.16)))
        node.setComment(f'EDIT THIS TRANSFORM — drives portrait view {view}; final camera adds subtle drift')
        node.parm('primpath').set(f'/camera_controls/portrait_view_{view.lower()}')
        node.parm('aspectratiox').set(9); node.parm('aspectratioy').set(16)
        for name,value in values[view].items(): node.parm(name).set(value)
    camera.setInput(0,previous); replace_expression_paths(camera)
    camera.setComment('VIEWPORT: look through /cameras/portrait_abc_a; select A/B/C controls upstream and use handles')
    old.destroy()
    portrait_box=next((box for box in stage.networkBoxes() if box.comment()=='PORTRAIT 9:16 — CAMERA / QUALITY / OUTPUT'),None)
    if portrait_box:
        for node in controls: portrait_box.addItem(node)
        portrait_box.fitAroundContents()
    note=stage.createStickyNote(); note.setText('LIVE PORTRAIT CAMERA CONTROLS\n1. View /cameras/portrait_abc_a\n2. Lock the viewport to camera\n3. Select PORTRAIT_VIEW_A/B/C_CTRL\n4. Use transform handles — drift remains automatic\n\nVIEW_A drives A1 + A2')
    note.setPosition(hou.Vector2((12,-15))); note.setSize(hou.Vector2((8,4)))
    return {'controls':[node.path() for node in controls],'camera':camera.path(),'migrated_values':values}


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument('hip',type=Path); parser.add_argument('--probe-only',action='store_true'); args=parser.parse_args(); hip=args.hip.resolve()
    backup=hip.with_name(f"{hip.stem}.pre-stage-camera-controls-{datetime.now().strftime('%Y%m%d-%H%M%S')}{hip.suffix}"); shutil.copy2(hip,backup)
    hou.hipFile.load(str(hip),suppress_save_prompt=True); camera=hou.node('/stage/CAM_EDIT_ABC_A_PORTRAIT'); before=sample(camera); result=migrate(); after=sample(camera)
    for frame in FRAMES:
        for name in PARAMETERS:
            if abs(before[frame][name]-after[frame][name])>1e-6: raise RuntimeError(f'migration changed frame {frame} {name}')
    b=hou.node('/stage/PORTRAIT_VIEW_B_CTRL'); original=b.parm('tx').eval(); b.parm('tx').set(original+0.5); shifted=sample(camera); b.parm('tx').set(original)
    if any(abs(shifted[f]['tx']-after[f]['tx']-0.5)>1e-6 for f in (316,630)): raise RuntimeError('Stage B control failed')
    if any(abs(shifted[f]['tx']-after[f]['tx'])>1e-6 for f in (1,315,631,945,946,1260)): raise RuntimeError('Stage B leaked')
    if args.probe_only:
        print(json.dumps({'framing_preserved':True,'stage_handle_controls':True,**result},indent=2)); return
    hou.hipFile.save(str(hip)); hou.hipFile.clear(suppress_save_prompt=True); hou.hipFile.load(str(hip),suppress_save_prompt=True); reopened=sample(hou.node('/stage/CAM_EDIT_ABC_A_PORTRAIT'))
    for frame in FRAMES:
        for name in PARAMETERS:
            if abs(reopened[frame][name]-after[frame][name])>1e-6:
                shutil.copy2(backup,hip); raise RuntimeError(f'reopen mismatch {frame} {name}; restored backup')
    result.update({'hip':str(hip),'backup':str(backup),'sha256':hashlib.sha256(hip.read_bytes()).hexdigest(),'framing_preserved':True,'stage_handle_controls':True})
    (hip.parent/'stage-camera-controls-receipt.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result,indent=2))


if __name__=='__main__': main()
