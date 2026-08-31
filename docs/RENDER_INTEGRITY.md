# Render integrity

## Scope

What can and cannot be verified about a rendered sequence in this project, and the
render procedure that follows from it. Stage 5 of `VISION.md`, expanding
`ARTIST_LED_LOOK_HANDOFF.md` section 7.

Everything below is measured on Study 001 (`refractory-route` live HDA, Karma XPU,
1080x1350, 64 samples per pixel, depth of field on, motion blur off, Houdini
22.0.368). Figures are observations from that scene, not general constants.

## Reproducibility limits

Two components of the pipeline are not bit-reproducible across processes.

**Karma XPU.** Rendering one frame twice from the same file, same frame, same
settings produced images differing in 78.2 percent of pixels, mean absolute
difference 32.9 over the differing pixels, median 8. At 64 samples per pixel with
dense small geometry under depth of field, per-pixel noise is large.

**The multi-threaded solver.** Cooking the same frame in two processes produced
identical point counts (350,208 at frames 100, 225, and 450) but different position
hashes. Accumulation over hundreds of steps drifts at float level.

Three consequences:

1. A render cannot be verified by re-rendering and comparing pixels. Any difference
   is swamped by noise of the same magnitude.
2. A change to a HIP cannot be shown to be image-neutral by re-rendering. Argue it
   from the parameter diff instead, and record the diff.
3. Frames rendered in separate runs sit on slightly different solver trajectories.

## Run seams

Point 3 is the one that reaches a delivery.

`houdini/render_look_sequence.py` is resumable: it renders contiguous runs of missing frames
and skips frames already on disk. Each run re-cooks the solver from the start frame.
Because the solver drifts between processes, frames from different runs do not share
a trajectory, and the join is a discontinuity.

The discontinuity is invisible to per-frame checks. Frame numbering, dimensions,
decoding, blank detection, and duplicate detection all pass. It reads as a one-frame
pop when the sequence plays.

Measured on the Study 001 delivery render, using the temporal residual defined below
against a sequence median of 4.97:

| Sequence composition | Residual at the join | Ratio |
| --- | --- | --- |
| Within a single run | 4.97 | 1.0x |
| Join between two runs | 11.4 to 11.6 | 2.3x |
| Single-frame run (reused probe frame) | 19.31 | 3.8x |

A run of length one is the worst case. It shares a trajectory with neither neighbour,
so it disagrees in both directions.

### How the probe frame got in

The render cost estimate came from timing one frame. That frame was written to the
delivery path, so the resumable renderer counted it as already valid and reused it.
The sequence then contained one frame from a single-frame run. It survived frame
validation and a visual check of five downscaled thumbnails, and was caught by KC
watching the encoded video.

Two rules follow, both now enforced in the tools:

- A timing or preview probe renders to a throwaway path, never into a delivery
  sequence directory.
- A delivery render is one uninterrupted run over the whole frame range.

## Verifying a sequence

`scripts/verify_render_sequence.py` runs the per-frame checks and the temporal
residual scan.

```powershell
python scripts/verify_render_sequence.py studies/<study>/02_look/renders `
    --pattern "look.*.png" --start 1 --end 450
```

The temporal residual for each interior frame is:

```text
residual(n) = mean(|f(n) - (f(n-1) + f(n+1)) / 2|)
```

Within a continuous run this is dominated by render noise and inter-frame motion and
stays near the sequence median. A frame from a different trajectory disagrees with
both neighbours, so its residual rises and both neighbours rise with it. A seam
therefore shows as a pair or a quartet of elevated frames, not a single one.

The default threshold flags frames above 1.8 times the median. Measured clean
sequences stay within 1.13 times. Seams reach 2.3 times and an isolated frame 3.8
times, so the threshold separates them with margin.

The scan reads every frame and takes a few minutes for a 450 frame sequence. Run it
before handing a render to the detail pass, and again after any partial re-render.

## Render procedure

1. Take the lock snapshot and preflight (`ARTIST_LED_LOOK_HANDOFF.md` section 6).
2. Estimate cost from a probe frame rendered to a scratch path.
3. Render the full range in one run. `renders/` must be empty so every frame is
   pending and the plan reports one run.
4. Verify with `verify_render_sequence.py`.
5. Encode the preview and write the receipt.

`houdini/render_look_sequence.py` records `runs`, `run_ranges`, `single_contiguous_run`, and
`seam_risk` in its receipt, warns when a render would be stitched, and refuses to
start under `--require-contiguous` when frames would be reused.

Patching a bad frame does not work. Re-rendering a window around it replaces one seam
with two, which was measured directly: repairing frames 215 to 225 moved the 3.8x
anomaly at 225 to a 2.3x seam and added a second at 214 to 215. Delete the frames and
render the range again in one pass.

## Making resume safe

The seams exist because the geometry is recomputed per run. Caching the simulation to
disk removes the cause: every run reads identical geometry, so runs become
interchangeable and resume becomes safe.

The look templates already carry a disconnected File SOP for this
(`SOURCE_PROMOTED_SIMULATION`), and `ARTIST_LED_LOOK_HANDOFF.md` section 3 permits a
cache as a performance optimization provided the HDA stays the canonical artifact.

This is worth doing for a long render, a scene likely to need partial re-renders, or
an unattended overnight render. It requires enabling a cache in the Look HIP, which
is a scene change and needs KC's approval when the HIP is already locked. Study 001
was delivered without it, by rendering 450 frames in a single 2 hour 31 minute run.

## Snapshot caveat

A locked HIP copied into a subdirectory does not cook in place. The behavior HDA is
referenced relative to `$HIP`, so a snapshot under `02_look/locked/` loads with the
HDA unresolved and the simulation output returns zero points.

Snapshots under `locked/` are archival records for checksum binding. To run one, copy
it back beside the authoritative Look HIP first, and render from that HIP.

## Operational notes

**Git Bash mangles Houdini node paths.** MSYS rewrites arguments that look like
absolute POSIX paths, so `/obj/PLAYGROUND_SIM/OUT_SIMULATION` arrives as
`C:/Program Files/Git/obj/...`. Export `MSYS_NO_PATHCONV=1` for any hython command
taking node paths.

**Do not snapshot every parameter in a scene.** Iterating all parameters under `/obj`
and `/stage` and evaluating each one crashed hython on this scene by forcing USD stage
evaluation. Scope a parameter diff to the node being changed.

**The HDA cannot checksum-bind its own manifest headlessly.** The exporter records a
HIP checksum only when `hou.hipFile.hasUnsavedChanges()` is false
(`build_refractory_route_hda.py`). In hython that call returns true immediately after
a clean load, before anything is modified, and Houdini 22 has no
`hou.hipFile.clearUnsavedChanges()`. A bare headless export therefore produces
`hip_dirty: true` and `hip_sha256: null`, which is valid for the detail pass and not
valid for locked delivery.

For locked delivery, run the system driver instead:

```powershell
hython houdini\export_overlay_manifest_headless.py <locked.hiplc> <node_path>
```

The driver hashes the HIP before loading, presses the HDA's exporter with no other
scene mutation, verifies the file is unchanged afterwards, and binds the manifest to
that hash (`bind_headless_overlay_manifest` in `overlay_parameter_manifest.py`). The
binding is recorded as `source.checksum_binding: "headless-clean-load"`; a GUI export
stays valid and is left untouched. No HDA rebuild is required.
