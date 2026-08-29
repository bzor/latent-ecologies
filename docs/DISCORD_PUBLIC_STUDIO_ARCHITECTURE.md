# Discord-controlled public Studio architecture

## Decision

Discord is the sole human interaction surface for Bzor Computational Studio. KC chats, brainstorms, reviews previews, makes choices, and curates each Study from its persistent Discord forum thread.

The private local Studio remains the canonical record and artifact vault. The website is a read-only public Study assembled from deliberately selected material. It has no login and no public mutation, comment, approval, upload, shell, or runner interface.

```text
Discord Seed Bank forum
  one brainstorm thread per possible project
                 │
                 ▼
private canonical Seed
  complete summaries, references, questions, constraints
                 │ explicit promotion
                 ▼
Discord Study thread
  conversation, previews, buttons, requests, decisions
                 │
                 ▼
private local Studio
  complete assets, receipts, lineage, and authoritative state
                 │ explicit allowlist
                 ▼
read-only public Study
  curated living notebook and focused final archive
```

## Seed Bank

The Studio begins before production. The `seed-bank` Discord forum uses one thread per Seed for conversational incubation. Canonical Seed records retain stable legacy `idea-*` identities so existing proposals and lineage do not break, while adding a title, short summary, long summary, typed reference links, tags, open questions, constraints, lifecycle timestamps, and optional resulting Study.

Seeds begin private and unscoped. Their lifecycle states are `inbox`, `incubating`, `ready`, `promoted`, and `archived`. Public Seed inclusion is a separate decision with `private`, `site-draft`, `site-live`, and `retired` states. Rights clearance and explicit KC confirmation are required before `site-live`.

Promoting a ready Seed creates exactly one linked canonical Study, preserves the Seed, and opens a separate Study conversation. Retried promotion is idempotent; it cannot create a second Study or silently redirect an existing promotion.

The public `/seeds/` projection contains only approved titles, summaries, tags, typed external links, lifecycle state, and an optional resulting Study reference. It excludes raw brainstorm notes, Discord identifiers, local paths, receipts, credentials, and unpublished source material. Public visitors can browse but cannot create, edit, promote, or publish Seeds.

## Authority

A Discord message may request an action, but the action becomes official only after a narrow Studio command validates exact record IDs, writes canonical local state, and returns an idempotent receipt. Discord transcripts, attachments, reactions, poll totals, and button labels are not themselves the project database.

Hermes button choices or explicit confirmation are appropriate for canonical decisions. Ordinary Discord polls may collect non-binding preferences or research signals, but their totals remain evidence rather than authority.

## Study topology

Use one persistent Discord forum thread per Study initially. Keep Behavior, artist-led Look, Specimen, and Delivery as structured phases in the local records rather than fragmenting the conversation into many threads. Colour, materials, camera, and framing remain part of the artist-owned Look HIP rather than separate phases.

A private conversation-binding record maps a Discord thread to one canonical Study ID. It stores routing identifiers only and never stores Discord credentials.

## Site inclusion

Site inclusion is independent of production promotion:

- production promotion selects a behavior, Look, or specimen for the next phase;
- site inclusion permits a verified artifact to appear in the public Study.

An informative rejected branch can be public. A selected component can remain private.

Site inclusion uses these states:

- `private`: local only;
- `site-draft`: public-safe projection prepared locally but not deployed;
- `site-live`: visible in the active living Study;
- `archive-keep`: selected for the closed Study archive;
- `retired`: omitted from the focused page but treated as previously public.

The governing rule is that public exposure is effectively irreversible. Retiring an item cannot retract downloads, caches, indexes, screenshots, or copied links.

## Publication boundary

The publisher consumes an explicit allowlist of site-inclusion records. It never scans the working tree for publication candidates and never infers public eligibility from a directory, tag, production promotion, Discord attachment, or prior preview.

The public manifest contains only allowlisted fields and content-hashed derivatives. It strips:

- local absolute paths and machine information;
- credentials and private notes;
- operational receipts and runner metadata;
- caches, redundant exports, and frame floods;
- source material without confirmed publication rights.

Canonical originals remain in private local storage. Public derivatives are separate, bounded outputs.

## Living Study lifecycle

### Active

Hermes sends meaningful previews in Discord. KC flags interesting evolution milestones for the public site. Routine nitpicks, redundant tests, broken outputs, and uninformative dead ends remain private.

### Closing

Hermes presents the `site-live` set in manageable Discord batches. KC chooses what to keep, combine, recaption, preserve as process evidence, or retire. A frozen archive manifest is generated and validated locally.

### Archived

The public page becomes a focused narrative with selected evolution, comparisons, useful rejected branches, and stable content-hashed assets. Reopening the Study creates a new revision instead of silently rewriting the archived interpretation.

## Hosting direction

The destination is a static public subdomain on KC's existing site. The hosting and media provider remain deliberately unselected until the generated Seed Bank, Study pages, derivative sizes, and bandwidth requirements are measured. No public authentication or database is required initially. Any future upload/delete credentials remain server-side and outside browser bundles, records, logs, and source control.

No deployment, upload, public bucket mutation, domain change, or paid service action occurs without KC explicitly approving the exact local preview and destination.

## Local compatibility

The existing Review Studio may remain available locally as an administrative and diagnostic fallback while the new Discord workflow stabilizes. It is not the public site and must not be exposed through a public bind or tunnel.
