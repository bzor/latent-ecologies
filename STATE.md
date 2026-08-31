# Studio state

Living snapshot of where every Study and the system itself stands, and **whose turn it
is**. Update at the end of any session (Discord or dev) that changes it. Canonical
records in `studio/` and per-study `00_study/` always win over this summary.

_Last updated: 2026-08-31_

## Studies

### Study 001 — memory field (`studies/001-memory-field/`, legacy layout)
- **Phase:** reopened for a vertical Look pass (KC decision 2026-08-31). The 4:5
  delivery of 2026-08-30 stands (promoted behavior HDA, artist-led Look, verified
  450-frame Karma render, detail pass, checksum-bound package in `04_delivery/`);
  KC is adding a 9:16 camera to the Look HIP as the dual-camera practice's first
  run, then re-lock → overnight verified render → 9:16 overlay config → vertical
  delivery. Plan: `.hermes/plans/2026-09-01_overlay-aspect-flexibility.md`.
- **Waiting on:** KC — 2026-09-01 session: long aspect-flexibility pass on the
  design overlay generator (corner/edge anchoring, procedural edge placement)
  with the Study 001 9:16 Look as the live test case. Final 4:5 mp4 post still
  pending. Hold the `02_look/renders/` (~1.1 GB) cleanup until the vertical pass
  completes.
- Stays under its legacy directory name; migration to the vault contract is an
  explicit decision, not assumed. `00_study/` now holds the KC-approved study
  card (created for the post kit; not a vault migration).

### Study 002 — scar tissue (`studies/study_002_scar-tissue/`)
- **Phase:** look (active). Behavior promoted 2026-08-23: Rapid Surgical Zipper —
  Two-turn Settling Helix (`component-behavior-4d1068fdc350`); Look starter built and
  verified from the `basic` setup. Reset 2026-08-22 preserved the behavior and archived
  all prior Look/specimen work (`99_archive/pre-reset-golden-run-2026-08-22/`).
- **Waiting on:** KC — Look development in
  `02_look/bhvr_002_var_004_rapid-surgical-zipper.look_r001.hiplc`, then declare the lock.
- Note: `study.json` extensions still reference pre-three-axis Look filenames
  (`var_004_...` instead of `bhvr_002_var_004_...`); harmless but stale.

### Study 003 — nonlocal affinity dance (`studies/study_003_nonlocal-affinity-dance/`)
- **Phase:** look (active). Behavior promoted; live HDA verified against the starter
  instantiation (`houdini/instantiate_look_starter.py`).
- **Waiting on:** KC — artist-led Look development in the HIP, then declare the lock.

### Study 004 — three-dimensional fieldwriting ants (`studies/study_004_three-dimensional-fieldwriting-ants/`)
- **Phase:** look (active). Frozen selections: A3 gap-4 and C2 radius-3 (2026-08-22);
  behavior immutable for Look. Held branch: RUL relay-node (`held-branches.json`).
- **Waiting on:** system/Hermes — package the frozen behaviors as live HDAs and build
  the Look starter, then hand off to KC.

## System — recently shipped

- **Social publishing, Phase 1 (2026-08-31):** strategy and phased plan in
  `docs/SOCIAL_PUBLISHING.md` (X, Instagram, Bluesky, Shorts, TikTok; process /
  hero / recap tiers tied to pipeline gates). `python -m houdini_ai.post_kit`
  builds the complete post kit: feed (1080×1350) and vertical (1080×1920)
  derivatives, per-platform caption drafts from the study card, alt text,
  Discord summary, receipt with constraint checks. Hand-post from the kit for
  now; Phase 2 (Discord approval loop → Postiz adapter → publication receipts)
  and Phase 3 (post queue + weekly nudge) are specified in the doc. First
  candidates: Study 001's delivery video and lineage poster. Study 001's card
  is KC-approved (wording edited 2026-08-31); its vertical derivative ships
  padded (accepted). Study 002 still needs a card before a kit can build.
  From Study 002 on, Look HIPs carry a second 9:16 camera so both aspects
  render overnight from one lock (dual-camera practice, `SOCIAL_PUBLISHING.md`
  § Derivative matrix) — applies to the Looks now active in 002, 003, and 004.

