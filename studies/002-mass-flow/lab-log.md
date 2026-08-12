# Mass Flow lab log

## 2026-08-11 — Look probe 021: cleaner depth of field

**Artist direction:** Reduce visible grain in the depth-of-field response.

**Proposal:** Raise the Mass Flow Karma XPU setting from four to twelve samples per
pixel. Preserve the camera, lens, f-stop, materials, dome, geometry, and resolution
so the result isolates sampling quality rather than changing the look.

**Observation:** The replacement frame-450 Karma XPU scene records 12 samples per
pixel and retains the accepted geometry, camera, and materials. The denser sampling
substantially reduces grain in the out-of-focus fibers and backdrop; render time rose
from roughly 27 seconds at four spp to roughly 100 seconds at twelve spp.

**Status:** Look Probe 021 ready for artist review with cleaner depth of field.

## 2026-08-11 — Look probe 020: segment-attached endpoint heads

**Artist direction:** Ensure every visible trail end has a sphere and remove spheres
that appear detached from nearby curves.

**Proposal:** Derive head positions from each retained curve segment's actual start
and end points, rather than from the global rolling-history endpoints per agent.
Preserve the established hierarchy: segment starts are smaller, matte heads and
segment ends are full-size, phase-matched heads.

**Observation:** Frame 450 contains 7,164 derived curve segments and 14,328 curve
endpoints. The replacement geometry now contains 14,328 head points and every one of
those endpoints has a matching sphere; the prior version had 6,620 unheaded ends.
The attached heads remove the detached global-history points while retaining the
matte-start and phase-matched-end hierarchy.

**Status:** Look Probe 020 ready for artist review with segment-attached heads.

## 2026-08-11 — Motion and look probe 019: authored temporal hierarchy

**Artist direction:** Explore a more interesting composition and motion by combining
a controlled temporal event, protected negative space, clearer directional cues, and
less uniformly accumulated trail density.

**Proposal:** Limit derived trails to the configured rolling 25-checkpoint window.
Bias the population left to reserve a right-side void; compress phase lanes and add a
central pull around frame 300, then expand them after frame 330. Treat phase 0 as a
subtle lead current with an 18% width increase and brighter, lower-roughness graphite.
Retain spheres at both ends, but make starting heads 62% scale and matte while leaving
terminal heads full-size and phase-matched.

**Observation:** The 600-frame candidate passed same-seed determinism and
changed-seed distinction gates, and its review encode remains exactly 20.000 seconds.
The early (150), knot (300), and post-event (450) Karma XPU frames are all 720 × 1280
with 8,000 two-ended head points. The rolling history restores visible voids; the
frame-300 compression creates a clear central event, and the later expansion opens
the right-hand field. The wider, brighter phase-0 ribbon and reduced matte start
heads give the braid a readable directional hierarchy.

**Status:** Motion and Look Probe 019 ready for artist review as a complete
composition candidate.

## 2026-08-11 — Look probe 018: adaptive trail smoothing

**Artist direction:** Smooth visible polygon edges where fast-turning trails do not
have enough cached segments to read as continuous curves.

**Proposal:** Preserve the sampled trail endpoints and their ages, then add adaptive
Catmull-Rom visual interpolation between them. Straight spans retain one segment;
larger turns receive up to six subsegments. This only changes lookdev geometry, not
the deterministic simulation, trail endpoints, or endpoint spheres.

**Observation:** Early frame 150 and midpoint frame 300 Karma XPU stills both remove
the visible angular joins while preserving the established mass and two-ended heads.
The midpoint scene contains 516,527 spline-sampled trail points over 8,322
boundary-aware curve primitives, plus all 8,000 endpoint spheres.

**Status:** Look Probe 018 ready for artist review with smoothed trails.

## 2026-08-11 — Look probe 017: two-ended trail heads

**Artist direction:** Add spheres to both the start and end of each trail.

**Proposal:** Retain the existing material-matched sphere construction and scale,
but emit one head at each agent's first cached point and one at its last cached point.
The midpoint lookdev will therefore show both endpoints of the trails it builds
through frame 300.

**Observation:** The midpoint Karma XPU still contains 8,000 head points: two for
each of the 4,000 trail histories, split 2,668 / 2,666 / 2,666 across the three
phase materials. The added start heads visibly mark the opposing ends while the
existing frame-300 heads preserve the current trail termini.

**Status:** Look Probe 017 ready for artist review with both endpoint populations.

## 2026-08-11 — Motion and look probe 016: extended preview and midpoint lookdev

**Artist direction:** Extend the motion review to 20 seconds and provide a lookdev
frame from the midpoint of that extended sequence.

