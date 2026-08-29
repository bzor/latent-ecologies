# Look Development — Rapid Surgical Zipper

Current variation: `var_004_rapid-surgical-zipper`  
Artist starter: `var_004_rapid-surgical-zipper.look_r001.hiplc`

The frozen Behavior is imported from `../01_behavior/03_selected/selection_002/` for frames 1–300 at 30 fps. The Curve-first starter retains all 256 promoted points and 384 authoritative bank/zipper primitives.

## Render layers

- **Points:** packed sphere copies imported to Solaris as `/World/RenderPoints/instances` (`PointInstancer`).
- **Edges:** bank and zipper polylines imported as `/World/RenderEdges/bank_edges` and `/World/RenderEdges/zipper_edges` (`BasisCurves`).
- **Environment:** the Basic template neutral floor.

## Primary controls

- `/obj/PLAYGROUND_SIM/point_radius`
- `/obj/PLAYGROUND_SIM/bank_width`
- `/obj/PLAYGROUND_SIM/zipper_width`
- `/stage/MATERIALS_STARTER/POINTS_STARTER_SHADER`
- `/stage/MATERIALS_STARTER/EDGES_STARTER_SHADER`
- `/stage/SELECT_LIGHTING_MODE`
- `/obj/main_cam`
- `/stage/RENDER_KARMA_SETTINGS`

The saved Karma XPU output is 1080×1350 at the Basic template's 64 spp / 128 path-traced samples. Depth of field is disabled in the neutral starter so the point/edge topology stays inspectable; re-enable it only as an artist-owned Look decision. Render output defaults to `var_004_rapid-surgical-zipper.look_r001.renders/beauty.$F4.exr`.

KC now owns this HIP. Hermes must not regenerate over it. Save revisions in place as `look_r002`, `look_r003`, and so on. Rendering begins only after KC identifies and locks the authoritative revision.