- **Studio rituals (2026-08-31):** completion posters
  (`python -m houdini_ai.lineage_poster`), the study-close held-branch revisit, and
  the weekly Seed Bank digest (`studio seed-digest`) — see `docs/STUDIO_PROTOCOL.md`
  § "Studio rituals". Study 001's lineage poster is rendered and in its vault
  (`studies/001-memory-field/04_delivery/bhvr_001_var_001_memory-field.lineage-poster.png`).

- **Ceremony trim (2026-08-31):** retired the creative-session layer (stores to
  `studio/archive/`, modules to `scripts/archive/retired-modules/`), ten CLI
  commands including the executed one-shots, and the `look-round-*` wiring for the
  autonomous Look workflow VISION had already retired. Audit + execution record:
  `.hermes/plans/2026-08-31_ceremony-audit.md`. Kept after correction: `study-state/`
  (focused-study pointer) and `affinity-presets/` (HDA rebake consumers).

- **Behavior postable standard (2026-08-31):** `python -m houdini_ai.behavior_postable`
  conforms any behavior render to 1080×1350 / 30 fps / monochrome-with-CMYK-accents
  for eventual X posting. New renderers draw with its palette constants directly.
  Protocol: `docs/STUDIO_PROTOCOL.md` § "Make a behavior postable".
- **Review packets (2026-08-31):** `python -m houdini_ai.review_packet` closes any
  work round with one postable artifact — labelled contact sheet, labelled comparison
  video, caption, receipt. Protocol: `docs/STUDIO_PROTOCOL.md` § "Close a round with a
  review packet".

## System — known gaps (from `docs/VISION.md`)

- **Study-specific modules (ceremony audit Group 3):** KC decision 2026-08-31 —
  the ~15 study-specific modules (`fieldwriting_ants*`, `nonlocal_affinity*`,
  `scar_*`, `mass_flow`, `affinity_presets`) stay in `src/houdini_ai/` until KC
  revisits them after Study 001 is done (final mp4 posted and the study closed).
  Plan: relocate per-study into vaults/archive, tests alongside — see
  `.hermes/plans/2026-08-31_ceremony-audit.md` Group 3.

- **Detail-promote wiring:** `python -m houdini_ai.detail_promote` exists; Hermes-side
  trigger from a Discord promote + posting the preview back is not wired.
- **HDA packaging:** still bespoke per behavior (follow `build_nonlocal_affinity_hda.py`);
  a reusable path emerges with repetition.
- **Safe render resume:** delivery renders are single-pass until a Study's sim is
  cached to disk in the Look HIP (post-lock change; needs KC approval per Study).
- **Overlay manifest checksum:** closed 2026-08-31 via
  `houdini/export_overlay_manifest_headless.py` (binds the checksum after verifying a
  clean load; no GUI export or HDA rebuild). Binder logic unit-tested; the hython
  driver itself has not yet run against a real locked HIP — exercise it on the next
  locked delivery.
- **Process notes:** closed 2026-08-31 — capture is now harness-carried: `decide` and
  `promote` print a micro-retro reminder, `studio retro` records both answers in one
  command, and the digest regenerates on every capture. The remaining part is habit:
  actually asking the two questions at each gate.

## Ritual reminders

- Micro-retro at every gate: "what dragged?" / "what was fun?" → `studio retro`.
- At study close: revisit held branches and archived directions against the final look.
- Completion poster per finished Study (`lineage_poster`) — Study 001's is done.
- Weekly: post `studio seed-digest` to Discord. Three inbox seeds have been waiting
  since 2026-08-17 (gradient-rose attractors, lineage machines, evolving-the-rule).
