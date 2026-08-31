# Bzor Computational Studio — Vision

> **This is the canonical statement of the studio pipeline.** Every other document in
> `docs/` either supports a stage described here or is historical. When another document
> contradicts this one, this one wins and the other should be updated or archived.
>
> This document is meant to be edited. When the practice changes, change this first.

## Identity

A computational research and production system where KC and Hermes construct, test,
instrument, and document rule-based models, then convert selected results into reproducible
audiovisual specimens. The primary subjects are agent-based systems, cellular automata,
graph dynamics, fields, collective motion, stochastic processes, and related numerical
methods.

Project language follows `TECHNICAL_VOICE.md`. Summaries, descriptions, captions, labels,
and public copy use scientific and technical terminology with explicit claim status,
provenance, measurements, and limitations. KC may select a poetic main display title when
useful, paired with a technical subtitle. KC owns visual treatment and presentation, but
presentation language must not overstate what a model or experiment establishes.

Discord is the sole human interaction surface. The local Studio is the private canonical
vault (records, artifacts, receipts, lineage). The public website is a read-only, curated
projection. Nothing becomes public without explicit approval.

## The pipeline

```text
Seed Bank (Discord forum)
  pool of initial ideas, incubated conversationally
        │  KC promotes a seed
        ▼
Study (Discord forum thread)
  brainstorm sim directions: paper reproduction or from scratch
        │  KC promotes one or more behaviour directions
        ▼
Behaviour production (system-built)
  route A: threeJS sim with sliders  ·  route B: straight to Houdini
  simple renders per candidate; iterate on the most promising
        │  KC promotes the best behaviour
        ▼
Look development (artist-led)
  sim finalized as a live HDA, linked into a look template
  KC authors look / feel / colour / camera in the HIP
        │  KC declares the HIP locked
        ▼
Render (system-owned)
  bounded, single-pass, verified; not yet the final artifact
        │  render verified
        ▼
Detail pass (design overlay generator)
  KC adjusts overlay details in realtime over the render
        │  KC promotes
        ▼
Final package
  postable video, archival media, reproducible source, lineage
        │  KC approves destination, media, and text
        ▼
Publish (socials + Field Station archive)
```

Every arrow crossed by a gate is an explicit, recorded KC decision with a durable local
receipt. The system proposes and produces; KC promotes.

## Stages and gates

### 1. Seeds

The `seed-bank` Discord forum holds one thread per idea. Hermes reads all input
collaboratively, maintains the canonical private Seed record (title, summaries, typed
references, tags, open questions, constraints), and incubates the conversation.

**Gate:** KC promotes a ready Seed. This creates exactly one linked Study and its forum
thread in the studies forum. Promotion is idempotent; the Seed is preserved.

### 2. Study brainstorm

One persistent forum thread per Study. The conversation explores directions for the
underlying simulation — implementing a research paper (reproduction, interpretation, and
mutation clearly labelled) or designing a mechanism from scratch. Behaviour, Look,
Detail, and Delivery are phases in the local records, not separate threads.

**Gate:** KC promotes one or more behaviour directions into production.

### 3. Behaviour production

The system builds each promoted direction. Two legitimate routes:

- **Route A — threeJS prototype:** a browser sim with sliders for realtime parameter
  exploration. Findings and chosen parameter ranges are recorded so the Houdini
  implementation inherits them.
- **Route B — straight to Houdini:** VEX/OpenCL kernels, cheap instrument scenes,
  reproducible HIP files.

Either route produces simple diagnostic renders per candidate. Iteration concentrates on
the most promising candidate; the others are archived with their evidence, not deleted.

**Gate:** KC promotes the best behaviour to look development.

### 4. Look development

The promoted sim is finalized as a **live HDA**: exposed parameters, re-simmable inside
the look scene, behaviour still tweakable while the look develops. Heavy sims may bake an
internal cache as a performance optimization, but the HDA is the canonical artifact — a
cache is never the handoff itself.

The HDA is linked into a **look template** from the setup library
(`houdini/look_setups/`): environment + lighting starting points. `basic` is the first
and currently only entry; the library grows from setups KC has actually used, never from
speculative generalization.

KC owns everything visual from here: look, feel, colour, materials, lighting, camera,
framing — authored directly in the flat artist-owned Look HIP. Hermes provides technical
support on request but never regenerates over the artist file.

**Gate:** KC declares the HIP locked and identifies the authoritative file. The system
snapshots it (path, checksum, versions, frame range) and preflights a fresh reopen.

### 5. Render

The system owns bounded rendering of the locked snapshot: deterministic frame paths,
frame validation, temporal continuity validation, encoding, and a render receipt bound to
the locked HIP checksum. A completed render is not yet the final artifact.

