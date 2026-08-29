# Bzor Computational Studio — roadmap

> **Phase model revised 2026-08-21.** Chromatic and Cinematography are no longer separate
> Study phases. KC authors colour, material, lighting, camera, and framing directly in the flat
> artist-owned Look HIP. The active sequence is Behavior → Look → Specimen → Delivery. Detailed
> Chromatic/Cinematography sections below remain historical capability notes, not directory or
> automation requirements.

## Direction

Rebuild the current Houdini AI laboratory as a modular creative studio with Behavior,
artist-led Look Development, Specimen, Delivery, and Field Station concerns.
Keep proven automation where it serves the new practice; replace assumptions that couple
simulation, look, camera, rendering, and publication into one study manifest.

This roadmap is ordered by creative leverage. Public integrations come after the local
studio can capture decisions and produce credible work.

## Active golden-path release

The current release is completion-oriented: represent **Scar Tissue** as the backward
golden specimen, then build **Pilot Study 003** forward through the same structured path.
This avoids completing six isolated labs before testing whether they form a pleasant
creative practice.

The release sequence is:

1. Preserve the clean Houdini-free baseline and current generated evidence.
2. Register Scar Tissue's exact behavior, look, palette, cinematography, handoff, render,
   and delivery state as one complete specimen lineage.
3. Replace legacy-job-only discovery with one safe artifact catalog and Review Inbox.
4. Add an active creative session showing phase, selected branch, open decisions, process
   notes, blockers, and recommended next action.
5. Add a Behavior Direction Board between seed selection and probe implementation.
6. Use Pilot Study 003 to validate Behavior, a flat artist-owned Look HIP, direct Specimen/detail
   handoff, Delivery, and private Field Station workflows in order.
7. Run a bounded completion audit: fix release blockers, defer non-blocking refinements,
   and stop expanding the release once the pilot reaches a validated private package.

Release completion requires:

- Scar Tissue is queryable as the first complete structured specimen lineage.
- Pilot Study 003 travels from seed to validated private Field Station package.
- Ordinary review requires no directory hunting and uses one Review Inbox.
- Conceptual branches remain distinct from parameter iterations.
- Cheap motion checks and one-frame refinements are available before expensive rendering.
- Substantial compute remains approved, resumable, and independently validated.
- Process observations are captured in context and visible in the Studio.
- Nothing is uploaded or made public.

The detailed implementation plan is stored at
`.hermes/plans/2026-08-15_112312-computational-studio-golden-path.md`.

Baseline at release start: **155 tests passed, 1 skipped** with
`PYTHONPATH=src python -m unittest discover -s tests`.

## What remains useful

Retain and generalize:

- Houdini, Hython, Karma, XPU, FFmpeg, and license/device discovery;
- deterministic source-state and effective-configuration snapshots;
- job directories, stage receipts, logs, resume, and artifact validation;
- PNG-sequence repair and independent encoding/package stages;
- VEX-heavy simulation and versioned Houdini scene builders;
- local Review Studio media discovery, range serving, path containment, comparisons,
  timecoded notes, and implementation responses;
- private-by-default, approval-gated publication boundary;
- Study 001 and Mass Flow as historical prototypes and regression fixtures.

Replace or retire:

- the single monolithic study schema;
- hard-coded Study 001 pipeline paths and captions;
- Mass Flow-specific parameter discovery in the review interface;
- the assumption that every experiment proceeds through a full specimen render;
- track status inferred from render quality;
- social outputs generated before an editorial candidate has been selected.

Do not delete historical jobs or studies during the redesign. Archive their role in the new
index and remove only after a separately reviewed retention plan.

## Phase 0 — Freeze and reframe

**Goal:** establish a clean boundary between the prototype era and the new studio.

Work:

- Mark Study 001 and Study 002 as legacy prototype-era records.
- Preserve the currently running Mass Flow output without further artistic iteration.
- Replace the project north-star and workflow documentation with the studio model.
- Record an architecture decision describing what is retained, adapted, and retired.
- Define shared vocabulary for tracks, lifecycle states, artifacts, components, proposals,
  promotions, and publication candidates.

Acceptance:

