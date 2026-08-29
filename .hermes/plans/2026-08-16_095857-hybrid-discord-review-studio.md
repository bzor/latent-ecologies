# Hybrid Discord + Review Studio Implementation Plan

> **Superseded on 2026-08-16:** KC selected Discord as the sole human interaction surface and a curated read-only public Study/archive instead of a web mutation/review interface. The active replacement plan is `2026-08-16_101926-discord-public-study.md`. This document is retained as historical design context only.

> **For Hermes:** Use strict RED → GREEN development when executing this plan. Do not commit, publish, upload, expose the local Studio publicly, delete legacy records, or modify Discord/Hermes credentials unless KC explicitly approves that action.

**Goal:** Reframe Bzor Computational Studio as a hybrid collaboration system where Discord forum threads are the mobile conversational surface, Review Studio is the canonical project/review/asset application, and the existing CLI/Houdini pipeline remains the production backend.

**Architecture:** Preserve the dependency-light file-backed Studio kernel, lifecycle records, safe artifact catalog, local media streaming, and verified runner boundary. Add first-class Study identity, private Discord-thread bindings, canonical cross-surface command receipts, and a unified review model. Replace the current all-purpose dashboard with a project-first review application; Discord initiates work but never becomes the authoritative database.

**Tech Stack:** Python 3.11, `unittest`, JSON Schema, atomic JSON records, dependency-free ES modules/HTML/CSS, local `ThreadingHTTPServer`, Hermes Discord gateway, Houdini 22/Hython/VEX, FFmpeg.

---

## 1. Product decision

### Surface responsibilities

| Surface | Owns | Explicitly does not own |
|---|---|---|
| Discord | Conversation, brainstorming, phone capture, references, requests, notifications, proxy previews | Canonical assets, lifecycle state, final approvals, lineage database |
| Review Studio | Study overview, Review Inbox, comparisons, timecoded review, decisions, lineage, components, specimens, storage projections | General-purpose chat, autonomous shell execution, public publication |
| CLI / Studio command service | Validated mutations, idempotent receipts, automation entry points used by Hermes from any surface | Creative interpretation without Hermes, arbitrary free-text execution |
| Houdini / runners | Simulation, rendering, caching, scene generation, receipts | Project-management authority, publication |

### Canonical-source rule

A Discord message may initiate an action, but the action is official only after the Studio command layer writes a validated record and returns a receipt ID. Discord attachments are review proxies or source references; canonical artifacts remain under contained project storage with checksums.

### Discord information architecture

Initial private server structure:

```text
COMPUTATIONAL STUDIO
├─ #studio-lobby        general planning and routing
├─ #field-notes         phone ideas, references, observations
├─ #review-inbox        mostly agent-posted completion/review notifications
└─ Studies              Discord Forum
   ├─ Study 003 — Nonlocal Affinity Dance   one persistent forum thread/session
   ├─ Study 004 — ...
   └─ ...
```

Use one main Discord forum thread per study at first. Do not create a thread for every lifecycle stage; Review Studio owns stage structure. Hermes already gives each Discord thread an isolated conversational session.

### Terminology correction

Reserve **conversation session** for Hermes/Discord context. Replace the user-facing meaning of the current Studio “session” with **Study workspace** or simply **Study**. The existing session records remain readable during migration and are never deleted.

---

## 2. Current implementation audit

### Retain

- `src/houdini_ai/studio_store.py`: atomic, contained file-backed storage.
- `src/houdini_ai/studio_schema.py` and `schemas/studio/`: typed private records.
- `src/houdini_ai/studio_api.py`: application-service boundary; expand rather than bypass.
- `src/houdini_ai/artifact_catalog.py`: contained catalog, project grouping, media metadata, opaque URLs.
- `src/houdini_ai/review_studio.py`: byte-range media serving, local-only security, mutation token, path containment.
- `src/houdini_ai/review_inbox.py`: useful aggregation concept.
- Proposal, direction, experiment, promotion, component, specimen, editorial, lineage, and process-note modules.
- Existing tests and all historical records/artifacts.
- Dependency-free frontend until measured complexity proves a framework necessary.

### Refactor

