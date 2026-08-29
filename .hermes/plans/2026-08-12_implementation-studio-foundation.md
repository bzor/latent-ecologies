# Studio foundation implementation plan

> **For Hermes:** Implement this plan task-by-task using test-driven development. Do not
> commit, push, delete legacy artifacts, install dependencies, or start expensive renders
> without KC's explicit direction.

**Goal:** Build the local studio kernel and interaction workflow that can capture ideas,
create bounded proposals, review artifacts, promote components, and tag publication
candidates before implementing the new creative labs.

**Architecture:** Preserve the current dependency-light Python CLI, atomic JSON storage,
local HTTP service, and safe artifact serving. Add typed studio records and APIs beside the
legacy study pipeline, then use them to implement the first Behavior Lab vertical slice.
Versioned intent lives under `studio/`; quick capture and mutable operational state live
under ignored `work/studio/`.

**Tech stack:** Python 3.10+, standard library, jsonschema, Pillow, Houdini 22/Hython/VEX,
MaterialX/Karma, FFmpeg, vanilla HTML/CSS/JavaScript, unittest, Ruff when available.

---

## Delivery discipline

For every code task:

1. Write a focused failing test.
2. Run it and confirm the expected failure.
3. Implement only the required behaviour.
4. Run the focused test.
5. Run `PYTHONPATH=src python -m unittest discover -s tests`.
6. Run `python -m ruff check .` only when Ruff is available; do not install it without KC's
   approval.
7. Inspect `git diff --check` and `git status --short`.
8. Do not commit unless KC asks.

Keep legacy Study 001 and Study 002 tests passing until an explicit migration removes them.

## Milestone 1 — Vocabulary and schema foundation

### Task 1.1: Add shared studio definitions

**Objective:** Define stable track, lifecycle, decision, visibility, editorial-role, and cost
vocabularies in one module.

**Files:**

- Create: `src/houdini_ai/studio_types.py`
- Create: `tests/test_studio_types.py`

**Tests:**

- accepted and rejected track names;
- lifecycle transition tables;
- decisions include keep, iterate, mutate, hold, archive, reject, promote;
- private visibility dominates public-candidate tags;
- cost tiers have a strict ordering.

**Acceptance:** Other studio modules import constants and validators rather than duplicating
string sets.

### Task 1.2: Add JSON Schemas

**Objective:** Validate the core records independently of the legacy study schema.

**Files:**

- Create: `schemas/studio/common.schema.json`
- Create: `schemas/studio/idea.schema.json`
- Create: `schemas/studio/proposal.schema.json`
- Create: `schemas/studio/experiment.schema.json`
- Create: `schemas/studio/component.schema.json`
- Create: `schemas/studio/specimen.schema.json`
- Create: `schemas/studio/editorial.schema.json`
- Create: `src/houdini_ai/studio_schema.py`
- Create: `tests/test_studio_schema.py`

**Tests:**

- one minimal valid fixture per record type;
- invalid IDs, unknown tracks, missing lineage, unknown visibility, and malformed tags fail;
- proposal runner is an identifier, never a command string;
- public candidates require explicit artifact references but remain unapproved by default;
- schemas reject unknown properties unless deliberately declared extension data.

**Acceptance:** `validate_record(kind, value)` returns path-specific errors and never mutates
the input.

## Milestone 2 — Atomic store and lineage

### Task 2.1: Implement a contained atomic record store

**Objective:** Safely create, list, read, and update local studio records.

**Files:**

- Create: `src/houdini_ai/studio_store.py`
- Create: `tests/test_studio_store.py`

**Tests:**

- create/read/list round trip;
- duplicate IDs fail unless update is explicit;
- traversal and malformed IDs fail;
- temporary files are atomically replaced;
- interrupted or malformed records are reported without corrupting valid siblings;
- concurrent local writes are serialized;
- store roots cannot escape `work/studio/` or the explicitly supplied test root.