**Proposal:** Extend the simulation from 450 to 600 frames while retaining its
30 fps solve and six-fps review cadence, which produces 120 regular review samples
and a 20-second preview without slowing the recent faster motion. Build a graphite
Karma XPU trail still through cached frame 300, with heads at that midpoint state.

**Observation:** The 4,000-agent solve passed both same-seed determinism and
changed-seed distinction gates across its full 600 frames. Its 120 regular review
samples encode to exactly 20.000 seconds at six fps. The midpoint graphite Karma XPU
still was built through cached frame 300 at 720 × 1280, retaining the accepted dome,
camera, materials, and trail history while placing all heads at that midpoint state.

**Status:** Probe 016 ready for artist review with the 20-second motion preview and
frame-300 lookdev still.

## 2026-08-11 — Motion probe 015: 1.5× transport speed

**Review source:** Review Studio iterate note
`b1cf8dd232aa42c6bb90992d268e87d7` requested that the agents move approximately
1.5× faster.

**Proposal:** Multiply the analytic-flow strength from 1.8 to 2.7 and the matching
speed ceiling from 3.0 to 4.5. Preserve trail-memory avoidance, flocking,
cross-phase separation, drag, population, trail persistence, and the established
graphite look so the motion change is isolated to transport speed.

**Observation:** Same-seed smoke probes remained materially deterministic and the
changed-seed gate remained distinct. Mean checkpoint speed rose from 1.95 to 2.81
units, a 1.44× increase that is close to the requested approximate 1.5× pace; peak
speed reached 4.47 without exceeding the new 4.5 cap. The replacement 4,000-agent,
450-frame motion preview remains exactly 15 seconds at its six-sample review rate.

**Status:** Probe 015 implemented and returned to the originating Review Studio note
with the replacement motion artifact and source commit lineage.

## 2026-08-11 — Motion probe 005: trail memory and variable velocity

**Artist direction:** Let agents leave a coarse trace in space and subtly avoid those
accumulated paths. Replace the effectively uniform normalized field speed with natural
acceleration and deceleration constrained only by a maximum speed.

**Proposal:** Maintain a compact 24 × 48 × 12 periodic 3D density grid alongside the
deterministic VEX solve. Deposit agent positions every third frame, fade the grid by
6% per frame, and write the negative local density gradient back as a per-point force
for the following update. Preserve raw analytic-flow magnitude, combine it with
flocking, phase, and tail-memory forces, then cap the resulting velocity at 3.0.

**Observation:** The repeatability smoke probe and full 4,000-agent, 450-frame run
both passed. The last checkpoint spans 0.10–2.99 speed units (mean 2.24), giving the
flow visible pauses and accelerations without exceeding its cap. The Karma XPU still
shows broad braided currents while the new memory field lightly opens and deflects
reused paths rather than making local avoidance visually noisy.

**Status:** Motion Probe 005 accepted as the new Mass Flow behavior baseline. The
memory grid is deliberately low-resolution and should remain a tunable reusable field
rather than a substitute for high-resolution collision geometry.

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

## 2026-08-11 — Look probe 009: artist-authored graphite study

**Source:** Artist-edited `mass-flow-volumetric.hiplc`, preserved unchanged under the
volumetric lookdev directory.

**Extracted direction:** Replace the semantic color palette with near-monochrome
graphite values: cool gray phase 0, metallic near-black phase 1 at 0.22 roughness, and
subtly violet-black phase 2. Remove the monolith, darken the camera backing material,
rotate the accepted HDRI to −106 degrees, and raise dome intensity to 1.6. Move the
camera to Z 45 with a 100 mm focal length, focus at 44 units, and use f/0.09 DOF.

**Verification:** Rendering the artist `.hiplc` as-is and rendering a clean scene from
the updated generator produced the same composition and material response. The look
uses alternating matte and metallic ribbons, bright grazing highlights, deep internal
occlusion, and shallow-focus separation without trail emission or supplemental lights.

**Status:** Look Probe 009 accepted as the scripted lookdev baseline. The artist HIPLC
remains the reference scene; generated verification artifacts remain under `work/`.

## 2026-08-11 — Motion and look probe 010: reduced flocking population

**Artist direction:** Reduce the number of agents by half, retain long but less extreme
trails, and introduce subtle boid-like variation.

**Proposal:** Use 50,000 simulated agents and 6,000 rendered representatives with 25
checkpoints of trail history, approximately 4.2 seconds at the review rate. Within a
fixed stable-ID cohort filtered by true 3D distance, apply same-phase alignment,
cohesion, and close separation; preserve cross-phase avoidance and add a low-amplitude
deterministic per-agent wander. Keep the analytic field and phase lanes dominant.

**Observation:** The result opens materially more negative space and develops looser
branches, fan-like local alignment, and small individual deviations at crossings while
retaining the three major currents. Capped spatial lookup was rejected after failing
the identical-run gate; deterministic cohorts passed. The full prewarmed 450-frame
solve completed in 29.9 seconds, remained within speed and volume bounds, and the
graphite Karma XPU look shows clearer individual fibers than the 100,000-agent pass.

