# Study 004 — Visual prior-art boundary

Status: private working audit · companion to `PRIOR_ART_AND_TEST_MATRIX.md` · 2026-08-22

## The saturated look

The most occupied visual territory is now clear: **one ant writes coloured cubes on a cubic lattice while an orbit camera watches a blocky mass accumulate**.

Public Three.js, OpenGL and Java/OpenGL implementations already cover that language.[16][17][18]

A WebGL/WASM example and a Blender/Python rendering study make the point stronger.[19][20]

Therefore the following do **not** constitute a distinctive Look direction:

- substituting polished, rounded, emissive or translucent cubes;
- adding fog or a more expensive renderer;
- orbiting a voxel sculpture after the simulation;
- using more cell colours without exposing different behavior;
- presenting one final occupied-state shell with no temporal anatomy.

Those treatments may be useful diagnostic receipts, but not promotable Look work.

## Less exhausted visual families

### 1. Highway anatomy rather than occupancy

Hamann’s published 3D examples include drifting highways, line-by-line planar triangles and very different pre-highway resource demands.[2] Recent generalized-ant work also shows that one rule can support many distinct highways and that highway and non-highway asymptotics may coexist.[14][15]

Promising representations:

- swept trajectory tubes with radius driven by recurrence;
- orientation ribbons whose torsion records the body frame;
- separated chaotic and periodic strata;
- translucent triangle sheets;
- sectional views through a highway bundle;
- a moving local frame rendered as three orthogonal filaments.

### 2. Shared-memory scars

Multiple-ant behavior is not determined by the individual ant rule alone. Peer-reviewed multi-turmite work treats synchronous/asynchronous scheduling and exclusion/conflict semantics as behaviorally significant.[11]

Promising representations:

- collision wounds and rewrite scars;
- ownership/lineage shown separately from semantic scalar state;
- temporal offsets between synchronous and asynchronous runs;
- trails visible only where another ant later rewrote them;
- merged, parasitized, blocked or erased highways;
- territorial interface sheets rather than uniformly coloured agents.

### 3. Full-space orientation-frame behavior

Dorbec and Gajardo distinguish velocity-only particles from “insects” carrying a full orthogonal body frame, and show that many apparently n-dimensional rules collapse to diagonal planes.[3]

Promising representations:

- frame ribbons and twisting triads;
- a planarity-to-volume transition made visible over time;
- separate curves for decision orientation and actual displacement;
- volumetric rules ranked against embedded-plane controls.

### 4. Topological seams

An informal multiple-ant project explores torus, Klein-bottle, projective-plane and folded-sphere identifications with finite-lived trails.[22] The mechanism is interesting only if seam crossings and orientation reversal remain visible.

Promising representations:

- paired parameter-space and embedded-surface views;
- ghost continuation across seams;
- seam scars and orientation flips;
- cut-open fundamental domains rather than unexplained teleportation.

### 5. Aperiodic substrates

Generalized ants on Penrose tilings already have a strong informal visual culture, including kaleidoscopic and recognizable fractal outcomes.[21] Repeating that mandala vocabulary would not be distinctive.

A better 3D translation would expose adjacency and hierarchy through:

- dual-graph cables;
- depth assigned by Penrose orientation class;
- inflation/deflation levels controlling tube scale;
- failed adjacency choices left as voids;
- non-periodic star directions revealed without a centered mandala.

### 6. Transient and continuous fieldwriting

The formal higher-dimensional sources remain lattice-based; this audit found no comparably canonical continuous Langton-ant family.[2][3] A continuous version should therefore be called **Langton-inspired**, not a standard ant variant.

Potential mechanisms:

- continuous heading steered by a deposited scalar field;
- finite-width VDB trails with decay, diffusion or erosion;
- local Frenet-frame turns;
- arbitrary-surface motion;
- anisotropic trail memory producing ribbons or vessels.

This is the cleanest route away from common voxel demonstrations, but it belongs after the exact lattice receipts so that the mutation remains legible.

### 7. Event and sound structure

A public 3D visualization/sonification sketch already establishes the broad idea of sonifying a 3D ant.[23] The stronger opportunity is not decorative sound but event-structural mapping:

- turn types as voices;
- collision chemistry as transient events;
- rewrite/erase operations as paired gestures;
- highway lock-in as rhythmic phase transition;
- spatialized voices by ant lineage.

## Visual test shortlist

The first Behavior previews should compare these representations on identical cached simulations:

1. **Diagnostic occupancy voxels** — intentionally plain, never promoted.
2. **Trajectory skeleton** — tubes plus recurrence/age attributes.
3. **Orientation-frame ribbon** — exposes yaw/pitch/roll or working-plane changes.
4. **Shared-memory scar volume** — rewrite, erasure, collision and lineage fields.
5. **Highway tomography** — cross-sections separating transient chaos from drift.
6. **Excavated topology** — cavities and tunnels from build/erase hypotheses.

All six must use neutral cameras and palette-independent semantic attributes. We should select behavior from structural differences, not from whichever preview receives the strongest lighting treatment.

## Sources

[2] https://www.complex-systems.com/abstracts/v14_i03_a04 — Definition and Behavior of Langton's Ant in Three Dimensions (Hamann, 2003)
[3] https://doi.org/10.1088/1751-8113/41/40/405101 — Langton's flies (Dorbec & Gajardo, 2008)
[11] https://doi.org/10.25088/ComplexSystems.21.3.165 — Robustness of Multi-agent Turmite Models (Belgacem & Fatès, 2012)
[14] https://arxiv.org/abs/2409.10124 — Ants on the Highway (Gajardo, Lutfalla & Rao)
[15] https://arxiv.org/abs/2505.05426 — Sideways on the Highways (Lutfalla)
[16] https://github.com/mauriciabad/Langton_Ant_3D — Mauricia Bad's Langton Ant 3D
[17] https://github.com/qJay44/Langtons-ant-3D — qJay44's Langton-ant-3D
[18] https://github.com/michalkolodziejski/java-ai-langton3d-opengl — Java/OpenGL 3D Langton Ant
[19] https://github.com/daka0522/langtonsAnt — WebGL/WASM Langton Ant 2D/3D
[20] https://github.com/deadSwank001/Langton-s_Ant_in_Bpy — Langton Ant in Blender Python
[21] https://github.com/ptiles/ant — Generalized Ants on Penrose Tilings
[22] https://github.com/nasqret/langton-sphere-sim — Langton Ants on Alternative Surface Topologies
[23] https://github.com/crashingbooth/3d-langton — 3D Langton Visualization and Sonification