**Acceptance:** Quick capture can write ignored local state without touching versioned files.

### Task 2.2: Implement lineage and immutable promotions

**Objective:** Connect records and prevent promoted payloads from being silently rewritten.

**Files:**

- Create: `src/houdini_ai/lineage.py`
- Create: `tests/test_lineage.py`

**Tests:**

- allowed edges validate source and target types;
- missing referenced records fail;
- supersession creates a new component version;
- component content hashes are stable;
- cycles are rejected where lifecycle meaning requires a DAG;
- KC rationale and source artifact are required for promotion.

**Acceptance:** A promoted component can be traced to experiment, job, artifact, source state,
and rationale.

## Milestone 3 — CLI interaction kernel

### Task 3.1: Add idea capture and listing

**Objective:** Provide a scriptable path for Hermes to translate `Seed: ...` into local state.

**Files:**

- Create: `src/houdini_ai/studio_cli.py`
- Modify: `src/houdini_ai/cli.py`
- Create: `tests/test_studio_cli.py`

**Commands:**

```text
houdini-ai studio seed "raw idea" [--track behavior] [--source URL]
houdini-ai studio ideas [--state inbox]
houdini-ai studio show <record-id>
```

**Tests:**

- seed preserves raw text exactly;
- optional source and track validate;
- default visibility is private;
- command output includes stable ID and record path;
- no Houdini process is launched.

**Acceptance:** Hermes can capture an idea with one local command and read it back.

### Task 3.2: Add bounded proposals

**Objective:** Convert an idea into a non-executable experiment proposal.

**Files:**

- Modify: `src/houdini_ai/studio_cli.py`
- Create: `src/houdini_ai/proposals.py`
- Modify: `tests/test_studio_cli.py`
- Create: `tests/test_proposals.py`

**Commands:**

```text
houdini-ai studio propose <idea-id> <proposal-json>
houdini-ai studio proposals [--state proposed]
houdini-ai studio approve <proposal-id>
```

**Tests:**

- proposal requires question, mechanism, outputs, stop conditions, runner, and cost tier;
- unregistered runners fail;
- approval state does not execute the runner;
- study/specimen/external cost tiers retain confirmation requirements;
- raw idea and notes never become shell arguments.

**Acceptance:** A proposal can be reviewed and approved without compute.

### Task 3.3: Add decisions, promotions, and editorial tags

**Objective:** Support the complete non-rendering lifecycle from review to candidate package.

**Files:**

- Modify: `src/houdini_ai/studio_cli.py`
- Create: `src/houdini_ai/promotions.py`
- Create: `src/houdini_ai/editorial.py`
- Create: `tests/test_promotions.py`
- Create: `tests/test_editorial.py`

**Commands:**

```text
houdini-ai studio decide <artifact-id> <decision> --note "..."
houdini-ai studio promote <artifact-id> --kind behavior --rationale "..."
houdini-ai studio tag <artifact-id> publish:x role:field-observation
houdini-ai studio untag <artifact-id> <tag>
houdini-ai studio editorial
```

**Tests:**

- promotions require valid, checksum-verified source artifacts;
- private visibility blocks projection even with publish tags;
- tags are deduplicated and vocabulary-checked;
- `readiness:approved` requires a separate approval operation;
- tag and promote operations perform no network access;
- rejection and archive retain lineage and artifacts.

**Acceptance:** KC can promote one aspect of an artifact, tag another for publication, and
keep both private.

## Milestone 4 — Local Studio API and interface

### Task 4.1: Refactor backend stores without breaking review

**Objective:** Extend the existing Review Studio into a Studio API while preserving media
security and review compatibility.

**Files:**

- Modify: `src/houdini_ai/review_studio.py`
- Optionally create: `src/houdini_ai/studio_api.py`
- Modify: `tests/test_review_studio.py`
- Create: `tests/test_studio_api.py`

**Endpoints:**

