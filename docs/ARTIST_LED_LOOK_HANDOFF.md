# Artist-led Look handoff

## Status

This is the active Look workflow. It replaces autonomous agent-authored full Look rounds.

Hermes supports setup, validation, rendering, packaging, and tool handoff. KC owns visual Look Development and final presentation decisions.

## Lifecycle

```text
Behavior promoted
→ behavior finalized and verified as a live HDA
→ short KC–Hermes setup brainstorm
→ explicit starter-file specification
→ jointly curated setup selected or adapted
→ Hermes builds and verifies starter HIP
→ KC performs Look Development in Houdini
→ KC declares HIP locked
→ Hermes renders the locked HIP
→ Hermes launches the render in the detail/overlay system
→ KC completes the detail pass
→ post-ready artifact exported
→ repeated manual patterns reviewed for possible automation
```

## 1. Setup brainstorm

The brainstorm is intentionally short. It does not produce competing Look directions or ask an autonomous worker to finish a Look.

KC describes the file explicitly, including whichever details matter:

- which promoted Behavior HDA (and version) to load;
- desired SOP, LOP, MaterialX, camera, light, and render starting structure;
- a named setup-library entry to use;
- which controls should be exposed;
- the frame range and representative starting frame;
- whether a neutral dome, key/fill/rim rig, or both should be present;
- any initial geometry or material scaffolding KC wants;
- what must remain absent so the file stays open for exploration.

Hermes may suggest setup combinations or ask focused technical questions, but must not turn the conversation into a full autonomous Look brief.

## 2. Setup library

The library will be created collaboratively from setups KC has actually used. It is not pre-filled with speculative generalized systems.

Canonical source location:

`E:\Projects\houdini-ai\houdini\look_setups\`

Each setup should eventually contain:

```text
<setup-id>/
  SETUP.md                 purpose, visual use, limitations
  setup.json               stable IDs, parameters, compatibility
  build.py                 deterministic builder or adapter
  verify.py                cheap open/cook checks where needed
  assets/                  optional MaterialX, HDRI, geometry, presets
  examples/                small reference images approved by KC
