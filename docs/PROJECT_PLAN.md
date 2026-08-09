# Project plan

## 1. North star

Build a living collection of VEX-heavy artificial ecologies inspired by patterns
and processes in nature. AI participates in hypothesis formation, rule design,
implementation, parameter exploration, anomaly detection, interpretation, and
documentation. The artist remains responsible for taste, direction, and the
decision to publish.

The working identity is **computational natural history**: a field notebook of
plausible processes from alternate natures.

## 2. Creative territory

The project begins near multi-neighborhood cellular automata, broad cellular and
random-system experimentation, and expressive flocking, then moves toward less
familiar combinations:

- Morphogenetic automata whose cells move, divide, die, and change neighborhoods.
- Stigmergic worlds whose agents communicate by altering their environment.
- Artificial embryologies in which compact genomes unfold through timed stages.
- Mutable physics where local rules, metrics, or time rates evolve spatially.
- Ecologies in which different organisms implement pieces of a computation.
- Interrupted growth: scarring, dormancy, parasitism, mutation, and regeneration.
- Fields that retain histories of movement, damage, resources, and extinction.
- Organisms that carry small evolvable programs instead of fixed behaviors.
- Symbiotic species whose joint behavior is richer than either species alone.

Scientific novelty is not a publication claim. The useful standard is that a
specific interaction of rules produces behavior the collaborators did not expect.

## 3. Collaboration model

Each study follows a traceable loop:

1. Observe a natural process or computational idea.
2. Extract a minimal local rule system.
3. Record hypotheses and competing proposals.
4. Implement deterministic, instrumented prototypes in VEX.
5. Generate probes and parameter families.
6. Select, reject, or redirect based on behavior and aesthetics.
7. Preserve anomalies and meaningful failures.
8. Promote selected branches to specimen renders.
9. Publish the result, lineage, code excerpts, and reproducibility status.

AI suggestions are proposals, not unattended authority. Audience replies are also
interpreted as proposals and translated into bounded parameters or code changes
before execution.

## 4. Study contract

Every study owns:

- A human-readable title and machine-safe identifier.
- Inspiration, observation, and initial hypothesis.
- Deterministic seed and explicit frame range.
- Rule genome: fields, neighborhoods, update rules, and mutations.
- Houdini scene-builder source and VEX source where practical.
- Quality tier, presentation mode, render look, and camera behavior.
- Cache and output locations outside version control.
- Measured metrics and noteworthy events.
- Publication state and reproducibility level.
- A short lab log recording decisions, anomalies, and branches.

Reproducibility levels are `open`, `partial`, `documented`, and `artifact`.

## 5. Visual system

Three modes may share the same simulation cache:

- **Organism:** clean, cinematic presentation.
- **Instrument:** restrained annotations expose selected internal processes.
- **Analysis:** dense diagnostics, comparisons, plots, and field slices.

The reusable instrument layer can show neighborhoods, temporary bonds, velocity,
steering forces, resource flow, age, lineage, mutation, signals, competition,
state transitions, and rare events. Relationships are curated rather than drawn
indiscriminately.

Annotations distinguish epistemic status:

- `MEASURED`: values directly emitted by the simulation.
- `DERIVED`: computed summaries.
- `OBSERVED`: recurring behavior noticed in output.
- `HYPOTHESIS`: a collaborator's interpretation.

## 6. Render philosophy

Karma produces a near-final look. PNG sequences are the everyday contract because
they are inspectable and require no manual grade. EXR is an intentional exception
for exposure-sensitive, volume-heavy, or deeply revisitable work.

Quality tiers:

- **Probe:** fast behavioral evaluation.
- **Study:** presentable test with modest sampling and selected overlays.
- **Specimen:** archival output, final instrumentation, sound, and delivery files.

Initial reusable looks are Void Macro, Field Study, Instrument, Specimen Glass,
and Environmental. Camera behaviors include static observation, macro tracking,
slow orbit, frontier follow, and event-driven focus. Depth of field must serve an
explicit subject; instrument mode can disable it for clarity.

## 7. Automated pipeline

The target zero-touch path after creative approval is:

```text
manifest → scene build → simulation/cache → probe validation → selection
→ resumable PNG render → frame validation → optional overlay composite
→ master encode → platform variants → thumbnail/alt text/caption
→ approval gate → website/X publication → lineage record
```

Automation requirements:

- Never rerun a valid simulation merely because encoding failed.
- Detect and render only missing or corrupt frames.
- Produce archive, website, social, preview-loop, and poster outputs together.
- Capture Houdini, renderer, package, seed, and source-revision metadata.
- Keep credentials out of study manifests and source control.
- Default all public actions to `approval_required`.
- Make jobs idempotent so rerunning a completed stage is safe.

## 8. Website and public studio

The website is the durable field notebook. A study page may include observation,
rules, renders, parameter comparisons, selected VEX, AI and artist decisions,
unexpected failures, lineage, dependencies, and downloadable HIP files.

X is a public studio conversation rather than a content treadmill. A typical
thread moves from a rough **field test**, through artist/AI direction, to a polished
**specimen** and a durable field-note link. The public may propose mutations or
choose branches, but engagement is never required to continue the work.

Participation levels:

- Private studio: complete working dialogue and unfiltered tests.
- Public notebook: selected tests and concise dialogue.
- Open branches: explicit invitations for outside proposals.

## 9. Delivery phases

### Phase 0 — Foundation (current)

- Repository conventions and manifests.
- Detailed creative and technical plan.
- Dependency-free validation/doctor CLI.
- Study 001 placeholder and lab log.

### Phase 1 — Local vertical slice

- Detect local Houdini/Hython and FFmpeg installations.
- Build a deterministic scene from Python.
- Cache and render a short Karma PNG sequence.
- Validate sequence continuity and dimensions.
- Encode master, website, and social variants automatically.
- Generate a local field-note and post draft.

Exit condition: one command produces reviewable deliverables from a clean checkout
without After Effects or manual frame handling.

### Phase 2 — Creative framework

- Shared VEX library for fields, neighborhoods, integration, growth, and memory.
- Reusable instrumentation attributes and overlay toolkit.
- Karma look and camera presets.
- Parameter sweeps, contact sheets, metrics, and branch lineage.
- First complete memory-field study.

### Phase 3 — Public notebook

- Study-index and detail pages.
- Media, genome, lab-log, download, and reproducibility components.
- Static metadata generation from manifests.
- Draft preview and approval workflow.

### Phase 4 — Public studio automation

- Prepare X post/thread drafts and accessibility text.
- Ingest selected replies as untrusted creative proposals.
- Translate proposals into bounded render plans.
- Approval-gated posting and reply threading.
- Record publication URLs back into study metadata or a separate state store.

### Phase 5 — Assisted discovery

- Automated behavioral metrics and anomaly surfacing.
- Visual embeddings or classifiers for variation grouping.
- Rule-genome mutation and crossbreeding.
- Compute/render budgets and queue management.
- Curated autonomous exploration windows with explicit safety limits.

## 10. Immediate decisions

Before Phase 1 is considered stable, record:

- Installed Houdini version, license constraints, and renderer availability.
- Preferred output resolution/aspect ratios and normal clip duration.
- GPU/CPU render capacity and acceptable overnight budget.
- Whether the first website is integrated with an existing site or standalone.
- Publication account arrangement and desired approval interface.
- Music/sound approach and licensing policy.

These choices should configure the system, not be hard-coded into each study.

