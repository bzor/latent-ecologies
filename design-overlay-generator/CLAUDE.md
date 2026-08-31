# Working on design-overlay-generator

Read `DESIGN.md` first — it is the full reference (visual language, file map,
component API, config schema, roadmap). This file is the operational guide.

## What this is

A configurable HUD/design-overlay system rendered on canvas, previewed in
`web/index.html` (open directly, `file://` works — no server, no build step,
classic scripts only). The owner (kc) iterates on the look per "study" via the
left panel; settings persist per study id.

Preferred way to open it: via the review studio server — run
`python -m houdini_ai review` in the houdini-ai root and open
`http://127.0.0.1:8765/overlay/`. Some browsers treat every `file://` URL as
a unique origin, which blocks the render backdrop and persistence; the http
origin has neither problem, and study renders are reachable through
`/overlay-media/<project-relative path>` (render pointers in configs use
project-relative paths for exactly this).

## Verify every visual change with a screenshot

Headless Chrome works on this machine (note `--headless=new`; old `--headless`
produces no file):

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --headless=new `
  --disable-gpu --allow-file-access-from-files --hide-scrollbars `
  --virtual-time-budget=4000 --window-size=900,1000 `
  --screenshot="<scratchpad>\shot.png" `
  "file:///E:/Projects/houdini-ai/design-overlay-generator/web/index.html?ar=1:1&frame=300"
```

Then Read the PNG. URL params: `ar` (prefix-matches preset: `9:16`, `4:5`,
`1:1`, `16:9`), `frame` (0-599 in sample study), `palette` (exact name).
Check at least two aspect ratios for layout changes — collisions differ by AR.
`--allow-file-access-from-files` + `--virtual-time-budget` are required for
fonts to load before the shot.

## Rules

- **Determinism**: draw code must be a pure function of (size, study, frame,
  config). Never `Date.now()` / `Math.random()` in overlay.js/components.js —
  use `h.sval(shared.seed, a, b)`. Time-based animation = function of `frame`.
- **Units**: all geometry in u-units (`u = min(W,H)/1000`), via `L.u`. Never
  raw pixels. Margins come from `L.m`.
- **UI is generated**: never hand-write panel controls for component params —
  add `defaults` + `schema` entries in components.js and the panel builds
  itself (types: number/bool/select/series/track/text/list). Same for palettes
  (`OVERLAY.PALETTES`) and fonts (`FONT_LIBRARY` in fonts.js).
- **Config compatibility**: saved configs deep-merge over defaults (localStorage
  key `dog.study.<id>`), so *adding* params is safe; avoid renaming existing
  param keys without reason.
- **letterSpacing leaks**: canvas `ctx.letterSpacing` persists — reset to
  `"0px"` after any large-type draw (see studyBlock component).
- **Cross-component layout** goes through the `shared` object (documented in
  DESIGN.md); always handle a missing key (source component toggled off).
- **Fonts**: canvas won't trigger lazy @font-face loads — any code path that
  applies a new family must `document.fonts.load()` then repaint (app.js
  `applyType` does this).
- No external resources of any kind — the headless pipeline and `file://`
  preview must keep working offline.

## Owner's taste (from review of references and iterations)

Subtle over loud: hairline strokes, micro-type at the edge of legibility,
one restrained accent color, subject stays hero. Real metadata only — no fake
greeble. Mostly static with a few ticking elements. When in doubt, quieter.

## Current phase

Componentized system is done, and the batch pipeline exists: Houdini exporter
(`../houdini/export_overlay_study.py`), headless capture (`capture.html` +
`capture.js`, driven by `../src/houdini_ai/detail_promote.py`), and ffmpeg
composite (see DESIGN.md → Pipeline). capture.js mirrors app.js config
semantics — keep them in sync when the config shape changes. Now: small
per-component visual refinements and new components (wishlist in DESIGN.md),
keeping everything configurable and persisted.