- `website/index.html` and `website/app.js` currently combine cockpit, forms, direction workshop, catalog, legacy jobs, review, promotion, specimens, and editorial in one page.
- `src/houdini_ai/studio_cli.py` and `StudioAPI` duplicate some command behavior and do not emit one consistent machine-readable receipt.
- `studio_sessions.py` models one globally active workspace; Discord will support several independently active study threads.
- Legacy reviews under `work/reviews/` are separate from canonical Studio records and reference job paths instead of stable artifact IDs.
- Project identity is partly inferred from paths rather than represented directly.
- The Review Inbox is global and read-only; it needs project filtering and stable links to actionable records.

### Demote from primary UI

Keep as fallback/admin tools, not top-level destinations:

- manual Seed form;
- manual session creation form;
- large direction-authoring form;
- generic proposal card list;
- generic record grids;
- duplicated legacy Runs/Reviews navigation.

Discord becomes the preferred capture and brainstorming surface. The Studio still shows all resulting records and retains bounded decision controls.

### Do not build now

- custom web chat;
- custom Discord bot separate from Hermes;
- database migration;
- React/Vue/Svelte build chain;
- public internet exposure;
- Discord CDN as artifact storage;
- emoji-only canonical approval;
- automatic publication;
- automatic creation of many stage-specific Discord threads.

---

## 3. Target domain model

### Study

Create a canonical project record keyed by the existing project ID, e.g. `study-003-nonlocal-affinity-dance`.

Minimum fields:

```json
{
  "schema_version": 1,
  "id": "study-003-nonlocal-affinity-dance",
  "title": "Study 003 — Nonlocal Affinity Dance",
  "state": "active",
  "current_phase": "behavior",
  "intent": "...",
  "selected_branch_id": null,
  "approved_selection_ids": [],
  "unresolved_questions": [],
  "blockers": [],
  "recommended_next_action": "...",
  "created_at": "...",
  "updated_at": "...",
  "visibility": "private"
}
```

The existing global active-session pointer becomes an optional **focused study** pointer for the local UI only. It is not authority over which Discord thread may work.

### Conversation binding

Private operational record mapping a platform scope to a Study:

```json
{
  "schema_version": 1,
  "id": "binding-discord-study-003",
  "study_id": "study-003-nonlocal-affinity-dance",
  "platform": "discord",
  "guild_id": "...",
  "parent_channel_id": "...",
  "thread_id": "...",
  "state": "active",
  "created_at": "...",
  "visibility": "private"
}
```

Discord IDs are routing metadata, not creative intent and not credentials. Bot tokens remain exclusively in Hermes credential storage.

### Activity receipt

Append-only record for cross-surface mutations:

```json
{
  "schema_version": 1,
  "id": "activity-...",
  "study_id": "study-003-nonlocal-affinity-dance",
  "action": "artifact.decide",
  "actor": "kc",
  "origin": "discord",
  "idempotency_key": "discord:<message-id>:artifact.decide:<artifact-id>",
  "source_ref": "discord:<guild>:<thread>:<message>",
  "result_refs": ["artifact-..."],
  "summary": "KC held Neighbor and selected Mixed.",
  "created_at": "...",
  "visibility": "private"
}
```

The idempotency key prevents a recovered or duplicated Discord delivery from applying the same action twice.

### Canonical review record

Replace new writes to the legacy job-path review format with a stable artifact-ID-based record:

```json
{
  "schema_version": 1,
  "id": "review-...",
  "study_id": "study-003-nonlocal-affinity-dance",
  "artifact_id": "artifact-...",
  "kind": "decision",
  "decision": "hold",
  "text": "Preserve it, but do not advance it.",
  "timecode": 6.2,
  "status": "open",
  "origin_activity_id": "activity-...",
  "created_at": "...",
  "visibility": "private"
}
```

Legacy `work/reviews/*.json` stays readable through a compatibility projection until explicitly retired.

---

## 4. Canonical action flows

### Discord idea capture

```text
KC posts in #field-notes or a Study thread
→ Hermes identifies/binds Study context
→ Hermes invokes constrained Studio CLI command
→ command service validates and writes Idea + Activity receipt
→ Hermes replies with record ID and captured interpretation
```

No raw Discord text becomes shell or runner parameters.

### Discord proposal approval and experiment request

```text
KC asks for bounded work
→ Hermes creates Proposal record
→ cost/outputs/stop conditions returned in Discord
→ KC approves
→ command service records approval Activity
→ existing typed runner path executes
→ Artifact records and receipts are verified
→ proxy preview and Review Studio deep link returned to same Study thread
```

### Web review decision

