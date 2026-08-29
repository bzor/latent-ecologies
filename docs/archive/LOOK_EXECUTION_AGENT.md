# Look Execution Agent

> **Research status — paused 2026-08-20.** This autonomous full-Look workflow is retained for
> provenance and for reusable verifier/render infrastructure. It is not the active production path
> and must not be executed again without KC explicitly reopening the research direction. The active
> artist-led workflow is `ARTIST_LED_LOOK_HANDOFF.md`; the decisive research conclusion is retained in
> `studies/study_003_nonlocal-affinity-dance/02_look/AUTONOMOUS_LOOK_RESEARCH.md`.

The Look Execution system turns selected structural Look Direction Briefs into isolated,
sequential Hermes work packets. Each direction receives a fresh process and workspace.
Behavior remains read-only. Geometry translation, materials, animation treatment, framing,
lighting, renderer setup, and final-image evidence are mandatory Look Development work.
Technical probes remain useful engineering checkpoints but cannot complete a direction.

## Trust and isolation boundary

Each direction gets a new OS process, fresh Hermes context, attempt-scoped working directory, and
only its own packet in the runtime prompt. Sibling briefs are not supplied. Worker timeouts and
output overflow terminate the entire descendant process tree.

This is **workflow isolation, not a hostile-code security sandbox**. Look workers are trusted
local Studio components running as KC's Windows user; that user can technically traverse or
rewrite any accessible project file. Round anchors, parent verification seals, canonical path
checks, and hashes detect normal corruption and unauthorized workflow mutation, but they are not
a cryptographic defense against malicious same-user code that deliberately rewrites every trust
record. Untrusted worker implementations must run in a separate OS account, VM, or container.

## Contract

A round has three explicit operations:

1. `look-round-prepare` validates the promoted Behavior handoff and selected direction briefs,
   then freezes a `00_look` playground packet plus one packet and worker prompt per direction.
2. `look-round-run` first builds and independently reopens the non-competing `00_look` Karma
   playground. For each direction, parent Hython then builds a deterministic protected scaffold
   containing the frozen-cache source chain, active final output, MaterialX/USD binding, exact
   neutral rig, hero rig, Karma settings, and renderer output before launching Hermes. Each protected
   node receives a persistent parent identity; the scaffold receipt is hashed into a read-only seal
   outside the worker attempt and fresh Hython must recover the exact identities after the worker.
   The creative
   worker extends that scene rather than recreating render infrastructure. A direction must produce an
   editable render scene, decoded render package, split mechanical/visual claim evidence, and
   parent Hython audit before it becomes `decision-ready`. Review stays withheld.
3. `look-round-review` succeeds only after every direction passes mechanical, render-setup,
   visual, motion, and decision-readiness gates under equivalent neutral conditions. It creates
   one image-first `COMPARISON.md` and machine-readable review manifest for KC.

A failed worker or invalid receipt stops the round. Parent diagnostics are persisted in the failed
attempt. At most one targeted repair clones that scene and evidence into a new immutable attempt,
reads the exact diagnostics, and changes only the failing contract. It does not perform another blind
full rebuild. Already verified directions are never rebuilt.

## Resource and retry budgets

Every newly prepared round freezes an execution policy in `round-manifest.json`:

- two attempts maximum per direction: one creative pass and at most one targeted repair;
- 1,800 seconds maximum per worker, clamped even if a caller requests a larger CLI timeout;
- post-run acceptance ceilings of 200,000 reported tokens and USD 10 estimated cost per attempt;
- fail-closed Hermes `--usage-file` accounting for token count, estimated cost, API calls, model,
  and provider. Hermes reports these values when the process exits; because it exposes no per-run
  mid-generation token/cost interrupt, the wall-time/process-tree limit is the live safety bound;
- a hard stop requiring pipeline diagnosis when accounting is unavailable or any budget is exceeded.

