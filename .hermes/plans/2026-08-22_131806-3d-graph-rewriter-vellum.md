# 3D Graph Rewriter + Vellum Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task. Do not attempt the graph grammar, dynamic topology, Vellum integration, and final visual treatment in one pass.

**Goal:** Build a compact developmental graph system that favors rings, short branches, reconnection, and capped forms, then embody that graph as a genuinely connected Vellum mechanism whose physical state can eventually influence later rewrites.

**Architecture:** Keep two explicit authorities. A deterministic graph engine owns identity, ports, connectivity, lineage, rewrite legality, and event history. Houdini/Vellum owns physical positions, velocities, collisions, and strain. Exchange versioned snapshots through stable IDs; do not let either side silently redefine the other.

**Tech Stack:** Python 3.11 reference model and tests; JSON receipts/snapshots; Houdini 22 Hython/SOPs/Vellum; VEX only where it materially improves geometry conversion, measurements, or persistent state; unittest; BGEO caches; lightweight viewport/software motion checks before Look.

---

## 1. Creative and technical target

The target is a small self-assembling soft mechanism rather than a massive tree:

- rings, partial rings, fused ring pairs, hooks, and compact asymmetric loops;
- short 1–3 segment connectors and rare bifurcations;
- few simultaneously open growth tips;
- frequent reconnection, closure, capping, and pruning;
- bounded material and spatial extent;
- coherent physics: pulling one region visibly transmits force through the connected organism;
- growth occurs in readable pulses separated by physical relaxation.

This plan stops at a verified **Behavior** system and neutral motion evidence. It does not select materials, colour, lighting, camera language, or final surface treatment. If promoted later, KC receives an artist-owned `02_look/look.hiplc` starter built from frozen Behavior caches.

## 2. Authority boundary

### Graph authority

The graph engine owns:

- immutable node, port, edge, motif, rule-event, and lineage IDs;
- node/port types and capacities;
- which ports are open, connected, capped, or retired;
- legal rewrite candidates and the selected rewrite event;
- connectivity and component membership;
- the exact historical event prefix;
- graph-derived metrics such as degree, tip count, component count, and cycle rank.

### Physics authority

Houdini/Vellum owns:

- `P`, `v`, orientation, collision response, and deformation;
- measured edge strain, motif curvature, spatial proximity, and contact;
- physical settling between growth events;
- cache-derived bounds, energy proxies, and motion diagnostics.

### Exchange contract

- The graph snapshot enters Houdini with stable IDs and physical parameters.
- Vellum returns a feedback snapshot keyed by the same IDs.
- The graph engine may use measured feedback to rank future **legal** rewrites.
- Physics must never create an unrecorded topological bond.
- The graph engine must never claim a physical position that was not measured from the cooked Vellum state.

## 3. Recommended implementation ladder

Do not start with live topology mutation inside one Vellum Solver. Use this ladder:

1. **Graph-only reference:** deterministic rewrites, replay, invariants, and compactness controls.
2. **Static Vellum embodiment:** one frozen graph becomes a connected soft mechanism.
3. **Prepared growth schedule:** prebuild a full topology and activate successive motifs/constraints over time.
4. **Chunked coupled growth:** rewrite once, rebuild/extend constraints, simulate a bounded settling window, measure, then rewrite again.
5. **Physics-informed grammar:** strain, proximity, curvature, and contact influence candidate ranking.

Each rung is independently reviewable. A failed rung triggers diagnosis rather than bypassing it with more complexity.

---

## 4. Graph-side design

### 4.1 Core records

Create a small, serializable domain model rather than storing network meaning only in Houdini attributes.

**Node**

- `node_id`: immutable integer or stable string
- `node_type`: initially `joint`, `terminal`, `ring_anchor`, `cap`
- `generation`, `created_event`, `parent_node_id`
- `port_ids`: ordered list
- `motif_ids`: motifs using this node
- optional neutral embedding hint: position and local frame (not authoritative after Vellum)

