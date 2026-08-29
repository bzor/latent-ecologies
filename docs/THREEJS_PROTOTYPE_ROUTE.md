# Browser prototype route (threeJS)

Stage 3, route A of the pipeline in `VISION.md`: a promoted behaviour direction can be
built first as a browser sim with sliders for realtime parameter exploration, before —
or instead of going straight to — the Houdini implementation. The route formalizes what
Study 003 already proved informally: its Canvas prototype (`website/affinity-core.js`),
the pinned `mulberry32-v1` RNG, and the identity-ladder scripts that replayed the exact
JS graph and event history in VEX.

```text
direction selected (Study thread)
→ Hermes builds a prototype kernel in the shared harness
→ KC explores with sliders, saves presets
→ presets + findings exported into the Study vault
→ KC promotes a preset in the Study thread
→ Houdini implementation inherits the identity contract and parameters
```

## Shared harness

One small shared harness, following the design-overlay-generator conventions: plain
classic scripts, no build step, works from `file://`, no network dependencies
(three.js is vendored into the harness). It lives at the repo top level:

```text
behavior-playground/
├── CLAUDE.md                operational guide (kernel contract, rules, screenshots)
├── web/
│   ├── harness.js           panel generation, playback, seed control, preset export/import
│   ├── rng.js               mulberry32-v1 — the studio's canonical prototype RNG
│   ├── styles.css           dark panel/stage UI
│   ├── vendor/three.min.js  vendored three.js r0.160.1
│   └── template.html        copied per prototype by scripts/scaffold_prototype.py
└── reference/affinity/      reference kernel wrapping website/affinity-core.js verbatim;
                             Node parity-tested regression target
```

The harness provides what every prototype needs so kernels stay tiny: auto-generated
sliders from a param schema (the overlay generator's `defaults` + `schema` pattern),
play/pause/step/reset, steps-per-display-frame, a seed field with New Seed, a frame
counter, and canonical preset export/import.

## Per-study prototypes

Kernels and their evidence are Study-owned and live in the vault:

```text
studies/study_NNN_slug/01_behavior/01_work/prototypes/<proto-id>/
├── index.html           generated from template.html; static script tags only
├── kernel.js            the sim: init / step / draw against the harness contract
└── presets/             exported preset JSON files
```

KC-flagged presets and comparison captures go to `01_behavior/02_review/`; the
promoted preset is copied immutably to `01_behavior/03_selected/`.

## Identity contract

The point of the route is that what KC found in the browser survives the trip to
Houdini. Every kernel declares, and every exported preset records:

- mechanism id and version (e.g. `nonlocal-affinity-v1`);
- `rng: mulberry32-v1` and the documented order in which random values are consumed;
- the initialization convention and event/update ordering
  (e.g. `before-synchronous-position-update`);
- seed, full parameter values, and counts;
- `integration_authority: houdini-vex` — the prototype is evidence, Houdini is the
  production authority.

The preset shape generalizes `schemas/studio/affinity-preset.schema.json` into a
mechanism-agnostic `prototype-preset` schema. The Houdini implementation replays the
identity — same RNG, same consumption order, same event ordering — and verifies it by
state digest where feasible, exactly as the Study 003 identity ladder did. The
eventual behavior HDA exposes the same parameter names and ranges as the prototype's
sliders, so KC's slider intuition transfers directly to the Look HIP.

## Discord previews

The prototype runs locally. For the Study thread, the harness renders
deterministically from URL params (`?preset=…&frame=N`, like the overlay generator),
so Hermes can capture headless-Chrome stills and short clips of named presets and
post them for comparison. Poll responses in the thread remain non-binding evidence;
KC's preset promotion is the gate.

## Rules

- Deterministic: no `Date.now()`, no `Math.random()` in kernels — `rng.js` only.
  Same preset, same frame, same pixels.
- Preview-tier counts: prototypes explore mechanism and parameter feel, not scale.
  Scale belongs to Houdini.
- The exported preset file is the canonical record; browser localStorage is not.
- Prototypes never execute untrusted input and never load network resources.
- A promoted preset is immutable; refining it produces a new preset with lineage.

## Built

1. Harness (`behavior-playground/web/`) with the Study 003 affinity mechanism as the
   reference kernel — it wraps `website/affinity-core.js` verbatim, and
   `tests/test_behavior_playground.py` proves step-for-step parity and RNG identity
   (JS vs Python) in Node.
2. `schemas/studio/prototype-preset.schema.json`, registered as a validatable record
   kind in `studio_schema.py`; exported presets validate before registration.
3. `scripts/scaffold_prototype.py` — creates a wired prototype (index + kernel stub +
   presets/) in a Study vault; `--three` enables the vendored three.js view.
4. `scripts/capture_prototype.py` — deterministic headless-Chrome capture of any
   preset/frame for Discord previews.
