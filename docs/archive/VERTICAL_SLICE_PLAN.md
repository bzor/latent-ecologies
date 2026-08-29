# Vertical slice plan — Study 001: Memory Field

## Objective

Prove the complete local workflow with one small but authentic creative study:

```text
study manifest → generated HIP → deterministic simulation → Karma PNG frames
→ validation → encoded videos → poster and metadata → local publication package
```

The result must require no After Effects work or manual frame stitching. Public
posting is deliberately excluded from this slice; it will consume the same verified
publication package later.

## Definition of done

One command can take Study 001 from its versioned sources to a review directory
containing:

- A generated, reopenable `.hip` file.
- A deterministic simulation cache or reproducible scene state.
- A complete Karma PNG sequence.
- An archival video master.
- A website video and poster frame.
- A 9:16 social master compatible with Instagram Reels, TikTok, and X.
- A 4:5 feed derivative.
- A lightweight preview loop.
- A manifest snapshot, job receipt, render log, caption draft, and alt text.
- A local field-note page or structured field-note payload.

Rerunning the command skips valid stages, repairs missing frames, and never publishes
anything externally.

## Constraints

- Optimize for unattended operation during client work.
- Use PNG as the default final-look frame format.
- Use EXR only when a study explicitly justifies it.
- Houdini/Karma establishes the final color and lighting intent.
- Keep optional overlays separate only when doing so improves clarity or reuse.
- All simulations and renders must be deterministic from manifest plus source revision.
- Public actions remain approval-gated.
- External replies or captions never become executable code or shell input.

## Milestone 1 — Workstation discovery

**Status: complete (2026-08-10).**

### Work

- Locate installed Houdini versions and `hython`/`hbatch` executables.
- Record Houdini build, Python version, license type, Karma availability, and render devices.
- Locate FFmpeg or install/configure it explicitly if absent.
- Determine whether headless Karma rendering succeeds under the available license.
- Add local configuration discovery without committing machine-specific paths.
- Expand `houdini-ai doctor` with actionable results.

### Acceptance

`houdini-ai doctor` identifies every required executable and returns a nonzero exit
code with a useful explanation when a required dependency is unavailable.

## Milestone 2 — Job model and workspace

**Status: complete (2026-08-10).**

### Work

- Define a job identifier derived from study, seed, quality, and source state.
- Create `work/jobs/<job-id>/` with stage receipts and logs.
- Resolve all paths from the repository root.
- Snapshot the effective project and study configuration for reproducibility.
- Add safe stage states: pending, running, complete, failed, and stale.
- Add `plan`, `run`, and `status` CLI commands.

### Acceptance

Running `plan` creates no Houdini output and explains exactly what will run, where
artifacts will be written, and why any prior artifact is reusable or stale.

## Milestone 3 — Generated Houdini smoke scene

**Status: complete (2026-08-10).**

### Work

- Create a versioned Python scene builder executed through `hython`.
- Build a minimal Solaris/Karma-compatible scene without manual node editing.
- Add a camera, lighting, material, render settings, and frame range from the manifest.
- Save the generated HIP into the job directory.
- Render a single diagnostic frame first.

### Acceptance

The generated HIP opens without missing references, and the diagnostic PNG has the
expected resolution, frame number, and nonempty image content.

## Milestone 4 — Memory Field prototype

**Status: complete (2026-08-10).**

### Minimal rule system

- Agents sense a resource field.
- Agents steer toward resource and away from local inhibition.
- Movement deposits inhibitory memory.
- Resource is consumed locally.
- Memory decays over time.
- Boundary behavior and collision avoidance are explicit.

### Instrumentation attributes

- Agent identifier and lineage identifier.
- Age, speed, resource intake, and local inhibition.
- Steering contribution from each field.
- Recent deposit strength.
- Active, dormant, or terminated state.

### Work

- Implement rules primarily in reviewable VEX.
- Separate simulation state from visualization where practical.
- Add bounded parameters and deterministic initialization.
- Cache metrics alongside geometry.
- Provide organism and instrument display branches.

### Acceptance

The same seed produces materially identical metrics and frames across two clean
runs. A changed seed produces a distinct but valid result. Instrument mode can
explain at least resource attraction and memory avoidance.

## Milestone 5 — Karma looks and camera

**Status: complete (2026-08-10).**

### Work

- Implement initial `field-study` look.
- Implement `static-observation` camera.
- Add a restrained organism palette and semantic instrument accents.
- Keep depth of field disabled for the first instrument render.
- Establish a path for later Void Macro and event-driven focus presets.

### Acceptance

The image reads clearly at social-feed size, and overlays remain legible without
obscuring the simulated behavior.

## Milestone 6 — Resumable frame rendering

**Status: complete (2026-08-10).**

### Work

- Render the configured PNG sequence through a subprocess wrapper.
- Capture command, environment summary, stdout, stderr, and exit status.
- Validate expected frame numbers, dimensions, readable files, and minimum size.
- Resume only missing or invalid frames.
- Avoid rerunning simulation when only render output is incomplete.

### Acceptance

Deleting one middle frame and rerunning the job regenerates that frame without
rebuilding valid simulation caches or rerendering the complete sequence.

