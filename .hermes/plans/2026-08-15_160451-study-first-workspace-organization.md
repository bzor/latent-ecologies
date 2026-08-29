# Study-First Workspace Organization Implementation Plan

> **For Hermes:** Implement this plan task-by-task with RED → GREEN tests. Migration must be non-destructive and must not publish, commit, or delete historical material without KC's approval.

**Goal:** Make every creative project understandable by opening one `study-NNN-name/` directory containing its complete phase history, runs, review media, receipts, and deliverables.

**Architecture:** Replace the human-facing phase-first/global-pool layout with a canonical study-first tree under `work/studies/`. Preserve the useful global Review Studio as a derived index that scans study roots; do not maintain a second writable copy of canonical creative records. Introduce compatibility reads before migrating existing paths, then migrate one study at a time with an old→new path manifest and checksum verification.

**Tech Stack:** Python 3.11/3.12, pathlib, JSON Schema, unittest, local Review Studio HTTP/catalog layer, Houdini job builders.

---

## Organizing principles

1. **A study is the primary container.** Everything needed to understand, resume, review, or deliver a study lives beneath one stable study directory.
2. **The filesystem should tell the creative story.** Phases appear in workflow order rather than being spread across type-indexed global collections.
3. **IDs are stable; names are descriptive.** Use a fixed numeric ID plus a lowercase kebab-case slug: `study-003-nonlocal-affinity-dance`.
4. **Phase numbers are ordering aids, not identity.** Use increments of ten so a future phase can be inserted without renaming every later directory.
5. **Branches are concepts; runs are executions.** A behavior/look/shot idea gets a stable branch directory. Each execution gets a numbered run beneath it.
6. **Versions belong to artifacts and records, not every directory.** Use `v001`, `v002`, etc. for immutable outputs. Do not produce vague names such as `final`, `new`, `latest`, or `test2`.
7. **Review is a facet, not a creative phase.** Each run owns its `review/` media. The browser aggregates those review folders across all studies.
8. **Caches are not review artifacts.** Keep heavy reproducible intermediates in `cache/`; keep only human-facing images, videos, and comparison sheets in `review/`.
9. **One canonical writable home.** Global catalogs, inboxes, and dashboards are projections/indexes. They must not become alternate writable copies of study content.
10. **Migration is receipt-backed and non-destructive.** Record old→new paths and hashes before switching readers. Do not delete legacy material during the initial migration.

## Canonical tree

```text
work/
  studies/
    study-003-nonlocal-affinity-dance/
      README.md
      study.json
      00-seed/
        seed.json
        sources/
      10-directions/
        direction-001-faithful-baseline/
          direction.json
        direction-002-graph-choreography/
          direction.json
        direction-003-encounter-memory/
          direction.json
      20-behavior/
        behavior-001-faithful-baseline/
          branch.json
          runs/
            run-001-probe/
              run.json
              source/
              cache/
              review/
                motion-check-v001.mp4
                contact-sheet-v001.png
              receipts/
      30-look/
        look-001-<slug>/
          branch.json
          runs/
      40-chromatic/
        palette-001-<slug>/
          branch.json
          runs/
      50-cinematography/
        shot-001-<slug>/
          branch.json
          runs/
      60-specimen/
        specimen-001-<slug>/
          specimen.json
          assemblies/
          review/
      70-delivery/
        delivery-001-<slug>/
          delivery.json
          masters/
          derivatives/
          receipts/
      80-field-station/          # create only when used
      90-publication/            # create only when explicitly authorized
      _study/
        notes/
        migration/
        lineage.json
```

Only create phase directories when the study enters that phase, except `00-seed` and `_study`, which exist from bootstrap.

## Naming contract

### Directories

- Study: `study-NNN-<slug>`
- Direction: `direction-NNN-<slug>`
- Behavior branch: `behavior-NNN-<slug>`
- Look branch: `look-NNN-<slug>`
- Chromatic branch: `palette-NNN-<slug>`
- Cinematography branch: `shot-NNN-<slug>`
- Specimen: `specimen-NNN-<slug>`
- Delivery: `delivery-NNN-<slug>`
- Execution: `run-NNN-<tier>` where tier is one of `smoke`, `probe`, `review`, or `final`

All slugs are lowercase ASCII kebab-case. Numeric IDs are zero-padded to three digits. Renaming a descriptive slug must not change the numeric identity stored in manifests.

### Standard files inside a branch/run

