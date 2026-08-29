# Basic Look setup

`basic.hiplc` is the default artist-ready Look starter. It was extracted directly from KC's first hand-edited Study 003 Look experiment, not reconstructed by Hermes. The only post-extraction change was replacing the obsolete round-local render output with `$HIP/renders/basic.$F4.png`.

## Character

The setup keeps the promoted simulation visible, adds a Trail SOP branch, merges trails with the live points, provides a neutral floor, editable MaterialX starters, KC's OBJ camera, multiple dome choices, the optional photographer rig, and Karma XPU output.

It is intentionally a starting point—not completed Look Development.

## Instantiation

When a new Behavior enters Look Development, Hermes runs
`houdini/instantiate_look_starter.py`, which:

1. copies `basic.hiplc` directly into the Study's flat `02_look` directory, named
   `look.hiplc` unless KC asks for another name;
2. copies the promoted behavior HDA beside the HIP and installs it;
3. creates a `PROMOTED_BEHAVIOR` HDA node inside `/obj/PLAYGROUND_SIM` and wires it
   into `ENSURE_POINT_VISIBILITY` — the behavior stays live and re-simmable;
4. leaves `SOURCE_PROMOTED_SIMULATION` disconnected as a documented cache fallback
   for heavy sims that later bake;
5. changes `/stage/RENDER_KARMA_SETTINGS/picture` to a path local to the new Study;
6. checks the three local HDRI dependencies and reports any missing files;
7. reopens the saved HIP, cooks the simulation output at representative frames, and
   writes a `*.starter-receipt.json` beside the HIP;
8. returns the file to KC as `artist-ready-starter`.

Do not alter the camera, trails, materials, lighting, framing, samples, or graph layout unless KC asks during the setup brainstorm.

After KC edits the copied HIP, that Study file is authoritative. Never regenerate over it.

## Source and verification

- Template: `E:\Projects\houdini-ai\houdini\look_setups\basic\basic.hiplc`
- Setup receipt: `E:\Projects\houdini-ai\houdini\look_setups\basic\setup.json`
- Fresh-Hython inventory: `E:\Projects\houdini-ai\houdini\look_setups\basic\inspection.json`
- Original KC source SHA-256: `1ad73f9acc8b3d8f946ffd27cf76d5421873db2f13b91e4bef65210be05bca68`
- Portable template SHA-256: `070d6875e4e77051c09056960bbc1420f231fbb8dafa05aa227dad553f70f5cb`
- Houdini: 22.0.368 Indie

The source and copied template had identical byte hashes at extraction. Their current hashes differ only because the copied template's render output was rebound and the HIP was resaved.
