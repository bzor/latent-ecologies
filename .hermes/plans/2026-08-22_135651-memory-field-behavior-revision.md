# Memory Field Behavior Revision Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Reopen Study 001 as an explicit Behavior revision and turn its one-way resource-depletion field into a legible ecology with recurring route formation, abandonment, encounter, and recovery events suitable for interesting animation.

**Architecture:** Preserve the archived Probe 007 implementation and receipts unchanged. Build three small VEX-authoritative sibling mechanisms from the same deterministic initial identity, compare them through neutral diagnostic motion and transition metrics, then extend only the selected branch. Keep Python/Hython orchestration-only: VEX evolves agent and field state; Python creates initial identity, advances cached state, extracts cooked metrics, and assembles review media.

**Tech Stack:** Houdini 22 / SOP Attribute Wrangles / VEX, Hython cache loop, Python 3.11 metrics and review tooling, BGEO caches, JSON receipts, MP4 diagnostic previews.

---

## 1. Current diagnosis

### Evidence inspected

- Archived source: `studies/001-memory-field/study.json`
- Agent VEX: `houdini/vex/memory_field_agents.vfl`
- Field VEX: `houdini/vex/memory_field_fields.vfl`
- Cache driver: `houdini/simulate_memory_field.py`
- Review/validation: `src/houdini_ai/simulation.py`
- Accepted Probe 007 job: `work/jobs/001-memory-field-s18432-probe-07a4f73b738f/`
- Diagnostic contact sheet, instrument frame, metrics, and receipt from that job

### What the current system actually does

1. **The animation is mostly a one-way wash.** Resource falls from `1670.440` to `393.896`; mean inhibition rises from `0` to `0.255`. There is no resource regeneration or conversion cycle, so the strongest temporal event is gradual depletion plus stain accumulation.
2. **The population has no functioning behavioral phases.** `min_speed = 0.2`, while `dormant_speed = 0.08`; the speed clamp makes dormancy unreachable. The accepted 240-frame run records zero dormant agent-frames.
3. **Most agents accelerate into the same high-energy regime.** Mean speed reaches roughly `1.06–1.14` after frame 60 against a `1.25` maximum. Speed-linked deposition therefore tends toward a near-uniform high deposit rather than expressing distinct intent or condition.
4. **Memory has magnitude but no semantics.** A scalar inhibition field records where agents passed, but not direction, age phase, lineage, ownership, or whether a route is being reinforced, contested, abandoned, or recovered.
5. **Agent interaction is weakly differentiated.** Occupancy is instantaneous repulsion only. It can keep points apart but cannot create joining, yielding, pursuit, exchange, territorial negotiation, or collective state changes.
6. **Steering reads broad and noisy rather than eventful.** Resource and inhibition directions are normalized weighted sums over nearby field values, not explicit gradients or directional trail samples. The contact sheet shows redistribution and increasingly dense memory, but few identifiable interaction events or phase changes.
7. **The review contract measures survival, not interest.** Current checks prove finite in-bounds motion, deterministic output, resource consumption, and relic-era metrics. They do not measure encounters, route reuse, abandonment, state transitions, recovery, clustering, migration, or temporal recurrence.

### Baseline motion receipt to preserve

The accepted 256-agent run remains the frozen reference:

- 240 frames; deterministic receipt complete;
- mean trajectory travel approximately `8.680` field units;
- mean displacement/travel ratio approximately `0.452`;
- mean nearest-neighbor distance grows from approximately `0.363` to `0.389`;
- `1072` accumulated boundary-contact agent-frames;
- no dormant transitions;
- no artifact mechanics enabled.

This baseline must remain reproducible after the revision work. Do not rewrite its VFL files, manifest, job, or lab-log acceptance entry in place.

---

## 2. Behavior Direction Workshop outcome

These are causally different sibling mechanisms, not parameter presets. Build them sequentially and retain all three records.

### Direction A — Refractory Route Ecology **(recommended first)**

**Entities:** mobile agents; resource field; fresh trail; refractory scar; recovering substrate.

**Persistent state:** agent mode (`forage`, `follow`, `deflect`, `rest`), energy, stable seed-derived sensitivity profile; field resource, fresh-trail strength, stored trail direction, scar strength, and age.

**Interactions and feedback:**

1. Hungry agents seek resource and weakly align with fresh directional trails.
2. Traversal deposits a directed fresh trail.
3. Repeated use converts fresh trail into a refractory scar.
4. Scar deflects later traffic, splitting and abandoning established routes.
5. Unvisited scars heal and locally regenerate resource.
6. Rested agents can re-enter healed territory, producing route return rather than permanent avoidance.

