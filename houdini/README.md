# Houdini integration

This directory contains versioned scene builders, VEX libraries, and Karma look tools;
it remains the source location for future HDAs, camera rigs, and instrumentation
systems. Binary HIP/HDA deliverables are generated or released artifacts; their source
intent should remain reviewable wherever Houdini permits it.

Planned conventions:

```text
houdini/python/       Scene construction and pipeline shelf tools
houdini/vex/          Reusable fields, neighborhoods, growth, and memory functions
houdini/otls/         Generated/local HDAs (ignored by default)
houdini/materials/    Karma material and look presets
houdini/overlays/     Instrumentation geometry and annotation systems
houdini/look_setups/  Reusable look templates (environments + lighting)
houdini/archive/      Unreferenced historical scripts, kept for reproducibility
```

Implemented study-level tools currently include deterministic Memory Field and Mass
Flow simulators, shared VEX integration helpers, volumetric flocking, derived 3D trail
and head construction, MaterialX assignment, HDRI dome lighting, Karma CPU/XPU output,
and reopenable generated HIP scenes. Generated scenes and media are indexed by the
local Review Studio rather than committed to Git.