**Port**

- `port_id`, `node_id`, `port_index`
- `role`: `axial`, `lateral`, `closure`, or `cap`
- `state`: `open`, `bound`, `capped`, `retired`
- `max_connections`, normally one
- local direction/frame hint for initial placement

**Edge**

- `edge_id`
- endpoint port IDs and derived endpoint node IDs
- `edge_type`: `spine`, `ring`, `junction`, `closure`
- physical defaults: rest length, stretch stiffness, damping class
- `created_event`, `active_event`, optional `retired_event`

**Motif**

- `motif_id`, `motif_type`: `ring`, `short_chain`, `branch`, `cap`, `fused_pair`
- ordered node/edge IDs
- physical profile: bend class, thickness class, collision radius
- motif-local ordering needed to create Vellum curves and bend constraints

**Rewrite event**

- event index and deterministic event ID
- rule name/version
- matched node/port IDs
- created/updated/retired IDs
- random draw receipt or candidate ranking receipt
- graph digest before and after
- optional physics-feedback digest used for selection

### 4.2 Minimal rule vocabulary

Implement only enough rules to discover whether the idea works:

1. `grow_short_chain(open_port, length=1..3)`
   - extends a tip through a small number of nodes;
   - creates at most one new open terminal.

2. `grow_ring(open_port, sides=5..10)`
   - creates a closed loop attached at one anchor;
   - optionally exposes zero or one lateral continuation port.

3. `close_nearby_tips(port_a, port_b)`
   - connects compatible open ports already close in physical space;
   - strongly preferred over new branching.

4. `branch_once(open_port)`
   - creates a short Y junction with two tips;
   - rare and forbidden when the active-tip budget is near its limit.

5. `cap_tip(open_port)`
   - retires a growth site without increasing topology;
   - always available as a safe terminal rule.

Defer pruning, motif substitution, ring fusion, edge splitting, and recurrent regrowth until this vocabulary is stable and visually useful.

### 4.3 Anti-bushiness contract

Hard constraints:

- one connected component unless a test explicitly requests otherwise;
- maximum node degree `3`;
- maximum open tips `4–6` (probe as a small parameter sweep);
- maximum node count `64–128` for early probes;
- maximum consecutive branch events `1`;
- every growth event must preserve a path to eventual capping;
- no rule may create more than two new open ports;
- branch rule is illegal when cycle count is below a configurable minimum after an early grace period.

Candidate scoring, highest priority first:

1. legal closure between existing tips;
2. create a ring without increasing active-tip count;
3. continue a short connector toward a useful nearby site;
4. cap a stale or strained tip;
5. branch only when silhouette or reach is insufficient.

Record score terms independently. Do not hide them in one unexplained random weight.

### 4.4 Determinism and replay

Given a seed, initial graph, rule configuration, and feedback snapshot sequence:

- candidate enumeration order must be stable;
- tie-breaking must be seeded and recorded;
- every event must replay to the same canonical graph digest;
- physical feedback may change selection, but its exact digest and measured values must be part of the receipt;
- a later extended run must preserve the accepted event prefix exactly.

### 4.5 Graph metrics

At every event record:

- node, edge, motif, open-tip, and capped-tip counts;
- connected components;
- degree histogram and maximum degree;
- cycle rank `E - V + C`;
- ring motif count and size distribution;
- branch-event ratio;
- closure-to-growth ratio;
- graph diameter and average shortest-path length for the small graph;
- event replay digest.

Behavior failure indicators:

- open tips trend upward without closure;
- cycle rank remains near zero;
- branch ratio dominates ring/closure events;
- node count grows while silhouette remains visually redundant;
- many nodes occupy one featureless dense clump.

---

## 5. Vellum-side design

### 5.1 Representation options

**Option A — graph points plus distance constraints**

- Cheapest connectivity test.
- Useful only for the first live tracer.
- Rings collapse and junction angles have little character.

**Option B — motif curves plus shared graph anchors (recommended)**