```text
GET/POST /api/studio/ideas
GET/POST /api/studio/proposals
PATCH    /api/studio/proposals/<id>
GET/POST /api/studio/promotions
GET      /api/studio/components
GET/PATCH /api/studio/editorial/<id>
GET      /api/studio/summary
```

**Tests:**

- API round trips for every record;
- payload size, IDs, paths, and lifecycle transitions validate;
- media byte ranges and traversal tests still pass;
- POSTing notes or ideas cannot invoke runners;
- all writes remain local and atomic.

**Acceptance:** Existing `/api/jobs`, `/api/reviews`, and `/media` behaviour remains intact.

### Task 4.2: Add Studio navigation and Inbox/Proposal views

**Objective:** Make idea capture and proposal review usable without CLI syntax.

**Files:**

- Modify: `website/index.html`
- Modify: `website/styles.css`
- Modify: `website/app.js`
- Add or modify browser-independent API tests in `tests/test_studio_api.py`

**Views:** Inbox, Proposals, Runs, Reviews, Components, Specimens, Editorial.

**Acceptance:** KC can capture an idea, inspect a proposal and its cost, and approve or hold
it from the browser. Free text remains data.

### Task 4.3: Extend artifact decisions and promotion UI

**Objective:** Turn artifact review into explicit branch and component decisions.

**Files:**

- Modify: `src/houdini_ai/review_studio.py`
- Modify: `website/index.html`
- Modify: `website/styles.css`
- Modify: `website/app.js`
- Modify: `tests/test_review_studio.py`

**Tests:**

- new decision vocabulary;
- promotion of behavior/look/palette/shot independently;
- rationale and exact source required;
- publication tags shown separately from promotion;
- private visibility clearly displayed and cannot be bypassed by a tag.

**Acceptance:** A Mass Flow artifact can be marked `archive` while its pipeline technique or
camera setup is promoted independently.

## Milestone 5 — Generic jobs and runner registry

### Task 5.1: Generalize job identity and stage graphs

**Objective:** Allow track-specific cheap workflows without forcing all legacy stages.

**Files:**

- Modify: `src/houdini_ai/jobs.py`
- Create: `src/houdini_ai/stages.py`
- Modify: `tests/test_jobs.py`

**Tests:**

- legacy stage graph remains unchanged for old studies;
- behavior probe graph may be validate/build/simulate/instrument/package;
- look and camera graphs define their own bounded stages;
- job IDs include record kind, ID, seed/version, source state, and input digest;
- stale and resume logic works per graph.

**Acceptance:** A Behavior Lab probe does not create empty render/composite/social stages.

### Task 5.2: Add a typed runner registry and cost gate

**Objective:** Dispatch known implementations safely and disclose expected cost.

**Files:**

- Create: `src/houdini_ai/runners.py`
- Create: `src/houdini_ai/costs.py`
- Create: `tests/test_runners.py`
- Create: `tests/test_costs.py`

**Tests:**

- only registered runner IDs dispatch;
- typed parameters validate before process launch;
- study/specimen/external tiers require an approval receipt;
- command arrays originate in runner code, not stored prose;
- estimates and actual time/storage can coexist in receipts.

**Acceptance:** An approved tiny/probe runner can execute locally; costly runners fail closed
without the correct approval record.

## Milestone 6 — Scar Tissue Behavior Lab vertical slice

### Task 6.1: Define the experiment and instrument contract

**Objective:** Record the first post-reset behavior study without choosing its final look.

**Files:**

- Create: `studio/ideas/scar-tissue.json`
- Create: `studio/experiments/behavior/scar-tissue/base.json`
- Create: `studio/sources/` record only if external sources are actually used
- Create: `studies/behavior/scar-tissue/README.md`
- Create: `studies/behavior/scar-tissue/lab-log.md`
- Add schema fixtures/tests as required.

**Mechanism:** Agents deposit an oriented path field. Low concentration attracts or aligns
subsequent motion; saturation becomes inhibitory; the field decays and permits regrowth.

