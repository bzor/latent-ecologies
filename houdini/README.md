# Houdini integration

This directory will contain versioned scene builders, VEX libraries, HDAs, Karma
looks, camera behaviors, and instrumentation tools. Binary HIP/HDA deliverables
are generated or released artifacts; their source intent should remain reviewable
wherever Houdini permits it.

Planned conventions:

```text
houdini/python/       Scene construction and pipeline shelf tools
houdini/vex/          Reusable fields, neighborhoods, growth, and memory functions
houdini/otls/         Generated/local HDAs (ignored by default)
houdini/materials/    Karma material and look presets
houdini/overlays/     Instrumentation geometry and annotation systems
```

