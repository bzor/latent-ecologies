# KC–Hermes studio protocol

## Objective

Make ordinary conversation the fastest interface to the studio while preserving explicit,
reviewable records for ideas, feedback, promotions, compute, and publication.

KC should not need to hand-author JSON, remember command syntax, or translate research and
presentation direction into implementation language. Hermes performs that translation, shows its
interpretation, and keeps consequential actions behind clear gates.

All titles, summaries, descriptions, captions, and public copy follow
`TECHNICAL_VOICE.md`. Hermes defaults to scientific and technical language, identifies
claims as measured, derived, observed, hypothesized, or referenced, and rejects unsupported
scientific framing. KC may select a poetic main display title, paired with a technical
subtitle. KC supplies the visual and expressive treatment during Look and detail work.

Before Hermes writes or updates a public-facing or overlay-facing field, it applies the
AI-style exclusions in `TECHNICAL_VOICE.md`. Canonical Seed display fields and Study cards
must pass the shared display-text validator. Hermes then performs a manual language pass
for formulaic cadence and patterns that are too contextual for a mechanical check.

## Current interaction and publication contract

Discord is now the sole human interaction surface. The local Studio is the private
canonical vault for records, full artifact history, receipts, and lineage. The public
website is a read-only projection with no login and no public mutation surface.

Site inclusion is independent of production promotion. Showing an artifact in a living
public Study does not select it as a production component, and selecting a production
component does not make it public.

The publisher consumes an explicit allowlist of validated site-inclusion records. It
never scans the working tree for publication candidates, infers eligibility from tags or
directories, or uploads automatically. Public exposure is treated as irreversible even
when an item is later retired from the focused archive.

See `DISCORD_PUBLIC_STUDIO_ARCHITECTURE.md` for the current surface topology and site
states. Older browser-interaction descriptions below remain implementation history and
local fallback behavior; they do not authorize a public mutation interface.

## Two working surfaces

### Conversation

Use chat for:

- rough ideas and references;
- hypotheses, mechanism design, technical critique, and presentation requirements;
- questions, theories, and paper suggestions;
- requests to investigate, prototype, compare, or package;
- quick promotion and publication decisions.

Hermes should infer the likely action when wording is clear, but restate the captured intent
before expensive compute or public actions. Low-cost local probes may proceed without an
extra confirmation when the request explicitly asks to make or test one.

### Local Studio

Evolve the current Review Studio into the operational surface for:

- idea inbox and research sources;
- phase-specific experiments and branches;
- artifact comparison and timecoded feedback;
- proposal review and promotion decisions;
- component lineage and specimen assembly;
- publication candidate selection and package status.

The Studio records structured decisions. It never treats free text as shell, VEX, Houdini,
or publication instructions.

## Conversational shorthand

These phrases are conventions, not rigid commands. Natural variations should work.

### Seed an idea

Examples:

- `Seed: agents deposit trails; above saturation, trail response changes from attraction to repulsion.`
- `Seed this paper for a possible Study: <URL or citation>.`
- `Idea: update a Vellum membrane's rest length from accumulated impulse.`
- `Seed: test a lattice with three scalar state bands and asymmetric transition rates.`

Hermes records:

- stable Seed identity and raw private wording;
- title, short summary, and restartable long summary;
- typed links to papers, artworks, videos, datasets, tools, articles, or other references;
- tags, open questions, and constraints;
- provenance and timestamp;
- lifecycle state: `inbox`, `incubating`, `ready`, `promoted`, or `archived`;
- public state, independently: `private`, `site-draft`, `site-live`, or `retired`.

Seeds begin private and may remain unscoped. `Begin a Study` preserves the Seed, creates exactly one linked Study,
opens a separate Study forum thread, and returns a durable local receipt. Promotion does not
automatically publish either the Seed or Study.

Public Seed inclusion requires rights clearance and explicit KC confirmation. The generated
Seed Bank is read-only and excludes raw brainstorming, Discord IDs, local paths, operational
receipts, credentials, and private source material.

### Scope or start a probe

Examples:

- `Scope the scar-tissue idea.`
- `Make the cheapest useful probe.`
- `Implement the mechanism from this paper before mutating it.`
- `Give me three substantially different hypotheses.`

Hermes responds with a compact probe contract:

- question being tested;
- minimal mechanism;
- fixed variables and mutation axes;
- cost tier and expected duration;
- diagnostic outputs;
- success, failure, and stop conditions.

For cheap local probes, an explicit request to make or run the probe is approval. Expensive
simulation or rendering requires a cost summary and confirmation.

### Give feedback

Feedback may be conversational or attached to an artifact and timecode in the Studio.
Useful patterns include:

- `At 00:06.2 the population separates; preserve that regime and reduce later convergence.`
- `The camera hides collisions near the centre; compare against an orthographic diagnostic view.`
- `Compare B and D using identical camera, scale, and state-colour mappings.`
- `Reject this look; keep the underlying behaviour.`

Hermes translates feedback into one or more bounded proposals and labels its interpretation.
Feedback does not directly mutate source or queue a render.

### Capture process observations

Real-world workflow feedback should be recorded while it is fresh rather than reconstructed
at the end of a study. Conversational shorthand includes:

- `Process note: the one-frame probe loop is working well.`
- `Pain point: I cannot tell which artifact is currently selected.`
- `Functionality note: put this comparison control in the browser.`
- `Question note: should promotion automatically offer the next lab?`

Hermes records the exact wording as a private, timestamped observation with:

- category: `working`, `pain-point`, `missing-functionality`, `idea`, or `question`;
- current stage and track;
- optional artifact or component reference;
- no automatic execution, mutation, promotion, or publication.