```text
KC watches artifact in Review Studio
→ submits timecoded decision
→ web endpoint calls same command service
→ canonical Review + Activity records written
→ Review Inbox and Study activity update
→ optional Discord notification is deferred to notification phase
```

### Discord review decision

```text
KC says “promote Mixed; hold Neighbor”
→ Hermes resolves exact artifact IDs
→ one bounded command per decision with shared source message ID
→ records are idempotent
→ Hermes returns canonical result IDs
```

### Attachment/reference flow

```text
Discord attachment or URL
→ treat as external source reference
→ copy into contained private source storage only when needed
→ hash and record provenance
→ never treat Discord CDN URL as permanent canonical storage
```

---

## 5. Implementation sequence

## Milestone H0: Record the hybrid architecture decision

**Objective:** Make the new surface contract explicit before changing code.

**Files:**
- Create: `docs/HYBRID_STUDIO_ARCHITECTURE.md`
- Modify: `docs/STUDIO_ARCHITECTURE.md`
- Modify: `docs/STUDIO_PROTOCOL.md`
- Modify: `docs/STUDIO_ROADMAP.md`
- Modify: `website/README.md`
- Reference: `.hermes/plans/2026-08-15_112312-computational-studio-golden-path.md`

**Steps:**

1. Add a failing documentation assertion in `tests/test_studio_hybrid_docs.py` requiring the Discord/Studio/CLI ownership table and canonical-source rule.
2. Run: `PYTHONPATH=src python -m unittest tests.test_studio_hybrid_docs`
3. Write the architecture document and update existing docs without deleting historical roadmap content.
4. Mark this plan as a refinement of the golden path, not a replacement for its creative milestones.
5. Run the focused documentation test.

**Exit gate:** A collaborator can explain where chat, decisions, files, compute, and publication authority live.

---

## Milestone H1: Introduce canonical Study workspaces

**Objective:** Replace the single-global-session assumption with first-class project identity while preserving all existing session records.

**Files:**
- Create: `schemas/studio/study.schema.json`
- Create: `src/houdini_ai/studies.py`
- Create: `tests/test_studies.py`
- Create: `scripts/migrate_studio_sessions_to_studies.py`
- Modify: `src/houdini_ai/studio_schema.py`
- Modify: `src/houdini_ai/studio_api.py`
- Modify: `src/houdini_ai/studio_cli.py`
- Modify: `tests/test_studio_schema.py`
- Modify: `tests/test_studio_api.py`
- Modify: `tests/test_studio_cli.py`

**TDD sequence:**

1. Write a failing schema test for a valid `study-003-nonlocal-affinity-dance` record and invalid public/path-like records.
2. Write a failing service test proving two Studies can both be active while only one is the local UI focus.
3. Implement `create_study`, `update_study`, `list_studies`, `focus_study`, and `focused_study`.
4. Add `StudioAPI` and JSON CLI commands for those operations.
5. Write a migration test using current `session-*` fixtures. Require:
   - dry-run by default;
   - deterministic Study IDs based on existing `project_slug`/known project ID;
   - no deletion or mutation of source session records;
   - idempotent repeated apply;
   - conflict report rather than overwrite.
6. Run the dry-run against real local records and save its report.
7. Ask KC before applying the real migration.

**Compatibility:** Existing `/api/studio/session*` and CLI session commands remain available through the migration window. User-facing UI stops calling them after H5.

**Exit gate:** Study 003 and Scar Tissue have canonical Study records; Discord activity in one Study cannot steal “active session” status from another.

---

## Milestone H2: Add Discord conversation bindings

**Objective:** Reliably resolve a Discord forum thread to one canonical Study without embedding Discord concerns in creative records.

**Files:**
- Create: `schemas/studio/conversation-binding.schema.json`
- Create: `src/houdini_ai/conversation_bindings.py`
- Create: `tests/test_conversation_bindings.py`
- Modify: `src/houdini_ai/studio_schema.py`
- Modify: `src/houdini_ai/studio_api.py`
- Modify: `src/houdini_ai/studio_cli.py`
- Modify: `tests/test_studio_api.py`
- Modify: `tests/test_studio_cli.py`

**TDD sequence:**

1. Write failing tests for bind, resolve, deactivate, and duplicate active-thread rejection.
2. Reject malformed platform IDs, unknown Study IDs, public visibility, and path-like values.
3. Implement atomic binding records under `work/studio/conversation-bindings/`.
4. Add machine-readable commands:

