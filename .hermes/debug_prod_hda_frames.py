import hou
p=r'E:/Projects/houdini-ai/work/studio/handoffs/study-003-affinity-shallow3d-parallel-hda-v1/nonlocal-affinity-parallel.hda'
hou.hipFile.clear(suppress_save_prompt=True); hou.hda.installFile(p)
g=hou.node('/obj').createNode('geo'); [c.destroy() for c in g.children()]
a=g.createNode('bzor::nonlocal_affinity_parallel::1.0')
for f in (1,2,3,25,1,2):
 hou.setFrame(f); a.cook(force=True); geo=a.geometry(); print(f,len(geo.points()),geo.findGlobalAttrib('simstep').defaultValue() if geo.findGlobalAttrib('simstep') else None,[str(e) for e in a.errors()])
