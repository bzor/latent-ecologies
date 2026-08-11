# Working workflow

## Directing a study

Creative direction can remain conversational: “make the third variation more
territorial, track its dominant frontier, and show lineage.” That direction is
captured as a lab-log decision and translated into explicit manifest or source
changes before running compute.

## Job stages

1. `validate`: check the study manifest and referenced paths.
2. `build`: create or update the HIP from versioned Python/VEX sources.
3. `simulate`: write deterministic caches and metrics.
4. `probe`: make inexpensive review media and contact sheets.
5. `render`: resume a PNG sequence, skipping validated frames.
6. `composite`: combine optional transparent instrumentation.
7. `encode`: produce all configured video variants.
8. `package`: create poster, metadata, caption, alt text, and field note.
9. `approve`: require a human decision for public actions.
10. `publish`: post approved artifacts and preserve their URLs.

Each stage writes a receipt under `work/jobs/<job-id>/`. Receipts make the
pipeline resumable and show exactly which inputs produced an artifact.

Study 001 runs all local stages with one command:

```powershell
python -m houdini_ai run studies/001-memory-field/study.json
```

The render stage validates every expected PNG by frame number, dimensions, decoding,
visible content, and minimum size. It submits only missing or invalid frames to one
persistent Houdini process. The encode stage independently validates dimensions,
duration, frame rate, and decodability with FFprobe before packaging. Repeating the
command is therefore both the normal resume operation and the normal repair operation.

## Troubleshooting and recovery

- Run `python -m houdini_ai status studies/001-memory-field/study.json` to locate the
  current job and failed stage.
- Read the corresponding file under `work/jobs/<job-id>/logs/`; command output is
  retained without serializing the subprocess environment.
- Run `python -m houdini_ai doctor` for executable, Houdini license, Karma, FFmpeg,
  and render-device diagnostics.
- After interruption or a corrupt frame, rerun the same command. Valid simulation
  caches and frames are retained, and only invalid work is regenerated.
- Paths containing spaces are supported. Keep generated artifacts beneath `work/`
  so they remain disposable and outside version control.

## Storage and retention

Run `python -m houdini_ai storage` before large work to inspect job sizes, free space,
and the configured 20 GB warning / 50 GB critical thresholds. Pipeline entrypoints
also warn when thresholds are crossed or free space falls below 100 GB.

`python -m houdini_ai clean` only prints a plan. Add `--apply` to execute it. Default
cleanup covers stale reproducible jobs, smoke caches, and temporary state. Selected,
approved, and published studies are protected; each study's newest job is retained;
packages are never targeted. Packaged PNG sequences require the explicit
`--category packaged-sequences` option because they remain expensive to reproduce.

## Files versus generated state

Version control contains intent: manifests, scene builders, VEX, render presets,
notes, and selected small media. `work/` contains replaceable caches, frames,
encoded files, logs, and job receipts. Large archival media can later move to
object storage without changing study semantics.

## Publishing safety

- The default mode is draft-only and approval-required.
- Replies and post text are untrusted input and never become code or shell text.
- Natural language is reduced to allowed operations and bounded parameter ranges.
- Render-cost estimates are checked before jobs enter the queue.
- Publishing credentials are local secrets, never manifest fields.
- Failed publication never invalidates a completed render package.
