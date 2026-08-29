# Discord-Controlled Living Public Study Implementation Plan

> **For Hermes:** Execute with strict RED → GREEN development. Do not commit, publish, upload, expose credentials, deploy publicly, delete legacy records, or modify the working Discord gateway without KC’s explicit approval. Local code, tests, manifests, static previews, and dry-run migration reports are approved.

**Goal:** Make Discord the sole human interaction and decision surface while retaining a private local Studio as the canonical record vault and producing an explicitly curated, read-only public Study site that evolves during a project and freezes into a focused archive when it closes.

**Architecture:** Each Discord forum thread maps to one canonical Study. Hermes translates conversational choices into narrow, idempotent local commands and returns receipt IDs. New artifacts remain private until KC selects them for site inclusion. A static publisher consumes only allowlisted site-inclusion records, generates safe content-hashed derivatives and a public manifest, and never scans or publishes the working tree automatically.

**Tech Stack:** Python 3.11, `unittest`, JSON Schema, atomic JSON records, dependency-free static HTML/CSS/JavaScript, Hermes Discord gateway, Vercel-compatible static output, optional Supabase public Storage for approved media, Houdini 22/Hython/VEX, Pillow, FFmpeg.

## Execution checkpoint — 2026-08-16

Implemented and verified locally: D0 through D7 foundations, plus publication-rights and KC-confirmation gates from D8. The real legacy sessions were projected into canonical Studies without source modification. A zero-item Study 003 static shell was generated locally; no real artifact was included or published. Deferred decisions are recorded in `2026-08-16_101926-discord-public-study-decisions.md`.

Seed Bank extension completed locally: Discord `studies` and `seed-bank` forums were created, Study 003 was bound and retitled `Study 003 — Non-Local Affinity` without changing its stable internal ID, stable `idea-*` identities were extended into complete private Seeds, bounded brainstorm updates and idempotent Seed-to-Study promotion were added, and a separate rights-gated static public Seed Bank projection was implemented. Existing incomplete Ideas remain private. No deployment or public upload occurred.

---

## 1. Final surface contract

```text
Discord Study thread
  conversation, previews, buttons, decisions, requests
                 │
                 ▼
Private local Studio kernel
  Studies, bindings, receipts, lineage, complete artifact vault
                 │ explicit site inclusion only
                 ▼
Publication manifest + safe derivatives
                 │
                 ▼
Read-only living public Study / final archive
```

### Discord owns

- all human conversation and brainstorming;
- phone capture and references;
- preview delivery;
- taste polling and canonical choice buttons;
- requests, holds, selections, combinations, and archive curation;
- status and completion notifications.

### Private local Studio owns

- authoritative Study state;
- complete private assets, including failures and debugging evidence;
- exact lineage and checksums;
- proposals, experiments, creative promotions, and specimens;
- receipt-backed decisions from Discord;
- site-inclusion and archive-selection records;
- publication manifests and deploy receipts.

### Public website owns

- read-only visual presentation;
- selected evolution milestones;
- comparisons and media playback;
- curated public-safe lineage;
- final Study archive.

It has no login, account, comment, approval, mutation, shell, runner, or upload interface.

---

## 2. Editorial model

### Site inclusion is independent of creative promotion

- **Creative promotion:** selects a behavior, look, palette, or shot for downstream production.
- **Site inclusion:** permits an artifact to appear publicly.

An informative rejected branch can be public. A selected production component can remain private.

### Site states

- `private`: local only; no public derivative.
- `site-draft`: locally prepared public projection, not deployed.
- `site-live`: visible in the active living Study.
- `archive-keep`: selected for the closed Study archive.
- `retired`: omitted from the current focused page but treated as previously public.

Public exposure is effectively irreversible. Retiring an item does not claim that downloads, caches, indexes, screenshots, or old links disappeared.

### Default inclusion policy

Remain private automatically:

