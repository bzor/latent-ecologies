# Pilot Study 003 — Nonlocal Affinity Dance Implementation Plan

**Status:** Faithful baseline implemented and verified. Awaiting KC's motion review before behavior promotion and independent departure experiments.

> **For Hermes:** Execute task-by-task with strict RED → GREEN tests. Do not commit, push, publish, or launch presentation rendering.

**Goal:** Reproduce Simon Woods’ nonlocal friend/enemy particle system faithfully in a deterministic Python reference and Houdini/VEX tracer, preserve it as an immutable baseline, then unlock independently judged experimental branches.

**Architecture:** Studio records capture provenance, three conceptual directions, selection, and a separately bounded proposal. `src/houdini_ai/nonlocal_affinity.py` owns the cheap deterministic reference and diagnostics. Houdini/VEX becomes authoritative only in the live parity tracer and later approved probe; Python may initialize, orchestrate cooks, and compare results but must not evolve VEX-authoritative state.

**Tech stack:** Python 3.11 standard library, existing Studio JSON schemas/store/API, Houdini 22 Hython/VEX, unittest, Pillow for cheap diagnostics.

---

## Scope and invariants

- Source: https://community.wolfram.com/groups/-/m/t/122095
- Baseline equation: `x_next = c*x + attraction*phi(friend-x) - repulsion*phi(enemy-x)`, `phi(d)=d/(softening+norm(d))`.
- Faithful parameters: 1,000 points, 2D, `c=0.995`, attraction `0.02`, repulsion `0.01`, softening `0.01`, one directed friend and enemy, occasional independent rewiring.
- Updates are synchronous and seeded.
- Baseline adds no inertia, 3D, local neighbors, trails, fields, shaders, or camera motion.
- Source URL and copied prose remain inert.
- No runner dispatch occurs through seed, direction, selection, proposal derivation, or approval.
- Fidelity is a completion gate, not an aesthetic constraint on descendant experiments.

## Task 1: Bootstrap Pilot Study 003 records

**Files:**
- Create: `src/houdini_ai/pilot_study_003.py`
- Create: `tests/test_pilot_study_003.py`
- Modify: `src/houdini_ai/studio_cli.py`

**RED:** Test an idempotent bootstrap against a temporary `StudioStore`. Require one provenance-rich behavior idea, an active Directions-phase session, three sibling Direction cards, faithful direction selected, other directions held, and one proposed—not approved or dispatched—baseline probe.

**GREEN:** Implement the minimal bootstrap operation and CLI command. Use stable IDs or exact lookup keys so retries do not duplicate records. Preserve the prior Scar Tissue session as resumable.

**Verification:**
- `PYTHONPATH=src python -m unittest tests.test_pilot_study_003`
- Inspect generated temporary records and assert `RunnerRegistry.dispatch` was never called.

## Task 2: Deterministic faithful Python reference

**Files:**
- Create: `src/houdini_ai/nonlocal_affinity.py`
- Create: `tests/test_nonlocal_affinity.py`

**RED→GREEN slices:**
1. Exact hand-calculated one-step update for a tiny fixed state.
2. Synchronous indexed reads; no point observes a partially updated peer.
3. Seeded initialization and independent friend/enemy indices.
4. Seeded rewire events with valid indices and recorded history.
5. Same-seed equality, changed-seed distinction, finite-state validation.
6. Baseline parameter factory records source semantics and original dimensionality.

**Diagnostics:** State digest, bounds/radial extent, displacement distribution, rewiring count, and compact sampled frames. Keep graph diagnostics separate from visual presentation.

**Verification:**
- `PYTHONPATH=src python -m unittest tests.test_nonlocal_affinity`
- Run a real 1,000-point bounded CPU probe and independently parse its metrics receipt.

## Task 3: Houdini/VEX live parity tracer

**Files:**
- Create: `houdini/vex/nonlocal_affinity_step.vfl`
- Create: `houdini/probe_nonlocal_affinity.py`
- Create: `tests/test_nonlocal_affinity_houdini.py`

**RED:** A tiny live-Hython test must fail until a VEX detail-wrangle path exists. It must require explicit `engine=hython-vex`, `state_authority=vex-geometry`, one cook per advanced step, zero VEX errors, and measured parity against the Python reference at a stated tolerance.

**GREEN:** Initialize topology in Python, evolve positions and optional rewiring only in VEX using prior cooked geometry, persist state through an explicit cache feedback loop, and derive metrics from cooked/reloaded geometry.

**Verification:**
- Tiny 8-agent, 3-step same-seed parity tracer.
- Reload saved BGEO and compute canonical decoded-state digest.
- Reopen generated HIP in a fresh Hython process and verify displayed-node geometry.
- Do not claim byte-identical BGEO/HIP determinism.

## Task 4: Bounded faithful baseline probe

**Prerequisite:** The exact Studio proposal must be approved before runner dispatch.

**Outputs:**
- authoritative caches under `work/studio/probes/pilot-study-003/nonlocal-affinity-baseline/`
- metrics JSON and checksum receipt
- fixed-camera diagnostic point frames
- short motion-check MP4 only; no presentation renderer
- reopenable organized HIP

**Stop conditions:** Any NaN/invalid index, VEX error, unexpected unbounded expansion, mismatched same-seed state, or failure to produce continuing structural reorganization.

**Verification:** Probe media dimensions/duration, all checksums independently recomputed, metrics parsed, morphology reviewed over time, and no Look/Chromatic/Cinematography commitments recorded.

## Task 5: Freeze fidelity and open independent departures

- Mark the faithful artifact/component as the reference baseline only after parity and motion review.
- Capture observed friction as contextual process notes.
- Create separate experimental branches for graph choreography and encounter memory.
- First isolate one causal change per branch; later deliberately combine successful mechanisms.
- Judge descendants on temporal identity, structural transformation, surprise, and animation value—not resemblance to the source.

## Validation gates

1. Focused unit tests for each RED→GREEN slice.
2. Focused Studio lifecycle tests.
3. Live-Hython parity tracer.
4. Real bounded baseline artifact verification.
5. `PYTHONPATH=src python -m unittest discover -s tests`.
6. `node --check website/app.js` and `git diff --check`.

## Risks and controls

- **Ambiguous Mathematica randomness:** Record executable-code semantics explicitly; friend/enemy draws and rewire target are independent draws.
- **Asynchronous drift:** Tests compare against a synchronous tiny fixture.
- **False Houdini authority:** Metrics must come from reloaded cooked geometry.
- **Premature look lock-in:** Use points, neutral fixed camera, semantic diagnostics only.
- **Reference becoming a cage:** Freeze the ancestor and evaluate descendants independently.
- **Dirty workspace:** Touch only Pilot Study, Studio adapter, targeted test, and plan files; preserve all unrelated modifications.
