# Look

This phase is deliberately flat and artist-owned.

## Active file

Variation: `variation-001-primary-treatment`  
Filename stem for new outputs: `var_001_primary-treatment`

`E:\Projects\houdini-ai\studies\study_003_nonlocal-affinity-dance\02_look\look.hiplc`

The existing HIP keeps its receipt-preserving historical name. New Look revisions use
`var_001_primary-treatment.look_rNNN.hiplc`.

State: `artist-in-lookdev`  
Setup: `basic`  
Behavior: `component-behavior-b5b98c543bc1` / `selection_002`

KC edits this HIP directly and owns geometry treatment, materials, colour, camera, framing, lighting, and final Look decisions. Hermes must not regenerate over it.

To version manually, duplicate it in this directory—for example:

```text
look-v002.hiplc
look-v003.hiplc
```

When one file is ready to render, KC identifies the authoritative filename and declares it locked. Hermes then snapshots, preflights, and renders that exact file without presentation changes.

## Files

- `look.hiplc` — current artist-owned Look file
- `look.json` — compact source/setup/state receipt
- `AUTONOMOUS_LOOK_RESEARCH.md` — retained summary of the discontinued autonomous experiment

No `00_brief`, `01_work`, or autonomous Look rounds are required. All visual decisions live in the HIP. After the locked render is complete, the Study proceeds directly to Specimen/detail work.