- caches and frame floods;
- HIP working scenes and internal packages;
- receipts, logs, machine paths, and operational diagnostics;
- redundant exports and routine parameter ticks;
- broken output without explanatory value;
- source material without confirmed publication rights;
- secrets and credentials.

Propose to KC through Discord:

- meaningful comparisons;
- representative behavioral or visual transitions;
- major discoveries;
- selected results;
- informative failures;
- explanatory diagrams and process evidence;
- milestones needed to understand the final work’s evolution.

---

## 3. Current codebase decision

### Preserve

- `src/houdini_ai/studio_store.py` atomic contained storage.
- Existing schemas and lifecycle services.
- `src/houdini_ai/artifact_catalog.py` and safe media containment.
- Existing Review Studio as a temporary local diagnostic/admin surface.
- Python/Hython/Houdini runner boundaries and receipts.
- All legacy sessions, reviews, handoffs, artifacts, and process notes.

### Reframe

- Current `session` records become compatibility input for first-class `Study` records.
- Current one-global-active-session pointer becomes optional local focus, not collaboration authority.
- Discord thread binding selects Study context.
- CLI/API mutation logic converges behind one idempotent command layer.
- The public site reads generated public manifests, never the private Studio API.
- Existing `website/` Review Studio is not deployed publicly.

### Do not build

- custom web chat;
- public web mutation routes;
- authentication or Supabase Auth;
- public database initially;
- Discord bot separate from Hermes;
- emoji-only canonical decisions;
- denylist-based workspace publishing;
- public upload or deployment during autonomous implementation;
- framework/build-chain migration before static-site needs justify it.

---

## 4. Canonical records

### Study

Canonical project workspace keyed by the existing Study/project identifier. Several Studies may be active concurrently; one may be locally focused.

### Conversation binding

Private operational mapping from Discord guild/forum/thread IDs to one Study ID. Never stores bot tokens.

### Activity receipt

Append-only record with Study, actor, origin, action, source message reference, result references, summary, timestamp, and unique idempotency key.

### Site inclusion

Private editorial record referencing one verified canonical artifact:

```json
{
  "schema_version": 1,
  "id": "site-inclusion-...",
  "study_id": "study-003-nonlocal-affinity-dance",
  "artifact_id": "artifact-...",
  "state": "site-draft",
  "public_title": "Tight Swirls — Cohort Lift",
  "public_caption": "...",
  "role": "comparison",
  "section": "behavior",
  "order": 30,
  "alt_text": "...",
  "included_by_activity_id": "activity-...",
  "created_at": "...",
  "updated_at": "...",
  "visibility": "private"
}
```

### Publication manifest

Generated allowlisted projection containing only public-safe fields, verified checksums, content-hashed derivative paths, media metadata, and safe lineage references. It performs no upload or deployment.

### Deploy receipt (later)

Records exact manifest hash, deployment provider, public URL, deployment identifier, time, and independently verified response. Credentials never enter the receipt.

---

## 5. Canonical interaction flows

### Preview and site inclusion

```text
Hermes completes and verifies artifact
→ sends proxy preview in Study Discord thread
→ KC chooses “include on living Study” or keeps private
→ constrained command resolves exact artifact ID
→ Activity receipt + site-draft record created idempotently
→ local static preview regenerated
→ public deployment remains a separate approved action
```

### Canonical decision

Use Hermes button choice or explicit conversational confirmation. Resolve labels to exact IDs before writing. Native Discord polls may gather taste evidence, but vote totals are not canonical project state.

### Study closure

```text
Hermes presents site-live items in manageable Discord batches
→ KC chooses archive keep / combine / rewrite / retire
→ archive decisions receive local receipts
→ frozen archive manifest generated and validated
→ deployment requires explicit approval
→ reopening creates a new revision
```

---

## 6. Implementation milestones

## Milestone D0: Document the Discord/public-site architecture

**Objective:** Remove the old assumption that the browser is a mutation surface.