- Each ring is an ordered closed curve.
- Each short branch/connector is an ordered open curve.
- Curves receive stretch and bend constraints.
- Junction particles are welded, stitched, or otherwise constrained through stable anchor IDs.
- Motif-local ordering remains explicit, so closed loops and branch spines behave differently.

**Option C — tetrahedral/soft-body organs**

- Potentially rich later, but far too expensive and difficult for first Behavior proof.

Start with A only as a disposable tracer, then move directly to B.

### 5.2 Physical geometry contract

Generate two related geometries:

1. **Graph identity geometry**
   - one point per graph node;
   - one primitive per graph edge;
   - stable `node_id`, `edge_id`, `motif_id`, `created_event`, `active_event`;
   - graph attributes remain intact for audits.

2. **Simulation spine geometry**
   - resampled closed curves for rings;
   - resampled open curves for chains/branches;
   - stable per-particle IDs derived from motif ID and local sample index;
   - anchor mapping back to graph node IDs;
   - point attributes for mass, collision radius, stiffness class, and activation.

Never infer graph topology back from resampled point numbers. Point numbers may change; stable IDs may not.

### 5.3 Constraint families

Use distinct named groups/classes:

- `stretch_ring`, `bend_ring`;
- `stretch_branch`, `bend_branch`;
- `junction_attach`;
- `closure_attach`;
- optional `shape_junction` for preserving branch angles;
- temporary `birth_pin` or high drag for staged materialization.

Initial physical intent:

- rings: moderate stretch stiffness, meaningful bend resistance, slight allowable flex;
- connectors: softer bend, similar or slightly softer stretch;
- junctions: stiffer local angle/attachment response;
- new motifs: short activation ramp from guided initial placement to free motion;
- self-collision enabled only after the basic connected-motion test passes.

Do not rely on distance constraints alone for recognizable rings.

### 5.4 Growth integration strategies

#### Stage 1: Static connectivity probe

- Freeze one graph with two rings, one short connector, and one capped branch.
- Convert it to simulation spines and constraints.
- Pin or impulse one region.
- Verify the entire connected organism responds while ring shapes remain legible.

#### Stage 2: Prepared activation

- Generate a deterministic full event schedule in advance.
- Build all particles/constraints before the solve.
- Keep unborn particles guided/pinned and constraints inactive or weak.
- At each event frame, reveal and activate one motif over a short ramp.
- This proves temporal legibility and constraint activation without changing topology inside the live solve.

Limitation: physics cannot influence which event happens because the schedule is already fixed. Label this honestly.

#### Stage 3: Chunked coupled solve (preferred real system)

For each event:

1. Load the previous authoritative settled cache.
2. Measure physics feedback from cooked geometry.
3. Ask the graph engine to select and apply exactly one legal rewrite.
4. Add only the new motif geometry with stable IDs and a guided initial pose.
5. Rebuild or extend constraints while preserving `P` and `v` by stable particle ID.
6. Run Vellum for a bounded settling window, e.g. 8–24 frames.
7. Save every cache in the window plus a settled checkpoint.
8. Reload the checkpoint and compute feedback/verification metrics.
9. Continue until the event, node, wall-time, or failure budget is reached.

This is simpler and more auditable than mutating arbitrary topology inside one uninterrupted DOP solve.

#### Stage 4: Physics-informed selection

Add one feedback term at a time:

1. proximity favors `close_nearby_tips`;
2. tip age favors `cap_tip`;
3. high strain suppresses outward growth or favors reinforcement/capping;
4. curvature/orientation biases the placement plane of a new ring;
5. contact may permit a fusion candidate, only after closure is stable.

For each term, compare against the same graph seed and prior event prefix. Do not introduce all terms simultaneously.

### 5.5 Feedback snapshot

Keyed by stable IDs and measured from reloaded Vellum caches:

