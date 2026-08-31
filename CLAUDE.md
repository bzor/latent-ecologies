# Claude Code orientation — Bzor Computational Studio

This repo is the automation system behind the studio. Sessions here are for **dev work
on the system itself** (pipeline code, tooling, docs, record stores). Day-to-day studio
operation happens elsewhere: KC works through **Hermes in Discord** and hands-on in
**Look HIP files** and the **overlay generator**. Don't run production stages from here
unless KC asks.

## The pipeline in five lines

Seed Bank (Discord) → Study brainstorm → behavior production (threeJS prototype or
straight Houdini) → live-HDA + look template → artist-led Look (KC owns the HIP) →
locked render (single pass, verified) → detail pass (overlay generator) → final
package → approval-gated publish. Every gate is an explicit KC decision with a durable
local receipt. The system proposes and produces; **KC promotes**.

## Read before touching

- `docs/VISION.md` — canonical pipeline; wins over every other doc.
- `docs/STUDY_VAULT.md` — per-Study directory contract and `bhvr_NNN_var_NNN_slug`
  three-axis naming. The HDA is the boundary between a behavior and a variation.
- `docs/STUDIO_PROTOCOL.md` — KC–Hermes conventions, approval boundaries.
- `docs/TECHNICAL_VOICE.md` — claim discipline for anything user- or public-facing.
- `STATE.md` — current studio/system state and whose turn it is. **Update it at the
  end of any session that changes it.**
- Subprojects have their own CLAUDE.md: `behavior-playground/`,
  `design-overlay-generator/` (also its DESIGN.md). Read them before working there.

## Layout

- `src/houdini_ai/` — the package. **Generic pipeline code only**; study-specific
  round scripts belong in the study vault (`studies/<study>/01_behavior/01_work/...`),
  not here. (Legacy `fieldwriting_ants_*` modules predate this rule.)
- `studies/` — canonical Study vaults. `001-memory-field` predates the
  `study_NNN_slug` contract and stays under its legacy name/layout.
- `studio/` — canonical record stores (ideas, proposals, promotions, notes, bindings).
  These are the project database; Discord transcripts are not.
- `work/` — disposable caches and staging. Never put canonical records here.
- `houdini/` — packages, HDAs, look setups (`look_setups/basic` is the only entry;
  the library grows from real use, never speculatively).

## Conventions

- Windows host; PowerShell primary. Python 3.10+; run `python -m unittest discover -s tests`
  and `python -m ruff check .` before committing.
- Receipts and records must report real paths and measured results — never plausible
  descriptions. Preserve KC's wording verbatim in decision records.
- Nothing is ever uploaded or published automatically; public exposure is irreversible.
- Promotion artifacts (HDA packages) go in `<study>/01_behavior/03_selected/` and get
  wired into the basic look template.
- Every work round with comparable candidates closes with one postable review packet
  (`python -m houdini_ai.review_packet`) — labelled sheet + comparison video + caption —
  posted to the Study thread so KC decides by replying with a letter.
- Behavior renders that leave the lab follow the postable standard
  (`houdini_ai/behavior_postable.py`): 1080×1350, 30 fps, monochrome with reserved
  CMYK accents. `python -m houdini_ai.behavior_postable` conforms existing renders.
- Capture process observations (`working` / `pain-point` / `missing-functionality` /
  `idea` / `question`) via `studio note` **while fresh** — opportunistically, whenever
  KC gripes or praises, without being asked. After every gate decision, run the
  sixty-second micro-retro ("what dragged?" / "what was fun?") with `studio retro`.
  The digest `studio/PROCESS_NOTES.md` regenerates on every capture.