```

A setup enters the reusable library only after KC has used or explicitly approved it. Generalization should follow repeated real use rather than precede it. Setup composition can remain manual until combinations recur reliably.

The first and default entry is KC's `basic` setup:

`E:\Projects\houdini-ai\houdini\look_setups\basic\basic.hiplc`

## 3. Behavior handoff artifact: live HDA

The canonical handoff artifact is a **live HDA**, never a bare cache. The promoted
behavior is packaged as a SOP HDA with:

- exposed artist parameters (identity, dynamics, playback) with sensible ranges;
- the promoted state embedded or deterministically regenerable from a seed;
- a fresh-session audit receipt proving the HDA reopens, cooks, and matches the
  promoted behavior's verified state (`build_nonlocal_affinity_hda.py` is the
  reference implementation of this pattern).

The behavior stays re-simmable during Look Development: KC can tweak behavior
parameters while the look develops. A heavy simulation may bake an internal cache
(for example a File Cache SOP downstream of the HDA) as a performance optimization,
but the cache is never the handoff itself and is always regenerable from the HDA.

The canonical handoff package (HDA, demo scene, embedded initial states, receipts,
and audit) lives inside the Study, at `studies/<study>/01_behavior/03_selected/`,
not under `work/studio/handoffs/` (KC direction, 2026-08-24: keep promotion
artifacts in the studies directory). Promotion is not complete until the HDA is
also wired into the chosen look-setup template in the Study's `02_look` directory
via `houdini/instantiate_look_starter.py` — delivering a bare `.hda` without the
lit starter HIP is only half the handoff.

### Overlay parameter manifest

The Behavior HDA includes an `Overlay Detail` folder. Before exporting an approved
variation, KC sets its variation number and title, saves the HIP, and presses
`Export Overlay Parameter Manifest`. The default output is:

`$HIP/$HIPNAME.overlay-parameters.json`

The button exports curated HDA controls carrying stable dotted keys, labels, evaluated
values, units, declared comparison ranges, animation status, HDA node identity, frame,
HIP path, and HIP checksum when the file is saved and clean. Parameters enter the export
through HDA parameter-template tags. Internal or incidental Houdini controls stay absent.

Each approved HIP variation therefore produces its own manifest. The overlay generator
uses the declared comparison range across sibling variations, so bars and dials remain
comparable. A dirty HIP produces a manifest with `hip_dirty: true` and no checksum; that
file is suitable for preview and must be regenerated after save for locked delivery.

## 4. Starter HIP delivery

Hermes creates only the requested starting file, normally with
`houdini/instantiate_look_starter.py`: it copies the chosen look-setup template into
the Study's flat `02_look` directory, copies and installs the behavior HDA beside it,
wires a `PROMOTED_BEHAVIOR` HDA node into the template's simulation entry point
(leaving the template's legacy cache File SOP disconnected as a documented fallback),
binds the render output to a Study-local path, verifies a fresh reopen and cook, and
writes a starter receipt next to the HIP.

The delivery must be immediately usable and artist-readable:

- the promoted Behavior enters as the live HDA node described above;
- requested nodes, controls, cameras, lights, and renderer are present;
- connected networks are arranged clearly, top-to-bottom, with parallel systems in adjacent columns;
- file paths are portable within the project where practical;
- the displayed output cooks at representative frames;
- the HIP reopens in a fresh Hython process;
- no unrequested visual solution is presented as completed Look Development.

The file is placed directly in the Study's flat `02_look` directory, normally as `look.hiplc`.
There are no Look brief/work subdirectories: KC owns colour, materials, lighting, camera, and
framing together in this HIP.

The starter delivery includes:

- explicit local HIP path;
- source Behavior identity and frame range;
- setup-library entry IDs and versions used;
- a compact setup receipt;
- any known limitations or intentionally unfinished sections.

At this stage the state is `artist-ready-starter`, never `look-approved`.

## 5. KC-owned Look Development

After delivery, KC opens and edits the HIP directly. That artist-edited HIP becomes authoritative.

Hermes must not regenerate over it. If KC requests technical help during Look Development:

1. inspect the current artist file first;
2. make a backup before edits;
3. change only the requested scope;
4. preserve unrelated parameters, keyframes, node types, connections, and layout;
5. reopen and verify the modified copy;
6. return the exact path and change summary.

Visual judgment, selection, and the declaration that the Look is complete belong to KC.

## 6. Lock handoff

Rendering begins only when KC explicitly says the HIP is locked and identifies the authoritative file.

On lock, Hermes should:

1. record the exact HIP path, byte size, checksum, Houdini version, the behavior HDA file and its checksum, frame range, cameras, render settings, output products, and color pipeline;
2. regenerate and validate the overlay parameter manifest from the saved locked HIP;
3. copy or snapshot the locked file to a protected handoff location without altering the artist original;
4. run a fresh-reopen preflight;
5. report blockers rather than silently repairing visual or scene choices;
6. request KC's approval for any change that would affect the locked image.

Layout cleanup, material replacement, camera adjustment, lighting adjustment, geometry edits, or cache substitution are not permitted after lock unless KC unlocks or versions the Look.

Suggested states:

- `artist-ready-starter`
- `artist-in-lookdev`
- `artist-locked`
- `render-preflight-passed`
- `rendering`
- `render-complete`
- `detail-in-progress`
- `post-ready`

## 7. Render execution

Hermes owns bounded rendering and verification. Presentation decisions stay with KC.

The render stage should:

- consume the locked snapshot;
- render deterministic frame paths;
- render a delivery sequence as one uninterrupted run;
- validate frame numbers, dimensions, decoding, freshness, and visible content;
- validate temporal continuity across the sequence;
- record errors and terminate bounded process trees on timeout;
- encode and probe requested video or image-sequence outputs;
- generate a render receipt bound to the locked HIP checksum;
- never publish automatically.

A completed render is still not the post-ready artifact.

### Single-run rule

A live-HDA scene re-cooks its solver from the start frame on every render run, and a
multi-threaded solver drifts at float level between processes. Frames rendered in
separate runs therefore sit on different trajectories, and the join reads as a
one-frame pop in motion. Per-frame validation cannot see it.

A delivery render is one run over the whole frame range, with `renders/` empty so
every frame is pending. Cost probes render to a scratch path, never into the delivery
directory, because a reused single-frame run is the worst case of this failure.

`render_look_sequence.py` records run structure in its receipt, warns when a render
would be stitched from several runs, and refuses to start under `--require-contiguous`
when it would reuse frames.

Resume stays unsafe for such a scene until the simulation is cached to disk. That
option, its cost, and the measured figures behind this rule are in
`RENDER_INTEGRITY.md`.

### Verification

Frame-level checks are not sufficient on their own. Run the temporal residual scan
before handing a render onward, and again after any partial re-render:

```powershell
python scripts/verify_render_sequence.py studies/<study>/02_look/renders `
    --pattern "look.*.png" --start <first> --end <last>
```