**Files:**
- Create: `docs/DISCORD_PUBLIC_STUDIO_ARCHITECTURE.md`
- Modify: `docs/STUDIO_ARCHITECTURE.md`
- Modify: `docs/STUDIO_PROTOCOL.md`
- Modify: `docs/STUDIO_ROADMAP.md`
- Modify: `website/README.md`
- Create: `tests/test_discord_public_studio_docs.py`

**TDD:**

1. Write a failing documentation contract requiring the three-surface topology, explicit allowlist, site states, and no public mutations/login.
2. Run the focused test and confirm it fails for missing documentation.
3. Write/update documentation without deleting historical roadmap content.
4. Run the focused test and `git diff --check`.

**Exit gate:** A collaborator can identify the authority and privacy boundary for chat, records, artifacts, site inclusion, and deployment.

---

## Milestone D1: Introduce canonical Study records

**Objective:** Replace the one-global-session collaboration assumption while preserving session compatibility.

**Files:**
- Create: `schemas/studio/study.schema.json`
- Create: `src/houdini_ai/studies.py`
- Create: `tests/test_studies.py`
- Create: `scripts/migrate_studio_sessions_to_studies.py`
- Modify: `src/houdini_ai/studio_schema.py`
- Modify: `src/houdini_ai/studio_api.py`
- Modify: `src/houdini_ai/studio_cli.py`
- Modify: focused schema/API/CLI tests.

**Required behavior:**

- create, read, list, and update Studies;
- several Studies may have state `active`;
- one optional focused Study pointer for local convenience;
- no Study record is public merely because its site is public;
- dry-run session migration by default;
- deterministic project IDs;
- no source mutation/deletion;
- repeated apply is idempotent;
- conflicts report and fail closed rather than overwrite.

**Exit gate:** Study 003 and Scar Tissue can be represented without Discord activity stealing a global active pointer.

---

## Milestone D2: Add Discord conversation bindings

**Objective:** Resolve a forum thread to exactly one canonical Study.

**Files:**
- Create: `schemas/studio/conversation-binding.schema.json`
- Create: `src/houdini_ai/conversation_bindings.py`
- Create: `tests/test_conversation_bindings.py`
- Modify: schema/API/CLI modules and tests.

**Required behavior:**

- bind, resolve, and deactivate;
- reject unknown Study IDs and duplicate active bindings;
- validate numeric Discord identifiers as strings;
- store no credentials;
- provide JSON CLI output for Hermes;
- do not modify live gateway configuration autonomously.

**Blocked input:** Real guild/forum/thread IDs. Implement and test the capability; log actual binding as deferred until IDs are available in the originating Discord context.

---

## Milestone D3: Add idempotent activity receipts and command context

**Objective:** Make Discord retries safe and consequential choices official.

**Files:**
- Create: `schemas/studio/activity.schema.json`
- Create: `src/houdini_ai/activity_log.py`
- Create: `src/houdini_ai/studio_commands.py`
- Create: `tests/test_activity_log.py`
- Create: `tests/test_studio_commands.py`
- Modify: `src/houdini_ai/studio_cli.py`
- Modify: `src/houdini_ai/studio_api.py`

**Core interface:**

```python
@dataclass(frozen=True)
class CommandContext:
    study_id: str
    actor: str
    origin: str
    source_ref: str
    idempotency_key: str
```

**Vertical command slices:**

1. capture process note;
2. record artifact decision;
3. create site inclusion;
4. transition site state;
5. later refactor direction/proposal/component commands through the same layer.

Every slice follows RED → GREEN and returns the original result on replay.

---

## Milestone D4: Implement site-inclusion records

**Objective:** Separate creative promotion from public eligibility.

**Files:**
- Create: `schemas/studio/site-inclusion.schema.json`
- Create: `src/houdini_ai/site_inclusions.py`
- Create: `tests/test_site_inclusions.py`
- Modify: command/schema/CLI modules and tests.

**Rules:**