- A new collaborator can explain the six tracks, promotion flow, and safety boundaries from
  the documentation alone.
- Existing tests and historical commands still work.
- No existing generated artifact is deleted or publicly exposed.

## Phase 1 — Studio kernel and idea inbox

**Goal:** make conversation and the local Studio a reliable front door for new work.

Work:

- Introduce separate schemas for idea, proposal, experiment, component, specimen, and
  editorial records.
- Store versioned creative intent under `studio/`; keep mutable local operational state
  beneath `work/studio/`.
- Add CLI operations to capture/list/show ideas and create bounded proposals.
- Add Studio API and interface views for Inbox, Proposals, Runs, Reviews, Components,
  Specimens, and Editorial Queue.
- Expand decisions to keep, iterate, mutate, hold, archive, reject, and promote.
- Add promotion records and private-by-default publication tags.
- Generate a compact machine-readable studio summary for Hermes.

Acceptance:

- KC can say `Seed: ...`; Hermes can capture it without hand-editing JSON.
- An idea can become a proposal without launching Houdini.
- A proposal displays question, track, cost tier, outputs, and stop conditions.
- A reviewed artifact can be promoted with rationale and exact lineage.
- Tagging an artifact for X or the website performs no network action.

## Phase 2 — Behavior Lab vertical slice

**Goal:** reach a useful diagnostic result from an idea quickly enough to support genuine
exploration.

Work:

- Define a behavior experiment manifest independent of materials and final camera.
- Build canonical cheap instrument scenes and OpenGL or low-cost Karma preview paths.
- Support a small family of bounded mutations from one base mechanism.
- Emit sharp motion loops, field slices, force decomposition, selected metrics, and a HIP.
- Add research-source records with citation, license, reproduction boundary, assumptions,
  and mutation notes.
- Add behavior comparison and promotion views to the Studio.
- Implement the first post-reset experiment: scar-tissue paths that reinforce, saturate,
  repel, decay, and regenerate.

Target budget:

- first still or viewport evidence in under two minutes after Houdini startup;
- a ten-second diagnostic loop in under ten minutes on the current workstation;
- no full Karma specimen render in the Behavior Lab acceptance path.

Acceptance:

- Same-seed probes are materially reproducible; changed seeds are distinct.
- Mechanism and measured effects are legible in instrument mode.
- At least three conceptually different mutations can be compared in one Studio view.
- KC can promote one behaviour or archive the family without creating a specimen.

## Phase 3 — Look Development and Chromatic Labs

**Goal:** develop reusable presentation languages without contaminating behavioural judgment.

Look Development work:

- Add canonical geometry, motion, scale, and lighting test scenes.
- Define look components with MaterialX, geometry representation, lighting dependencies,
  renderer compatibility, and cost.
- Prototype the first independent study: a Vellum membrane or fiber skin responding to
  canonical fields.
- Render contact sheets under controlled neutral and environmental lighting.

Chromatic work:

- Define OKLCH palette records with semantic roles, intended ratios, gamut, and mappings.
- Build harmony and ratio proposal tools around chosen anchors and reference images.
- Export palette roles to Houdini/MaterialX and CSS.
- Analyze rendered frames for observed area, luminance, chroma, contrast, signal scarcity,
  and major gamut failures.
- Keep instrument, specimen, and Field Station palettes separate.

Acceptance:

- Look and palette components can be reviewed and promoted without a behavior dependency.
- The same look can be applied to two canonical scenes without copying source.
- Palette contact sheets show intended roles and measured rendered proportions.
- Automated analysis reports evidence but cannot promote or reject a palette.

## Phase 4 — Cinematography Lab

**Goal:** find viewpoints and time windows that reveal or productively reinterpret a system.

Work:

- Define shot records with subject queries, event windows, camera rigs, lens, aspect,
  framing intent, focus policy, and composition guides.
- Extract spatial and temporal features from behavior caches.
- Generate deliberately diverse camera candidates rather than local transform jitter.
- Render low-resolution scout stills and short clips with optional thirds, diagonals,
  safe frame, depth segmentation, and focus overlays.