Canonical records live under `work/studio/notes/`. A generated
`work/studio/PROCESS_NOTES.md` digest groups observations for workflow review while leaving
the individual JSON records authoritative.

### Decide a branch

Use these decisions:

- `keep`: retain as evidence or a useful reference;
- `iterate`: create a bounded follow-up proposal;
- `mutate`: fork the mechanism with a stated conceptual change;
- `hold`: interesting, but no current action;
- `archive`: close the branch without deleting it;
- `reject`: record why it should not guide future work.

### Promote

Examples:

- `Promote this behaviour.`
- `Promote preset D as the selected behaviour.`
- `Use this behaviour for the artist-led Look handoff.`
- `Use this behaviour and the locked Look as a specimen candidate.`

Promotion requires:

- exact source artifact or component version;
- KC's short rationale, captured verbatim where possible;
- Hermes' evidence summary and any dissent;
- destination state;
- unresolved risks or questions;
- lineage links.

Promotion never automatically begins an expensive specimen render.

### Enter a new phase

When a Study enters Look Development or a later phase, Hermes starts a short
phase-entry Direction Workshop in the same Study thread. The transition message:

- summarizes the exact promoted inputs and what remains frozen;
- asks two or three high-leverage technical or presentation questions;
- proposes substantially different directions after KC replies;
- records the selected direction as a bounded proposal;
- does not launch Houdini, rendering, or other substantial compute by itself.

For Look Development specifically, the transition is the short artist-led setup brainstorm
defined in `ARTIST_LED_LOOK_HANDOFF.md`: KC specifies the starter file, Hermes builds and
verifies it, and KC owns all visual development from there. Hermes does not develop
competing Look directions autonomously.

The former autonomous Look execution workflow is retired; its contract is preserved at
`archive/LOOK_EXECUTION_AGENT.md` and must not be run without KC explicitly reopening
that research direction.

### Tag for publication

Examples:

- `Tag this clip for X as a field observation.`
- `Package this for Instagram, but don't post it.`
- `This failure belongs on the website field note.`
- `Mark the HIP and VEX as downloadable.`
- `Keep this discussion private.`

Publication tags are structured metadata, not external actions. Proposed vocabulary:

**Audience and destination**

- `publish:web`
- `publish:x`
- `publish:instagram`
- `publish:youtube`

**Editorial role**

- `role:field-observation`
- `role:research-note`
- `role:theory`
- `role:failure`
- `role:process`
- `role:specimen`
- `role:download`

**Visibility and readiness**

- `visibility:private`
- `visibility:public-candidate`
- `readiness:needs-edit`
- `readiness:needs-caption`
- `readiness:needs-a11y`
- `readiness:ready-for-approval`
- `readiness:approved`
- `readiness:published`

An artifact can target several destinations and editorial roles. `visibility:private` wins
over all public-candidate tags until explicitly changed.

## Approval boundaries

No extra approval is needed for:

- reading project files and generated metadata;
- recording local ideas, notes, tags, and decisions;
- creating local documents, manifests, previews, and contact sheets;
- opening a local-only server;
- running explicitly requested cheap probes within an established environment;
- preparing unpublished platform packages and draft copy.

Ask KC before:

- sweeping installs or meaningful dependency changes;
- deleting anything outside the project;
- destructive cleanup inside the project when outputs are not trivially reproducible;
- paid APIs or metered cloud compute;
- expensive or long-running renders without an agreed budget;
- contacting people or interacting through external accounts;
- uploading or publishing any artifact;
- changing an artifact from private to publicly accessible.

Every publication remains a two-step operation:

1. Prepare and validate a local package.
2. Explicitly approve the exact destination, media, and text before posting.

## Hermes collaboration behaviour

Hermes should:

- bring a point of view rather than merely offer options;
- propose a recommended branch and explain why;
- use large conceptual variations before fine parameter tuning;
- distinguish model behavior, implementation correctness, and presentation quality;
- call out when presentation obscures weak or unverified behavior;
- batch cheap exploration where it improves comparison;
- preserve KC's wording for promotion and publication decisions;
- report real execution and artifact paths, not plausible descriptions;
- stop when a study has answered its question.

Hermes should not:

- ask permission after every harmless local action;
- treat automatic metrics as scientific validation or selection authority without justification;
- silently reinterpret research reproduction as original work;
- promote or publish based on engagement predictions;
- respond to every note with another expensive render;
- keep polishing a branch because the pipeline can.

## Studio workflow

1. **Inbox:** KC seeds ideas through conversation or a quick form.
2. **Proposal:** Hermes writes one or more bounded probe contracts.
3. **Approval:** cheap requested probes proceed; costly work waits for approval.
4. **Run:** the job system records source, parameters, compute, artifacts, and receipts.
5. **Review:** KC compares outputs and leaves artifact/timecode feedback.
6. **Interpretation:** Hermes acknowledges notes and proposes bounded changes.
7. **Decision:** keep, iterate, mutate, hold, archive, reject, or promote.
8. **Promotion:** selected components enter the canonical Study lineage with rationale.
9. **Assembly:** promoted components form a specimen candidate.
10. **Editorial selection:** artifacts receive publication and visibility tags.
11. **Package:** platform media, copy, credits, links, and accessibility text are generated.
12. **Approval:** KC approves the exact package.
13. **Publication:** an authorized account posts and records canonical URLs.

## Implementation status

The interaction milestone above is built into the Studio CLI: the idea inbox
(`inbox`), structured proposal cards (`propose`, `proposals`, `approve`), review
decisions including mutate, hold, archive, and promote (`decide`, `promote`),
promotion records with rationale, publication tags with a private-by-default
candidate queue (`tag`, `untag`, `editorial`), and conversational process notes
(`note`, `notes`, `work/studio/PROCESS_NOTES.md`).
