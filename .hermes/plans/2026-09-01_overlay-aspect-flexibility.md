# 2026-09-01 — Overlay generator aspect-flexibility pass + Study 001 9:16 reopen

KC direction captured 2026-08-31 (evening dev session). Process note:
`studio/notes/note-135ad4e7e27d.json`.

## Overlay generator (`design-overlay-generator/`) — long pass, KC-led

Goal: one overlay layout survives both delivery aspects (4:5 1080×1350 and
9:16 1080×1920) without manual re-layout per aspect.

KC's asks (wording preserved): "make things snap to corners and procedurally be
placed along the edges so it looks fine in either aspect ratio" — "more
flexible". KC has a backlog of further ideas to bring to the session.

Concrete directions implied:

- an anchor system: elements lock to corners and edges rather than absolute
  positions;
- procedural placement along edges (distribute/flow elements along a chosen
  edge);
- aspect-agnostic layout so one config renders correctly at both deliverable
  aspects;
- vertical-platform safe zones (right rail ~120 px, bottom ~320 px on
  Reels/TikTok; see `docs/SOCIAL_PUBLISHING.md` § Derivative matrix) should
  become visible guides or placement constraints, including a TikTok-sized
  guide variant.

Before working there: read `design-overlay-generator/CLAUDE.md` and
`DESIGN.md`.

## Study 001 — reopen for the 9:16 Look (live test case)

KC decision 2026-08-31: unlock Study 001 and author the vertical camera in the
Look HIP rather than shipping the padded vertical. This is the first run of the
dual-camera practice and deliberately exercises the whole loop so the process
is proven before Studies 002–004 reach their locks:

unlock → second 9:16 camera in the Look HIP → re-lock (new snapshot +
checksum) → overnight verified single-pass render per camera → 9:16 overlay
config through the reworked generator → detail pass → vertical delivery
package.

Notes:

- The existing 4:5 delivery package stands; this adds a vertical deliverable,
  it does not rework the shipped one.
- Render-integrity rules apply in full: new lock snapshot, single uninterrupted
  pass per camera, receipts bound to the new checksum
  (`docs/RENDER_INTEGRITY.md`).
- Learnings here feed the generator work and vice versa; expect iteration
  between the 9:16 overlay config and the new anchor system.
- Supersedes the padded-vertical acceptance recorded earlier the same day
  (`docs/SOCIAL_PUBLISHING.md` updated).

## Sequencing

- Hold the deferred `02_look/renders/` cleanup (~1.1 GB) until the vertical
  pass completes; the final 4:5 mp4 post also remains pending.
- After the vertical delivery exists, the Study 001 post kit can build both
  aspects from composed frames (no padding) and the first hero posts go out
  across all five platforms.