- Measure silhouette, frame occupancy, protected negative space, depth separation, motion
  direction, clipping, and colour hierarchy.
- Add coverage-set comparison and shot promotion to the Studio.

Acceptance:

- A cache can produce at least five meaningfully different shot families.
- Candidate sets include instrument, establishing, intimate, structural, and interpretive
  views when the source supports them.
- An event window may be selected from measured behavior rather than a fixed midpoint.
- KC can promote a shot while rejecting its temporary look or palette.

## Phase 5 — Specimen assembly

**Goal:** combine promoted components into the first coherent post-reset artwork.

Work:

- Define specimens as references to exact promoted behaviour, look, palette, shot, and
  optional sound components.
- Add compatibility checks and a deliberate override path for productive incompatibility.
- Build instrument and organism variants from the same behavioral lineage.
- Treat procedural sound, Ableton handoff, silence, and licensing as explicit choices.
- Reuse resumable rendering, validation, encoding, packaging, checksums, and provenance.
- Require a creative brief stating what the pairing reveals.

Acceptance:

- One command can plan cost and dependencies without launching a render.
- An approved plan can build a reproducible local specimen package.
- Interrupted rendering resumes without rerunning verified simulation.
- The package includes archival media, platform derivatives, HIP/source, field-note data,
  credits, accessibility text, and lineage.
- Nothing is uploaded.

## Phase 6 — Field Station alpha

**Goal:** publish a durable, distinctive archive from approved structured records.

Work:

- Define public/private editorial projections so private studio dialogue stays private.
- Generate static study, component, specimen, and lineage pages.
- Design the Field Station interface around branching experiments, observations, and
  relationships rather than a conventional gallery grid.
- Support media, source excerpts, citations, downloads, reproducibility, and accessibility.
- Create a local deploy preview and broken-link/media/license validation.
- Author a Field Station design system without forcing artwork palettes onto the UI.

Acceptance:

- The site builds locally from approved records only.
- A page distinguishes measured, derived, observed, and hypothesized claims.
- Downloadable assets have explicit inclusion and license status.
- Private notes, unapproved artifacts, local paths, and credentials cannot enter the build.

## Phase 7 — Editorial packaging and social publishing

**Goal:** turn selected studio output into platform-specific packages without letting
platform cadence drive the laboratory.

Work:

- Build editorial candidate queues for website, X, Instagram, and YouTube.
- Generate aspect, duration, codec, poster, caption, alt text, credits, links, and thread or
  description drafts per destination.
- Add approval views showing the exact media and text that would be posted.
- Record publication receipts and canonical URLs.
- Integrate one external destination at a time, using a dedicated bot or studio account
  only after KC explicitly authorizes credentials and scope.

Acceptance:

- Every platform package validates locally before approval.
- Editing a caption cannot invalidate or rerender the specimen.
- Posting requires explicit approval of destination, account, media, and final text.
- Failed posting never damages the local package or lineage.
- The system records what was actually published, not what was intended.

## Phase 8 — Assisted discovery

**Goal:** use automation to widen exploration while preserving artistic authority.

Possible work:

- paper and reference watchlists;
- bounded overnight mutation batches with compute budgets;
- anomaly and diversity surfacing;
- visual and behavioral embeddings for navigation;
- crossbreeding compatible rule genomes;
- audience proposals translated into non-executable candidate records;
- camera and palette diversity search;
- scheduled local editorial summaries.

Acceptance:

- Autonomous work has explicit time, storage, render, and mutation boundaries.
- Every surfaced result has source and parameter lineage.
- Audience input remains untrusted and cannot execute code or start compute.
- Metrics shortlist; KC promotes.

## First release sequence

The smallest useful order is:

1. Phase 0 documentation and vocabulary.
2. Idea inbox, proposals, decisions, promotions, and tags.
3. Scar Tissue Behavior Lab vertical slice.
4. Vellum canonical look study and first chromatic families.
5. Camera scout over the promoted scar-tissue candidate.
6. First assembled specimen.
7. Field Station alpha page for its complete lineage.
8. Approval-gated X field observation and Instagram specimen packages.

This sequence validates the entire studio with one lineage while keeping each laboratory
independently useful.
