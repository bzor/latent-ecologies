# Archived Houdini scripts

Scripts with no remaining references from `src/`, `tests/`, or `scripts/`. Preserved
for reproducibility of historical renders; not part of the current pipeline.

- `render_mass_flow_sequence.py`, `render_mass_flow_trails.py` — Mass Flow
  (prototype-era Study 002) render drivers. The simulator `../simulate_mass_flow.py`
  stays live as a regression fixture.
- `add_scar_tissue_palette_primvars.py` — one-off palette primvar patch from the
  Scar Tissue look experiments.
- `stage_affinity_behavior_cache.py` — superseded by
  `../stage_affinity_continuous_rewire_cache.py`.
- `stage_affinity_continuous_rewire_cache.py` — Study 003 continuous-rewire cache
  staging; superseded flow, promotion counterpart archived in `scripts/archive/`.
