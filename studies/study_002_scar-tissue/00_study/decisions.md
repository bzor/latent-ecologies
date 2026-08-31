# Decisions

> Backfilled 2026-08-31 from the canonical records (`study.json`, `variations.json`,
> `01_behavior/03_selected/selection_00{1,2}/selection.json`, `99_archive/`). The vault
> migration created this Study without a decisions log; those source records remain
> authoritative for anything summarized here.

## 2026-08-15 — Behavior v3 promoted (selection_001)

KC approved the directional-refractory v3 behavior as
`component-behavior-b3bcc837c3e2` (`artifact-scar-tissue-directional-refractory-v3`).

- Rationale (verbatim): "KC approved v3: it preserves directional memory and refractory
  renewal while replacing synchronized tight circles with varied, longer agent
  trajectories."
- Evidence: `01_behavior/03_selected/selection_001/behavior-review-directional-refractory-v3.mp4`.

## 2026-08-22 — Study reset; promoted Behavior preserved

The Study was reset from the legacy `scar-tissue` record. Scope: preserve the promoted
Behavior; archive all prior Look, palette, cinematography, specimen, render, and
delivery decisions.

- The pre-reset golden run is preserved at `99_archive/pre-reset-golden-run-2026-08-22/`.

## 2026-08-23 — Rapid Surgical Zipper promoted (selection_002)

KC selected **Rapid Surgical Zipper — Two-turn Settling Helix** in Discord message
`1541210300743950350`, frozen as `component-behavior-4d1068fdc350`
(`artifact-scar-tissue-rapid-surgical-zipper-two-turn`, frames 1–300). Supersedes
`component-behavior-b3bcc837c3e2` as the canonical behavior.

- Rationale (verbatim): "KC selected the original Rapid Surgical Zipper after reviewing
  matched two-turn 3D parameter alternatives; promote its verified helical lift
  unchanged into artist-led Look Development."
- Evidence: `01_behavior/03_selected/selection_002/review/rapid-zipper-two-turn-helix-combined.mp4`;
  canonical caches under `selection_002/run/cache/`.
- Held behavior siblings (not promoted): legacy pixel-memory; untwisted cylindrical
  lift; Puckered Irregular; Long Travelling Waves; Persistent Open Wound; Tug-and-Zip
  Fasciculation.

## 2026-08-24 — Artist-led Look starter built and verified

The system built the Look starter for variation
`variation-bhvr002-004-rapid-surgical-zipper` from the `basic` setup
(`houdini/look_setups/basic/basic.hiplc`), curve-first geometry foundation, and
verified it (`02_look/bhvr_002_var_004_rapid-surgical-zipper.look_r001.starter-receipt.json`,
`passed: true`).

- Next gate: KC develops the Look in
  `02_look/bhvr_002_var_004_rapid-surgical-zipper.look_r001.hiplc`, then identifies and
  locks the authoritative revision for bounded rendering.
