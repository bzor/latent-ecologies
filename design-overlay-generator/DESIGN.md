# Design Overlay Generator

HUD-style, high-design overlays composited over Houdini renders. One consistent
graphic system across wildly different studies — the studio's signature frame.
Part of Bzor Computational Studio's current pipeline: verified Houdini render →
KC-owned realtime detail pass → deterministic composite → post-ready package
(primarily portrait formats: 9:16, 4:5, and 1:1).

**Current status:** The web component system, schema-driven controls, per-Study
persistence, font controls, Houdini metadata exporter, deterministic headless
overlay renderer, FFmpeg composite, and checksum-bound promote/package command
are built. The active work is visual refinement, additional components, social
safe-zone handling, and settling Study-specific fonts and defaults.

## Visual language (distilled from `references/`)

- **Hairline everything.** 1px strokes, dotted construction lines, corner
  brackets, registration marks, crosshairs. The overlay behaves like a
  measurement instrument examining a specimen, not decoration.
- **Micro-type in gridded clusters.** 6–9px columns/blocks of type at the edge
  of legibility (pixel fonts welcome). Reads as texture first, data second.
- **One large typographic moment.** Study number huge, title small beneath,
  micro details under that. Distinct typographic voices, never blended.
- **Subject stays hero.** Elements hug margins and annotate inward. Tracking
  brackets wrap the sim's screen-space bounding box.
- **Data as furniture.** Label/value spec tables, tick dials, scan arcs,
  dot-matrix grids, small bar readouts — all driven by *real* pipeline
  metadata, never fake greeble.
- **Restrained accent.** Monochrome ink + one configurable accent color per
  study. Neutrals stay fixed for consistency; accent harmonizes with render.
- **Mostly static, some ticking.** Frame counter, bar readout, dial, table row
  highlight cycle, bbox brackets tracking. Everything else holds still.

## Content voice

All displayed titles, summaries, labels, parameter names, and captions follow
`../docs/TECHNICAL_VOICE.md`. KC may select a poetic main display title; the paired
subtitle and all supporting text remain technical. The overlay reports the model,
implementation, parameters, measurements, and identified observations. It does not add
fictional instrument readouts, anthropomorphic narration, or scientific claims inferred
from appearance.

Text fields come from canonical Study records. Biological, physical, or ecological
terms require a cited basis or an explicit analogy label. Metrics must retain their
definitions and units. Presentation controls such as typography, palette, and layout
do not alter the underlying technical description.

Canonical Study-card validation rejects em dashes, negative parallel constructions,
and high-confidence stock AI phrases before the text reaches the overlay. Aspect labels,
interface labels, and component defaults follow the same rule. Legacy aspect strings are
accepted as import aliases but are normalized before display or export.

Approved Look variations may provide a checksum-aware `overlay-parameter-manifest.json`
exported from the live Behavior HDA. Each record has a stable dotted key, label, Houdini
parameter token, scalar value, type, units, optional fixed comparison range, and animation
status. The generated `study.json` retains the records in `overlay_parameters`; components
should address stable keys rather than labels. Bar and dial components must use the declared
comparison range when comparing sibling variations.

## File map

```
design-overlay-generator/
├── DESIGN.md            ← this file (reference)
├── CLAUDE.md            ← working guide for agents (verify commands, gotchas)
├── references/          ← the mood-board images the visual language came from
└── web/                 ← the whole app; open index.html directly (file:// ok)
    ├── index.html       ← shell: left panel skeleton + canvas + scrubber
    ├── styles.css       ← panel/stage styling (dark UI)
    ├── fonts/           ← font files (user-supplied)
    ├── fonts.js         ← FONT_LIBRARY registry; injects all @font-face rules
    ├── sample-study.js  ← window.SAMPLE_STUDY: deterministic fake study.json
    ├── capture.html     ← headless single-frame capture page (see Pipeline)
    ├── capture.js       ← capture entry: applies {study, config}, draws once
    ├── overlay.js       ← core: palettes, TYPE, layout, helpers, registry,
    │                      drawOverlay()
    ├── components.js    ← all overlay components (registration order = draw
    │                      order); the design system itself
    └── app.js           ← panel UI generation, canvas, playback, drag-drop
                           preview, persistence (localStorage + export/import)
```

Plain classic scripts, no build step, no modules, no network dependencies —
must keep working from `file://`.

## Pipeline (built — see houdini-ai docs/DETAIL_PASS_PROMOTE.md)

```
Houdini exporter                 →  study.json sidecar
  (../houdini/export_overlay_study.py, hython)
web/ deterministic renderer      →  live preview  +  headless PNG seq (alpha)
  (capture.html + capture.js, driven by ../src/houdini_ai/detail_promote.py)
ffmpeg                           →  composite over graded render → mp4
  (../src/houdini_ai/detail_promote.py composite_overlay)
```

Headless capture: `capture.html?frame=N&w=…&h=…` renders exactly one overlay
frame on a transparent canvas via the same `drawOverlay()`. The driver writes a
per-run `capture-input.js` (`window.CAPTURE_INPUT = {study, config}`) beside it
and removes it afterwards (gitignored); without it the page falls back to
SAMPLE_STUDY + defaults for manual testing. capture.js mirrors app.js config
semantics (defaults, deep-merge, TYPE application) — keep them in sync when the
config shape changes.