**Expected animation:** paths appear, recruit traffic, overload, split, fade, and get recolonized. The field should breathe through recurrent waves rather than only darken.

**Cheapest diagnostic:** 96 agents, `48 x 80` field, 180 frames, neutral top-down review with fresh trail, scar, and agent mode shown separately.

**Why first:** It preserves the original environmental-memory premise while adding temporal causality and interactions without importing the removed artifact or requiring multiple species.

### Direction B — Lineage Border Negotiation

**Entities:** two or three inherited lineages sharing resource.

**Persistent state:** lineage ID; energy; own-lineage directional trace; foreign-lineage pressure; contested-cell age.

**Interactions and feedback:** Agents follow weak kin routes, avoid dense foreign trace, and yield or cross depending on energy. Encounters deposit short-lived contested boundaries; resource exhaustion weakens ownership and allows invasion.

**Expected animation:** fronts form, bend, perforate, exchange territory, collapse, and reform. Encounters become spatially legible rather than generic repulsion.

**Cheapest diagnostic:** 96 agents split evenly between two lineages, identical resource identity, 180 frames, plus a border-age and crossing-event view.

**Risk:** It can become a familiar red-vs-blue territory simulation. Reject if lineage identity is readable only through colour or if borders freeze.

### Direction C — Successional Bloom and Migration

**Entities:** agents with hungry/sated/resting phases; resource patches with depletion and recovery clocks.

**Persistent state:** agent energy and mode; patch resource, exhaustion age, recovery potential, and local occupancy stress.

**Interactions and feedback:** Feeding creates local crowding and patch collapse; sated agents slow and disperse; exhausted patches enter dormancy; recovery occurs preferentially in long-unvisited regions. Population motion follows a moving landscape created by its own history.

**Expected animation:** convergence, crowding, bloom collapse, outward migration, quiet recovery, and renewed colonization.

**Cheapest diagnostic:** 128 agents, `48 x 80` field, 240 frames, with event labels for patch activation, collapse, and recolonization.

**Risk:** Without directional memory it may read as ordinary attraction to blinking blobs. Promote only if migration geometry is shaped by historical use rather than scripted patch timing.

---

## 3. Recommended implementation sequence

## Task 1: Freeze the archived baseline contract

**Objective:** Prove the accepted Probe 007 remains reproducible while all revision work uses new files and job identities.

**Files:**
- Create: `studies/001-memory-field/01_behavior/00_baseline/baseline-receipt.json`
- Create: `tests/test_memory_field_behavior_revision.py`
- Read only: `studies/001-memory-field/study.json`
- Read only: `houdini/vex/memory_field_agents.vfl`
- Read only: `houdini/vex/memory_field_fields.vfl`

**Steps:**

1. Add a regression test that locates the accepted Probe 007 config, verifies artifact mechanics are disabled, and records the existing input digest and authoritative cache receipt.
2. Run the existing short deterministic simulation twice and require identical canonical cooked state, not necessarily identical serialized BGEO bytes.
3. Add a negative test that fails if the revision runner writes into the archived job or imports the legacy VFL paths as writable branch sources.
4. Record the baseline metrics listed above with `measured_from` paths and hashes.

**Verification:**

```powershell
python -m unittest tests.test_memory_field_behavior_revision.BaselineContractTests -v
```

Expected: baseline identity and deterministic state pass; attempted in-place revision fails.

---

## Task 2: Create a versioned V2 Behavior backend

**Objective:** Establish a VEX-authoritative branch path without changing the archived simulation.

**Files:**
- Create: `houdini/vex/memory_field_v2_agents.vfl`
- Create: `houdini/vex/memory_field_v2_fields.vfl`
- Create: `houdini/simulate_memory_field_v2.py`
- Create: `houdini/build_memory_field_v2_scene.py`
- Create: `studies/001-memory-field/01_behavior/00_brief/README.md`
- Create: `studies/001-memory-field/01_behavior/01_candidates/`
- Modify: `tests/test_memory_field_behavior_revision.py`

**State layout:**

- Agent point attributes: `id`, `profile`, `mode`, `energy`, `mode_age`, `v`, `heading`, sampled field values, branch activation counters.
- Field point attributes: `resource`, `fresh_trace`, `trace_dir`, `scar`, `idle_age`, `recovery`, `occupancy`.
- Detail attributes: frame, branch ID, VEX cook count, transition counters, cumulative encounter/event counters.

