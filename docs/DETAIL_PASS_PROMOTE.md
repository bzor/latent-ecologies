# Detail-pass promote flow

Stage 6 of the pipeline in `VISION.md`: a verified render travels through KC's
design-overlay generator and, on promotion, becomes the final postable package.
The gate lives in Discord, like every other promotion.

```text
render verified
→ Hermes stages the overlay project (study.json + render backdrop)
→ KC adjusts the overlay in realtime (web preview)
→ KC exports the overlay config into the Study
→ KC says "promote" in the Study thread
→ Hermes rebuilds the overlay headlessly, composites, encodes, packages
→ post-ready package + Discord preview
```

## 1. Import (Hermes)

After render verification (`ARTIST_LED_LOOK_HANDOFF.md` §7), Hermes prepares the
overlay project:

- generate the `study.json` sidecar from canonical Study records — real metadata
  only (the overlay system's rule is no fake greeble). Text identity (number,
  title, summaries, bullets, headline params) comes from the Study's
  `00_study/study-card.json` (`src/houdini_ai/study_card.py`), seeded from the
  Seed record and maintained conversationally; per-frame data (subject bbox,
  tracked-point screen positions/depths/values, scalar series) comes from
  `houdini/export_overlay_study.py` — tracked points are flagged in the HIP via
  the `overlay_track` point group + optional `track_label` attrib, or by point
  number on the CLI;
- load the locked variation's `*.overlay-parameters.json` with
  `--parameter-manifest`; the exporter copies its structured records into
  `overlay_parameters`, updates the sidecar variation identity, and appends readable
  values to the existing `params` table;
- write the sidecar to the Study vault as
  `03_specimen/var_NNN_title-slug.specimen.json`, beside the variation-matched
  overlay config it pairs with;
- record the render location in the overlay config's `render` pointer so the
  preview auto-loads it as the backdrop (video, else first-frame still);
- hand KC the preview entry point and paths.

State: `detail-in-progress`.

## 2. KC detail pass

KC works in `design-overlay-generator/web/index.html` — realtime, per-study
persisted config, aspect-ratio presets. Hermes does not adjust KC's presentation choices.

When satisfied, KC clicks **export for promote** in the panel, which downloads
the exact config with its canonical name, and saves it as
`03_specimen/var_NNN_title-slug.overlay-config.json` in the Study vault. The exported file is the
canonical record; browser localStorage is not.

## 3. Promote (KC, in Discord)

KC says `promote` in the Study thread. Hermes then:

1. validates the trio: verified render receipt, variation-aware specimen sidecar, and matching overlay config;
2. renders the overlay PNG sequence (alpha) headlessly at final resolution from
   (study.json, config, frame) — the overlay's determinism invariant makes this
   pixel-identical to KC's preview;
3. composites the overlay over the verified render frames with FFmpeg;
4. encodes the archival master and platform derivatives, reusing the existing
   resumable encode/package stages;
5. writes a promote receipt binding the SHA-256 of: locked HIP, render receipt,
   specimen sidecar, overlay config, and the overlay generator source version;
6. sets state `post-ready`, stores the package in `04_delivery`, and posts a
   preview back to the Study thread.

Nothing is uploaded to any public destination; publishing remains its own
approval-gated stage.

## Built

1. `houdini/export_overlay_study.py` — hython exporter: per-frame subject bbox
   projected through the render camera into normalized screen space (origin
   top-left), study metadata, solver info, params, and optional scalar series
   from float detail attributes → `study.json`.
2. Headless overlay sequence renderer — `design-overlay-generator/web/capture.html`
   + `capture.js` (single deterministic frame, transparent canvas, same
   `drawOverlay()` the preview uses) driven by
   `src/houdini_ai/detail_promote.py` / `scripts/render_overlay_sequence.py`
   (parallel Chrome captures, resumable, per-frame alpha verification;
   per-run `capture-input.js` injects study + config and is cleaned up after).
3. FFmpeg composite stage — `composite_overlay()` /
   `scripts/composite_overlay.py`: overlay sequence over an encoded video or
   PNG-pattern render, frame-count verified, H.264 faststart output.
4. Promote command + receipt — `python -m houdini_ai.detail_promote --study …
   --config … --render … --out …` runs validate → overlay render → composite →
   `var_NNN_title-slug.delivery.json` binding SHA-256s of the specimen sidecar, overlay config,
   render input/receipt, and the overlay source version (hash of `web/`
   sources). This command is the integration point Hermes calls when KC says
   `promote` in the Study thread; the Discord wiring itself lives with Hermes.

Regression coverage: `tests/test_detail_promote.py` (validation, receipts,
frame verification, capture-page contract, plus Chrome and FFmpeg smoke tests
that skip when the tool is absent).

## Rules

- The exported config file is the single source of truth for the overlay; a
  promote never reads localStorage or any browser state.
- The promote receipt must pin the overlay generator version so a package can be
  rebuilt bit-for-bit.
- A failed promote never damages the verified render or the Study record.
- Editing overlay config after promote creates a new promote, never a silent
  rewrite of the delivered package.
- A promote requires canonical variation identity and emits
  `var_NNN_title-slug.delivery.mp4`, `var_NNN_title-slug.delivery.json`, and a
  variation-matched overlay-frame directory.
