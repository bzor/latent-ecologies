# Computational Studio Golden Path Implementation Plan

> **For Hermes:** Implement this plan task-by-task with strict RED → GREEN verification. Do not commit, publish, upload, or delete historical artifacts unless KC explicitly asks.

**Goal:** Turn the existing studio kernel and Scar Tissue proving run into a complete, pleasant start-to-finish creative laboratory, validated continuously by one deliberately small new project.

**Architecture:** Keep the dependency-light, file-backed Studio kernel and local-only Review Studio. Backfill Scar Tissue as the golden completed lineage while a small Pilot Study 003 exercises the workflow forward from seed through private Field Station package. Build thin vertical capabilities in lifecycle order rather than completing six isolated labs.

**Tech Stack:** Python 3.11, `unittest`, JSON Schema, dependency-free HTML/CSS/JavaScript, local `ThreadingHTTPServer`, Houdini 22/Hython, VEX, MaterialX, Karma XPU, FFmpeg.

---

## Product decision: use a new project during implementation

Do not wait for an abstract definition of “platform complete” before beginning another study.

Use two complementary acceptance fixtures:

1. **Scar Tissue: backward golden path**
   - Already contains real behaviour, look, chromatic, cinematography, handoff, render, crash recovery, and process evidence.
   - Reveals whether the platform can faithfully represent completed work without inventing or losing lineage.

2. **Pilot Study 003: forward live path**
   - Begins only after the front door and Behavior Direction Board exist.
   - Must be deliberately small: one core mechanism, two or three competing directions, cheap diagnostics, one restrained look/palette, a minimal shot set, and a short final specimen.
   - Reveals collaboration friction at the moment it occurs.

Scar Tissue prevents us from designing a toy system. Pilot Study 003 prevents us from merely documenting the old workflow.

## Definition of platform completion for this roadmap

This roadmap is complete when KC and Hermes can use the local Studio to take Pilot Study 003 through:

```text
seed
→ competing behavior directions
→ approved probe contracts
→ diagnostic runs and unified review
→ behavior promotion
→ broad look branches and one-frame refinements
→ chromatic inventory and palette promotion
→ motion-aware cinematography and shot promotion
→ specimen assembly and cost approval
→ resumable render, validation, and encode
→ private Field Station package
```

Completion also requires:

- Scar Tissue represented as the first complete structured specimen lineage.
- One Review Inbox across tracks and stages.
- Process notes visible and capturable in context.
- No directory hunting required for ordinary artifact review.
- Every expensive action explicitly budgeted and approved.
- Nothing published or made public.
- Fast non-Houdini regression tests passing.
- A retrospective that converts Pilot Study 003 friction into a bounded refinement backlog rather than expanding scope indefinitely.

---

## Milestone 0: Baseline, vocabulary, and preservation

**Objective:** Establish an honest baseline before changing lifecycle or interface behavior.

**Files:**
- Review: `docs/STUDIO_VISION.md`
- Review: `docs/STUDIO_PROTOCOL.md`
- Review: `docs/STUDIO_ARCHITECTURE.md`
- Modify: `docs/STUDIO_ROADMAP.md`
- Review: `work/studio/PROCESS_NOTES.md`
- Test: existing `tests/test_studio_*.py`, `tests/test_review_studio.py`, `tests/test_projection.py`

**Steps:**

1. Run the complete Houdini-free test suite and record the real baseline.
2. Inventory implemented, partially implemented, and documentation-only capabilities.
3. Add this golden-path release sequence and completion definition to `docs/STUDIO_ROADMAP.md` without erasing the longer-term roadmap.
4. Preserve all legacy studies, jobs, handoffs, renders, notes, and crash evidence.
5. Verify the working tree before each milestone so unrelated existing work is not overwritten.

**Verification:**

```powershell
cd E:\Projects\houdini-ai
python -m unittest discover -s tests
```

**Exit gate:** We can state exactly which capabilities exist and which are missing, with no generated artifact deleted or moved.

---

## Milestone 1: Register Scar Tissue as the golden specimen lineage

**Objective:** Represent the real proving run with exact records rather than a narrative-only retrospective.