```powershell
houdini-ai studio bind-conversation --study study-003-nonlocal-affinity-dance --platform discord --guild-id <id> --parent-channel-id <id> --thread-id <id>
houdini-ai studio resolve-conversation --platform discord --thread-id <id> --json
```

5. Never store or request bot tokens in this project.
6. Bind the existing Study 003 forum thread only after its real IDs are available from the gateway context or KC.

**Discord configuration acceptance:**

- Forum parent or selected threads are mention-free only if KC wants that behavior.
- `#review-inbox` should be bot-focused; ordinary chatter belongs in Study threads.
- Verify thread replies remain in the same isolated Hermes session.

**Exit gate:** Given a Discord thread ID, the system returns exactly one Study ID or an explicit unbound result.

---

## Milestone H3: Create one idempotent cross-surface command service

**Objective:** Ensure Discord, web, and CLI mutations share validation, receipts, and duplicate protection.

**Files:**
- Create: `schemas/studio/activity.schema.json`
- Create: `src/houdini_ai/activity_log.py`
- Create: `src/houdini_ai/studio_commands.py`
- Create: `tests/test_activity_log.py`
- Create: `tests/test_studio_commands.py`
- Modify: `src/houdini_ai/studio_api.py`
- Modify: `src/houdini_ai/studio_cli.py`
- Modify: `tests/test_studio_api.py`
- Modify: `tests/test_studio_cli.py`

**Core interface:**

```python
@dataclass(frozen=True)
class CommandContext:
    study_id: str
    actor: str
    origin: str
    source_ref: str
    idempotency_key: str


def execute_command(
    store: StudioStore,
    context: CommandContext,
    action: str,
    payload: dict[str, object],
) -> dict[str, object]:
    ...
```

**TDD sequence:**

1. RED: duplicate idempotency key currently applies a mutation twice.
2. GREEN: activity lookup returns the existing result without reapplying.
3. RED/GREEN one vertical command at a time:
   - idea capture;
   - process note capture;
   - direction decision;
   - proposal approval/hold;
   - artifact review decision;
   - component promotion.
4. Keep runner execution outside generic command parsing. Commands may reference only registered runners and typed records through existing safety gates.
5. Add `--json`, `--origin`, `--source-ref`, and `--idempotency-key` to relevant CLI commands while preserving human-readable defaults.
6. Refactor `StudioAPI` and CLI handlers to delegate to this service rather than duplicating mutations.

**Exit gate:** Replaying the same Discord source message cannot duplicate a decision, promotion, or idea.

---

## Milestone H4: Canonicalize artifact reviews and project-filter the inbox

**Objective:** Give Discord and the web one stable review model based on artifact IDs rather than transient job paths.

**Files:**
- Create: `schemas/studio/review.schema.json`
- Create: `src/houdini_ai/studio_reviews.py`
- Create: `tests/test_studio_reviews.py`
- Create: `scripts/migrate_legacy_reviews.py`
- Modify: `src/houdini_ai/review_inbox.py`
- Modify: `src/houdini_ai/review_studio.py`
- Modify: `src/houdini_ai/studio_api.py`
- Modify: `tests/test_review_inbox.py`
- Modify: `tests/test_review_studio.py`
- Modify: `tests/test_studio_api.py`

**TDD sequence:**

1. Add failing schema tests for comments, timecoded decisions, responses, valid transitions, and artifact containment.
2. Add failing project-filter tests: `build_review_inbox(root, study_id=...)` must return only the selected Study plus global workflow items explicitly marked global.
3. Implement canonical review creation through `studio_commands.py`.
4. Keep `ReviewStore` read compatibility for legacy records; route new writes to `work/studio/reviews/`.
5. Implement a dry-run/idempotent legacy migration that resolves job-path references through the artifact catalog and reports unresolved records without deletion.
6. Add stable deep-link metadata to inbox items: Study ID, artifact ID, review ID, and target Studio query parameters.
7. Add `GET /api/studio/studies/<id>/inbox` and canonical review endpoints; keep old `/api/reviews/*` routes during migration.

**Exit gate:** A review created from Discord appears in the same Study inbox as a review created in the browser, with one canonical artifact reference.

---

## Milestone H5: Add project-first query projections

**Objective:** Make frontend rendering simple and prevent it from reassembling domain state from many unrelated collections.

