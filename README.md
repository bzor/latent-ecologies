# Houdini AI — Computational Natural History

An automation-first creative laboratory for VEX-heavy Houdini systems inspired by
natural processes, artificial life, cellular automata, flocking, esoteric
computation, and unfamiliar rule spaces.

The project treats the artist and AI as collaborators. The goal is not to produce
isolated “AI-generated” effects, but to observe, propose, test, mutate, interpret,
and publish evolving artificial ecologies.

## Principles

- Local rules before predetermined shapes.
- Emergence, accidents, and failed experiments are valuable outputs.
- The artist spends time on direction and taste—not frame handling or encoding.
- Every published specimen retains its seed, rule lineage, and environment.
- Public participation is welcome but never required.
- Instrumentation explains what is measured, derived, observed, or hypothesized.

## Repository map

```text
config/             Shared project and render defaults
docs/               Vision, architecture, workflow, and roadmap
houdini/            Houdini packages, HDAs, materials, and scene tools
src/houdini_ai/     Automation CLI and pipeline code
studies/            One reproducible directory per experiment
tests/              Automation tests
website/            Local review studio; future public field notebook
work/               Local caches and renders (ignored by Git)
```

Start with [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md), then read
[docs/WORKFLOW.md](docs/WORKFLOW.md). The immediate implementation sequence is in
[docs/VERTICAL_SLICE_PLAN.md](docs/VERTICAL_SLICE_PLAN.md).
The implemented review milestones and next interaction work are tracked in
[docs/REVIEW_STUDIO_PLAN.md](docs/REVIEW_STUDIO_PLAN.md).

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

## First vertical slice

Study 001 is a memory-field experiment. Its first milestone is deliberately
small: construct a deterministic Houdini scene, cache a short simulation, render
a PNG sequence in Karma, validate the frames, encode platform variants, and
prepare a local field-note and post draft for approval.

The complete local vertical slice and the first Phase 2 Mass Flow study now feed the
local Review Studio. The current regression suite contains 36 tests, including HTTP
range delivery, path-containment, artifact discovery, and feedback round trips.
