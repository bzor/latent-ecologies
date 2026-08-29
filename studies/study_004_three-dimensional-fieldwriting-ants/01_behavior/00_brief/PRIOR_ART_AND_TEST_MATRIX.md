# Study 004 — Langton-family prior art and 3D test matrix

Status: private working audit · Behavior prerequisite · 2026-08-22

Visual implementation and Look saturation are audited separately in `VISUAL_PRIOR_ART.md`.

## Correction to the Seed premise

The current Seed text says the reference does not define a three-dimensional ant. That is true of the 2026 Wolfram Community reference itself, but false for the wider literature.[1]

Heiko Hamann published an explicit cubic-lattice 3D generalization in 2003. It gives the ant a heading plus a working plane, uses cyclic rule strings over `L R U D`, reports 3D highways, classifies them by period and pre-highway resource use, and tabulates short rules.[2] Dorbec and Gajardo later treated Langton-like systems on n-dimensional lattices more systematically, distinguishing a velocity-only lattice-gas formulation from an artificial-life formulation whose orientation is a full orthogonal basis.[3] Bunimovich had already studied many-dimensional Lorentz cellular automata and their computational properties.[4]

**Consequence:** our first 3D gate must reproduce published 3D formalisms before we call any orientation algebra or highway novel. Hamann is a mandatory historical baseline, but the literature does not establish one uniquely canonical 3D ant.

## Prior-art families that matter to this Study

| Family | Established move | Why it matters visually | Study treatment |
|---|---|---|---|
| Original Langton ant | Two cell states; state-dependent left/right turn; cyclic rewrite | chaotic transient → 104-step drifting highway | 2D receipt only; control case.[10] |
| Generalized multicolour ants | Cyclic cell alphabet encoded by `L/R` strings; known symmetric growth, space filling and convoluted highways | strongest small-rule source of distinct silhouette classes | lift selected 2D exemplars into frozen 3D algebras; do not claim the string idea.[6] |
| Turmites / turning machines | Ant has internal state as well as cell state; transition table controls write, turn and next state | spirals, frames, diamonds, textured growth, highways; much richer than colour-only ants | include a bounded 3D internal-state branch after the colour-only baseline.[5] |
| Multiple generalized ants | Several walkers rewrite one shared field; outcome depends on interaction/update semantics | collisions, cooperation, interference, territorial writing | replicate the Wolfram and Beuret–Tomassini baselines; treat scheduler, exclusion and write conflicts as part of the rule.[1][8][11] |
| Highway multiplicity and competing asymptotics | A generalized rule can support many distinct highways; recent work also finds highway and non-highway asymptotics for one rule under different finite starts | branching highway vocabularies and transition-dependent morphology | use as a warning against classifying a rule from one seed or one highway.[14][15] |
| Graph and non-square ants | Rule transferred to bi-regular graphs or grids with different turn groups | separates lattice connectivity from local rule and expands crystalline morphology | use graph-port frames; do not call one hex/graph convention canonical.[12][13] |
| Hamann 3D ants | One published cubic formalism: heading + working plane; `L/R/U/D`; three or more turn letters required for nontrivial 3D motion | planar triangle construction, short- and very-long-period highways, compact near-spherical occupation | exact mandatory historical baseline; not the uniquely canonical 3D ant.[2] |
| n-dimensional “Langton’s flies” | Two systematic nD formulations; some rules collapse to diagonal planes, others use the full space | gives us a principled planarity test and warns that “3D coordinates” may still yield 2D behavior | exact representative rules once full transition tables are extracted.[3] |
| Many-dimensional Lorentz/rotator models | Moving particle reads and changes local scatterers in arbitrary dimension | vortex sheets, reversibility, obstacle-memory and confinement | adjacent canonical branch; keep separate from ant-orientation models.[4] |
| Alternative grids and lattices | triangular, hexagonal, cubic and higher-dimensional Turing-machine/turmite searches | changes rotational group, local valence, symmetry and reachable morphology | square/hex 2D controls; cubic first; BCC/tetrahedral only after cubic replay.[5] |
| Paterson’s worms / edge-memory walkers | Rule depends on previously traversed edges around a triangular-grid vertex | self-avoiding filaments and fossil-like trail grammar rather than painted cells | one 3D edge-state branch; label as worm-derived rather than a Langton invention.[9] |
| Boundaries and topology | walls, reflective edges, toroidal domains; source reports deflection and erasure | recurrence, self-erasing highways, trapped loops | test only after infinite sparse-lattice baselines.[1] |
| Splitting / annihilating turmites | transition can spawn more than one direction; meetings can annihilate | branching fronts, territorial cancellation, particle-like events | later experimental branch; not novel as a general mechanism.[5] |