These limits are release controls, not suggestions. Repeated long-running failures require redesign
of the deterministic scaffold, schema, preflight, or repair mechanism rather than another fresh agent.
Fresh Hython performs graph, cache, MaterialX, USD, camera, light, and renderer preflight before any
parent proof render, so structural defects fail cheaply.

## Inputs

The promoted Behavior handoff JSON requires:

- `id`, `component_kind: behavior`, and `state: promoted`; these must match the canonical
  `work/studio/components/<id>.json` record rather than merely being asserted by the handoff;
  the canonical record is rechecked before execution and final review;
- a `sha256:` content hash matching that promoted component;
- one or more existing `cache_paths` beneath the Study's canonical
  `01_behavior/03_selected/` handoff. Cache byte counts and SHA-256 values are frozen during
  preparation and rechecked before execution and final review.

Direction briefs follow `docs/examples/look-direction-briefs.example.json`. Every brief includes
a `visual_target` packet: references, final-image thesis, required and prohibited reads, material,
framing, lighting, and temporal intent. Materials, palette, framing, lighting, or cinematography
cannot be listed as deferred exclusions. Every aesthetic
claim must include an authoritative source attribute, visible response, Houdini mechanism,
and acceptance observable. Briefs also name neutral lighting assumptions and a cost tier. Every
selected direction must define at least four ordered `implementation_stages`; each stage names its
intent, simulation-data inputs, Houdini strategy, concrete output, and acceptance observation.
This prevents selection from degenerating into a vague prompt followed by a token node sketch.
Validated selected briefs are copied to the canonical `02_look/00_brief/<round>/` directory and
bound to their execution packets by SHA-256.

## Direction workspace and scene naming

Every direction owns one consistently named workspace. Every retry preserves the same internal
layout, so plans, HIPs, probes, and evidence are predictable rather than scattered:

```text
02_look/01_work/look-round-001/
  00_look/
    00_look.hiplc
    README.md
    playground-packet.json
    playground-receipt.json
    playground-audit.json
    playground-seal.json
    renders/
  01_affinity-weave/
    execution-packet.json
    WORKER_PROMPT.md
    attempt-001/
      00_design/PARENT_SCAFFOLD.json
      00_design/IMPLEMENTATION_PLAN.json
      00_design/PARENT_FAILURE_DIAGNOSTIC.json (failure only)
      01_scene/01_affinity-weave.hip|.hiplc|.hipnc
      02_probes/
      03_motion/
      04_evidence/annotated-claim-sheet.png
      04_evidence/graph-audit.json
      agent-usage.json
      agent-process.json
      receipt.json
```

The round review manifest and `COMPARISON.md` expose the exact canonical HIP path for each
direction, so opening the artist-facing scene never requires searching an attempt tree.

## Personal `00_look` playground

`00_look/00_look.hiplc` is KC's minimal personal sandbox, not a selected direction and never a
comparative-review candidate. It is generated deterministically before direction workers run and
contains:

- the frozen promoted simulation cache under `/obj/PLAYGROUND_SIM`, with a fallback point-scale
  control that applies only when the cache does not already provide `pscale`;
- a neutral floor/environment, editable MaterialX starter materials, and automatic camera framing
  derived from the simulation bounds;
- a `/stage` **Lighting Mode** menu that switches between a neutral dome and an editable
  photographer rig with `KEY`, `FILL`, and `RIM` lights;
- artist-readable network boxes, sticky notes, top-to-bottom flow, Karma CPU settings, a render
  product, and an `OUT_KARMA` USD Render ROP.

The builder writes an attempt-scoped temporary scene; only a successful second-process Hython
reopen is atomically promoted to the canonical HIP. The verifier cooks every frozen simulation
frame through the exact File SOP → visibility → output chain plus the floor and Karma settings;
binds each evaluated path, byte count, hash, and frame range to the cache receipt; validates the
floor import, MaterialX shaders/assignments, camera, lighting, and render nodes and their critical
connections; and exercises both lighting-selector values before the parent writes a receipt and
seal. Interrupted or corrupt unsealed HIPs are preserved under `failed-builds/` with a non-HIP
suffix and rebuilt, so they cannot permanently wedge a retry or become an ambiguous scene.
Symlinked artifacts and workspace aliases resolving outside the project root are rejected. The parent repeats artifact, seal,
source-provenance, and recursive HIP-uniqueness checks before aggregate review. If you want to
preserve a tangent as another HIP, save it outside the generated `00_look` directory; the
single-scene invariant keeps the canonical playground unambiguous.

