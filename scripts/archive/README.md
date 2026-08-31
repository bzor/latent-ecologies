# Archived one-off scripts

Session scripts with no remaining references from `src/`, `tests/`, `docs/`, or the
README. They are preserved for reproducibility of historical renders and selections
(the studio keeps the seed and rule lineage of every approved specimen); they are not
part of the current pipeline and receive no maintenance.

Contents by campaign:

- `*scar_tissue*` — Study 002 (scar tissue) probe, audit, lighting, camera, and
  render-drive sessions.
- `*fieldwriting_ant*` — Study 004 (fieldwriting ants) option builds and selection
  freezes (`build_fieldwriting_ant_robustness.py` and
  `freeze_fieldwriting_ant_c2_radius2_selection.py` stay live in `scripts/` — the
  regression suite imports them as modules).
- `*affinity*` — Study 003 (nonlocal affinity) endurance runs and behavior promotions.
- `export_refractory_route_select_receipts.js` — Study 001 (memory field) behavior
  select receipt export.

The live helper scripts stay in `scripts/`: `capture_prototype.py`,
`composite_overlay.py`, `render_overlay_sequence.py`, `scaffold_prototype.py`,
`verify_render_sequence.py`.