- `study.json`: canonical study identity and active phase
- `seed.json`, `direction.json`, `branch.json`, `specimen.json`, `delivery.json`: canonical local record for that concept
- `run.json`: immutable execution inputs, source state, seed, runner, status, and output index
- `source/`: editable HIP, VEX, scripts, or imported reference material used by this run
- `cache/`: reproducible geometry/simulation caches
- `review/`: media intended for immediate human review
- `receipts/`: checksums, render receipts, parity metrics, migration receipts
- `notes/`: append-oriented observations tied to the containing study or branch

### Artifact filenames

Because directory context already supplies study, phase, branch, and run identity, filenames stay concise:

- Frames: `frame-0001.png`, `frame-0001.exr`, `frame-0001.bgeo.sc`
- Motion review: `motion-check-v001.mp4`
- Still review: `still-v001.png`
- Comparison: `comparison-v001.png`
- Contact sheet: `contact-sheet-v001.png`
- Editable Houdini scene: `scene-v001.hiplc`
- Master: `master-v001.mov`
- Delivery derivative: `<target>-v001.mp4`
- Receipt: `<operation>-receipt-v001.json`

Four-digit frame numbers remain sufficient for current timelines such as Scar Tissue's 1–1260 range. Increase the width per study only if `study.json` declares it before frames are produced.

## Why the current system existed

The current split is technically understandable:

- `work/studio/<record-type>/` makes schema collections and list operations simple.
- `work/jobs/<job-id>/` makes execution containment, cleanup, media serving, and recency sorting simple.
- phase-specific roots made early lab implementations independent.

The cost is high human friction: a single study is fragmented across global records, job directories, and phase folders, while phase folders contain material from many studies. The new design retains machine-friendly manifests and derived indexes but moves canonical ownership to the study.

---

### Task 1: Freeze and test the naming/path contract

**Objective:** Define one parser/path builder before moving any material.

**Files:**
- Create: `src/houdini_ai/study_paths.py`
- Create: `tests/test_study_paths.py`
- Create: `schemas/studio/study.schema.json`
- Modify: `src/houdini_ai/studio_schema.py`

**RED tests:**

- accept `study-003-nonlocal-affinity-dance`;
- reject missing padding, uppercase, whitespace, traversal, absolute paths, and ambiguous suffixes;
- build each numbered phase path;
- build branch and run paths without escaping the study root;
- enforce closed run tiers;
- preserve stable numeric identity independently from the slug.

**Verification:**

```bash
PYTHONPATH=src python -m unittest tests.test_study_paths
```

Expected: tests fail before implementation, then pass after the smallest contained path model is added.

### Task 2: Make new Studio records study-aware

**Objective:** Require every new creative record to identify its owning study and phase.

**Files:**
- Modify: `schemas/studio/common.schema.json`
- Modify: applicable schemas under `schemas/studio/`
- Modify: `src/houdini_ai/studio_api.py`
- Modify: `src/houdini_ai/studio_sessions.py`
- Test: `tests/test_studio_schema.py`
- Test: `tests/test_studio_api.py`

**Approach:**

- Add stable `study_id` and `phase` references without allowing callers to override canonical envelopes.
- Keep idea→direction→proposal→experiment→artifact lineage unchanged.
- Ensure selecting or approving records still performs no execution.
- Establish `study.json` as the source of study identity; sessions reference it rather than inventing a parallel project slug.

### Task 3: Add a study-first store with legacy compatibility reads

**Objective:** Make new canonical writes study-first while old records remain readable.

**Files:**
- Create: `src/houdini_ai/study_store.py`
- Modify: `src/houdini_ai/studio_store.py`
- Test: `tests/test_study_store.py`
- Test: `tests/test_studio_api.py`

**Approach:**

- New writes go beneath `work/studies/<study-id>/<phase>/...`.
- Reads first resolve canonical study paths, then consult the legacy type-indexed store during migration.
- Listing merges both sources by immutable record ID and reports conflicts explicitly.
- Atomic write, containment, append history, and malformed-record reporting remain unchanged.
- Do not maintain mirrored writable JSON in both locations.

### Task 4: Move generated runs beneath their owning branch

**Objective:** Replace the global job pool for new work with branch-local runs.

**Files:**
- Modify: job path creation in `src/houdini_ai/jobs.py`
- Modify: `src/houdini_ai/review_studio.py`
- Modify: `src/houdini_ai/storage.py`
- Modify: relevant Houdini builders under `houdini/`
- Test: `tests/test_jobs.py`
- Test: `tests/test_review_studio.py`
- Test: `tests/test_storage.py`

**Acceptance:**

- a run path resolves to exactly one study, phase, and branch;
- cleanup understands branch-local runs and remains receipt/protection-aware;
- media routes serve only contained review artifacts;
- Review Studio still presents recent review media without requiring filesystem knowledge;
- legacy `work/jobs` remains readable during migration.

