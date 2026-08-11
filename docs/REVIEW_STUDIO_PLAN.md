# Review studio plan

## Objective

Replace manual filesystem-link review with a structured local interface for motion
tests, look development, comparisons, and actionable artist feedback. Preserve the
existing boundary: generated artifacts and comments are local state; accepted intent
is translated into versioned manifests, VEX, scene builders, and lab logs.

## Implementation map

- `src/houdini_ai/review_studio.py`: discovery, safe media serving, JSON API, atomic
  review store, and local HTTP lifecycle.
- `website/index.html`, `website/styles.css`, `website/app.js`: dependency-free review
  client.
- `tests/test_review_studio.py`: discovery, path traversal, HTTP byte ranges, feedback
  validation, persistence, and state transitions.
- `website/README.md`: operator quick start and trust boundary.

API surface:

- `GET /api/jobs`
- `GET /api/reviews/<study-id>`
- `POST /api/reviews`
- `PATCH /api/reviews/<study-id>/<item-id>`
- `GET /media/<job-id>/<artifact-path>` with byte-range support

There is intentionally no execution endpoint.

## Milestone R1 — Artifact index

**Status: complete (2026-08-11).**

- Discover valid jobs from `work/jobs/*/effective-config.json`.
- Index bounded review, lookdev, package, and publication artifacts.
- Exclude frame sequences, caches, and temporary geometry from browser listings.
- Expose study metadata, source state, receipts, and selected system parameters.

## Milestone R2 — Local review service

**Status: complete (2026-08-11).**

- Add `houdini-ai review` with a local-only default bind.
- Serve static assets without a new runtime dependency.
- Support HTTP byte ranges for responsive video seeking.
- Enforce resolved-path containment for every artifact request.
- Provide no shell, Houdini, render, or arbitrary filesystem mutation endpoint.

## Milestone R3 — Review interface

**Status: complete (2026-08-11).**

- Present studies and jobs in recency order.
- Play motion artifacts and inspect stills.
- Switch among artifacts and compare same-kind outputs across jobs.
- Display run parameters and reproducibility provenance.
- Adapt from a three-column desktop studio to smaller screens.

## Milestone R4 — Structured feedback

**Status: complete (2026-08-11).**

- Record comments and constrained decisions.
- Attach optional playback timecodes.
- Store records atomically under `work/reviews/<study-id>.json`.
- Validate study identifiers, artifact existence, decision vocabulary, text length,
  timecode bounds, and open/resolved state.

## Milestone R5 — Reliability

**Status: complete (2026-08-11).**

- Cover discovery, frame-directory exclusion, path traversal, byte ranges, feedback
  round trips, artifact validation, and state updates with automated tests.
- Keep `work/reviews/` outside version control through the existing `work/*` rule.
- Document startup, trust boundaries, and the promotion path for accepted feedback.

## Next milestones

### R6 — Review queue and branch proposals

- Convert selected open notes into a read-only proposed change summary.
- Link resolved notes to resulting source commits and replacement jobs.
- Add named comparisons and approved artifact sets.

### R7 — Controlled execution

- Add a bounded queue for existing manifest-defined actions only.
- Show storage estimates, stage progress, logs, and cancellation state.
- Require explicit confirmation before starting expensive renders.
- Keep natural-language feedback separate from executable parameters.

### R8 — Public notebook extraction

- Generate curated study pages from approved artifacts and field notes.
- Separate private studio notes from public excerpts.
- Preserve publication approval and accessibility checks.
