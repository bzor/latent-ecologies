# Studio architecture

## Architectural decision

Use a small file-backed studio kernel and keep Houdini execution behind typed experiment
and specimen records. Extend the current dependency-light Python service before considering
a database or frontend framework.

Reasons:

- the existing JSON, filesystem, HTTP, and test approach works locally;
- versioned Study intent remains readable and portable;
- generated state stays disposable and out of Git;
- atomic JSON records are sufficient for one operator and one local agent;
- the system can reveal its true query and concurrency requirements before acquiring a
  database-shaped hat.

Revisit SQLite or another store when record count, indexing, concurrent writers, or public
service requirements make file-backed state measurably painful.

## Layers

```text
KC ↔ Hermes conversation
        ↓
Local Studio UI and CLI
        ↓
Studio kernel: records, validation, lineage, decisions, tags
        ↓
Phase runners: behavior / artist-led look setup / render / specimen / delivery
        ↓
Houdini + VEX + MaterialX + Karma + FFmpeg
        ↓
Validated artifacts and receipts
        ↓
Editorial projection → Field Station and platform packages
```

## Storage roles

The human-facing canonical artifact layout is defined in `STUDY_VAULT.md`.

Study-owned material lives beneath a numbered vault:

```text
studies/study_NNN_slug/
  00_study/             identity, status, decisions, lineage, artifact index
  01_behavior/          fixed phase contract: brief/work/review/selected
  02_look/              flat artist-owned HIP plus compact documentation
  03_specimen/          flat detail/overlay source, preview, and compact metadata
  04_delivery/          flat final media, package receipt, and necessary frame sequence
  90_shared/
  99_archive/
```

`work/` is disposable operational staging and legacy generated material. No approved
artifact may exist only beneath `work/`. `studio/` is reserved for system-wide records
and reusable components.

## Versioned intent and generated state

Versioned under Git:

```text
studio/
  ideas/                 selected or developed research seeds
  sources/               paper/reference metadata and notes
  experiments/           behavior and technical setup definitions
  components/            promoted immutable component records
  specimens/             assemblies referencing exact components
  editorial/             approved public selections and field-note copy
schemas/studio/           JSON Schemas for every record type
houdini/                  scene builders, VEX, materials, rigs, and render tools
src/houdini_ai/           studio kernel, CLI, runners, API, and packaging
```

Legacy mutable/generated state remains beneath ignored `work/` during migration:

```text
work/studio/inbox/        quick uncured idea capture
work/studio/proposals/    local proposals awaiting decisions
work/studio/promotions/   pending promotion records
work/studio/editorial/    tags and package candidates
work/jobs/                transient caches, staging, previews, renders, logs, receipts
work/reviews/             artifact and timecoded feedback
```

New Study-owned outputs resolve into the phase contract under `studies/`; the legacy paths
above remain readable until their callers have migrated. Quick ideas begin as local inbox records so capturing one does not dirty Git. When an idea
is scoped or selected, Hermes creates a versioned record with KC's approval or as part of an
explicit implementation request.

## Core record types

### Idea

Identity, raw wording, source links, inspiration, tags, questions, constraints,
provenance, visibility, and lifecycle state.

### Proposal

References an idea and defines question, hypothesis, minimal mechanism, fixed variables,
mutation axes, diagnostic outputs, estimated time/storage/render tier, stop conditions,
and approval state. A proposal cannot execute arbitrary commands.

### Experiment

Holds phase-specific intent and references approved runner identifiers and bounded parameters.
New work follows the Behavior → artist-owned Look → Specimen → Delivery lifecycle. Legacy
records may retain a `track` field for schema compatibility, but it does not define separate
departments or Study phases. Execution creates jobs; the experiment does not contain
shell text.

### Artifact

A generated file plus kind, role, checksum, dimensions or duration, source job, visibility,
editorial tags, and validation state. Artifact records never imply publication.

### Review decision

Artifact/timecode feedback with keep, iterate, mutate, hold, archive, reject, or promote;
assistant responses; status; and optional bounded implementation result.

### Component

An immutable promoted version of a behavior, look, palette, shot, or sound setup. It records
KC's rationale, evidence, source artifact/job/commit, compatibility metadata, dependencies,
and supersession lineage.

### Specimen

References exact component versions and states the technical and presentation rationale for their combination,
deliverables, sound decision, render budget, and approval status.

### Editorial candidate

References exact artifacts and holds destinations, editorial roles, visibility, readiness,
copy drafts, accessibility, credits, licenses, and approval receipts. Upload state is
separate from package readiness.

## Lifecycle and lineage

Records use stable IDs and append-only lineage links. Mutable workflow state may change;
promoted component payloads do not. Revisions create new versions and may supersede old
ones without destroying them.

```text
idea → proposal → experiment → job → artifact → component
                                           ↘ review
components → specimen → package → editorial candidate → publication receipt
```

Lineage edges carry a reason such as `derived-from`, `reproduces`, `mutates`, `promotes`,
`pairs-with`, `supersedes`, or `published-as`.

## Runner safety

Experiment records choose a known runner and typed parameters. A registry maps those names
to Python functions and versioned Houdini scripts. Free text, review comments, source URLs,
and publication copy never become command arguments without explicit bounded translation.

Cost tiers:

- `tiny`: no Houdini or a sub-minute local diagnostic;
- `probe`: expected under ten minutes and modest storage;
- `study`: longer local compute or selected Karma work, confirmation required;
- `specimen`: substantial render/storage/package work, explicit plan approval required;
- `external`: paid or remote services, separate explicit approval required.

Receipts record estimates and actual time/storage where measurable.

## Compatibility with the prototype pipeline

Wrap existing job and media infrastructure rather than rewrite it first:

- `doctor.py` remains workstation discovery.
- `jobs.py` becomes generic over record type and stage graph.
- `pipeline.py` is split gradually into shared execution/media utilities and legacy Study
  001 adapters.
- `mass_flow.py` remains a historical track runner until archived.
- `review_studio.py` grows studio stores and APIs while retaining safe media delivery.
- old manifests continue validating through `study.schema.json`; new records use
  `schemas/studio/`.

This compatibility layer lets the current Behavior phase use proven infrastructure while the
old vertical slice is retired gradually.

## Field Station boundary

The public site never reads `work/` directly. A projection step consumes only explicitly
approved editorial records, copies validated public artifacts into a clean build input,
removes local paths and private fields, and fails closed on unknown visibility or license.

Social adapters consume the same approved projection. Credentials and publication receipts
remain local secrets/state; canonical public URLs may be copied into versioned editorial
records after review.

## Testing strategy

- JSON Schema tests for valid and invalid records.
- Unit tests for lifecycle transitions, lineage, tags, visibility, and cost gates.
- Path-containment and atomic-write tests for every store.
- API round trips for ideas, proposals, decisions, promotions, and editorial tags.
- Runner registry tests proving free text cannot select commands or paths.
- Golden fixture tests for editorial projection with private-data leakage checks.
- Existing Houdini-free tests remain the fast regression suite.
- Small Hython smoke probes verify scene build, deterministic output, and artifact metadata.
- Full Karma and specimen renders are explicit workstation acceptance tests, not ordinary
  unit-test dependencies.