**Files:**
- Create: `src/houdini_ai/study_projection.py`
- Create: `tests/test_study_projection.py`
- Modify: `src/houdini_ai/artifact_catalog.py`
- Modify: `src/houdini_ai/studio_api.py`
- Modify: `src/houdini_ai/review_studio.py`
- Modify: `tests/test_artifact_catalog.py`
- Modify: `tests/test_review_studio.py`

**Read-only projections:**

- `GET /api/studio/studies`
- `GET /api/studio/studies/<id>`
- `GET /api/studio/studies/<id>/activity`
- `GET /api/studio/studies/<id>/inbox`
- `GET /api/studio/studies/<id>/artifacts`
- `GET /api/studio/studies/<id>/lineage`
- `GET /api/studio/studies/<id>/components`
- `GET /api/studio/studies/<id>/specimens`

**TDD sequence:**

1. Build fixtures containing two Studies with overlapping tracks and legacy artifacts.
2. Require stable sorting, explicit validation errors, no private filesystem targets, and no Discord IDs except in an authenticated/private Study-detail projection.
3. Move catalog project filtering to the server while retaining the existing full catalog endpoint temporarily.
4. Add latest artifact, open review count, current phase, selected branch, blockers, and recommended next action to Study summaries.
5. Ensure projection errors are surfaced rather than silently dropping malformed records.

**Exit gate:** The frontend can render any Study page from one overview request plus focused sub-resource requests.

---

## Milestone H6: Rebuild Review Studio as a project-first application shell

**Objective:** Turn the browser into a focused visual review/storage application rather than a second conversation interface.

**Files:**
- Modify: `website/index.html`
- Modify: `website/styles.css`
- Replace gradually: `website/app.js`
- Create: `website/studio/api.js`
- Create: `website/studio/router.js`
- Create: `website/studio/state.js`
- Create: `website/studio/dom.js`
- Create: `website/studio/views/studies.js`
- Create: `website/studio/views/overview.js`
- Create: `website/studio/views/inbox.js`
- Create: `website/studio/views/review.js`
- Create: `website/studio/views/artifacts.js`
- Create: `website/studio/views/lineage.js`
- Create: `website/studio/views/records.js`
- Create: `tests/test_studio_frontend.py`
- Modify: `tests/test_review_studio.py`

**Information architecture:**

```text
Global
├─ Studies
├─ Review Inbox
└─ Instruments

Selected Study
├─ Overview
├─ Review
├─ Artifacts
├─ Lineage
├─ Decisions & Notes
└─ Package (when relevant)
```

Components, specimens, proposals, directions, and editorial records appear in Study context. A global library view can return later when there is enough cross-study material to justify it.

**Primary Study page:**

- title, state, phase, question/intent;
- recommended next action;
- open decisions and blockers;
- latest verified comparison;
- promoted selections;
- recent activity from Discord/web/CLI;
- Discord thread link when bound.

**Review workspace:**

Retain and improve the strongest current interaction:

- large media stage;
- A/B or three-way comparisons;
- synchronized playback where media durations match;
- timecoded notes;
- keep/iterate/mutate/hold/archive/reject/promote controls;
- provenance and parameters;
- sibling preservation visibility;
- direct canonical receipt after mutation.

**Demoted forms:**

Manual seed, direction, proposal, and Study creation forms move into a collapsed `Records / manual fallback` area or CLI documentation. Do not delete their backend operations.

**Frontend implementation rules:**

1. Use native ES modules; do not introduce a build tool in this milestone.
2. Preserve text-safe DOM construction; no untrusted `innerHTML`.
3. Use query-string routing compatible with the current static server:
   - `/?study=study-003-nonlocal-affinity-dance&view=review&artifact=artifact-...`
4. Create a coherent design-token layer in CSS before styling individual views.
5. Optimize desktop review first, then a useful narrow/mobile read-only layout. Full remote phone access is a later security milestone.
6. Preserve `/affinity.html` as a Study instrument, linked from Study 003 rather than global primary navigation.

**TDD sequence:**

1. RED/GREEN route parsing and deep-link serialization.
2. RED/GREEN safe Study list and empty/error states.
3. RED/GREEN project overview projection rendering.
4. RED/GREEN Review Inbox links.
5. RED/GREEN media player and decision receipt rendering.
6. RED/GREEN legacy catalog URL compatibility.
7. Browser visual QA at wide, laptop, and narrow widths.

**Exit gate:** Opening Review Studio answers “which Study, what needs attention, what evidence is ready, and what decision can I make?” without presenting conversational authoring forms first.