A delivery render runs as one uninterrupted pass. Resume is only safe once a scene's
geometry is cached to disk, because a live-HDA scene re-cooks its solver per run and the
joins between runs are visible in motion. Deliverables are 30 fps, and the preview encode
sits in the Look directory beside the HIP. See `RENDER_INTEGRITY.md`.

**Gate:** render verified — the package moves automatically to the detail pass.

### 6. Detail pass

The verified render is loaded into the **design overlay generator**
(`design-overlay-generator/`). KC adjusts the detail/HUD overlay in realtime over the
footage.

**Gate:** KC promotes from within the detail pass. This produces the final postable
video plus the full package: archival media, platform derivatives, source, credits,
accessibility text, and lineage.

### 7. Publish

Approval-gated, one destination at a time. Posting requires KC's explicit approval of the
exact media, text, account, and destination. The Field Station (public website) archives
the curated Study record; site inclusion is a separate decision from production promotion,
governed by an explicit allowlist. Public exposure is treated as irreversible.

## Rules that do not change

1. KC has final authority over research direction, selection, and presentation. Hermes
   proposes testable alternatives, reports evidence, challenges unsupported claims, and
   follows firm direction.
2. Promotion is a KC decision. Metrics and scores are evidence, never automatic gates.
3. Every promotion and publication decision produces a durable local record.
4. Public actions always require explicit approval; nothing is uploaded automatically.
5. Test mechanisms cheaply; separate model evaluation from visual presentation.
6. Preserve informative failures, null results, and rejected branches; do not retain every variation.
7. Automate a step only after it has repeated manually and can be verified mechanically.
8. Publish exhaust from real work; platform cadence never drives the laboratory.

## Known gaps (next work)

- **HDA packaging (stage 4):** the live-HDA contract and starter instantiation are in
  place (`houdini/instantiate_look_starter.py`, verified against the Study 003 HDA),
  but packaging a behavior as an HDA is still per-behavior bespoke work following the
  `build_nonlocal_affinity_hda.py` pattern; a reusable packaging path emerges as more
  behaviors repeat it.
- **Detail-pass promote (stage 6):** built — see `DETAIL_PASS_PROMOTE.md`. The
  remaining wiring is Hermes-side: calling `python -m houdini_ai.detail_promote` when
  KC promotes in the Study thread, and posting the preview back.
- **Safe resume (stage 5):** a delivery render must currently run in one pass, because
  runs do not share a solver trajectory. Caching a simulation to disk in the Look HIP
  removes the cause and makes resume safe. Not yet adopted; it is a post-lock scene
  change and needs KC's approval per Study. See `RENDER_INTEGRITY.md`.
- **Overlay manifest checksum (stage 6):** a headless manifest export cannot bind a HIP
  checksum, so locked delivery needs one manual GUI export. Fixing the dirty check in
  the HDA builder would close it.
- **Legacy Study directories:** `studies/001-memory-field/`, `studies/002-mass-flow/`,
  and `studies/behavior/scar-tissue/` predate the `study_NNN_slug` contract; none has a
  `00_study/`, and Study 001 uses `01_behavior/02_selects/` instead of `02_review/`.
  `study-init` would create a parallel directory rather than adopt one, so migration is
  an explicit decision. Study 001 completed the full stage 4-6 pipeline (through the
  2026-08-30 promote) in place under its legacy name; its variation identity lives in the
  specimen sidecar's `variation` record rather than `00_study/variations.json`.
- **Setup library (stage 4):** only `basic` exists; grows organically with use.

## Document map

Current, canonical:

- `VISION.md` — this document.
- `STUDY_VAULT.md` — the per-Study directory and three-axis naming contract.
- `STUDIO_ARCHITECTURE.md` — storage split, record stores, and compatibility layer.
- `TECHNICAL_VOICE.md` — terminology, claim discipline, and writing standard for all outputs.
- `DISCORD_PUBLIC_STUDIO_ARCHITECTURE.md` — Discord surfaces, seed bank, site states,
  publication boundary.
- `STUDIO_PROTOCOL.md` — KC–Hermes conversational conventions.
- `ARTIST_LED_LOOK_HANDOFF.md` — stage 4–6 mechanics (live-HDA contract).
- `RENDER_INTEGRITY.md` — stage 5 reproducibility limits, the single-run rule, and sequence verification.
- `DETAIL_PASS_PROMOTE.md` — stage 6 detail-pass and promote flow.
- `THREEJS_PROTOTYPE_ROUTE.md` — stage 3 browser-prototype route and identity contract.

Historical documents (superseded vision/roadmap/plans, retired workflows) are being moved
to `docs/archive/` — kept for reference, no longer authoritative.
