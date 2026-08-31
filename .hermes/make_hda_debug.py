import json
from pathlib import Path
from houdini_ai.affinity_presets import load_affinity_preset
from houdini_ai.nonlocal_affinity import prepare_canvas_run, lift_prepared_to_3d
root=Path(r'E:/Projects/houdini-ai')
out=root/'.hermes/hda-debug'
out.mkdir(parents=True,exist_ok=True)
preset_path=root/'studio/affinity-presets/affinity-preset-32e76e5d39d0.json'
preset=json.loads(preset_path.read_text())
config=load_affinity_preset(preset_path,agent_count=64,dimensions=2,steps=6)
planar=prepare_canvas_run(config,rewire_probability=float(preset['rewiring']['probability_per_simulation_step']))
(out/'prepared.json').write_text(json.dumps(lift_prepared_to_3d(planar,seed=config.seed,depth=0.15)))
