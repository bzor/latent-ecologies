# Bzor Computational Studio

An automation-first system for constructing, testing, and documenting computational
models, then producing reproducible audiovisual specimens in Houdini. Its scope
includes agent-based models, cellular automata, graph dynamics, field methods,
collective motion, stochastic processes, and rule-based simulation.

KC Austin defines the research direction and presentation. Hermes supports literature
review, hypothesis formation, implementation, parameter exploration, instrumentation,
validation, rendering, and reproducible packaging. Scientific and technical claims must
remain tied to sources, defined measurements, or identified observations.

## Current direction

The studio runs one explicit pipeline: Discord Seed Bank → Study brainstorm →
behaviour production (threeJS prototype or straight Houdini) → live-HDA + look
template → artist-led look development → locked render → realtime detail pass →
final package → approval-gated publishing. Every promotion is an explicit KC
decision with a durable local record.

Start here:

- [Vision — the canonical pipeline](docs/VISION.md)
- [Scientific and technical voice](docs/TECHNICAL_VOICE.md)
- [Discord public studio architecture](docs/DISCORD_PUBLIC_STUDIO_ARCHITECTURE.md)
- [KC–Hermes studio protocol](docs/STUDIO_PROTOCOL.md)
- [Studio architecture](docs/STUDIO_ARCHITECTURE.md)
- [Study vault directory contract](docs/STUDY_VAULT.md)
- [Artist-led Look handoff](docs/ARTIST_LED_LOOK_HANDOFF.md)
- [Render integrity](docs/RENDER_INTEGRITY.md)
- [Detail-pass promote](docs/DETAIL_PASS_PROMOTE.md)
- [threeJS prototype route](docs/THREEJS_PROTOTYPE_ROUTE.md)

Superseded vision, roadmap, and prototype-era plans are preserved in
[docs/archive/](docs/archive/).

## Principles

- Define local rules, state, update order, and boundary conditions before presentation.
- Preserve anomalous, null, and failed experiments when they provide evidence.
- KC spends time on research direction and presentation, not frame handling or encoding.
- Every published specimen retains its seed, rule lineage, and environment.
- Public participation is welcome but never required.
- Instrumentation explains what is measured, derived, observed, or hypothesized.

## Repository map

```text
behavior-playground/  Shared browser-sim prototype harness (threeJS route)
config/             Shared project and render defaults
design-overlay-generator/  HUD overlay design system and headless renderer (detail pass)
docs/               Vision, architecture, and stage protocols
houdini/            Houdini packages, HDAs, materials, and scene tools
schemas/            JSON schemas for studio records and presets
scripts/            Pipeline helper scripts (render verify, overlay render, composite)
src/houdini_ai/     Automation CLI and pipeline code
studies/            Canonical numbered Study vaults and phase-owned artifacts
studio/             System-wide records and reusable components
tests/              Automation tests
website/            Local review studio; future public field notebook
work/               Disposable caches, staging, and legacy generated work
```

The canonical per-Study directory contract is defined in
[docs/STUDY_VAULT.md](docs/STUDY_VAULT.md). The prototype-era job pipeline is
documented in [docs/archive/WORKFLOW.md](docs/archive/WORKFLOW.md); it remains
supported as implementation history.

## Quick start

Python 3.10 or newer is supported.

```powershell
python -m houdini_ai doctor
python -m houdini_ai validate studies/001-memory-field/study.json
python -m houdini_ai plan studies/001-memory-field/study.json
python -m houdini_ai run studies/001-memory-field/study.json
python -m houdini_ai status studies/001-memory-field/study.json
python -m houdini_ai storage
python -m houdini_ai clean
python -m houdini_ai review
python -m houdini_ai studio seed "Agents reinforce paths until saturation makes them repellent"
python -m houdini_ai studio ideas
houdini-ai studio study-init study-003-nonlocal-affinity-dance
python -m unittest discover -s tests
python -m ruff check .
```

`plan` creates a deterministic workspace and stage receipts without launching
Houdini. `run` executes the complete local vertical slice: validated scene build and
diagnostic probe, deterministic simulation, look-development checkpoints, resumable
Karma PNG sequence rendering, FFmpeg variants, and a checksummed draft publication
package. A repeated run reuses verified artifacts; missing or invalid sequence frames
are the only frames rendered again. Public posting is never performed.

The final local package is written beneath `work/jobs/<job-id>/package/` and includes
an archival ProRes master, 9:16 social video, 4:5 feed video, website video, preview
loop, poster, effective configuration, caption draft, alt text, field-note payload,
and checksums. Use `status` at any time to inspect resumable stage receipts.