**Steps:**

1. Write a failing live-Hython tracer requiring two consecutive VEX cooks, persisted prior state, explicit `engine = houdini-vex-cache-loop`, and `state_authority = vex-geometry`.
2. Build initial geometry with stable point ranges and deterministic agent profiles; profiles must alter thresholds/timescales, not initial visual appearance.
3. Implement the explicit cache-reload loop: frame `N` must consume the saved geometry from frame `N-1`.
4. Extract all metrics from cooked/reloaded geometry.
5. Reopen the generated HIP in a fresh Hython process, cook `OUT_STATE`, and verify its digest against the final reloaded cache.

**Verification:**

```powershell
& 'C:\Program Files\Side Effects Software\Houdini 22.0.368\bin\hython.exe' tests\live_memory_field_v2_tracer.py
python -m unittest tests.test_memory_field_behavior_revision.VexAuthorityTests -v
```

Expected: live compile/cook succeeds, state persists, authority labels are honest, and no Python function evolves agent or field state.

---

## Task 3: Repair the common motion substrate

**Objective:** Remove dead or homogenizing mechanics before comparing creative branches.

**Files:**
- Modify: `houdini/vex/memory_field_v2_agents.vfl`
- Modify: `houdini/vex/memory_field_v2_fields.vfl`
- Modify: `tests/test_memory_field_behavior_revision.py`

**Steps:**

1. Replace the unreachable speed-based dormancy condition with explicit energy/mode transitions.
2. Add velocity drag and bounded turn response so steering changes heading without driving almost every agent to `max_speed`.
3. Compute resource/scar steering from local contrast or finite-difference gradients; retain raw sampled magnitudes for diagnostics.
4. Replace hard clamp-only wall handling with a soft inward field plus deterministic reflection at the final boundary. Count soft-zone entries separately from hard contacts.
5. Make deposition depend on agent mode and energy, not speed alone.
6. Add bounded resource recovery only for branches that require it; preserve a no-recovery baseline switch.
7. Verify profile heterogeneity produces distinct trajectories without creating arbitrary noise.

**Acceptance:**

- all intended modes are entered and exited;
- speed distribution remains broad and does not pin most agents to the maximum;
- hard boundary contacts fall below the archived baseline under matched scale;
- identical seed/config repeats produce matching decoded final state;
- changed seed produces a distinct state;
- no invalid positions or field values occur.

---

## Task 4: Build Direction A — Refractory Route Ecology

**Objective:** Produce recurrent route birth, reinforcement, overload, abandonment, healing, and return.

**Files:**
- Create: `studies/001-memory-field/01_behavior/01_candidates/refractory-route/config.json`
- Create: `studies/001-memory-field/01_behavior/01_candidates/refractory-route/mechanism.md`
- Modify: `houdini/vex/memory_field_v2_agents.vfl`
- Modify: `houdini/vex/memory_field_v2_fields.vfl`
- Modify: `tests/test_memory_field_behavior_revision.py`

**Steps:**

1. Add directional trace deposition using the depositing agent’s normalized velocity.
2. Blend trace direction by weighted recent use; decay magnitude and direction confidence separately.
3. Convert sustained fresh trace into refractory scar after a thresholded exposure interval.
4. Give stable profiles staggered `follow → deflect → explore/rest` phases rather than applying one fixed turn every frame.
5. Heal unvisited scars and couple healing to slow resource recovery.
6. Instrument transition-level counters: trace reinforced, scar threshold crossed, route abandoned, scar healed, healed region revisited.
7. Run a tiny 24-agent/60-frame tracer to prove every branch predicate activates.
8. Run the 96-agent/180-frame diagnostic probe.

**Acceptance:** At least two spatially distinct routes must complete the full lifecycle `birth → reinforcement → abandonment → re-entry`. The review movie must show these events without requiring beauty rendering or prose to infer them.

---

## Task 5: Build Direction B — Lineage Border Negotiation

**Objective:** Test whether inherited sensitivities create changing borders and crossings rather than static segregation.

**Files:**
- Create: `studies/001-memory-field/01_behavior/01_candidates/lineage-borders/config.json`
- Create: `studies/001-memory-field/01_behavior/01_candidates/lineage-borders/mechanism.md`
- Modify: `houdini/vex/memory_field_v2_agents.vfl`
- Modify: `houdini/vex/memory_field_v2_fields.vfl`
- Modify: `tests/test_memory_field_behavior_revision.py`

