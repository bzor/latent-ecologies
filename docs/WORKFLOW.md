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

Each stage will write a receipt under `work/jobs/<job-id>/`. Receipts make the
pipeline resumable and show exactly which inputs produced an artifact.

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