## Deep implementation contract

The execution worker first inspects real cache ranges, then expands the selected stages into an
implementation plan before creating the scene. It implements and cooks one stage at a time. The
plan must preserve the selected stage order and bind every completed stage to verified evidence.
Each expanded stage must name its network section, node families, at least two topologically
ordered nodes by absolute path/type/role plus their exact direct `inputs`, its output node, and
artist controls by node path and parameter. Empty `inputs` identify sources; parallel sources or
probes remain parallel instead of being falsely serialized. Each stage also requires a distinct
evidence artifact. The parent rejects shared placeholder evidence, duplicate planned node paths,
forward/self/cyclic input references, or a stage whose output is not the final listed node.

The plan also freezes a direction-local `render_setup`. The HIP must contain canonical `/stage`
roles for SOP import, editable MaterialX library and assignment, neutral and hero cameras, neutral
dome, hero key/fill/rim, lighting selector, Karma settings, and USD render output. The fresh-Hython
verifier checks semantic node families, material content, assignments, Karma cooking, and that
every required role participates in the rendered USD stream. A shared `00_look` playground cannot
substitute for this integration.

The verifier also authors parent-owned Karma proof renders after reopening the delivered HIP:
locked-neutral early/middle/late frames, one hero frame, and eight contiguous neutral-motion
frames. These proofs are written under
`04_evidence/parent-renders`, hash-bound into the parent graph audit, decoded by the parent, and used
for comparative still and motion review. The parent assembles the eight audited source-frame renders
into a hash-bound GIF; worker-authored motion cannot satisfy the motion gate by itself. The audit
records the evaluated neutral camera, dome,
resolution, sampling, selector mode, and active OCIO-config hash; those measured values—not a rig
label alone—must match across directions.

The implementation plan embeds the frozen Behavior cache receipt. At every neutral and motion proof
frame, fresh Hython re-hashes the corresponding cache, proves that a planned File SOP was involved in
the final SOP's forced cook (inactive Switch/bypass inputs do not count), evaluates to that exact file,
proves the Solaris Look import references the verified final SOP output,
and recomputes the authored USD MaterialX target and binding immediately before each proof render.
Frame-dependent SOP imports or material assignments therefore fail at the first divergent evidence
frame. A scene animated independently of the promoted Behavior cannot pass. Parent output paths are
deleted before each Karma invocation, render-node errors are checked, and only freshly authored
files are admitted. Camera, dome, and render-setting signatures are sampled at every evidence frame,
so animated review-rig differences cannot converge at one frame and evade comparison.

Generated HIPs are handoff artifacts, not opaque build receipts. Networks must use descriptive
SOURCE_/LOOK_/MAT_/OUT_ sections, flow top-to-bottom, place parallel systems in adjacent columns,
and expose display/render flags on the final direction output. After the worker exits, the parent
launches a separate Hython process which loads the canonical HIP from disk, resolves every planned
node and artist control against the real graph, reconciles the declared DAG inputs, cooks every
stage output, requires flags on the final output, and measures layout. Intermediate outputs must
cook cleanly but are not required to hold Houdini's mutually exclusive display/render flags. The
parent—not the worker—writes and seals
`04_evidence/graph-audit.json`. Upward edges, duplicate node positions, missing or mismatched
nodes/controls, any additional `.hip`/`.hiplc`/`.hipnc` anywhere beneath the attempt workspace,
or reopen/cook errors fail verification. The recursive HIP uniqueness check runs both at initial
acceptance and again before aggregate review.