---

## Milestone H7: Pilot the real Discord workflow with Study 003

**Objective:** Validate the hybrid workflow before building notifications, buttons, or remote web access.

**Repository changes:**
- Modify: `docs/HYBRID_STUDIO_ARCHITECTURE.md` with operator workflow.
- Create: `docs/DISCORD_STUDY_WORKFLOW.md`
- Add only missing CLI/command tests revealed by the pilot.
- Capture friction through canonical process notes.

**Pilot steps:**

1. Confirm the real forum channel and Study 003 thread IDs through the working Hermes gateway.
2. Bind that thread to `study-003-nonlocal-affinity-dance`.
3. Verify mention/free-response behavior in the forum parent and thread.
4. From the phone/Discord thread, exercise:
   - capture one process note;
   - request one bounded comparison;
   - receive one preview attachment and Studio deep link;
   - hold one branch;
   - select or promote one artifact;
   - request current Study status.
5. Verify every mutation has one Activity receipt and no duplicate action after message replay/recovery.
6. Verify the same records appear in the local Review Studio.
7. Record usability friction before changing the UI further.

**Do not add yet:** custom Discord components, reaction approvals, webhooks, or automated channel creation.

**Exit gate:** KC can progress Study 003 from a phone and later inspect the same canonical state in Review Studio with no manual reconciliation.

---

## Milestone H8: Add bounded preview/share projections

**Objective:** Make phone review useful without turning Discord into canonical storage.

**Files:**
- Create: `src/houdini_ai/review_share.py`
- Create: `tests/test_review_share.py`
- Modify: `src/houdini_ai/studio_cli.py`
- Modify: `src/houdini_ai/studio_api.py`

**Behavior:**

- Given a verified artifact ID, return a safe share projection:
  - Study title;
  - artifact title/role;
  - compact evidence summary;
  - contained proxy-media path;
  - checksum;
  - Review Studio deep link;
  - decisions currently requested.
- Generate a compressed proxy only when the original is unsuitable for Discord; preserve the original.
- Do not upload automatically from the core service. The gateway agent decides delivery in the originating thread.
- Record delivered preview metadata as Activity, not as a new canonical artifact unless the proxy itself has durable editorial value.

**Tests:** containment, verified-only source, deterministic metadata, no secret/local absolute path leakage in message text, proxy checksum, and no implicit publication.

**Exit gate:** Hermes can post a useful Discord review card from one verified artifact ID without hand-assembling paths.

---

## Milestone H9: Optional notifications after the pilot

**Objective:** Notify the correct Study thread when bounded work completes, without coupling runners to Discord APIs.

**Preferred design:** local, platform-neutral notification outbox consumed by Hermes/gateway integration.

**Potential files:**
- Create: `schemas/studio/notification.schema.json`
- Create: `src/houdini_ai/notification_outbox.py`
- Create: `tests/test_notification_outbox.py`

**Rules:**

- Runner completion writes a local event, not a Discord HTTP call.
- Event references Study and artifact IDs, never arbitrary attachment paths.
- Delivery adapter resolves the active conversation binding.
- Delivery retries are idempotent and preserve failure state.
- Completion notification is not inserted as a creative decision.
- Do not implement until the manual Study 003 pilot proves which notifications are valuable.

---

## Milestone H10: Optional private remote Review Studio

**Objective:** Allow secure phone access to the full web review interface only after local hybrid use is stable.

**Not part of initial implementation.** The current server deliberately accepts loopback authority and should remain local.

Before implementation, write a separate threat model covering:

- Tailscale/private-network access;
- authentication and mutation-token delivery;
- trusted proxy headers;
- TLS termination;
- read-only versus mutation routes;
- origin/CSRF policy;
- media range requests;
- loss/stolen-phone response;
- audit logs and revocation.

Do not bind Review Studio to `0.0.0.0` or expose it through a public tunnel as a shortcut. Discord proxy previews cover the initial mobile requirement.

---

## 6. Migration and compatibility policy

1. Never delete or rewrite existing `session-*`, legacy review, artifact, experiment, or handoff records.
2. Every migration script defaults to dry-run and writes a machine-readable report.
3. Apply mode must be explicitly requested and idempotent.
4. Preserve current URLs during one full Study 003 cycle:
   - `/api/jobs`;
   - `/api/reviews/*`;
   - `/api/studio/session*`;
   - `/api/studio/catalog`;
   - `/media/*`;
   - `/catalog-media/*`.