**Steps:**

1. Add two-lineage trace channels and contested-cell age.
2. Implement energy-dependent yielding/crossing at foreign pressure gradients.
3. Record encounter, yield, cross, local takeover, and border-release events.
4. Run a tiny branch-coverage tracer, then the matched 96-agent/180-frame probe.
5. Reject the branch if borders freeze, if one lineage deterministically exterminates the other, or if behavior is illegible without categorical colour.

---

## Task 6: Build Direction C — Successional Bloom and Migration

**Objective:** Test recurring collective convergence and dispersal driven by endogenous patch history.

**Files:**
- Create: `studies/001-memory-field/01_behavior/01_candidates/successional-bloom/config.json`
- Create: `studies/001-memory-field/01_behavior/01_candidates/successional-bloom/mechanism.md`
- Modify: `houdini/vex/memory_field_v2_agents.vfl`
- Modify: `houdini/vex/memory_field_v2_fields.vfl`
- Modify: `tests/test_memory_field_behavior_revision.py`

**Steps:**

1. Add explicit hungry, sated, dispersing, and resting transitions.
2. Add local patch exhaustion and occupancy-stress accumulation.
3. Allow recovery only after an unvisited refractory interval; do not script global patch activation times.
4. Record convergence, patch collapse, migration departure, recovery, and recolonization events.
5. Run a tiny branch-coverage tracer, then the 128-agent/240-frame probe.
6. Reject the branch if patch timing, rather than agent history, explains the animation.

---

## Task 7: Upgrade behavioral diagnostics

**Objective:** Make the selection depend on measured interactions and inspectable motion, not attractive field colour.

**Files:**
- Modify: `houdini/simulate_memory_field_v2.py`
- Create: `src/houdini_ai/memory_field_behavior_metrics.py`
- Create: `tests/test_memory_field_behavior_metrics.py`
- Create: `houdini/render_memory_field_v2_diagnostic.py`

**Per-agent metrics:**

- travel, displacement/travel ratio, heading-change distribution, cumulative winding;
- mode dwell times and transition counts;
- resource gain and deposition by mode;
- encounter, yield, join/follow, split, and crossing counts where applicable.

**Field metrics:**

- active fresh-trace area, scar area, healed area, directional coherence;
- resource depletion and recovery rates;
- route component count, lifetime, reuse, abandonment, and re-entry;
- occupied-area entropy and largest-cluster fraction;
- hard boundary contacts and soft-zone dwell.

**Review media:**

1. Locked top-down neutral movie with agents and field values.
2. Agent-mode movie using semantic scalar indices `0 / 0.5 / 1` where three states are compared; continuous ages remain separate.
3. Event timeline strip with marked transition frames.
4. Sampled trajectory plot for the same stable agent IDs in every branch.
5. Early/middle/late state panels plus a continuous motion check.

**Tests:** Use synthetic records to prove metrics distinguish route reuse from repeated random crossing, cumulative events from final gauges, and real state transitions from merely selected branch IDs.

---

## Task 8: Sequential branch comparison and selection gate

**Objective:** Choose one mechanism on behavior alone.

**Execution order:** Direction A, then B, then C. Complete and verify each before beginning the next; do not run these candidate builds in parallel.

**Matched controls:**

- same deterministic initial positions and headings where the mechanism permits;
- same domain, field resolution, review camera, duration class, and display sampling;
- flat neutral presentation; no trails, materials, lighting, depth, or camera treatment that differs by branch;
- bounded per-branch wall time and one correction retry after diagnosis.

**Selection questions:**

1. Can KC point to at least three distinct interactions or state changes in the movie?
2. Does the field alter later behavior rather than merely visualizing past traffic?
3. Does the system generate recurrence, escalation, or reversal instead of one-way filling?
4. Are local causes visible in the subsequent motion?
5. Does the result avoid generic particle-flow, flocking, territory-demo, or blinking-attractor reads?
6. Does it retain interesting behavior after removing diagnostic colour?

**Stopping rule:** Reject branches that remain behaviorally flat after one diagnosed correction. Do not compensate with Look Development.

---

## Task 9: Extend only the selected branch

**Objective:** Prove the selected behavior survives a longer horizon and yields useful animation windows.

**Files:**
- Create: `studies/001-memory-field/01_behavior/02_selected/selection_001/`
- Create: `studies/001-memory-field/01_behavior/02_selected/selection_001/selection.json`
- Create: `studies/001-memory-field/01_behavior/02_selected/selection_001/component.json`
- Create: `studies/001-memory-field/01_behavior/02_selected/selection_001/behavior-review.mp4`
- Modify only after KC approval: `work/studio/studies/study-001-memory-field.json`

