import hou
p=r'E:/Projects/houdini-ai/.hermes/hda-debug/hda/nonlocal-affinity-parallel.hda'
hou.hda.installFile(p)
g=hou.node('/obj').createNode('geo'); [c.destroy() for c in g.children()]
a=g.createNode('bzor::nonlocal_affinity_parallel::1.0')
print('asset',[(n,a.parm(n).eval()) for n in ('contraction','attraction','repulsion','softening','apply_rewires','depth_scale','cohort_spread')])
for path in ('INITIAL_IDENTITY_CONTROLS','solver/d/s/APPLY_ORDERED_REWIRES','solver/d/s/INTEGRATE_POINTS_SYNCHRONOUSLY'):
 n=a.node(path); print(path,[(p.name(),p.eval(),p.unexpandedString() if p.parmTemplate().type()==hou.parmTemplateType.String else '') for p in n.parms() if p.name() in ('contraction','attraction','repulsion','softening','apply_rewires','depth_scale','cohort_spread')])
for f in range(1,8):
 hou.setFrame(f); geo=a.geometry(); print('frame',f,'simstep',geo.attribValue('simstep'),'P0',geo.point(0).position())
