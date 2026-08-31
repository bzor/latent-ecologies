# Ceremony audit — 2026-08-31

Evidence-based retirement proposal for record stores, CLI surface, and package
modules. Nothing here is deleted; retirement means moving records to
`studio/archive/`, removing CLI wiring, and relocating modules out of
`src/houdini_ai/`. KC decides per group.

## Evidence

Store activity (records / latest dated content):

| Store | Records | Latest | Verdict |
|---|---|---|---|
| notes | 16 | 2026-08-31 | alive |
| studies | 5 | 2026-08-31 | alive |
| ideas | 15 | 2026-08-22 | alive (lineage chain) |
| proposals / experiments / artifacts / components / specimens / directions | 66 | — (undated records; chain feeds promotions) | alive (lineage chain) |
| activities | 4 | 2026-08-23 | alive (seed-promotion idempotency) |
| conversation-bindings | 11 | 2026-08-22 | alive (Discord threads) |
| archive | 2 | 2026-08-22 | alive (is the archive) |
| sessions | 2 | 2026-08-22 | RETIRED 2026-08-31 → `studio/archive/` |
| session-state | 1 | stale pointer to pilot-003 | RETIRED 2026-08-31 → `studio/archive/` |
| study-state | 1 | focused-study pointer | KEPT — audit correction: `focus_study`/`list_studies` read it |
| affinity-presets | 7 | 2026-08-16 | KEPT — audit correction: the Study 003 HDA rebake test and `build_nonlocal_affinity_hda.py` (the documented packaging reference) read it |
| work | 0 | empty directory | dead |

CLI surface: 51 subcommands. Retirement candidates and why:

- `session-create`, `session-update`, `session-activate`, `sessions` — the session
  workspace model was replaced by canonical Studies.
- `study-migrate` — one-shot sessions→studies projection, executed 2026-08-29.
- `bootstrap-pilot-003` — one-shot Study 003 bootstrap, executed.
- `register-golden` — one-shot scar-tissue golden-specimen registration, executed.
- `look-round-prepare`, `look-round-run`, `look-round-review` — the autonomous Look
  execution workflow VISION retires ("must not be run without KC explicitly
  reopening that research direction"), yet the commands remain live. Removing the
  wiring makes the doc's safety rule mechanical. `look_execution.py` is 2,930
  lines — the largest module in the package — and only its own tests import it.

Module placement (new CLAUDE.md rule: study-specific code lives in vaults, not the
package): `fieldwriting_ants*` (5 modules), `nonlocal_affinity*` (3),
`scar_cylindrical_review`, `scar_mechanics_package`, `scar_tissue_edit`,
`mass_flow`, `affinity_presets`, `pilot_study_003`, `golden_specimens` — 15
study-specific modules inside `src/houdini_ai/`.

## Proposed groups

**Group 1 — retire now (dead weight, no live consumers):**
move `sessions/`, `session-state/`, `study-state/`, `affinity-presets/` into
`studio/archive/`; delete empty `studio/work/`; remove the five session/migrate CLI
commands plus the two executed one-shots; archive `studio_sessions.py`,
`pilot_study_003.py`, `golden_specimens.py` with their tests.

**Group 2 — retire the retired (safety alignment):**
remove `look-round-*` CLI wiring and archive `look_execution.py` + its two test
files, per VISION's retirement of the autonomous Look workflow. The contract stays
preserved in `docs/archive/LOOK_EXECUTION_AGENT.md`.

**Group 3 — phase 2, separate decision (bigger refactor):**
relocate the remaining study-specific modules (fieldwriting/nonlocal/scar/mass_flow)
out of the package into their study vaults or `scripts/archive/`, moving their tests
alongside. Mechanical but wide; propose doing it one study at a time as each study
closes.

**Keep, explicitly:** the lineage chain stores, notes/retro, activities,
conversation-bindings, seed bank, directions, editorial/tagging, study vault
commands, doctor/validate/storage/clean, and the Review Studio as the documented
local fallback.

## Execution record — 2026-08-31

Groups 1 + 2 executed with two corrections found during execution: `study-state/`
and `affinity-presets/` stay (live consumers above). Retired: `sessions/` and
`session-state/` stores; ten CLI commands (`session-create`, `session-update`,
`session-activate`, `sessions`, `study-migrate`, `bootstrap-pilot-003`,
`register-golden`, `look-round-prepare`, `look-round-run`, `look-round-review`);
modules and tests to `scripts/archive/retired-modules/`; session endpoints and
cockpit session UI removed from the Review Studio (the `/api/studio/session`
mutation-token bootstrap endpoint remains, token-only); `review_inbox` no longer
surfaces session questions. Full suite after: 350 tests OK (3 environment skips).

## Group 3 decision — 2026-08-31

KC: wait on the study-specific modules; KC will revisit them after Study 001 is
done. Tracked in `STATE.md` under known gaps so the revisit surfaces at Study 001
close.