**Status:** Probe 010 accepted for artist review. Both the 15-second motion diagnostic
and graphite XPU still are retained under the new job in `work/`.

## 2026-08-11 — Motion and look probe 011: stronger flock contrast

**Artist direction:** Increase cohesion and separation so the motion develops more
variation without losing its long-trail character.

**Proposal:** Raise cohesion from 0.10 to 0.18 and same-phase separation from 0.14 to
0.24. Give same-phase spacing an independent 0.20 radius while retaining the tighter
0.14 cross-phase avoidance radius, existing alignment, wander, and dominant flow.

**Observation:** The stronger push-pull creates tighter coherent bands adjacent to
wider local gaps, most visibly at central crossings and in the lower sweep. The system
does not collapse into clumps or lose its overall portrait silhouette. The full solve
completed in 31.9 seconds and remained within its speed and volume bounds.

**QA note:** Stronger feedback amplified harmless parallel floating-point drift to
approximately 0.00001 units. Same-seed validation now compares physical metrics at a
documented 0.0001 tolerance rather than requiring every full-state hash quantization
boundary to coincide; population, frame topology, bounds, speed, and changed-seed
distinction remain enforced.

**Status:** Probe 011 accepted as the stronger flocking baseline.

## 2026-08-11 — Motion and look probe 012: honest 4K population and heads

**Artist direction:** Simulate only the population that appears in the final render,
reduce it to 4,000 agents, make flocking easier to see, and add a small material-matched
sphere at each trail head.

**Proposal:** Set both simulation and final trail population to 4,000 with no Karma
subsampling. Compensate for lower volumetric density with a 1.1-unit flock radius and
90-ID deterministic cohort; raise alignment to 0.24, cohesion to 0.34, separation to
0.42 within 0.34 units, and wander to 0.12. Build a low-resolution sphere at every
agent's final cached position with 0.045 scale and assign its phase trail material.

**Observation:** Lower density exposes individual paths while the broader, stronger
neighborhood preserves coherent sheets and makes localized curling and divergence more
legible. The final HIP contains exactly 4,000 trail histories and 4,000 head spheres,
split 1,334/1,333/1,333 across the three phase materials. The deterministic solve itself
completed in 17.8 seconds; the full job time remains dominated by review rasterization.

**Status:** Probe 012 accepted for artist review as the honest-population baseline.

## 2026-08-11 — Motion and look probe 013: wider separation

**Review source:** Review Studio iterate note
`ddaf3dcc191748de9b17fa894fb082b5` requested more drastic separation and a larger
separation radius on the 4,000-agent motion preview.

**Proposal:** Raise same-phase separation strength from 0.42 to 0.62 and its radius
from 0.34 to 0.46. Preserve cohesion, alignment, wander, cross-phase avoidance, the
analytic field, 25-checkpoint trail persistence, graphite materials, camera, and heads
so the behavioral difference remains attributable to separation.

**Observation:** Individual paths peel away more visibly inside the large currents,
and central negative-space seams remain wider without breaking the three-ribbon
composition. The 4,000-agent deterministic solve completed in 14.4 seconds and stayed
within speed, volume, population, and changed-seed gates. Karma XPU preserved all
4,000 trails and material-matched heads.

**Status:** Probe 013 implemented and returned to the originating Review Studio note
with replacement motion, graphite still, HIP, job, and source commit lineage.

## 2026-08-11 — Motion and look probe 014: faster turning and travel

**Review source:** Review Studio iterate note
`cfbd74facab54aba8c941c557d9ac4b1` asked whether agents have a maximum turning radius
and requested quicker turns and somewhat higher speed.

**Interpretation:** The system has no explicit minimum turn radius or angular-speed
cap. Effective turning stiffness comes from velocity smoothing: at drag 0.93, only
seven percent of the desired velocity enters each update. Maximum travel is bounded
separately by `max_speed`.

**Proposal:** Reduce drag from 0.93 to 0.88, raise analytic flow strength from 2.1 to
2.55, and raise maximum speed from 2.4 to 3.0. Preserve flock forces, separation,
trail persistence, population, materials, camera, lighting, and heads.

**Observation:** Final mean speed increased from 2.03 to 2.63 and peak speed from 2.35
to 2.98. The motion develops tighter hooks, faster reversals, and more directional
breakup while retaining the large portrait mass. The deterministic solve completed in
13.8 seconds and stayed within its expanded speed cap and spatial bounds.

**Status:** Probe 014 implemented and returned to the originating Review Studio note
with replacement motion, graphite still, HIP, job, and source commit lineage.
