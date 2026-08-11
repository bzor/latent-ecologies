---
name: field-note-implementation
description: Process open Houdini AI Review Studio field notes into serial, verified implementation tasks. Use when asked to review, triage, implement, address, or autonomously work through open field notes, review notes, or feedback in this project.
---

# Field Note Implementation

Run `python .codex/skills/field-note-implementation/scripts/list_open_field_notes.py`
from the project root. It reads only `work/reviews/*.json` and emits deterministic task
records for notes whose status is `open`.

For each emitted task, oldest first:

1. Create one explicit implementation-plan item. Keep only that item in progress.
2. Inspect the referenced job, artifact, study manifest, lab log, and current worktree.
   Form a bounded implementation plan from the note; do not broaden it into unrelated
   cleanup or redesign.
3. Record an `acknowledged` Review Studio response before changing the work. Use
   `scripts/respond_to_field_note.py` when the local API is unavailable. State the
   intended scope and any meaningful parameter changes.
4. Implement the task, preserving unrelated changes. Put generated media, caches, and
   task receipts under `work/`; never commit generated artifacts or local HDRIs.
5. Run focused checks plus relevant project tests. For simulation or render changes,
   run the deterministic smoke checks and produce the smallest meaningful review
   artifact before accepting the change.
6. Commit and push one coherent change. Reply to the note with status `implemented`,
   its commit, job id, and verified artifact paths. Leave it `implemented` for artist
   review; only mark it `resolved` after explicit approval or an explicit instruction
   to close it.
7. Mark the plan item completed and continue with the next open task.

Pause only for a material scope decision, missing credentials, an unrecoverable action,
or a dependency that prevents progress. Record the reason on the affected note before
asking the user. If an implementation fails but later notes are independent, record the
failure and continue serially.

Do not process notes already `acknowledged`, `implemented`, or `resolved` unless the
user explicitly asks to revisit them. Treat `open` as the queue, not as permission to
alter project-wide direction without validation.