If a run is interrupted, invoke the same `run` command again. Do not manually clear
the job directory: completed caches and frames are the resume state. Run `doctor` if
Houdini, Karma, FFmpeg, or licensing fails; detailed subprocess output is preserved
under the job's `logs/` directory. Machine-specific paths and environment values are
not copied into receipts or package metadata.

`storage` reports generated-work usage, free space, budgets, and per-job retention.
`clean` is a dry run unless `--apply` is supplied. Its defaults cover superseded
reproducible jobs, determinism-gate caches, and scratch files. Newest jobs are retained;
selected, approved, and published studies are protected; packages are never targets.
Full PNG sequences require the explicit `--category packaged-sequences` option.

`review` starts the local Review Studio at `http://127.0.0.1:8765`. It indexes
generated motion tests, lookdev stills, scenes, package media, receipts, provenance,
and selected simulation parameters. The browser can compare same-kind artifacts and
record comments or constrained decisions with optional video timecodes. Feedback is
written atomically beneath `work/reviews/`; it cannot execute commands or directly
modify VEX, manifests, HIP files, or render state.
Assistant replies can advance notes through acknowledged, implemented, and resolved
states and link completed work to a commit, replacement job, and verified artifacts.

The local Studio now also provides private idea capture, bounded proposals, component
promotion from verified lineage, proposal approve/hold controls, and editorial candidate
records. Its browser navigation separates Inbox,
Proposals, Runs / Reviews, Components, Specimens, and Editorial. These records are inert
local JSON: tagging an artifact never uploads or publishes it.

Scar Tissue now has three versioned mutation records, deterministic reference diagnostics,
and a separate sequential Houdini/VEX-authoritative probe. The latter persists agent and
oriented field geometry from one VEX cook to the next; it does not claim numerical parity
with the Python reference model. See `studies/behavior/scar-tissue/lab-log.md` for measured
scope and remaining observational evidence gaps.

```powershell
python -m houdini_ai clean
python -m houdini_ai clean --category smoke-caches --apply
python -m houdini_ai clean --category packaged-sequences
```

`doctor` searches `HOUDINI_BIN` and `FFMPEG_BIN`, then `PATH`, standard SideFX
installation directories, and WinGet FFmpeg packages on Windows. It probes Houdini
licensing and LOP/Karma availability and exits nonzero when a required tool is missing
or unusable. When SideFX's `hgpuinfo` is available, it summarizes CPU and GPU OpenCL
render devices without making optional accelerators a hard requirement. Either
environment variable may point to an executable or its containing directory; copy
`env.example` to `.env` as a reference, but load those values through your shell or
environment manager before invoking the CLI.

To reproduce the headless Karma smoke render on Windows, keep Houdini's temporary
files inside the writable project workspace and run the versioned scene builder:

```powershell
$env:HDAI_PROJECT_ROOT = (Get-Location).Path
$env:HOUDINI_TEMP_DIR = "$env:HDAI_PROJECT_ROOT\work\diagnostics\temp"
New-Item -ItemType Directory -Force $env:HOUDINI_TEMP_DIR | Out-Null
& "C:\Program Files\Side Effects Software\Houdini 22.0.368\bin\hython.exe" houdini\diagnostic_scene.py
```

The command writes `karma-headless.hiplc`, `karma-headless.0001.png`, and a
deterministically serialized `karma-headless.receipt.json` beneath
`work/diagnostics/`. It decodes the PNG and verifies dimensions, color mode,
visible content, and alpha before recording source, environment, and artifact
checksums in the receipt.

For a repeatable development environment, install with the checked-in constraints:

```powershell
python -m pip install -c constraints.txt -e ".[dev]"
```

For local development without installing the package:

```powershell
$env:PYTHONPATH = "$PWD/src"
python -m houdini_ai doctor
```

## First delivered Study

Study 001 (memory field) has completed the full pipeline end to end: promoted
behavior HDA, artist-led Look, verified 450-frame Karma render, realtime detail
pass in the overlay generator, and a checksum-bound promote to a post-ready
package in `04_delivery/` (2026-08-30, driven from the Discord Study thread).
It predates the `study_NNN_slug` vault contract and stays in place under its
legacy directory name.

The regression suite covers the pipeline stages, including HTTP range delivery,
path-containment, artifact discovery, detail-pass promote, and feedback round
trips.