This is intended as a comprehensive **family-level** audit, not a claim that every hobby implementation or every rule string has been enumerated. The registry should remain open as new sources appear.

## Historical 3D rules to reproduce first

Use Hamann’s exact update order and orientation semantics before any Studio variants.[2]

| Rule | Reported behavior | Why test it |
|---|---|---|
| `RLU` | short-rule 3D highway; resource class 1, period-length class 3 | smallest clean 3D receipt |
| `RUL` and `RUD` | short-rule 3D highways in a different period class | checks symmetry reduction and frame implementation |
| `RRLU` | period 32 | easy exact periodicity assertion |
| `RLRU` | period 22 | second short regression rule |
| `RLUD` | period 32, different class from `RRLU` | same period, different spatial morphology |
| `RRLDDDULRRLLLL` | plane-by-plane triangle construction; class 0 | strongest known architectural silhouette |
| `RLRUUUL` | reported highway period 25,436 | long-period volumetric braid candidate |
| `RRRULL` | compact, nearly spherical occupation even after extremely long simulation | strongest cavity/shell/density candidate; use staged budgets |

Do not infer correctness from a visually plausible voxel trail. Each receipt must assert positions, orientations, state counts and detected translation period against the paper’s reported short-rule cases.

## Bounded test programme

### Gate A — source-faithful receipts

1. Reproduce the Wolfram 2D multi-ant baseline: sequential and simultaneous stepping, shared field, open/reflective/toroidal boundaries and square/triangular/hexagonal tilings.[1]
2. Reproduce Hamann’s cubic 3D frame exactly, including the working-plane change under `U/D`.[2]
3. Run the eight historical 3D rules above on a sparse unbounded lattice.
4. Add a planarity detector before visual ranking. A path occupying 3D coordinates can still be dynamically confined to a plane, a central issue in the nD literature.[3][4]

### Gate B — known offshoots lifted to 3D

Test one axis at a time against a frozen Hamann control:

- 3–5 cyclic field states;
- full 3D turmites with 2 internal states × 2–3 field states;
- 2, 4 and 8 ants sharing one field;
- ordered, synchronous-read/transactional-write and independently clocked updates;
- open, reflective and 3-torus boundaries;
- cell-memory versus edge-memory;
- cubic first, then one higher-valence lattice.

### Gate C — Studio-composed hypotheses

These are proposed combinations, **not novelty claims** until a rule-level search is complete:

1. **Collision transducers:** same-voxel arrivals deterministically change both ant state and field state instead of merely resolving movement order.
2. **Lineage-gated rewriting:** ants read a scalar field state plus “self/other” provenance, allowing territorial boundaries without baked colour.
3. **Reversible excavation:** state cycle `0 → 0.5 → 1 → 0` alternates deposition, hardening and erasure, scored for cavities and self-sealing tunnels.
4. **Frame-writing voxels:** a voxel stores a local orientation transform that rotates later walkers; this is closer to a 3D rotator medium than a classic colour ant and must be compared to Lorentz/rotator prior art.[4]
5. **Topology-conditioned collisions:** ant–ant interactions depend on local trail degree or recurrence count, aiming for junctions and membrane-like sheets.
6. **Chiral paired colonies:** mirrored rule tables share the same field and can bind, cancel or braid; compare against ordinary multi-ant interference before promotion.