- graph-node world positions and velocities;
- open-port positions and outward frame estimates;
- edge strain `(current_length / rest_length) - 1`;
- motif curvature/shape deviation summary;
- nearest compatible tip IDs and distances;
- collision/contact counts where reliable;
- connected-component bounds and radius;
- consecutive-frame motion delta and settled/not-settled status;
- source cache path and hash.

### 5.6 Settling policy

Avoid waiting indefinitely for perfect rest.

A growth chunk ends when either:

- kinetic/motion proxy stays below a threshold for a small consecutive window;
- the configured frame budget is exhausted;
- invalid geometry, exploding bounds, NaNs, or solver errors trigger failure.

Record whether each event ended by `settled`, `frame_budget`, or `failure`.

---

## 6. Proposed files

### Graph/reference layer

- Create: `src/houdini_ai/graph_rewriter.py`
- Create: `src/houdini_ai/graph_rewriter_rules.py`
- Create: `src/houdini_ai/graph_rewriter_io.py`
- Create: `tests/test_graph_rewriter.py`
- Create: `tests/test_graph_rewriter_rules.py`
- Create: `tests/fixtures/graph_rewriter/`

### Houdini/Vellum layer

- Create: `houdini/build_graph_rewriter_probe.py`
- Create: `houdini/simulate_graph_rewriter_vellum.py`
- Create: `houdini/verify_graph_rewriter_cache.py`
- Create: `houdini/vex/graph_rewriter_feedback.vfl` only if measurements are awkward or slow in HOM
- Create: `tests/test_graph_rewriter_houdini.py`

### Behavior artifacts after explicit probe approval

- Create under a promoted Study, not while the Seed is merely incubating:
  - `studies/<study>/01_behavior/graph/`
  - `studies/<study>/01_behavior/caches/`
  - `studies/<study>/01_behavior/motion_checks/`
  - `studies/<study>/01_behavior/receipts/`

Do not create a Study directory, publish the Seed, or promote Behavior as part of planning.

---

## 7. Task sequence

### Task 1: Freeze the state and ID contract

**Objective:** Define serializable graph, motif, event, and feedback records with stable IDs.

**RED:** Tests reject duplicate IDs, bound ports with no edge, edges with missing endpoints, invalid motif ordering, and non-canonical serialization.

**GREEN:** Implement minimal dataclasses/validation and canonical JSON encoding.

**Verify:**

```bash
PYTHONPATH=src python -m unittest tests.test_graph_rewriter.GraphStateContractTests -v
```

Expected: focused contract tests pass; no Houdini dependency.

### Task 2: Implement graph invariants and metrics

**Objective:** Make graph validity and anti-bushiness measurable before adding growth rules.

**RED:** Fixtures intentionally violate component count, degree, tip budget, and motif membership.

**GREEN:** Implement validators plus graph metrics and canonical digest.

**Verify:** focused tests plus same-state/different-order canonical digest equality.

### Task 3: Implement one ring and one short-chain rewrite

**Objective:** Prove local RHS patches, port binding, lineage, and replay.

**RED:** Hand-authored fixtures specify exact nodes, ports, edges, motifs, and IDs after each rule.

**GREEN:** Implement `grow_ring` and `grow_short_chain` only.

**Verify:** apply, serialize, reload, replay, and compare graph digests.

### Task 4: Add closure, cap, and rare branch rules

**Objective:** Complete the minimal rule vocabulary without uncontrolled expansion.

**RED:** Test illegal self-closure, incompatible ports, exceeded tip budget, repeated branching, and always-available capping.

**GREEN:** Implement the three rules and candidate enumeration.

**Verify:** property-style seeded runs over many small seeds remain connected, bounded, and replayable.

### Task 5: Add transparent candidate scoring

**Objective:** Bias toward rings and closure while retaining deterministic variation.

**RED:** Fixed candidate sets must rank closure above ring, ring above continuation, and branch last under normal conditions.

**GREEN:** Implement named score terms, stable ranking, and seeded tie-break receipt.

