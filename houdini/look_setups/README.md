# Look setup library

This directory contains jointly authored starter setups for the artist-led Look workflow.

The default entry is `basic/`, extracted from KC's first hand-edited Study 003 Look experiment.
Do not populate the library with speculative autonomous Look systems. A new setup is added only
when KC explicitly asks to preserve a setup or collaborates on its design.

Each setup should use a stable directory ID and eventually include:

- `SETUP.md` — purpose, visual use, limitations, and artist notes;
- `setup.json` — identity, compatibility, parameters, source Behavior expectations, and version;
- `build.py` — deterministic starter-HIP builder or adapter;
- `verify.py` — cheap reopen/cook checks where useful;
- `assets/` — optional MaterialX, HDRI, geometry, or presets;
- `examples/` — KC-approved reference images.

The active workflow is documented at:

`E:\Projects\houdini-ai\docs\ARTIST_LED_LOOK_HANDOFF.md`
