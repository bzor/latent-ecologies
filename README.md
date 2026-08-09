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
