# Mass Flow lab log

## 2026-08-11 — Probe 001: stratified currents

**Hypothesis:** A very large population can read as a small number of authored currents
if initialization and phase forces establish hierarchy before local detail is added.

**Proposal:** Initialize three interleaved low-discrepancy populations across a portrait
domain, advect them through an O(N) analytic vector field, and apply weak phase-specific
attractors. Cache only measured checkpoints and a deterministic review subset during
the first scale test.

**Artistic gate:** The result should read as layered flow with distinct quiet and dense
regions, not uniform noise or a benchmark cloud.

**Observation:** Three broad populations remain visually distinct while repeatedly
braiding, narrowing, and opening large negative spaces. The deterministic sampling
reveals some comb-like microstructure, but at composition scale the system reads as
layered currents rather than a uniform benchmark cloud. The full 60-frame run retained
all 100,000 agents, stayed within bounds and speed limits, reached approximately 2.08
million agent-frames per second, and used 27.9 MB for bounded checkpoint state.

**Status:** Probe 001 accepted as the Phase 2 scale-and-motion foundation. Preserve
the three-current composition for the first MaterialX and Karma presentation tests.

## 2026-08-11 — Look probe 001: derived trails

**Artist direction:** Use derived trails as the first presentation of the accepted
mass-flow motion.

**Proposal:** Connect each deterministic review representative across the seven
checkpoint states, split trajectories at folded domain boundaries, fade older
segments, and retain a brighter current-position bead. Keep phase color semantic for
this diagnostic proposal before translating the accepted structure into Karma curves.

**Observation:** The trails reveal a substantially richer structure than the point
view: broad woven sheets tighten into hair-like fans, cross as three colored braids,
and preserve large black voids between masses. At 12,000 representatives the image is
deliberately dense and fibrous; a Karma translation can either preserve that textile
weight or importance-select fewer trajectories for a more sculptural reading.

**Status:** Look Probe 001 ready for artist review before Karma curve translation.

## 2026-08-11 — Look probe 002: Karma mineral fibers

**Proposal:** Translate all 12,000 representative histories into real Houdini polygon
curves with age-weighted width, preserve boundary splits, separate phases into three
Solaris imports, and shade them with restrained cyan mineral, oxidized orange, and
deep violet MaterialX fibers. Use a low-emission response and a single soft rim so
overlapping curves retain texture instead of clipping into flat light.

**Observation:** The first high-emission pass overexposed the dense crossings. Reducing
emission and deepening the base colors restored individual strands, layered occlusion,
and textile-like weight while preserving the broad braided composition.

**Status:** Look Probe 002 ready for artist review. Next test should compare this full
fiber mass against an importance-selected hero-curve layer with a softer derived body.

## 2026-08-11 — Look probe 003: monolith and HDRI environment

**Artist direction:** Add a large shape behind the simulation and use the available
HDRI collection for higher-quality environmental lighting. Proceed through routine
look variants autonomously.

**Proposal:** Place a shallow, oversized dark mineral ellipsoid behind the trail plane
as a non-interacting sculptural monolith. Compare three 4K EXR dome environments from
the local library with recorded rotations: `studio_small_03`, `skylit_garage`, and
`colorful_studio`.

**Observation:** `studio_small_03` produced the clearest fiber separation, a controlled
cool edge on cyan, useful warmth on the oxidized phase, and the most legible beveled
backdrop. `skylit_garage` was restrained but too flat and dark; `colorful_studio`
introduced attractive warmth but reduced semantic phase separation.

**Status:** Look Probe 003 accepted with `studio_small_03_4k.exr` at 25 degrees as the
current environment. The HDRI remains a local dependency supplied at render time and
is not copied into the repository.

## 2026-08-11 — Look probe 004: Karma XPU parity

**Proposal:** Render the accepted monolith, fibers, HDRI, camera, resolution, and
four-sample settings unchanged through Karma CPU and Karma XPU. Compare visual parity,
cold construction cost, and repeated render time before changing the default.

**Observation:** XPU preserved the look and produced visibly cleaner dense fibers and
backdrop shading at the same sample count. Loading the generated HIP and rendering
twice measured 14.3 and 14.1 seconds with XPU versus 32.3 and 29.8 seconds with CPU,
approximately a 2.2x steady-state speedup. The initial XPU scene-build invocation was
slow, confirming that production should build once and render many frames per process.

**Status:** Karma XPU accepted as the default Mass Flow renderer. Karma CPU remains an
explicit compatibility fallback through `--renderer cpu`.

## 2026-08-11 — Motion preview 001: 15-second flow study

**Proposal:** Extend the accepted deterministic simulation to 450 frames at 30 fps,
capture state every five frames, and encode a lightweight portrait motion review at
six samples per second. Display 3,000 deterministic representatives with short rolling
derived trails so the large-scale rhythm can be judged before a full Karma sequence.

**Observation:** The complete 100,000-agent run produced 90 regular checkpoints after
the seed state. They encode to exactly 15 seconds at 720 × 1280 and preserve the three
phase populations, folded boundaries, dense crossings, and shifting negative space.

**Status:** Motion Preview 001 ready for artist review. This is a simulation-faithful
review encode, not the final Karma XPU render.

## 2026-08-11 — Motion preview 002: cross-phase avoidance

