# Phase 2 plan — Creative framework

## Strategy

Build four bounded, art-directed capability studies—scale and motion, materials and
lighting, cameras and composition, then fields and environments. Preserve components
after their first use and promote them into shared libraries when a second use proves
their reusable shape. Finish Phase 2 with one integrated specimen.

Every capability study must pass both a technical gate and an artistic gate. Point
count, render correctness, or automation alone is not acceptance; the result must
also establish hierarchy, rhythm, material intent, and an authored point of view.

## Milestone 2.1 — Scale and motion

**Status: complete (2026-08-11).**

- Simulate at least 100,000 deterministic agents in Houdini.
- Use an O(N) motion kernel suitable for dense populations.
- Separate full simulation scale from adaptive review/render representation.
- Record throughput, memory, bounds, speed distribution, and population integrity.
- Produce checkpoint caches and a portrait contact sheet without rendering every frame.
- Establish probe, study, and specimen population/render budgets.
- Extract shared deterministic initialization, integration, bounds, and metric conventions.

Original capability acceptance required two same-seed smoke runs with identical
semantic metrics and canonical state hashes quantized to `1e-5`, a changed-seed run
with distinct output, a valid 100,000-agent full probe, and
a review image with legible large-scale flow structure.

Probe 001 processed 100,000 agents across 60 frames at approximately 2.08 million
agent-frames per second after startup. Seven compressed checkpoints plus one transient
state consumed 27.9 MB. Canonical ordered-point checksums matched across same-seed
smoke runs; the changed seed produced a distinct state.

The capability proof remains preserved, but art direction subsequently moved the
active Mass Flow branch to an honest 4,000-agent population rendered one-to-one. The
current branch is volumetric, prewarmed, uses 25-checkpoint trails, deterministic
cohort-based flocking, and material-matched head spheres. Stronger feedback introduced
approximately `1e-5` parallel float drift, so current same-seed validation compares
physical metrics at `1e-4` tolerance while retaining changed-seed distinction and full
state digests for diagnosis.

Initial working budgets:

- **Probe:** 100,000 simulated agents, 12,000 deterministic review representatives,
  sparse checkpoint cache, host-side composition review.
- **Study:** up to 250,000 simulated agents, 25,000–75,000 adaptive render instances
  or derived trails, selected Karma checkpoints before sequence approval.
- **Specimen:** scale toward one million simulated agents only when the representation
  derives surfaces, curves, volumes, or importance-selected instances rather than
  asking the final renderer to shade every point identically.

## Milestone 2.2 — Materials and lighting

**Status: in progress.**

- Test a small set of materially distinct MaterialX languages on one accepted cache.
- Build reusable key/fill/environment rigs and Karma quality presets.
- Compare CPU and XPU support, visual behavior, and cost.
- Select one authored material language rather than treating every variant as equal.

Current result: Karma XPU is the accepted renderer; `studio_small_03_4k.exr` is the
accepted local dome source; trail emission is disabled; and the scripted look reproduces
the artist-authored graphite, metallic-black, dark-violet, 100 mm, shallow-DOF HIPLC
reference. Reusable non-environment key/fill rigs remain outstanding.

## Milestone 2.3 — Cameras and composition

**Status: in progress.**

- Implement static observation, macro tracking, slow orbit, frontier follow, and
  event-driven focus as reusable rigs.
- Add automatic bounds, safe-frame, focus-target, and portrait-composition checks.
- Select camera motion because it reveals behavior, not simply because it moves.

Current result: static portrait observation has a reproducible 100 mm camera, focus
distance 44, f/0.09 depth of field, and camera-relative backing card. Tracking, orbit,
frontier-follow, and event-focus rigs remain pending.

## Milestone 2.4 — Fields and environments

**Status: in progress.**

- Convert agent history into trails, surfaces, volumes, or environmental deformation.
- Test field-to-geometry, VDB, accumulation, and environmental shading workflows.
- Establish when full agents, derived representation, or a hybrid gives the strongest image.

Current result: cached agent history produces real 3D Karma curves with explicit depth
validation, and the active 4,000-agent branch renders every simulated trail plus every
head. Surface, VDB, accumulation, and environmental-deformation studies remain pending.

## Review integration

**Status: complete for the local-first milestone (2026-08-11).**

`houdini-ai review` indexes Phase 2 motion tests, lookdev stills, HIP/HIPLC scenes,
receipts, source state, and selected parameters. The browser supports comparisons and
timecoded structured feedback without exposing render or command execution. This is
the working approval surface while the remaining Phase 2 capabilities are developed.

## Milestone 2.5 — Integrated specimen

**Status: pending.**

- Combine the accepted scale, material, camera, and environment components.
- Produce organism and instrument versions at study quality.
- Promote genuinely reused code into stable libraries and document extension points.
- Run the complete resumable render, encode, and draft-package workflow.