A render is verified when the frame set is complete and uniform and the scan reports
no anomalies. Report the median and maximum residual in the render record.

### Delivery conventions

- **Frame rate is 30 fps.** `config/project.json` carries `default_fps`, and
  `instantiate_look_starter.py` sets it on every new starter rather than inheriting
  whatever rate the look template was authored at. Set `--fps` only when a Study needs
  something else, and record why.
- **The preview video sits in the Look directory**, as
  `studies/<study>/02_look/<variation-stem>.look-render.mp4`, beside the Look HIP.
  Frames stay in `02_look/renders/`. KC should not have to open the frame directory
  to watch a render. The preview carries the variation stem because a Study holds
  several of them at once.
- Point the overlay config's `render.video` at that path so the detail-pass backdrop
  loads from the same file KC reviews.

A render whose scene frame rate differs from the delivery rate plays at a different
duration than the scene timing implies. Record both rates when they differ.

## 8. Detail/overlay handoff

After render verification, Hermes stages the render package into KC's detail/overlay
generator and the promote flow follows `DETAIL_PASS_PROMOTE.md`: KC adjusts the overlay
in realtime, exports the canonical config into the Study, and promotes from the Study
thread; Hermes rebuilds the overlay headlessly, composites, and packages the post-ready
artifact.

The handoff should include:

- rendered sequence or still paths;
- resolution, frame rate, frame range, alpha, and color-space information;
- source HIP checksum and render receipt;
- requested detail-system project/output location;
- any required masks, AOVs, or metadata that KC has specified.

KC completes the detail/overlay pass and exports the final post-ready artifact. Hermes may verify encoding, dimensions, checksums, and package completeness afterward, but cannot approve the presentation.

## 9. Automation policy

Do not automate a step merely because it can be scripted. Consider automation only after several completed works expose a stable, repeated operation.

A candidate is appropriate when:

- KC performs substantially the same operation repeatedly;
- inputs and outputs are explicit;
- success can be verified mechanically;
- automation preserves rather than narrows KC's presentation choices;
- failures are cheap, bounded, and reversible.

Likely early candidates:

- promoted-cache import;
- setup instantiation;
- camera/light/render-product boilerplate;
- locked-HIP receipts and snapshots;
- resumable renders and encoding;
- detail-system project creation/import;
- final package verification.

Keep these KC-owned unless evidence proves otherwise:

- selecting the representational mapping;
- shaping silhouettes and composition;
- choosing material character;
- deciding when a Look is complete;
- final detail/overlay decisions;
- publication approval.

## Retired workflow

The former autonomous Look Execution Agent remains documented at:

`E:\Projects\houdini-ai\docs\archive\LOOK_EXECUTION_AGENT.md`

It is retained as research and as a source of optional validation/render infrastructure. It is not the default production workflow and must not be run again without KC explicitly reopening that research direction.

Round 008 records why:

`E:\Projects\houdini-ai\studies\study_003_nonlocal-affinity-dance\02_look\AUTONOMOUS_LOOK_RESEARCH.md`
