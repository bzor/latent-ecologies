# Scar Tissue lab log

## 2026-08-12 — Initial contract

**Question:** Can one oriented memory field produce reinforcement, congestion, abandonment, and regrowth without scripted composition?

**Probe:** Compare three conceptual mutations with the same seed, population, field resolution, fixed instrument camera, and colour semantics.

**Measured:** reinforced and saturated cell counts, cumulative post-occupancy trace
cells, cumulative previously-saturated cells now below saturation, field extrema, agent
bounds, and deterministic state digest. The short internal metric keys `abandoned` and
`regrown` are diagnostic shorthand rather than path-level or biological claims.

**Behavioral criterion:** at least one mutation should produce paths whose formation, saturation, abandonment, and re-entry are distinguishable in an unshaded diagnostic render.

**Status:** Reference simulator, temporal instrument renderer, legacy hybrid checkpoint
probe, and a separate sequential VEX-authoritative probe are implemented. Numerical
reference/VEX parity is deliberately not claimed.

## 2026-08-12 — Reference mutation comparison

**Execution:** Ran all three mutations for 300 frames with 256 agents on a 72 × 108
field using seed 9137. Each produced a distinct deterministic state digest.

**Measured final state:**

- Saturation repulsion: 5,748 reinforced cells, 3,420 saturated, 6,894 cumulative
  post-occupancy trace cells, and 4,854 previously-saturated cells below saturation.
- Directional scar: 3,021 reinforced cells, 2,015 saturated, 4,217 cumulative
  post-occupancy trace cells, and 2,243 previously-saturated cells below saturation.
- Refractory healing: 2,310 reinforced cells, 1,280 saturated, 5,180 cumulative
  post-occupancy trace cells, and 4,575 previously-saturated cells below saturation.

**Observed:** Directional scar is the clearest static diagnostic. It produces coherent
parallel channels and visibly oriented traffic rather than isotropic field noise.
Saturation repulsion produces strong voids but is over-saturated into broad cellular
blobs, obscuring individual path formation. Refractory healing creates the most open
territory and isolated rings, but a final frame cannot distinguish healing from simple
low occupancy.

**Next diagnostic change:** Preserve the cheap renderer but add temporal loops and a
three-state overlay for attractive, saturated/refractory, and healed territory. Do not
promote from static frames alone.

## 2026-08-12 — Temporal and Houdini verification

**Temporal package:** Generated a ten-second 360 × 540 diagnostic loop at 6 fps for
each mutation. The overlay distinguishes low field, attractive field, saturation, and
cells that fell below the attraction threshold between sampled checkpoints. The latter
is labelled `healed` as an instrument state, not proof of biological repair.

**Houdini execution:** Houdini 22.0.368 cooked the Scar Tissue agent VEX at all six
stored checkpoints for the base mutation, displaced agent points, emitted no node
errors, wrote six `.bgeo.sc` caches, and saved a reopenable `.hiplc`. Metrics record the
VEX source digest, cook count, displaced-point count, cache digests, and HIP digest.

**Limitation:** The Python reference remains the authoritative sequential field solve.
Houdini currently receives each reference checkpoint and applies one verified VEX agent
update before caching it. This demonstrates that the kernel compiles and acts on the
same state, but does not establish frame-by-frame numerical parity or a self-contained
Houdini field-feedback loop. No promotion claim should imply otherwise.

## 2026-08-12 — Versioned mutation records and regenerated comparison

Added explicit experiment records for `directional-scar` and
`refractory-healing`; all three records share seed 9137, frame range, population,
field resolution, and instrument grammar. Regenerated the reference temporal package
under `work/studio/probes/scar-tissue/temporal-v2/` with 60 frames per mutation. FFprobe
confirmed each MP4 is 360 × 540, 6 fps, and exactly 10 seconds; every receipt checksum
and byte count was recomputed successfully.

**Observed from the comparison:** The mutations are visibly distinct. Directional scar
has the strongest coherent diagonal channel structure. Saturation repulsion collapses
into broad red congestion masses. Refractory healing leaves much larger dark voids with
fragmented blue/green islands. The white agent marks are too sparse and small to make
local cause-and-effect legible in the contact sheet, and the colour classes alone do not
prove whether a blue cell represents durable renewal or a threshold crossing between
widely spaced samples. Temporal review remains required.

The reference state digest now includes oriented direction and idle arrays as well as
agent positions and scalar field values. This closes a false-equivalence gap where two
mechanically different oriented/idle states could previously hash identically.