### Task 5: Make the artifact catalog a derived cross-study index

**Objective:** Preserve the unified Review Studio without preserving global creative storage.

**Files:**
- Modify: `src/houdini_ai/artifact_catalog.py`
- Modify: `src/houdini_ai/review_studio.py`
- Modify: `website/app.js`
- Test: `tests/test_artifact_catalog.py`
- Test: `tests/test_review_studio.py`

**Acceptance:**

- catalog scans `work/studies/*/*/*/runs/*/review/` and explicit specimen/delivery review roots;
- every item exposes study, phase, branch, run, version, validation, and lineage context;
- catalog can filter by study first, then phase;
- legacy catalog roots remain visible with a `legacy` source marker until migrated;
- startup/caching protections remain intact.

### Task 6: Bootstrap Pilot Study 003 in the new shape

**Objective:** Use the smallest current study as the migration proof before touching large historical stores.

**Target:**

`work/studies/study-003-nonlocal-affinity-dance/`

**Files:**
- Modify: `src/houdini_ai/pilot_study_003.py`
- Modify: `src/houdini_ai/nonlocal_affinity_artifacts.py`
- Modify: `houdini/probe_nonlocal_affinity.py`
- Test: `tests/test_pilot_study_003.py`
- Test: `tests/test_nonlocal_affinity_houdini.py`

**Migration steps:**

1. Inventory every existing Pilot 003 record and artifact.
2. Write `_study/migration/legacy-to-study-v001.json` with old path, new path, size, and SHA-256.
3. Materialize the study-first tree without deleting legacy sources.
4. Recompute and compare every hash.
5. Update canonical records through versioned migration receipts rather than in-place historical rewrites.
6. Verify the motion-check MP4 opens through the catalog from its new contained path.
7. Keep the legacy source until KC approves later cleanup.

### Task 7: Migrate historical studies one at a time

**Objective:** Organize Memory Field, Mass Flow, and Scar Tissue without a risky bulk move.

**Candidate mapping requiring KC confirmation:**

- `study-001-memory-field`
- `study-002-mass-flow`
- `study-003-nonlocal-affinity-dance`
- assign Scar Tissue a stable study number before migration rather than guessing from its current phase-specific names

For each study, repeat inventory → manifest → copy/materialize → hash verification → reader switch → browser review. Do not delete old paths in this milestone.

### Task 8: Document the artist-facing contract

**Objective:** Make the hierarchy understandable without reading Python code.

**Files:**
- Create: `docs/STUDY_STRUCTURE.md`
- Modify: `docs/WORKFLOW.md`
- Modify: `docs/PROJECT_PLAN.md`
- Modify: `docs/REVIEW_STUDIO_PLAN.md`

**Documentation must include:**

- canonical tree example;
- naming table;
- distinction between branch, run, artifact version, and frame;
- where to find editable scenes, caches, review media, receipts, and masters;
- rule that Review Studio is a projection across study folders;
- legacy compatibility and migration policy.

## Validation

After every task:

```bash
PYTHONPATH=src python -m unittest <focused-test-module>
```

Final gate:

```bash
PYTHONPATH=src python -m unittest discover -s tests
node --check website/app.js
git diff --check
```

Also verify manually in a fresh browser:

1. select a study;
2. see its phases in order;
3. open its latest motion check;
4. trace that artifact to a branch, run manifest, source scene, and receipt;
5. navigate directly to the same material in `work/studies/<study>/` without understanding global internal collections.

## Risks and tradeoffs

- **Existing path references:** artifact records and review links currently embed `work/jobs` or `work/studio` paths. Migration needs explicit path receipts and compatibility reads.
- **Storage duplication:** non-destructive copy-first migration temporarily uses more disk. Report required/free space before each historical study migration.
- **Study numbering:** Memory Field and Mass Flow already imply 001/002; Scar Tissue needs a deliberate stable number.
- **Phase vocabulary:** the current session schema ends at delivery. Field Station and publication should remain optional, explicitly gated directories rather than automatic lifecycle phases.
- **Global operational state:** one small global pointer/index may remain necessary for active-session selection and fast lookup, but it must contain references only—not duplicate creative records or artifacts.
- **Too much nesting:** cap the meaningful hierarchy at study → phase → branch → run. Within a run, use only the fixed `source/cache/review/receipts` folders.

## Decision summary

Adopt the study-first layout. Keep global interfaces, but make them derived projections. Pilot Study 003 should be the first proof migration. Do not bulk-move or delete the existing historical tree until the new path model, compatibility reader, checksum migration receipt, and browser catalog all pass.