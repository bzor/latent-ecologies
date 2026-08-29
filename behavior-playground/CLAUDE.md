# Working on behavior-playground

The shared harness for browser behaviour prototypes — stage 3, route A of
`docs/VISION.md`; full design in `docs/THREEJS_PROTOTYPE_ROUTE.md`.

## What this is

A slider-driven sim playground: `web/harness.js` builds the panel, playback,
seed control, and preset export/import from a kernel's declared schema. Kernels
are tiny files implementing `init/step/draw`. Prototypes for a Study live in
that Study's vault (`01_behavior/01_work/prototypes/<id>/`, created with
`python scripts/scaffold_prototype.py <study> <proto-id> [--three]`); the
reference kernel lives at `reference/affinity/` and doubles as the regression
target. No server, no build step — `file://` works; classic scripts only.

## Kernel contract

`BP.registerKernel({...})` with: `id`, `title`, `mechanism` (`name-vN`),
`mechanismVersion`, `studyId`, `initialization`, `ordering`,
`view` (`"canvas2d"` or `"three"`), `defaults` (flat, must include `seed`),
`schema` (`{key, label, type: int|number|bool|select, min, max, step, options,
identity}` — `identity: false` marks display-only params that never reset the
sim), `init(params)`, `step(sim, params)`, `draw(view, sim, params, frame)`.

For `view: "three"` the harness supplies `{THREE, renderer, scene, camera}` and
calls `renderer.render` after `draw`; `vendor/three.min.js` is r0.160.1, exact
copy from npm — never modify it.

## Rules

- **Determinism**: `init`/`step`/`draw` are pure functions of (params, frame,
  canvas size). Never `Date.now()` or `Math.random()` — all randomness from
  `BP.mulberry32(params.seed)` (mulberry32-v1, bit-identical to
  `website/affinity-core.js` and the Python Mulberry32 in
  `houdini/build_nonlocal_affinity_hda.py`; never alter `web/rng.js` without
  versioning the identity contract).
- **Identity params reset the sim**; only `identity: false` params may change
  mid-run. Anything KC could not reproduce from an exported preset is a bug.
- **Presets are the record**: exported `*.preset.json` must validate against
  `schemas/studio/prototype-preset.schema.json` (`validate_record
  ("prototype-preset", ...)`). localStorage is never canonical.
- **Preview-tier counts** — mechanism and parameter feel, not scale. Scale
  belongs to Houdini (`integration_authority: houdini-vex`).
- The reference kernel wraps `website/affinity-core.js` verbatim; do not fork
  the sim math into the kernel. `tests/test_behavior_playground.py` enforces
  parity in Node — run it after touching the harness or kernel.

## Verify visual changes with a screenshot

```powershell
python scripts/capture_prototype.py behavior-playground/reference/affinity/index.html `
    --frame 240 --out "<scratchpad>\shot.png"
```

Then Read the PNG. `--use-angle=swiftshader` is already passed for `three`
kernels; headless URL params are `?p=<base64url preset>&frame=N&size=PX&autoplay=0`.
