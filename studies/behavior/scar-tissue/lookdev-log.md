# Scar Tissue look development log

## 2026-08-12 — First independent visual-language probes

**Fixed source:** promoted Behavior component `component-behavior-b3bcc837c3e2`, using
the final state of the approved directional-refractory v3 evidence. Behavior parameters,
palette semantics, camera, and composition were not varied.

Three deliberately different host-side probes were generated:

- **Fibrous memory:** direction vectors become fine filament bundles. It exposes local
  orientation most directly, but is currently too thin and sparse to communicate field
  strength or depth without motion/material development.
- **Etched substrate:** scalar memory becomes recessed relief in a pale physical surface.
  It gives the field convincing material continuity, but soft filtering loses some local
  direction and makes the diagnostic resolution visible.
- **Membrane stress:** scalar gradients produce luminous stress folds while idle occupied
  sites create cellular rings. It best suggests an active living surface, though the ring
  overlay currently competes with the continuous field and risks reading as decoration.

The probes are visibly and conceptually distinct; none is selected or promoted yet.
Outputs are under `work/studio/lookdev/scar-tissue-directional-refractory-v1/` and each
still has a completed Look experiment plus verified artifact record.

## 2026-08-12 — Memory grid, direction hairs, and chrome agents

KC proposed retaining the diagnostic grid as physical structure. A Houdini/Karma motion
probe now instances a beveled cube at every field cell, maps scalar memory to cube height,
raises a curved hair above reinforced cells in the stored direction, and places chrome
agent spheres plus short trails on a separate layer above the field. Materials remain
neutral so this is still Look Development rather than Chromatic or Cinematography work.

The mapping is legible in motion and gives every simulation value a physical role. Current
presentation limitations are bright trails competing with hairs, a nearly monochrome
chrome response, and black corner wedges from the first technical framing. Outputs are
under `work/studio/lookdev/scar-tissue-grid-hairs-motion-v1/`.

**v2 refinement:** Trails are thinner and darker, with a smaller sphere marking the old
endpoint as well as the chrome current agent. Hairs rise close to the agent layer, cube
height uses smoothstep easing, and an oversized ground slab removes exposed frame corners.
The paired endpoints reduce the single-headed biological reading, although dense regions
still need hierarchy work: agents remain bright and long hairs can visually merge with
short trails. Outputs are under `work/studio/lookdev/scar-tissue-grid-hairs-motion-v2/`.

**v3 trail hierarchy:** Increased trail radius from 0.006 to 0.01 and assigned the same
bright low-roughness chrome as the current agent heads. Trails now separate clearly from
the thinner matte direction hairs and read as one agent system with the endpoint spheres.
They are intentionally prominent again without hiding the cube topography. Outputs are
under `work/studio/lookdev/scar-tissue-grid-hairs-motion-v3/`.

**v4 temporal refinement:** Both trail endpoints now use the same sphere scale, while
trail radius is reduced from 0.01 to 0.008. Direction hairs use a twelve-frame exponential
history for memory strength and direction, so their growth and turning lag the raw field
rather than snapping to each sampled state. Outputs are under
`work/studio/lookdev/scar-tissue-grid-hairs-motion-v4/`.

**v5 scale probe:** Reduced both trail endpoint sphere scales to 0.015 and trail radius
to 0.004. The head position was corrected from Y 0.94 to the trail plane at Y 0.90;
head, tail, and trail now share one chrome material assignment. A single frame-150 probe
is under `work/studio/lookdev/scar-tissue-grid-hairs-scale-probe-v5/`.

**v6 bend probe:** Increased maximum directional hair lean to 0.58 and changed each hair
to a five-point curve whose lateral displacement follows `t^2.2`. Roots remain nearly
vertical while most directional bending occurs toward the tip. A single frame-150 probe
is under `work/studio/lookdev/scar-tissue-grid-hairs-bend-probe-v6/`.

**Selected and promoted:** KC approved v6 as the structural Look. The canonical private
package is `work/jobs/scar-tissue-look-memory-grid-v6/lookdev/scar-tissue-look-memory-grid-v6.zip`
and the promoted component is `component-look-6013004ba32c`. This promotion freezes the
memory-grid relief, eased tip-bending hairs, and centered shared-chrome agent segments;
palette, final lighting, and cinematography remain separate future decisions.

**Chromatic selection:** the approved Bioluminal Depth v7 mapping uses semantic field state
rather than a global tint: dormant cells are blue-slate, reinforced cells are electric blue,
and saturated cells are teal. `scar_value` modulates intensity, `scar_idle` dims older cells,
and a `t^2` vertical ramp holds cube bases at the floor colour while revealing state toward
their tops. The peak channel is bounded at `0.95`. The verified package was promoted as the
private Palette component `component-palette-a52433fdb147`; camera and lighting remain
unselected.