**Acceptance:** The manifest states what is measured, the cheapest useful probe, and stop
conditions without prescribing a specimen material or cinematic camera.

### Task 6.2: Implement deterministic simulation in VEX

**Objective:** Produce reproducible reinforcement, saturation, avoidance, decay, and return.

**Files:**

- Create: `houdini/vex/scar_tissue_agents.vfl`
- Create: `houdini/vex/scar_tissue_field.vfl`
- Modify or reuse: `houdini/vex/lib/agent_core.vfl`
- Create: `houdini/simulate_scar_tissue.py`
- Create: `src/houdini_ai/behavior_lab.py`
- Create: `tests/test_behavior_lab.py`

**TDD boundary:** Unit-test record preparation, metrics validation, determinism comparison,
and artifact contracts without Houdini. Verify VEX through an explicit Hython smoke test.

**Acceptance:** Same-seed metrics are materially stable, changed seed is distinct, bounds are
respected, and every claimed phase is measurable.

### Task 6.3: Build cheap instrument outputs

**Objective:** Make behavioural consequences legible without specimen rendering.

**Files:**

- Create: `houdini/render_behavior_probe.py`
- Modify: `src/houdini_ai/behavior_lab.py`
- Modify: `tests/test_behavior_lab.py`

**Outputs:**

- sharp ten-second diagnostic loop;
- agent-state view;
- field concentration and orientation view;
- attraction-to-inhibition transition view;
- metrics and selected event times;
- reopenable HIP/HIPLC;
- checksummed behavior package.

**Acceptance:** Diagnostic production meets the Phase 2 budget or records why it missed. A
reviewer can tell where reinforcement, saturation, abandonment, and regrowth occur.

### Task 6.4: Generate three conceptual mutations

**Objective:** Test breadth before parameter polish.

**Candidate mutations:**

1. saturation switches attraction to repulsion;
2. scar direction permits alignment along the scar; crossing resistance remains a
   separately measured hypothesis;
3. scars heal only after local inactivity, creating refractory territory.

**Files:**

- Create: `studio/experiments/behavior/scar-tissue/mutation-*.json`
- Modify: `studies/behavior/scar-tissue/lab-log.md`
- Add focused validation fixtures.

**Acceptance:** One comparison view presents the same seed and instrument grammar across all
mutations. No look-development work is required to decide among them.

## Milestone 7 — Editorial projection foundation

### Task 7.1: Build a fail-closed public projection

**Objective:** Produce clean local Field Station input from approved records only.

**Files:**

- Create: `src/houdini_ai/projection.py`
- Create: `tests/test_projection.py`

**Tests:**

- private artifacts never project;
- unknown visibility/license/readiness fails;
- approved public fields, checksums, citations, and downloadable assets project;
- local absolute paths, private notes, environment data, and credentials are rejected;
- projection is deterministic.

**Acceptance:** The projection can be inspected locally and contains no network integration.

### Task 7.2: Generate a first local field-note page

**Objective:** Prove that a promoted behavior can become a durable public-facing record
before building the full Field Station.

**Files:**

- Create: `src/houdini_ai/field_station.py`
- Create: `field-station/` minimal static template and assets
- Create: `tests/test_field_station.py`

**Acceptance:** A local static page shows the approved scar-tissue question, mechanism,
instrument media, selected observations, source/HIP download status, and lineage. It clearly
labels measured, derived, observed, and hypothesized claims.

## Completion gate

The studio foundation is complete when KC can:

1. seed an idea conversationally;
2. review a bounded proposal and its cost;
3. run a cheap Behavior Lab probe;
4. compare conceptual mutations and leave timecoded feedback;
5. promote a behavior with rationale;
6. tag selected artifacts as private publication candidates;
7. generate and inspect a local field-note projection;
8. do all of this without editing JSON or starting an external publication action.

Only then begin the independent Look Development, Chromatic, and Cinematography vertical
slices described in `docs/STUDIO_ROADMAP.md`.
