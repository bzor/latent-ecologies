# Studio process notes

Private observations captured during real-world use. Source records under `studio/notes/` are canonical.

## Working

- **2026-08-13T12:52:56Z · look / look · component-look-6013004ba32c**
  Conversational iterative look development using cheap one-frame probes made precise visual refinement fast and easy to evaluate.

- **2026-08-14T11:55:35Z · cinematography / cinematography**
  Collaborative cinematography handoffs should always separate artist framing from approved camera motion. Each semantic shot/view should expose a clearly named Stage-context parent or offset transform that can be adjusted while looking through the final camera in Solaris; subtle movement remains a relative layer. Controls default to identity or the approved framing, remain unkeyed, preserve cuts, and are grouped and documented in the Stage network.

- **2026-08-15T19:14:08Z · behavior / behavior · artifact-pilot-study-003-faithful-v1**
  The faithful 1,000-point VEX baseline passed the short-horizon parity tracer and the 240-step step-scaled tolerance. Long-horizon float32 drift is reported explicitly rather than described as exact numerical parity; graph indices remained identical and no VEX errors occurred.

- **2026-08-15T20:37:06Z · behavior / behavior · artifact-pilot-study-003-faithful-v1**
  KC review: the faithful Study 003 motion check works and looks very similar to Simon Woods's reference, though it feels less frenetic. Treat this as positive fidelity evidence and retain the energy difference for diagnosis before formal behavior promotion.

- **2026-08-16T13:22:53Z · behavior / workflow · experiment-study-003-affinity-cohort-100k-v1**
  Simulation pipeline decision: begin Behavior discovery and production scaling with agent-friendly external Python/Hython orchestration plus VEX-authoritative integration. This keeps deterministic graph/event receipts, automated verification, cache recovery, and batch execution simple. Treat an artist-editable Solver/HDA as an optional later packaging and handoff stage after behavior stabilizes—especially when sharing a HIP. Not every project requires an HDA; when one is warranted, expose proven controls first and add requested sliders or modes incrementally without replacing the verified batch backend.

## Pain points

- **2026-08-13T12:52:56Z · look / look · component-look-6013004ba32c**
  Static final-state Look probes were too basic to critique before the moving simulation elements and underlying memory field were explained.

- **2026-08-13T12:52:57Z · field-station / workflow · component-look-6013004ba32c**
  The canonical promotion path exposed lifecycle contradictions: decided artifacts became schema-invalid, and proposal creation did not advance the source Idea to the promotion-compatible state.

- **2026-08-13T13:01:03Z · field-station / workflow · component-look-6013004ba32c**
  probably the biggest pain point is just rooting through the directories trying to find each of the images/.mp4s to review. this will obviously be sorted once we have an interface, but thought I'd bring it up

- **2026-08-13T16:39:47Z · look / workflow · component-look-6013004ba32c**
  when I open the .hip files the nodes are all on top of each other, could use a quick cleanup/organization if possible

- **2026-08-31T16:31:18Z · behavior / behavior**
  behavior-stage renders drifted 'kind of all over the place in color and size'; adopted a postable standard: black and white as it's more about the behavior, CMYK colors if we need to differentiate things, postable 30fps 1080x1350 videos for eventual X posting. Shipped as houdini_ai.behavior_postable the same day.

## Missing functionality

- **2026-08-13T12:52:55Z · field-station / workflow · component-look-6013004ba32c**
  Create a lightweight way to capture what is working, pain points, questions, and desired functionality at each Studio step while the experience is fresh.

- **2026-08-13T12:57:55Z · behavior / probe**
  after the idea phase, I think you have this as the Probe phase, once the idea is promoted into the pipeline I'd like a brainstorming chat session picking various directions for the behaviour phase. so very different simulation ideas but within the umbrella of the idea. then we pick one or more of the directions to go into the behaviour lab, which actually simulates each of them in different ways (like what you did with scar tissue). so basically adding a brainstorming session in between the idea pick and the sim, to nail down what is actually being simulated (can be several that compete).

- **2026-08-13T13:02:27Z · look / look · component-look-6013004ba32c**
  also the look dev process should allow for both sweeping changes and small quick nitpicky iterative revisions (probably just on one frame)

- **2026-08-13T13:04:16Z · cinematography / workflow · component-look-6013004ba32c**
  and we should have a quick way to kick off a motion test, some sort of wireframe or flat shaded viewport render or some vary fast way to view motion. this can be in any phase that things are updated before rendering

- **2026-08-13T14:22:00Z · chromatic / chromatic · component-look-6013004ba32c**
  before starting the chromatic phase let's have a quick brainstorm where you summarize all of the sim components and values we have to work with, to better prep assigning colors to different objects/parameters. maybe summarize all values then suggest a few options then i can approve or suggest my own approaches before implmenting

- **2026-08-31T23:46:36Z · specimen / specimen · study-001-memory-field**
  overlay elements are hand-placed per aspect; KC: make things snap to corners and procedurally be placed along the edges so it looks fine in either aspect ratio. Long flexibility pass on the detail generator planned 2026-09-01, with Study 001 reopened for a 9:16 Look as the live test case.

## Ideas

- **2026-08-13T12:59:48Z · behavior / probe · component-look-6013004ba32c**
  exactly. this allows us to come back and revisit different directions after the look dev is done, as some of those might lend themselves better to where we ended up look wise.

## Questions

_None captured yet._