## Core invariants

- **Procedural layout, any AR/resolution.** All geometry derives from
  `u = min(W, H) / 1000` (scale unit) and margin `m = 0.055 * min(W, H)`
  (see `makeLayout` in overlay.js). Components are corner/edge-anchored.
  Never hardcode pixels; always multiply by `u`.
- **Deterministic per frame.** Rendering is a pure function of
  (size, study metadata, frame number, config). No `Date.now()`, no
  `Math.random()` in draw code — use `h.sval(seed, a, b)` for stable
  pseudo-randomness (`shared.seed` is hashed from study id). This makes the
  realtime preview and headless batch render pixel-identical.
- **Alpha-native.** The overlay draws on a transparent canvas; the checker /
  dropped render behind it is preview-only compositing done in app.js.

## Component system

Each component in `components.js` registers via
`window.OVERLAY.registerComponent({ id, label, defaults, schema, draw })`:

- `defaults` — param object (an `enabled: true` is added automatically).
- `schema` — array describing each param for the auto-generated panel UI:
  `{ key, label, type, ... }` with types:
  - `"number"` `{min, max, step}`
  - `"bool"`
  - `"select"` `{options: [...]}`
  - `"series"` (select over `Object.keys(study.series)`)
  - `"text"`
- `draw(env)` — `env = { ctx, L, P, study, frame, p, shared, T, h }`:
  - `L` layout `{W, H, u, m}` — see invariants above
  - `P` palette `{ink, faint, ghost, accent}`
  - `p` merged params (defaults ← saved config)
  - `T` type config (see Type system)
  - `h` helpers: `microFont(ctx, size, weight?)`, `drawMicroBlock(ctx, L, P,
    x, y, lines, align?)`, `pad`, `timecode`, `sval`, `hash32`,
    `studyBlockAnchor`, `studyBlockSpan`
  - `shared` — cross-component per-frame state (see below)

**Adding a component**: add one `R({...})` block to components.js in the
desired draw position. The panel UI, config defaults, and persistence pick it
up automatically — no other file needs touching. New params on existing
components likewise just need `defaults` + `schema` entries (saved configs
merge over defaults, so missing keys fall back cleanly).

**`shared` keys currently in use** (set → read):

- `seed` — set by core; stable per study.
- `anchor`, `studySpan` — set by core pre-pass from studyBlock config;
  read by ruler (tick avoidance) and studyBlock itself.
- `trBottom` — top-right column stacking cursor; set by dotMatrix, then
  advanced by dial. New top-right components should read + advance it.
- `tableTop` — set by specTable; read by bars to stack above the table.
  Components that stack should fall back gracefully when the key is
  undefined (source component disabled).

**Current registry (draw order):** frame (corner brackets + registration),
ruler (left edge), bbox (subject tracking brackets/coords/scanline),
trackCallout (markers/leaders/sparklines following study.tracks points),
identity (top-left micro cluster), dotMatrix (top-right), dial (top-right,
stacks under dotMatrix), studyBlock (big number + title, auto-anchored to the
vertical half the subject's bbox avoids), specTable (bottom-right label/value
rows with cycling highlight), bars (series histogram above the table),
summaryBlock (wrapped study-card summary column), bulletBlock (tick-marked
study-card bullets), footer (frame counter/timecode + blink), tag (rotated
edge text).

**Component wishlist (from references, not yet built):** background grid
(dot/line, spacing, region), hatched texture patches, scan arcs orbiting the
bbox, vertical micro-type columns for side margins, horizontal top ruler,
free-position data column (label/value pairs per corner).

## Type system

Three voices in `OVERLAY.TYPE` (mutated by panel, persisted in config):

| voice   | keys                                   | used for |
|---------|----------------------------------------|----------|
| numeral | `numeral, numeralSize, numeralTracking`| big study number |
| display | `display, titleSize, titleTracking`    | study title |
| micro   | `micro, microSize, microTracking`      | everything small |

Sizes are in u-units; tracking in em (applied via canvas `letterSpacing`,
which needs Chrome; always reset to "0px" after big-type draws so it doesn't
leak). `microSize` is a *base scale*: element code calls
`h.microFont(ctx, 8·u … 9·u)` and those sizes scale by
`TYPE.microSize / MICRO_BASE (8.5)`, preserving hierarchy. Line heights in
`drawMicroBlock` scale the same way.

Defaults: Isonorm Monospaced 110/−0.085 · Blender Pro Bold 21/0.14 ·
Iosevka Mono Light 8.5/0.08.

## Fonts

`fonts.js` holds `FONT_LIBRARY` (label + file); it injects `@font-face` rules
for all of them (CSS injection, not FontFace API — the API's fetch is blocked
on `file://`). To add a font: drop the file in `web/fonts/`, add one registry
line. Canvas does **not** trigger lazy font loads — app.js calls
`document.fonts.load()` before repainting whenever a family is applied; keep
that pattern.