**Steps:**

1. Reuse the exact selected initialization and historical prefix.
2. Extend to 480–720 frames only if the 180/240-frame probe remains active near its end.
3. Measure late-window motion, route/topology retention, recurrence, collapse, and recovery from consecutive cooked caches.
4. Identify two or three event-rich continuous windows for later artist-led Look work.
5. Reopen and cook the packaged HIP in a fresh Hython process; verify cache/HIP/state receipts.
6. Ask KC for explicit Behavior promotion. Do not advance Look automatically.

---

## 4. Likely files affected

### New revision files

- `houdini/vex/memory_field_v2_agents.vfl`
- `houdini/vex/memory_field_v2_fields.vfl`
- `houdini/simulate_memory_field_v2.py`
- `houdini/build_memory_field_v2_scene.py`
- `houdini/render_memory_field_v2_diagnostic.py`
- `src/houdini_ai/memory_field_behavior_metrics.py`
- `tests/test_memory_field_behavior_revision.py`
- `tests/test_memory_field_behavior_metrics.py`
- `tests/live_memory_field_v2_tracer.py`
- `studies/001-memory-field/01_behavior/**`

### Protected archived files

- `studies/001-memory-field/study.json`
- `studies/001-memory-field/lab-log.md`
- `houdini/vex/memory_field_agents.vfl`
- `houdini/vex/memory_field_fields.vfl`
- `work/jobs/001-memory-field-s18432-probe-07a4f73b738f/**`

Only update the archived lab log later with a clearly dated revision/promotion note; never rewrite Probe 007’s acceptance history.

---

## 5. Validation ladder

1. Pure-Python unit tests for metric semantics and receipt parsing.
2. Tiny live-Hython compile/cook tracer for each new state transition.
3. Same-seed deterministic replay and changed-seed distinctness.
4. Fresh-cache reload and decoded state digest.
5. Fresh-HIP reopen, cook, node-error, active-ancestor, and final-state checks.
6. 180/240-frame neutral diagnostic movie for each candidate.
7. Image/media QC: nonblank frames, stable framing, correct frame range, visible temporal change.
8. Independent image-first behavior review without branch prose.
9. KC selection gate.
10. Bounded 480–720-frame endurance only for the selected branch.

Suggested commands during implementation:

```powershell
Set-Location 'E:\Projects\houdini-ai'
python -m unittest tests.test_memory_field_behavior_metrics -v
python -m unittest tests.test_memory_field_behavior_revision -v
& 'C:\Program Files\Side Effects Software\Houdini 22.0.368\bin\hython.exe' tests\live_memory_field_v2_tracer.py
python -m unittest discover -s tests -v
```

---

## 6. Risks and tradeoffs

- **Too many mechanisms at once:** Combining lineages, excitable traces, energy, and succession immediately would make causality unreadable. Keep the branches separate until one earns synthesis.
- **False complexity from colour:** Diagnostic channels can make a dull system look eventful. Require neutral agent motion and event counters.
- **Static territorial attractor:** Lineage traces can lock the field. Include pressure release and resource-driven border weakening, then reject if fronts stop moving.
- **Synchronized cycling:** Shared thresholds can make all agents switch modes together. Use stable seed-derived profiles and inspect phase distributions.
- **Trail-following loops:** Directional memory can trap agents in synchronized orbits. Measure winding, displacement/travel ratio, heterogeneity, route splitting, and return.
- **Recovery becoming a hidden script:** Resource/scar recovery must depend on cooked idle history, not Python event timing.
- **Framework creep:** This is a Behavior revision, not a general multi-species ecology framework or HDA packaging project.
- **Archived-study ambiguity:** Treat the work as `Study 001 / Behavior revision 001`; preserve the prototype-era vertical slice as a regression fixture until KC explicitly promotes the revision.

---

## 7. Recommendation

Start with **Direction A — Refractory Route Ecology**. It most directly answers the original question—how environmental memory changes later inhabitants—while creating the temporal verbs the current piece lacks: **follow, reinforce, overload, split, abandon, heal, return**.

Do not begin by tuning the existing weights. The current weakness is structural: unreachable states, monotonic fields, uniform speed-linked deposition, and interaction without persistent social or directional consequence. Parameter sweeps would mostly groom the same behavior.