## Search budget and scoring

Use staged deterministic budgets per rule: `2^10`, `2^14`, `2^18`, then `2^22` steps only for survivors. Longer landmark runs require checkpointing and a separate wall-time approval. Deduplicate rotational/reflection symmetries before simulation.

Preserve per-step trajectory and sparse field history sufficient to derive:

- replay hash and first divergence;
- unique cells, revisit/write/erase rates and bounding-box growth;
- PCA dimensionality / distance from best-fit plane;
- translation-period and highway-vector candidates;
- connected components, branch degree and loop count;
- occupancy, age, recurrence, lineage and collision density;
- later: tunnel/cavity topology on shortlisted volumes.

Visual ranking is downstream of deterministic receipts. Neutral previews should expose trajectory tubes, occupied-state volume, age/recurrence and lineage as separate attributes; semantic field values remain scalar indices (`0`, `0.5`, `1`) for editable shader palettes.

## Promotion shortlist before any novel sweep

1. Hamann `RRLDDDULRRLLLL` — architectural planar triangles stacked through volume.
2. Hamann `RLRUUUL` — long-period braided highway.
3. Hamann `RRRULL` — compact near-spherical density/cavity field.
4. A genuinely full-space Dorbec–Gajardo rule — guards against accidental planarization.
5. 3D two-state turmite — internal-state spirals/frames lifted into volume.
6. Multi-ant transactional collisions — closest to the Study’s shared-memory thesis.
7. Reversible excavation — clearest Studio-composed route to cavities and self-erasure.

The first three are historical controls, not original directions. A promoted Study behavior should visibly exceed or meaningfully recombine them rather than rediscover them.

## Sources

[1] https://community.wolfram.com/groups/-/m/t/3782476 — Understanding and analyzing deeper Langton’s Ant
[2] https://www.complex-systems.com/abstracts/v14_i03_a04 — Definition and Behavior of Langton's Ant in Three Dimensions (Hamann, 2003)
[3] https://doi.org/10.1088/1751-8113/41/40/405101 — Langton's flies (Dorbec & Gajardo, 2008)
[4] https://doi.org/10.1142/S0218127496000618 — Many-Dimensional Lorentz Cellular Automata and Turing Machines (Bunimovich, 1996)
[5] https://github.com/GollyGang/ruletablerepository/wiki/TwoDimensionalTuringMachines — Rule Table Repository: multidimensional Turing machines and turmites
[6] https://arxiv.org/abs/math/9501233 — Further Travels with My Ant (Gale et al., 1995)
[8] https://infoscience.epfl.ch/record/28501 — Behaviour of Multiple Generalized Langton's Ants (Beuret & Tomassini)
[9] https://dspace.mit.edu/bitstream/handle/1721.1/6210/AIM-290.pdf — Paterson's Worms (Beeler, 1973)
[10] https://deepblue.lib.umich.edu/bitstream/2027.42/26022/1/0000093.pdf — Studying Artificial Life with Cellular Automata (Langton, 1986)
[11] https://doi.org/10.25088/ComplexSystems.21.3.165 — Robustness of Multi-agent Turmite Models (Belgacem & Fatès, 2012)
[12] https://doi.org/10.46298/dmtcs.2312 — A Symbolic Projection of Langton's Ant (Gajardo, 2003)
[13] https://doi.org/10.3390/a4010001 — Repeatable Configurations of Generalized Langton Ant (Tsukiji & Hagiwara, 2011)
[14] https://arxiv.org/abs/2409.10124 — Ants on the Highway (Gajardo, Lutfalla & Rao)
[15] https://arxiv.org/abs/2505.05426 — Sideways on the Highways (Lutfalla)