**Likely files:**
- Modify: `schemas/studio/artifact.schema.json`
- Modify: `schemas/studio/component.schema.json`
- Modify: `schemas/studio/specimen.schema.json`
- Modify: `src/houdini_ai/studio_schema.py`
- Modify: `src/houdini_ai/studio_store.py`
- Modify: `src/houdini_ai/lineage.py`
- Modify: `src/houdini_ai/promotions.py`
- Modify: `src/houdini_ai/studio_api.py`
- Create: `studio/specimens/scar-tissue-abc-a-v1.json`
- Create or normalize: exact Scar Tissue behavior/look/palette/shot component records under `studio/components/`
- Test: `tests/test_studio_schema.py`
- Test: `tests/test_lineage.py`
- Test: `tests/test_promotions.py`
- Test: `tests/test_studio_api.py`

**TDD sequence:**

1. Write a failing fixture test describing the minimum valid complete Scar Tissue lineage.
2. Run the focused test and confirm it fails for the missing representation, not an unrelated reason.
3. Implement only the schema/store/lineage support required by the fixture.
4. Register exact source paths, validated artifacts, component versions, creative rationales, dependencies, render state, and sound decision.
5. Distinguish completed frames from the still-pending final sequence; do not mark the specimen deliverable complete prematurely.
6. Run focused tests, then the Houdini-free suite.

**Exit gate:** The Studio can answer “what exact parts constitute Scar Tissue, where did each come from, what remains incomplete, and why were they selected?” without scraping chat or directories.

---

## Milestone 2: Unified artifact catalog

**Objective:** End ordinary directory hunting by indexing validated artifacts from legacy jobs, Studio handoffs, track probes, and specimens into one safe catalog.

**Likely files:**
- Create: `src/houdini_ai/artifact_catalog.py`
- Modify: `src/houdini_ai/review_studio.py`
- Modify: `src/houdini_ai/studio_api.py`
- Modify: `src/houdini_ai/studio_store.py`
- Test: `tests/test_artifact_catalog.py`
- Test: `tests/test_review_studio.py`
- Test: `tests/test_studio_api.py`

**TDD sequence:**

1. Add failing tests for discovery from:
   - `work/jobs/` legacy jobs;
   - `work/studio/handoffs/`;
   - registered Studio artifact records;
   - specimen output directories.
2. Require stable artifact IDs, source lineage, validation state, media metadata, stage, track, and safe media URL.
3. Deduplicate the same physical artifact when referenced through several records.
4. Exclude temporary render files, frame-directory floods, invalid media, secrets, and paths outside approved roots.
5. Replace direct legacy-job assumptions in Review Studio with the catalog while preserving old jobs.
6. Verify byte ranges and path containment remain intact.

**Exit gate:** Scar Tissue’s relevant behavior, look, camera, handoff, render, and review media are visible through one catalog with no manual path entry.

---

## Milestone 3: Active creative session and unified Review Inbox

**Status: Complete.** Verified against the real Scar Tissue session in the local browser cockpit.

**Objective:** Give KC one coherent operational surface showing the current project, current phase, selected branch, unresolved decisions, process notes, and next action.

**Likely files:**
- Create: `schemas/studio/session.schema.json`
- Create: `src/houdini_ai/studio_sessions.py`
- Modify: `src/houdini_ai/studio_api.py`
- Modify: `src/houdini_ai/review_studio.py`
- Modify: `src/houdini_ai/studio_cli.py`
- Modify: `website/index.html`
- Modify: `website/app.js`
- Modify: `website/styles.css`
- Test: `tests/test_studio_sessions.py`
- Test: `tests/test_review_studio.py`
- Test: `tests/test_studio_cli.py`

**Required behavior:**

- Exactly one explicitly selected active session, with other sessions safely resumable.
- Phase map: Seed, Directions, Behavior, Look, Chromatic, Cinematography, Specimen, Delivery.
- Current intent, approved selections, unresolved questions, blockers, and recommended next action.
- One Review Inbox aggregating open artifact notes, decisions, proposals, and process questions across all stages.
- Contextual process-note capture with category, stage, track, and selected artifact/component reference.
- No free text executes commands or queues Houdini work.

**TDD sequence:**

1. Add failing session lifecycle and path-containment tests.
2. Add failing API round-trip tests.
3. Implement the minimum store/API behavior.
4. Add UI rendering tests or deterministic DOM/content assertions where practical.
5. Build the cockpit UI without introducing a frontend framework.
6. Use Scar Tissue as the first displayed golden session while preserving its truthful incomplete delivery state.

**Exit gate:** On opening the Studio, KC can immediately tell what project is active, where it is in the process, what needs review, and what action is recommended next.

---

## Milestone 4: Behavior Direction Board