5. Add compatibility warnings to logs before retiring routes; do not show noisy warnings to KC during ordinary review.
6. Keep the current Review Studio usable at each milestone. Do not perform a flag-day frontend rewrite.
7. Keep all new records private by default.

---

## 7. Verification strategy

### Focused tests

```powershell
$env:PYTHONPATH = "src"
python -m unittest tests.test_studies
python -m unittest tests.test_conversation_bindings
python -m unittest tests.test_activity_log tests.test_studio_commands
python -m unittest tests.test_studio_reviews tests.test_review_inbox
python -m unittest tests.test_study_projection
python -m unittest tests.test_studio_frontend tests.test_review_studio
```

### Full regression

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
python -m py_compile `
  src/houdini_ai/studies.py `
  src/houdini_ai/conversation_bindings.py `
  src/houdini_ai/activity_log.py `
  src/houdini_ai/studio_commands.py `
  src/houdini_ai/studio_reviews.py `
  src/houdini_ai/study_projection.py
git diff --check
```

Do not claim Ruff passed unless `ruff` is available and actually executed.

### HTTP/security acceptance

- existing byte-range tests remain green;
- path traversal remains rejected;
- non-loopback Host/Origin remains rejected before H10;
- mutation token required for browser writes;
- Discord IDs never grant filesystem access;
- free text cannot select commands/runners;
- idempotency replay tests pass;
- malformed cross-study references fail closed.

### Real workflow acceptance

- one Discord forum thread resolves to one Study;
- a Discord idea/decision creates a canonical receipt;
- replay creates no duplicate;
- a web decision uses the same command service;
- both appear in one Study activity feed;
- a verified artifact preview reaches Discord as a proxy while the original remains canonical;
- Review Studio deep link opens the intended Study/artifact;
- all prior Study 003 artifacts remain viewable;
- nothing is published or publicly exposed.

---

## 8. Risks and tradeoffs

### Context fragmentation across Discord threads

Mitigation: one thread per Study; structured Study records and activity receipts carry durable state; avoid stage micro-threads initially.

### Two sources of truth

Mitigation: Discord messages are requests; only validated Studio records are authoritative. Every consequential reply includes receipt IDs.

### Duplicate Discord delivery

Mitigation: mandatory idempotency keys derived from source message + action + target.

### Frontend rewrite scope

Mitigation: preserve backend routes and migrate views incrementally. Build Study overview and review workspace before cosmetic breadth.

### File-backed query performance

Mitigation: retain current cache/index patterns and measure before adopting SQLite. Revisit storage only after project-filtered projections expose real bottlenecks.

### Mobile Review Studio security

Mitigation: defer remote web access; use Discord proxy previews first; require a separate security plan for private networking.

### Discord lock-in

Mitigation: conversation bindings are operational adapters; all Studies, activities, reviews, and artifacts remain local and platform-neutral.

### Over-structuring creative conversation

Mitigation: Discord remains natural conversation. Hermes—not KC—translates clear intent into records and only asks clarification when the consequential action is genuinely ambiguous.

---

## 9. Recommended first implementation slice

Implement only H0 through H3, then run a narrow Study 003 Discord pilot before rebuilding the frontend.

Why:

1. Study identity and conversation bindings solve the architectural mismatch.
2. Activity/idempotency receipts make Discord safe as a control surface.
3. The existing Review Studio remains usable during the pilot.
4. Real Discord use will reveal which current web forms are redundant and which review screens deserve design investment.
5. UI redesign after the pilot will be evidence-led rather than speculative.

Initial completion gate:

```text
Study 003 Discord thread
→ resolve canonical Study
→ capture note or decision
→ receive stable receipt ID
→ see same state in existing Review Studio
```

Only after that gate should implementation proceed to canonical review migration and the major interface redesign.

---

## 10. Open questions to resolve during implementation, not before planning

1. Exact Discord guild/forum/thread IDs for the existing server.
2. Whether the Studies forum parent should be mention-free or only selected threads.
3. Whether `#field-notes` should bind to a global inbox Study or require explicit Study routing.
4. Which Study 003 artifact should be the first phone-review pilot.
5. Whether web decisions should trigger Discord notifications automatically after the manual pilot.
6. Whether remote Review Studio is still needed once proxy previews and Discord decisions are exercised in practice.

None of these block H0–H3.