**Verify:** bounded sweeps report ring count, cycle rank, tip count, branch ratio, and closure ratio; reject bushy regimes before Houdini work.

### Task 6: Build a graph-to-Houdini static tracer

**Objective:** Import one frozen graph and preserve all stable IDs in cooked Houdini geometry.

**RED:** Live-Hython test requires exact graph-node/edge/motif counts and ID round-trip from a small fixture.

**GREEN:** Build graph identity geometry and simple point-distance constraints.

**Verify:** reopen HIP in a fresh Hython process, cook the displayed output, and compare IDs/counts to the fixture.

### Task 7: Prove connected physical motion

**Objective:** Show that force applied to one region propagates through the entire connected structure.

**RED:** Test requires nonzero downstream motion, finite geometry, bounded stretch, and retained single-component identity.

**GREEN:** Run a tiny static Vellum solve with two rings/one connector, initially using the simplest constraint representation.

**Verify:** inspect early/middle/late neutral motion frames and cache-derived motion metrics.

### Task 8: Upgrade to motif curves and bend behavior

**Objective:** Keep rings legible and branches flexible under movement.

**RED:** A ring-collapse metric fails the distance-only baseline.

**GREEN:** Generate ordered ring/branch curves, stretch/bend constraint classes, and junction attachments.

**Verify:** compare matched impulses for distance-only versus motif-curve systems; require improved ring retention without rigid-body lockup.

### Task 9: Implement prepared event activation

**Objective:** Establish readable growth pulses and birth-to-free-motion ramps without dynamic topology mutation.

**RED:** Test expects event-aligned activation, stable IDs, no pre-birth visible/free particles, and continuous existing motion.

**GREEN:** Prebuild a deterministic topology and activate motifs/constraints by event frame.

**Verify:** motion check visibly separates growth pulses; receipt states `schedule_authority=prepared`, not physics-informed.

### Task 10: Implement one chunked rewrite/settle cycle

**Objective:** Round-trip a Vellum checkpoint into one new graph event and a second settled checkpoint.

**RED:** Integration test requires preserved old particle IDs/`P`/`v`, new IDs only for the rewrite, one event receipt, and reloaded cache metrics.

**GREEN:** Orchestrate checkpoint load, feedback extraction, rewrite, geometry extension, constraint rebuild, bounded solve, and save/reload verification.

**Verify:** fresh-process replay reproduces the same graph event and canonical decoded state within stated floating tolerance.

### Task 11: Add proximity-driven closure

**Objective:** Let measured physics influence one clearly attributable graph decision.

**RED:** Two feedback fixtures with identical graph topology but different tip positions select different legal candidates.

**GREEN:** Feed nearest compatible tip distance into `close_nearby_tips` eligibility/scoring.

**Verify:** compare coupled and topology-only runs from the same historical prefix; record exactly where they diverge.

### Task 12: Bounded Behavior probe

**Objective:** Produce a neutral, reviewable Behavior artifact only after probe approval.

**Bounds:** small graph; explicit event cap; per-event Vellum frame cap; total wall-time and cache-size budgets; abort on repeated failure.

**Outputs:** authoritative caches, graph/event log, feedback receipts, verification report, reopenable organized HIP, and a lightweight motion check.

**Review gate:** KC judges whether growth is compact, rings remain distinct, movement feels physically connected, and the topology avoids bushiness. This gate does not authorize Look or publication.

---

## 8. Validation matrix

### Graph correctness

- deterministic same-seed replay;
- canonical digest independent of dictionary/insertion order;
- every bound port has exactly one legal connection;
- single component, bounded degree, bounded tips, bounded nodes;
- event prefix preservation across extended runs;
- candidate score receipt explains each selection.

### Vellum correctness

- live node cook reports no errors;
- fresh-reloaded BGEO contains finite positions and expected stable IDs;
- force propagates beyond the directly manipulated motif;
- ring shape-retention metric stays within an approved range;
- old particles preserve state through graph extension;
- cache measurements, not a Python reference, support physical claims;
- same-seed graph/event decisions replay; serialized BGEO byte identity is not required.