**Status: Complete.** Verified with a fresh temporary seed, three distinct direction theses,
multiple simultaneous selections, preserved rejected/held branches, mutation and merge lineage,
and separately proposed probe contracts. No Pilot Study 003 mechanism was preselected.

**Objective:** Insert the missing conceptual brainstorming stage between an accepted seed and simulation implementation.

**Likely files:**
- Create: `schemas/studio/direction.schema.json`
- Create: `src/houdini_ai/directions.py`
- Modify: `src/houdini_ai/studio_types.py`
- Modify: `src/houdini_ai/studio_api.py`
- Modify: `src/houdini_ai/studio_cli.py`
- Modify: `website/index.html`
- Modify: `website/app.js`
- Modify: `website/styles.css`
- Test: `tests/test_directions.py`
- Test: `tests/test_studio_api.py`
- Test: `tests/test_studio_cli.py`

**Required behavior:**

- A direction describes a distinct mechanism or simulation thesis, not merely parameter values.
- Each card records premise, mechanism, expected emergent behavior, cheapest informative probe, risks, and relation to sibling directions.
- Decisions: select, hold, mutate, merge conceptually, archive, or reject.
- Multiple directions may be selected for competing Behavior Lab probes.
- Held/rejected directions remain available for later reconsideration after look development.
- Proposal contracts derive from selected directions but remain separately approved records.

**Exit gate:** A fresh idea can produce two or three meaningfully different behavior directions, and KC can select more than one without starting Houdini.

---

## Milestone 5: Begin Pilot Study 003

**Status: In progress.** The accepted Nonlocal Affinity Dance seed, three Direction cards, approved bounded proposal,
deterministic Python reference, live VEX parity tracer, and verified faithful motion-check artifact now exist. Behavior
promotion and independent departure experiments await KC's review of the baseline motion.

**Objective:** Exercise the new front door before deepening downstream labs.

**Scope gate:** KC chooses the seed after reviewing several compact candidates. Do not preselect a mechanism in code or documentation.

**Constraints for the pilot:**

- One core question.
- Two or three conceptual behavior directions.
- Tiny/probe compute only until one behavior is promoted.
- Diagnostic motion before presentation rendering.
- Short final specimen, intentionally smaller than Scar Tissue.
- No requirement for publication.

**Likely records:**
- Create through Studio operations: one idea, direction cards, bounded proposals, experiments, jobs, artifacts, review decisions, and one promoted behavior.
- Version selected creative intent under `studio/`; keep generated work under `work/`.

**Exit gate:** The pilot reaches a promoted behavior using only the new workflow, and all friction is captured as contextual process notes.

---

## Milestone 6: Behavior Lab completion

**Objective:** Make behavior exploration fast, legible, reproducible, and independent of look polish.

**Likely files:**
- Modify: `src/houdini_ai/behavior_lab.py`
- Modify: `src/houdini_ai/behavior_package.py`
- Modify: `src/houdini_ai/runners.py`
- Modify: `src/houdini_ai/stages.py`
- Modify: `src/houdini_ai/studio_api.py`
- Modify: Review Studio UI files
- Test: `tests/test_behavior_lab.py`
- Test: `tests/test_behavior_package.py`
- Test: `tests/test_runners.py`
- Hython smoke tests only where needed

**Required behavior:**

- Sharp instrument views and concise mechanism summaries.
- Fast motion-test action available from relevant updates.
- Side-by-side sibling-direction comparison.
- Same-seed reproducibility and changed-seed distinction.
- Promotion without look, palette, or camera dependencies.

**Exit gate:** Pilot Study 003 has one promoted behavior and at least one preserved competing branch.

---

## Milestone 7: Look Development and Chromatic workspace

**Objective:** Support both large representational exploration and precise one-frame refinement without losing behavioral identity.

**Likely files:**
- Modify: `src/houdini_ai/lookdev_lab.py`
- Create or extend: palette/chromatic module under `src/houdini_ai/`
- Modify: component schemas and compatibility metadata
- Modify: Review Studio UI files
- Test: `tests/test_lookdev_lab.py`
- Add focused palette tests
- Add small Hython/MaterialX smoke probes

**Required behavior:**

- Before Chromatic work, generate an inventory of geometry classes, semantic states, scalar attributes, temporal values, and available mappings.
- Separate **broad look branches** from **single-frame refinements** in records and UI.
- Preserve sibling branches when a look is promoted.
- Palette roles use semantic scalar mappings and editable shader palettes, not baked geometry colors.
- Controlled contact sheets and one-frame probes are first-class review artifacts.