**Artist direction:** Let agents subtly avoid nearby agents belonging to the other
two color groups while preserving the established mass-flow composition.

**Proposal:** For each agent, inspect six stable IDs on either side, discard same-phase
and spatially distant candidates, and average a distance-weighted separation force
within 0.14 units. Add the resulting 0.16-strength force beneath the dominant 2.1
analytic flow. Read neighbors from a separate frozen input to keep parallel VEX
evaluation deterministic.

**Observation:** The 100,000-agent, 450-frame run remains visually faithful to the
accepted braid while opening fine seams where differently colored sheets meet. Exact
same-seed smoke runs match, peak speed remains below the 2.4 cap, and the full solve
completed in 48.6 seconds at approximately 0.92 million agent-frames per second.

**Status:** Motion Preview 002 accepted as a subtle interaction variant and ready for
artist review. The capped deterministic neighborhood preserves useful scale, although
it is approximately twice as expensive as the field-only update.

## 2026-08-11 — Motion preview 003: preroll and long persistence

**Artist direction:** Prewarm the system by 30 frames and make the visible trails ten
times longer.

**Proposal:** Advance the complete interaction model through 30 hidden frames before
recording visible frame 1. Alternate two bounded preroll caches so every VEX update
reads immutable prior state. Increase rolling review history from five checkpoints to
50, equivalent to approximately 8.3 seconds at the six-sample review rate.

**Observation:** The preroll removes the visibly initialized opening state. Long
persistence transforms isolated ribbons into broad woven surfaces and exposes much
more of the orbital structure, with intentionally heavier color overlap and less
negative space. The deterministic 100,000-agent solve completed 479 total updates in
64.1 seconds; the exact 15-second preview contains 90 frames.

**Status:** Motion Preview 003 ready for artist review as the maximal-persistence
variant. Retain the five-checkpoint setting as the lighter comparison look.

## 2026-08-11 — Look probe 005: camera-relative white field

**Artist direction:** Add a large white background well behind the simulation, using
the familiar camera-parented grid approach so it continues to cover the frame.

**Proposal:** Add a 16 × 28.5 unit, 0.04-deep backing card at Z −3 behind the trail
plane and monolith. Match the fixed portrait camera orientation and give the card
generous overscan, making it camera-relative in practice while retaining a simple SOP
and Solaris import. Shade it with a 0.92 neutral-white, high-roughness MaterialX
surface and retain the accepted studio HDRI.

**Observation:** Karma XPU confirms full edge-to-edge coverage at 720 × 1280. The card
reads as a softly lit near-white studio field; the existing monolith produces a broad
right-side shadow, and the cyan, orange, and violet long-persistence ribbons remain
distinct against the brighter ground.

**Status:** Look Probe 005 ready for artist review. The generated HIP and PNG remain
under the job's `work/` lookdev directory and are not tracked by Git.

## 2026-08-11 — Look probe 006: dome-only trail lighting

**Artist direction:** Remove emission from the trail materials.

**Observation:** Setting MaterialX emission to zero leaves the established palette
and composition nearly unchanged at the prior low emission level, while making the
accepted `studio_small_03` dome the sole illumination source. Trail shading now comes
entirely from base response, rough specular reflection, occlusion, and shadow.

**Status:** Look Probe 006 accepted as the physically lit material baseline.

## 2026-08-11 — Look probe 007: volumetric Mass Flow

**Artist direction:** Convert the planar simulation to 3D so the dome environment can
produce meaningful lighting, depth, and occlusion.

**Proposal:** Preserve the nine-by-sixteen portrait domain while adding four units of
bounded depth. Seed agents along phase-offset depth waves, add an animated Z component
to the analytic field, pull each phase toward its own moving depth lane, evaluate
cross-phase separation in full 3D, and fold escaped agents across the Z boundary.

**Observation:** The front composition remains recognizable, but ribbons now separate
through real parallax and occlusion and present varied orientation to the HDRI instead
of remaining coplanar. The final state spans Z −2.000 to 1.996, remains within the 2.4
speed cap, and completed the deterministic 100,000-agent solve at approximately 1.01
million agent-frames per second. The no-emission Karma XPU render completed against
the existing white card and accepted dome.

**Status:** Look Probe 007 accepted as the new volumetric baseline. The 2D review
encode remains an orthographic XY motion diagnostic; Karma carries the authored depth.

## 2026-08-11 — Look probe 008: volumetric handoff correction

**QA finding:** Artist inspection revealed that Look Probe 007's generated HIP was
still planar despite the simulation's valid Z metrics. The derived-trail builder was
explicitly reconstructing cached positions as `(x, y, 0)` and discarding Z before the
SOP and Solaris stages; the initial render therefore did not validate the intended
volumetric handoff.

**Correction:** Preserve the cached Z component when constructing every trail point
and fail the build if a study with configured depth produces less than ten percent of
that depth in its trail bounds.

**Verification:** The corrected HIP contains 1,137,239 trail points spanning Z −1.99998
to 1.99999, nearly the complete four-unit domain. The replacement XPU render now shows
strong depth layering, occlusion, curved surface response, and HDRI-driven contrast.

**Status:** Look Probe 008 supersedes the invalid Look Probe 007 HIP and render.