## Milestone 7 — Automated encoding and packaging

**Status: complete (2026-08-10).**

### Work

- Encode an archival master from the PNG sequence.
- Generate 9:16 social, 4:5 feed, website, and preview-loop variants from the master.
- Select or configure a poster frame.
- Validate duration, dimensions, frame rate, and successful decoding.
- Generate caption and alt-text drafts from study metadata.
- Generate a field-note payload with lineage and reproducibility information.
- Produce checksums and a final package receipt.

### Acceptance

The package can be reviewed without opening Houdini or running a manual media tool.
Encoding can be rerun independently of simulation and rendering.

## Milestone 8 — Reliability pass

**Status: complete (2026-08-10).**

### Work

- Test paths containing spaces.
- Test interruption and resume behavior.
- Test malformed manifests and unavailable executables.
- Test invalid, missing, and partially written frames.
- Ensure logs do not expose environment secrets.
- Document the one-command workflow and troubleshooting steps.

### Acceptance

All automated tests pass, a clean run completes, and at least one deliberately
interrupted run resumes correctly.

## Deferred until after the vertical slice

- Public website framework selection and deployment. A dependency-free local Review
  Studio is now implemented; it does not publish externally.
- X authentication, API integration, and automatic posting.
- Reply ingestion or audience-driven mutations.
- General-purpose parameter sweep UI.
- Sophisticated AI anomaly classification.
- Render-farm or cloud scheduling.
- Audio generation and synchronization.

## Post-slice review milestone

**Status: complete (2026-08-11).**

The local Review Studio now consumes the same generated job state proven by the
vertical slice. `python -m houdini_ai review` serves a local-only browser interface at
`http://127.0.0.1:8765` with motion playback, still inspection, HIP access, artifact
comparison, provenance, selected parameters, timecoded comments, constrained review
decisions, and open/resolved state. Feedback is stored beneath `work/reviews/` and is
never interpreted as executable input. See `docs/REVIEW_STUDIO_PLAN.md`.

## Post-slice continuation

The vertical slice is complete, Study 002 Mass Flow is active, and generated jobs now
feed the local Review Studio. Remaining work is tracked in `docs/PHASE2_PLAN.md` and
`docs/REVIEW_STUDIO_PLAN.md`. Public posting remains deliberately approval-gated.

Verified 2026-08-10:

- Houdini 22.0.368 is installed in the standard Windows SideFX location.
- `hython` and `hbatch` are present; `hython` reports Python 3.13.10 and an Indie license.
- The LOP context loads successfully and exposes Karma node types.
- A cold Houdini/license startup can exceed 20 seconds, so the probe allows 60 seconds.
- FFmpeg 9.0 and FFprobe are installed through WinGet and pass executable probes.
- A headless Karma CPU render succeeds through `hython`; its generated HIP and validated
  320 x 180 RGBA PNG are written under `work/diagnostics/`.
- `hgpuinfo` inventory reports the available CPU and GPU OpenCL render devices.
- The versioned Study 001 builder creates a job-local Solaris/Karma HIP. A separate
  `hython` process reopens it and renders a validated 1280 x 720 RGBA diagnostic PNG;
  reruns reuse checksum-verified HIP and PNG artifacts.
- Probe 001 established a deterministic 64-agent, 128 x 72 field simulation with a
  seeded central relic, resource consumption, inhibitory memory, bounded motion,
  instrumentation attributes, per-frame metrics, reproducibility gates, and an
  automatically encoded local review bundle.
- Probe 002 recomposes the field as a 9 x 16 domain sampled at 72 x 128, with native
  1080 x 1920 output and portrait-aware review media. Probe 001 remains the preserved
  landscape baseline.
- The `field-study` Karma look imports cached simulation geometry into Solaris, uses
  MaterialX charcoal, pale-organism, cyan-resource, and amber-memory materials, and
  renders through the portrait `static-observation` camera with depth of field off.
  Frames 1, 120, and 240 plus the instrument still form the accepted look-development set.
- Probe 007 disables artifact geometry and every artifact-derived influence while
  retaining 256 agents; resource, inhibition, occupancy, and boundaries now define
  the artifact-free baseline.
- A clean 240-frame 1080 x 1920 Karma sequence completed at the explicit two-sample
  probe tier. Moving frame 120 aside and resuming rendered exactly one frame, and its
  SHA-256 checksum matched the original byte for byte.
- FFmpeg produced an 8-second 30 fps ProRes archive, 9:16 social master, 4:5 feed
  derivative, website video, and preview loop. FFprobe verified codec, dimensions,
  duration, frame rate, and decoding before the checksummed draft package was written.
- Reliability coverage includes interruption recovery, missing and partial frames,
  paths containing spaces, malformed manifests, missing executables, and secret-safe
  subprocess logging. The current regression suite contains 36 passing tests, including
  local review discovery, byte-range media, path-containment, and feedback API coverage.

Useful orientation files:

- `README.md`
- `docs/PROJECT_PLAN.md`
- `docs/WORKFLOW.md`
- `studies/001-memory-field/study.json`
- `studies/001-memory-field/lab-log.md`
- `src/houdini_ai/cli.py`