**Exit gate:** Pilot Study 003 has a promoted look and palette, each independently traceable to the behavior and review rationale.

---

## Milestone 8: Cinematography workspace

**Objective:** Make the camera an interpretive layer with rapid motion evidence and artist-friendly final controls.

**Likely files:**
- Create or extend cinematography modules under `src/houdini_ai/`
- Modify shot schema/component compatibility
- Modify Houdini scene builders for the pilot
- Modify Review Studio UI files
- Add focused unit and Hython smoke tests

**Required behavior:**

- Generate conceptually distinct shot families.
- Use quick flat/wireframe/proxy motion checks before final rendering.
- Separate artist framing controls from approved camera motion.
- Expose clearly named Stage-context parent/offset controls while looking through the final Solaris camera.
- Preserve shot siblings and support a compact coverage set.

**Exit gate:** Pilot Study 003 has a promoted shot or short edit with verified motion continuity and editable Stage controls.

---

## Milestone 9: Specimen assembly, rendering, and delivery

**Objective:** Complete Pilot Study 003 through the same reproducible path proven manually by Scar Tissue.

**Likely files:**
- Modify: specimen schemas and assembly logic
- Modify: `src/houdini_ai/costs.py`
- Modify: `src/houdini_ai/editorial.py`
- Modify: `src/houdini_ai/projection.py`
- Modify or create pilot render/resume scripts under `scripts/`
- Test: `tests/test_costs.py`
- Test: `tests/test_editorial.py`
- Test: `tests/test_projection.py`
- Add artifact validation and resume acceptance checks

**Required behavior:**

- Exact component references and compatibility report.
- Creative reason for the combination.
- Explicit sound, Ableton handoff, or silence decision.
- Cost/storage/time plan before substantial compute.
- Resumable rendering with independent artifact validation.
- Final frame census, visual QC, encode, and local delivery package.

**Exit gate:** The pilot has a validated final specimen package, and an interrupted test render can resume without rerunning valid output.

---

## Milestone 10: Private Field Station projection

**Objective:** Prove that completed structured work can become a durable local field note without leaking private state.

**Likely files:**
- Modify: `src/houdini_ai/field_station.py`
- Modify: `src/houdini_ai/projection.py`
- Create or extend local static templates/assets
- Test: `tests/test_field_station.py`
- Test: `tests/test_projection.py`

**Required behavior:**

- Local-only pages for Scar Tissue and Pilot Study 003.
- Clear separation of measured, derived, observed, and hypothesized claims.
- Selected lineage, media, sources, credits, accessibility text, and download eligibility.
- Fail-closed exclusion of private notes, local absolute paths, credentials, unapproved artifacts, and unknown licenses.
- No deployment or social posting.

**Exit gate:** Both studies build locally from approved records, pass leakage/media/link checks, and require a separate explicit publication decision.

---

## Milestone 11: Completion audit and bounded refinement pass

**Objective:** Finish the roadmap rather than allowing perpetual platform expansion.

**Steps:**

1. Run the full Houdini-free suite.
2. Run documented Hython smoke tests.
3. Walk Pilot Study 003 from seed to private field note using the Studio interface.
4. Confirm Scar Tissue remains faithfully represented.
5. Review all process notes captured during the pilot.
6. Classify findings as:
   - release blocker;
   - next-project refinement;
   - longer-term idea;
   - intentionally rejected complexity.
7. Fix release blockers only.
8. Write a concise completion report and operator workflow.
9. Do not publish or commit unless KC separately requests it.

**Final acceptance:**

- A second small project completed through the platform.
- No ordinary directory hunting.
- One Review Inbox and visible process notes.
- Creative branching remains distinct from parameter iteration.
- Cheap motion and one-frame loops are available where needed.
- Expensive work remains gated and resumable.
- Private/public separation passes tests.
- Remaining ideas are explicitly deferred rather than silently treated as incomplete work.

---

## Working rhythm

For each milestone:

1. Restate the user-facing improvement in one sentence.
2. Write the focused failing test.
3. Confirm RED.
4. Implement the smallest coherent vertical behavior.
5. Confirm GREEN.
6. Exercise it with Scar Tissue or Pilot Study 003.
7. Capture fresh process feedback.
8. Update the roadmap status and move on only when the exit gate passes.

Avoid broad refactors, speculative abstractions, framework adoption, or publication integrations during this release. The measure of success is a smoother creative relationship and a second finished work, not the number of platform features.