- source artifact must exist, validate, be verified, remain inside approved roots, and match its checksum;
- `private → site-draft → site-live → archive-keep` are explicit transitions;
- `site-live/archive-keep → retired` is allowed but preserves exposure history;
- retired records are never deleted;
- `private` and `site-draft` never enter production manifests;
- captions and alt text are data, never paths/commands;
- public titles/captions cannot contain local absolute paths;
- creative artifact decision/promotion fields remain independent.

**Initial autonomous scope:** Implement local-only records and transitions through `site-draft`. Do not set real artifacts `site-live` without KC’s explicit selection.

---

## Milestone D5: Generate safe publication manifests

**Objective:** Produce deterministic public metadata from explicit inclusion records only.

**Files:**
- Create: `schemas/studio/publication-manifest.schema.json`
- Create: `src/houdini_ai/publication_manifest.py`
- Create: `tests/test_publication_manifest.py`
- Modify: CLI parser/tests.

**Required behavior:**

- consumes one Study and site-live/archive-keep records only;
- never scans `work/` for candidates;
- reloads canonical artifact and recomputes digest;
- deterministic sort by section/order/ID;
- allowlists public fields;
- strips absolute paths, machine information, private notes, Discord IDs, receipts, credentials, and runner metadata;
- reports missing/malformed/checksum-changed artifacts and emits nothing partial;
- dry-run writes to caller-selected local preview output only;
- includes a manifest digest and generation receipt.

**Exit gate:** A private fixture containing secrets and unrelated media yields a public manifest containing only explicitly included safe records.

---

## Milestone D6: Generate content-hashed public derivatives

**Objective:** Prepare approved public media safely without overwriting canonical originals.

**Files:**
- Create: `src/houdini_ai/public_media.py`
- Create: `tests/test_public_media.py`
- Modify: publication manifest generator and tests.

**Behavior:**

- images: preserve aspect ratio, selected quality/size variants, PNG/JPEG/WebP according to source and transparency;
- video: use discovered FFmpeg, H.264 MP4 proxy initially, no fake interpolation;
- scene/package files remain private unless a future explicit downloadable role is approved;
- filenames include content digest;
- receipts contain source artifact, output relative path, byte size, media metadata, and SHA-256;
- independent checksum and media probe verification;
- no network action.

**Judgment calls to log:** final public dimensions, video bitrate, and whether WebM/AV1 variants are worth the storage/encode cost. Implement conservative defaults behind explicit options.

---

## Milestone D7: Build the read-only public Study projection

**Objective:** Create a high-quality static living Study/archive from the manifest.

**Files:**
- Create: `public-site/README.md`
- Create: `public-site/index.html`
- Create: `public-site/styles.css`
- Create: `public-site/app.js`
- Create: `public-site/templates/` only if static generation requires it.
- Create: `src/houdini_ai/public_site.py`
- Create: `tests/test_public_site.py`

**Initial information architecture:**

```text
Study title / question / state
Selected specimen or latest milestone
Evolution timeline
Curated comparisons
Public-safe lineage
Process notes / discoveries
Archive metadata
```

**Rules:**

- static/read-only output;
- no account/login/mutation controls;
- no dependency on private Studio endpoints;
- media URLs come only from manifest;
- safe DOM/text rendering;
- responsive desktop/mobile viewing;
- accessible captions, alt text, keyboard media controls, and reduced-motion support;
- active and archived Study states render distinctly;
- existing private `website/` Review Studio remains local and separate.

**Exit gate:** A synthetic Study fixture builds a static site with no private paths or network dependency and can be served locally.

---

## Milestone D8: Add local preview and closure workflow

**Objective:** Exercise the entire public projection before any deployment.

**Files:**
- Create: `src/houdini_ai/publication_workflow.py`
- Create: `tests/test_publication_workflow.py`
- Modify: CLI and docs.

**Commands:**

```powershell
houdini-ai studio publication-manifest <study-id> --output <local-path>
houdini-ai studio public-preview <study-id> --output <local-directory>
houdini-ai studio archive-plan <study-id> --json
```

