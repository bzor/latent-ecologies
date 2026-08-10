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
website/            Future public field notebook
work/               Local caches and renders (ignored by Git)
```

Start with [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md), then read
[docs/WORKFLOW.md](docs/WORKFLOW.md). The immediate implementation sequence is in
[docs/VERTICAL_SLICE_PLAN.md](docs/VERTICAL_SLICE_PLAN.md).

## Quick start

Python 3.10 or newer is supported.

```powershell
python -m houdini_ai doctor
python -m houdini_ai validate studies/001-memory-field/study.json
python -m unittest discover -s tests
python -m ruff check src tests houdini/diagnostic_scene.py
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
