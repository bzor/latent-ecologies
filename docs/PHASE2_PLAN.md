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

Acceptance requires two same-seed smoke runs with identical semantic metrics and
canonical state hashes quantized to `1e-5`, a changed-seed run with distinct output,
a valid 100,000-agent full probe, and
a review image with legible large-scale flow structure.

Probe 001 processed 100,000 agents across 60 frames at approximately 2.08 million
agent-frames per second after startup. Seven compressed checkpoints plus one transient
state consumed 27.9 MB. Canonical ordered-point checksums matched across same-seed
smoke runs; the changed seed produced a distinct state.

Initial working budgets:

- **Probe:** 100,000 simulated agents, 12,000 deterministic review representatives,
  sparse checkpoint cache, host-side composition review.
- **Study:** up to 250,000 simulated agents, 25,000–75,000 adaptive render instances
  or derived trails, selected Karma checkpoints before sequence approval.
- **Specimen:** scale toward one million simulated agents only when the representation
  derives surfaces, curves, volumes, or importance-selected instances rather than
  asking the final renderer to shade every point identically.

## Milestone 2.2 — Materials and lighting

**Status: pending.**

- Test a small set of materially distinct MaterialX languages on one accepted cache.
- Build reusable key/fill/environment rigs and Karma quality presets.
- Compare CPU and XPU support, visual behavior, and cost.
- Select one authored material language rather than treating every variant as equal.

## Milestone 2.3 — Cameras and composition

**Status: pending.**

- Implement static observation, macro tracking, slow orbit, frontier follow, and
  event-driven focus as reusable rigs.
- Add automatic bounds, safe-frame, focus-target, and portrait-composition checks.
- Select camera motion because it reveals behavior, not simply because it moves.

## Milestone 2.4 — Fields and environments

**Status: pending.**

- Convert agent history into trails, surfaces, volumes, or environmental deformation.
- Test field-to-geometry, VDB, accumulation, and environmental shading workflows.
- Establish when full agents, derived representation, or a hybrid gives the strongest image.

## Milestone 2.5 — Integrated specimen

**Status: pending.**

- Combine the accepted scale, material, camera, and environment components.
- Produce organism and instrument versions at study quality.
- Promote genuinely reused code into stable libraries and document extension points.
- Run the complete resumable render, encode, and draft-package workflow.