## 2026-08-12 — Stateful VEX-authoritative probe

Added a separate `vex-authoritative` engine. Python creates topology, sets typed
parameters, advances the Houdini detail wrangle, and persists each cooked geometry as
the next frame's input; it does not evolve agent or field state. The VEX program owns
agent initialization and motion, scalar deposition/decay, oriented deposition, idle
age, threshold classification, and all three mutation branches.

The full versioned 300-frame records were run through Houdini 22.0.368. Each mutation
cooked 300 sequential VEX frames with distinct final state digests. Final measured VEX
geometry contained:

- Saturation repulsion: 7,036 deposited/oriented cells, 7,527 idle cells, and
  1,529,164 cumulative decayed-cell updates.
- Directional scar: 4,416 deposited/oriented cells, 7,564 idle cells, and 1,030,690
  cumulative decayed-cell updates.
- Refractory healing: 5,268 deposited cells, 4,223 oriented cells, 7,528 idle cells,
  and 1,112,282 cumulative decayed-cell updates.

All 900 cache checksums and three HIP checksums were independently recomputed without
mismatch. A focused live-Hython regression also confirmed same-seed VEX state and
checkpoint determinism. Outputs are under
`work/studio/probes/scar-tissue/vex-authoritative/`.

**Scope:** This proves a self-contained sequential Houdini/VEX mechanism and stable
local execution. It does not claim numerical parity with the Python reference; the
Python reference remains separate. A private VEX-derived package now exists under
`work/studio/probes/scar-tissue/vex-authoritative-v3/`: each mutation has 300 caches,
a reopenable HIPLC, 300 rendered diagnostic frames, a 10-second 30 fps MP4, metrics,
and a checksummed receipt, plus a same-seed comparison view.

An independent audit reproduced persistent state, branch activation, cache/HIP reopen
fidelity, and deterministic decoded state for short same-seed runs. Metric scope is now
explicit: final-frame and cumulative agent updates are separated; cumulative decay,
abandonment, and return are recorded; and canonical state digests are computed from the
reloaded displayed cache. Serialized BGEO/HIP bytes are not claimed deterministic.
Directional alignment is measured, but crossing resistance remains unproven and must
not be promoted as a verified behavior.

The final VEX comparison is visibly differentiated: saturation-repulsion produces a
dense saturated mass, directional-scar produces coherent diagonal bands, and
refractory-healing leaves sparse fragmented islands and large dark voids. Vector marks
make local orientation inspectable, but at this field density they also add substantial
texture; they support orientation, not a claim that agents resist crossing scars.

The final 300-frame measurements recorded abandonment/return counts of 7,011/841,
4,405/822, and 5,246/4,526 respectively. Refractory healing therefore produces the
strongest measured return signal in this bounded comparison. These are event-set counts
under the current instrument definition, not biological healing claims.

## 2026-08-12 — Directional refractory mutation

Combined stored-direction alignment with refractory avoidance and accelerated idle decay
in a fourth VEX branch. A same-seed 300-frame Houdini run produced 2,530 abandoned and
1,568 returned cells, 65,990 directional-alignment samples, and 647,341 cumulative
decayed-cell updates. Its 603-file receipt independently verified with no mismatches.

**Observed:** The final diagnostic is markedly more open than directional-scar while
retaining a loose vertical/channel tendency. Activity breaks into branching islands and
large voids rather than the directional version's continuous diagonal bands. This is a
credible bridge between the two parent behaviors, though the static final frame cannot
show the timing of renewal or prove that individual gaps were crossed after healing.

Outputs are under `work/studio/probes/scar-tissue/directional-refractory-v1/`.

**Movement correction:** The first combined run trapped every agent in sustained tight
turning: median cumulative winding was 12.96 revolutions and all 256 agents exceeded five
revolutions. Per-agent turning limits alone reduced synchrony but not looping. The revised
branch therefore gives agents stable individual movement profiles and staggered phases of
scar following, refractory deflection, and freer exploration. In the final v3 run, median
winding fell to 0.08 revolutions, no agent exceeded five, and the median displacement to
travel ratio rose from 0.022 to 0.218. Directional alignment remained active and measured
return increased to 6,355 cells. The corrected output is under
`work/studio/probes/scar-tissue/directional-refractory-v3/`.

**Selection:** KC approved v3. Its verified diagnostic artifact was promoted through the
canonical local lineage to Behavior component `component-behavior-b3bcc837c3e2`. This
freezes the mechanism and movement evidence; it does not freeze a look, palette, light,
or camera treatment.