### Motion/creative diagnostics

- active-tip count remains low over time;
- cycle rank and ring count rise earlier than branch count;
- silhouette changes remain legible between growth pulses;
- the organism does not collapse into one dense knot;
- connections visibly transmit motion;
- rings flex but remain recognizable;
- motion does not settle into a trivial synchronized wobble.

### Commands during implementation

```bash
PYTHONPATH=src python -m unittest tests.test_graph_rewriter -v
PYTHONPATH=src python -m unittest tests.test_graph_rewriter_rules -v
# Run Houdini-focused tests with the repo's configured Hython executable:
PYTHONPATH=src <hython> -m unittest tests.test_graph_rewriter_houdini -v
PYTHONPATH=src python -m unittest discover -s tests

git diff --check
```

Use the exact configured Houdini executable discovered from the repository/environment; do not guess its installation path in code.

---

## 9. Risks and controls

- **Dynamic Vellum topology becomes brittle:** use prepared activation first, then chunked rebuilds with stable IDs; defer in-solver arbitrary mutation.
- **Rings collapse into strings:** represent motifs as ordered curves with bend constraints, not graph-edge distances alone.
- **Constraint rebuilding resets motion:** transfer `P`, `v`, and physical attributes by stable particle ID and test preservation explicitly.
- **Graph and simulation identity drift:** never use Houdini point numbers as durable IDs; audit round-trips after every chunk.
- **Bushy output despite low branch probability:** enforce hard tip/degree budgets and closure/cycle scoring; inspect metrics and motion rather than relying on probability.
- **Physics feedback makes replay ambiguous:** hash and store every feedback snapshot used for candidate selection.
- **Solver never settles:** use consecutive-frame thresholds plus strict per-event frame and wall-time caps.
- **Self-collision knots the organism:** establish connected motion without self-collision, then introduce it gradually with measured collision radii.
- **Premature visual polish:** neutral points/curves and fixed cameras only until Behavior is selected.
- **One-shot complexity:** every rung must generate its own testable artifact and may be rejected without invalidating earlier work.

## 10. Open questions and proposed defaults

1. **Should rings be graph cycles or attached decorative curves?**
   - Default: real graph cycles with ordered motif metadata. Their closure must matter topologically and physically.

2. **Should new growth happen continuously or in pulses?**
   - Default: discrete rewrite followed by 8–24 frames of relaxation. It is clearer and easier to audit.

3. **Should the first coupled rule use strain or proximity?**
   - Default: proximity-driven tip closure. It directly supports compact ring-rich forms and is easier to validate.

4. **Should branches share exact particles with rings?**
   - Default: share graph anchor identity, but test weld/stitch versus literal shared simulation points in the motif-curve probe. Choose the most stable method from live evidence.

5. **How much graph should the first probe contain?**
   - Default: approximately 24–64 graph nodes, 2–6 rings, no more than 4 active tips, and a strict event cap. Increase only after motion remains readable.

6. **Should Vellum govern the initial placement of a newborn motif immediately?**
   - Default: no. Spawn from a deterministic port-local frame, guide/pin briefly, then ramp into free physics to avoid explosive births.

---

## 11. Completion definition

The first implementation cycle is complete only when:

- a compact graph can be deterministically generated and replayed;
- graph invariants prove it is connected, low-degree, tip-bounded, and ring-rich;
- the same graph is converted into reopenable Houdini geometry with stable identity;
- Vellum motion demonstrably propagates through the connected organism;
- rings retain recognizable form while connectors flex;
- one prepared growth schedule is motion-reviewed;
- one chunked graph→Vellum→feedback→graph cycle is verified from reloaded caches;
- proximity can influence a legal closure decision with a recorded feedback receipt;
- all runs remain within explicit event, frame, wall-time, and cache budgets;
- KC, not automation, decides whether the Behavior is worth promotion.