Notes: `kroe0756.ttf` = kroeger 07_56 and `SCHO1056.TTF` = schoenecker 10_56
(pixel fonts — crisp only near integer pixel sizes; nudge micro size in 0.25
steps at 100% zoom). `2DADEC_*.ttf` have blanked name tables (MyFonts kit),
actual face unknown — labeled "2DADEC A/B".

## Palettes

`OVERLAY.PALETTES`: name → `{ink, faint, ghost, accent}`. Ink family is fixed
per light/dark variant ("bone" for dark renders, "graphite" for light);
accent varies. Add palettes there; the select repopulates automatically.

The **custom** palette is built per study from four colors extracted from the
render itself: "create palette from frame" in the panel samples the current
backdrop frame (16-level histogram, then chroma-weighted farthest-point
selection so the render's own accent survives the dominant background) and
drops the four colors into the config, where color pickers refine them. A
role mapping links every palette slot (ink/faint/ghost/accent) to one of the
four; ink-family roles keep their standard alphas so hairlines stay
hairlines. Resolution lives in `OVERLAY.resolvePalette(name, custom)` —
shared by app.js and capture.js — and the resolved `P.chips` always carries
the four raw tones, which the frame component's color bar draws.

## Config & persistence

Config shape (the exported source of truth and headless render input):

```jsonc
{
  "studyId": "STUDY-042",
  "aspect": "9:16 | 1080x1920",        // key into PRESETS in app.js
  "palette": "bone / signal red",       // key into OVERLAY.PALETTES, or "custom"
  "custom": {                            // per-study four-color palette
    "colors": ["#d9f5fd", "#9ca3ac", "#ca5764", "#281539"],
    "roles": { "ink": 0, "faint": 0, "ghost": 0, "accent": 2 }
  },
  "render": {                            // optional: latest-render pointer,
    "video": "…/renders/look.mp4",       // written by the pipeline; loads as
    "still": "…/renders/look.0207.png"   // backdrop on boot (video → still →
  },                                     // checker). ?bg=<path> overrides.
  "type": { "numeral": "Isonorm Monospaced", "numeralSize": 110, /* … */ },
  "components": { "frame": { "enabled": true, "bracketLen": 16, /* … */ } }
}
```

- Autosaves on every change to `localStorage["dog.study.<studyId>"]`.
- A real exported study.json can be dropped or imported onto the page: it
  becomes the active study (persisted under `dog.activeStudy` — big number,
  tracks, series, and frame count all switch to it) until "sample study" in
  settings restores the stand-in. Configs are stored under the studyId they
  name, so study/config import order doesn't matter.
- Export/import buttons in the panel (import validates JSON then reloads).
- Saved configs deep-merge over defaults, so adding params/components never
  breaks old saves. Renaming a param key orphans the old saved value
  (harmless) and resets to default.
- URL params for headless driving / repro: `?ar=9:16&frame=300&palette=…`
  (`ar` prefix-matches the preset name).

## study.json schema (v0 — see sample-study.js for the live stand-in)

```jsonc
{
  "id": "STUDY-042",
  "number": 42,
  "title": "NONLOCAL AFFINITY",
  "subtitle": "agent fields with distance-defying attraction",
  "source": "arXiv:cond-mat/0611743",
  "date": "2026-08-19",
  "solver": { "name": "POP/VEX", "dt": "1/240", "substeps": 4, "seed": 8181 },
  "params": [["AGENTS", "250 000"], ["R_ATTRACT", "0.42"]],
  "summary": "long study-card summary for the summaryBlock column",
  "bullets": ["study-card bullet", "..."],
  "credits": "bzor computational studio",
  "fps": 24,
  "frames": 600,
  "series": { "energy": [/* per-frame 0..1 */], "cohesion": [] },
  "bbox":   [/* per-frame [x0,y0,x1,y1], normalized screen space */],
  "tracks": {
    "leader": {                       // flagged point exported per frame
      "screen": [[0.51, 0.44] /* or null when offscreen/behind camera */],
      "depth":  [6.2],                // raw camera depth
      "values": { "speed": [0.7] }    // sampled point attribs, normalized 0..1
    }
  }
}
```

`bbox` and `tracks` come from projecting sim geo through the render camera
(`../houdini/export_overlay_study.py`; tracked points are flagged in the HIP
via the `overlay_track` point group + optional `track_label` string attrib, or
by point number on the exporter CLI). Text fields (number, title, subtitle,
summary, bullets, params, credits) come from the Study's canonical
`00_study/study-card.json`. bbox drives study-block placement avoidance and
the tracking component; tracks drive the point-callout component.

## Open items

- **Per-component nitpicks + new components** (current phase — see wishlist).
- **Social safe zones.** Preview has an IG-guides toggle; may need "safe"
  layout variants per platform.
- **Bake chosen fonts/config as study defaults** once the look settles.

The completed export, headless render, composite, and promotion flow is documented
in `../docs/DETAIL_PASS_PROMOTE.md` and implemented by
`../src/houdini_ai/detail_promote.py`.