The receipt uses separate `mechanical_status` and `visual_status` for every selected claim, with
separate technical and rendered evidence paths. A `visual-review-ready` receipt requires all
claims to be demonstrated in both dimensions. The parent decodes and inspects three distinct,
matched neutral PNGs (early/middle/late), an art-directed hero PNG, a multi-frame motion GIF, and
an annotated PNG claim sheet. It rejects missing artifacts, path substitutions, hash drift,
undecodable or near-blank media, low resolution, mismatched neutral resolution, duplicate temporal
frames, and image-space claims pointing only to SVGs, viewport captures, topology images, or
technical records.

## Commands

```powershell
houdini-ai studio look-round-prepare study-003-nonlocal-affinity-dance `
  .\path\to\promoted-behavior.json `
  .\path\to\selected-look-directions.json

houdini-ai studio look-round-run `
  .\studies\study_003_nonlocal-affinity-dance\02_look\01_work\look-round-001\round-manifest.json

# Required when any selected brief is study, specimen, or external cost:
houdini-ai studio look-round-run `
  .\studies\study_003_nonlocal-affinity-dance\02_look\01_work\look-round-001\round-manifest.json `
  --approve-gated-cost

houdini-ai studio look-round-review `
  .\studies\study_003_nonlocal-affinity-dance\02_look\01_work\look-round-001\round-manifest.json
```

The default worker command is `hermes chat -q`. Testing or specialist harnesses may supply a
JSON command prefix through `--agent-command-json`. `look-round-run` also requires Hython; run
`houdini-ai doctor` if the independent scene verifier cannot be discovered or licensed.

Stage IDs and state-to-form acceptance observables must be unique within each direction. JSON
Schema validates their shape; runtime validation enforces these cross-item semantic constraints.

## Evidence and review

Each round also contains a read-only, hash-bound `round-descriptor.json` that freezes the exact
ordered selected-direction set, source provenance, packet paths, and packet hashes. Its digest is
also recorded in a separately derived `work/studio/look-round-anchors/` record outside the round
workspace. Mutable run state cannot remove or replace a selected direction without failing anchor
and descriptor validation.

Each direction workspace contains immutable base `execution-packet.json` and
`WORKER_PROMPT.md` files plus one `attempt-NNN/` directory per fresh process. Each attempt
contains its own hash-bound packet, process logs, `agent-process.json`, `receipt.json`, and
generated HIP, probe media, metrics, and supporting evidence. Failed attempts remain preserved;
a retry receives a new attempt identity, and final review accepts only the highest canonical
attempt number, so an earlier valid-looking receipt cannot be substituted. A parent-created
`verification-seal.json` distinguishes accepted attempts from receipts merely left behind by a
failed process and prevents mutable flags from selectively rerunning a verified candidate.

The dispatcher independently recomputes every Behavior-cache and output-artifact byte count and
SHA-256. It requires exactly one receipt claim for every acceptance observable, and every claim
must point to verified technical evidence and rendered image-space evidence. Direction state is
reported separately as `mechanically_verified`, `render_setup_verified`, `visually_demonstrated`,
`motion_verified`, and `decision_ready`; `art_director_approved` remains false until KC decides.
Canonical round, brief, packet, attempt, receipt, and review
paths are derived from the Study vault rather than trusted from mutable manifest strings. Each
attempt packet must equal the frozen base packet plus only its generated attempt ID. Captured
stdout and stderr are streamed through one-megabyte on-disk caps; overflow terminates the worker
and records the failure. A per-round exclusive lock prevents concurrent execution. Immediately
before aggregate release, the parent revalidates all packets, receipts, evidence paths, artifact
bytes, and recomputes split claim summaries. It also requires matching frame numbers, resolution,
renderer, color pipeline, and measured neutral camera/light/render/OCIO signature across all
candidates. `COMPARISON.md` presents parent-rendered matched
neutral renders, hero images, motion links, and annotated claim sheets before technical records.
Released `review-manifest.json`
and `COMPARISON.md` files are hash-bound by `review-seal.json`; calling review again verifies the
released package instead of silently trusting or overwriting it.