Approval and deployment remain separate. `archive-plan` lists site-live items for Discord batching and performs no transition automatically.

---

## Milestone D9: Vercel + Supabase deployment adapter (explicit approval required)

**Objective:** Publish verified static output and content-hashed media only after KC reviews the local preview.

**Potential files:**
- Create: `src/houdini_ai/publication_deploy.py`
- Create: `tests/test_publication_deploy.py`
- Create: deployment config under `public-site/`.

**Rules:**

- Vercel hosts static frontend;
- Supabase public Storage hosts selected media if needed;
- no Supabase database or Auth initially;
- service credentials stay server-side and outside repo/logs/receipts;
- uploads use content-hashed keys and are independently checked;
- deploy consumes a frozen manifest digest;
- successful CLI exit is insufficient: fetch public manifest/page/media and verify URL, bytes, and checksum where possible;
- no deployment during autonomous work without explicit approval.

**Blocked decisions:** actual Vercel project, domain, Supabase project/bucket, budget limits, and credentials.

---

## 7. Migration and compatibility

1. Preserve all session, review, artifact, handoff, and process records.
2. Migration scripts default to dry-run and are idempotent.
3. Keep existing Review Studio operational as a local admin/diagnostic fallback.
4. Do not expose private Review Studio endpoints or bind them publicly.
5. Do not move canonical artifacts merely to fit the publisher.
6. Keep public output under a new bounded build root such as `work/public-site/<study-id>/`.
7. Keep public derivatives separate from canonical artifacts.
8. Never infer site inclusion from creative promotion, tags, directory location, or prior Discord attachment.

---

## 8. Verification

### Focused

```powershell
$env:PYTHONPATH = "src"
python -m unittest tests.test_discord_public_studio_docs
python -m unittest tests.test_studies
python -m unittest tests.test_conversation_bindings
python -m unittest tests.test_activity_log tests.test_studio_commands
python -m unittest tests.test_site_inclusions
python -m unittest tests.test_publication_manifest
python -m unittest tests.test_public_media
python -m unittest tests.test_public_site
```

### Full

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
python -m compileall -q src tests scripts
git diff --check
```

### Required safety assertions

- replay returns original receipt and creates no duplicate;
- unknown/cross-study artifact fails;
- site inclusion does not creatively promote;
- creative promotion does not create site inclusion;
- private/site-draft cannot enter production manifest;
- manifest includes only explicit records;
- traversal, symlink escape, missing file, and checksum drift fail closed;
- generated public metadata contains no local absolute paths or private fields;
- no test or local command performs deployment/network publication;
- existing Review Studio media streaming and prior tests remain green.

---

## 9. Autonomous implementation boundary

Proceed without KC through:

- D0 documentation;
- D1 Study model and dry-run migration tooling;
- D2 binding model without real IDs;
- D3 activity/command foundation;
- D4 local site-draft inclusion model;
- D5 manifest generator with synthetic fixtures;
- D6 conservative local derivative generation when cheap;
- D7/D8 static local preview foundation;
- full verification and decision logging.

Stop and log rather than guess for:

- real Discord IDs/config changes;
- which real artifacts become site-live/archive-keep;
- public captions expressing KC’s voice;
- publication rights ambiguity;
- Vercel/Supabase project creation or credentials;
- paid usage;
- domain selection;
- any public upload/deployment;
- deletion/retirement of public or private evidence.

Log deferred items in a canonical private process note and a plain implementation handoff file so KC can review them on return.

---

## 10. Immediate execution order

1. D0 documentation test and architecture docs.
2. Baseline focused Studio tests.
3. D1 one vertical Study schema/service slice at a time.
4. D3 minimal receipt-backed command foundation.
5. D4 site-draft inclusion independent of creative promotion.
6. D5 safe deterministic manifest.
7. D7 minimal static Study output from synthetic data.
8. Neighboring and full regression verification.
9. Stop before real binding, real site-live selection, or deployment.
