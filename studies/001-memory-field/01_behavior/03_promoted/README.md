# Study 001 Refractory Route Behavior HDA v1

## Purpose

Artist-editable Refractory Route Ecology Behavior HDA promoting the five Study 001
browser selects into the VEX-authoritative Look Development handoff, with one-click
parameter-manifest export for the overlay detail generator.

## Files

- `refractory-route.hda`: `bzor::refractory_route::1.0`
- `refractory-route-demo.hiplc`: verified demonstration scene
- `initial-states/initial-state-{1..5}.bgeo.sc`: browser-exact initial states, embedded in the HDA per preset
- `receipts/*.receipt.json`: Node-exported identity receipts and reference trajectories from the promoted browser kernel
- `audit.json`: fresh-session cook, browser-parity, structural, procedural-identity, and manifest audit
- `audit-overlay-parameter-manifest.json`: exercised export-button probe

## Presets

The `Select Preset` menu applies the promoted select's full parameter set and resets
the simulation. Tokens map to the ordered selects in
`studies/001-memory-field/01_behavior/02_selects/`:

1. `14 · Braided deflection · Hard - switchbacks STUDY V1`
2. `26 · Resource pilgrimage · Drifting foragers STUDY v2`
3. `31 · Crowd pressure · Sparse crossings STUDY V3`
4. `38 · Drift and exploration · Responsive walkers - STUDY - v4`
5. `41 · Pulse waves · Long wave - v5`

Each preset loads a browser-exact embedded initial state. Changing an identity
parameter (seed, agent count, grid, domain, speed) regenerates a deterministic
procedural identity from the same mulberry32 consumption order; press
`Reset Simulation` after identity changes.

## Output

One point stream with two point groups:

- `field`: 128×213 route-memory cells carrying `resource`, `fresh`, `scar`,
  `trace_dir`, `idle_age`, `healed`, `occupancy`;
- `agents`: simulation agents carrying `v`, `energy`, `mode` (0 forage, 1 follow,
  2 deflect, 3 rest), and seed-derived profiles.

`Display` controls (point sizes, agent lift, preview colour) are viewport
conveniences, not Look decisions. Frame 1 is the initial state; with
`Steps / Display Frame` = S, frame N+1 contains N×S synchronous steps.

## Verification (audit.json)

- Embedded initial states match the browser receipts bit-exactly (all five presets).
- Agent trajectories match the browser reference within 4.2e-5 domain units through
  step 24 with 100% mode agreement (steps 1/6/12/24, all presets).
- Step-120 structural check: field statistics match the browser within ~1e-6;
  mode histograms match within a few agents; positions finite and in bounds.
- Procedural identity probe: changed seed regenerates a distinct finite identity.
- Fresh-session overlay parameter manifest export validates.

Known semantic notes: the browser kernel compares float32 state against float64
parameters; the follow-threshold comparison is `>=` in VEX to reproduce the
deposit-equals-threshold behavior of the Drifting Foragers select. The prototype's
`birth_threshold` only feeds browser event counters and is intentionally absent.
Browser event counters are not carried into the HDA.
