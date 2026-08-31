# Social publishing

> Strategy and implementation plan for putting studio work on social platforms.
> Extends stage 7 (Publish) of `VISION.md`; where they conflict, VISION wins.
> Decided with KC 2026-08-31.

## Decision

The studio publishes its production exhaust to five destinations: **X, Instagram,
Bluesky, YouTube Shorts, and TikTok**. The system prepares every post completely —
platform derivatives, caption drafts, alt text, constraint checks — at the pipeline
gates where postable material already exists. KC approves the exact media, text, and
destination before anything leaves the machine. Nothing is ever uploaded
automatically (VISION rule 4), and platform cadence never drives the laboratory
(VISION rule 8): posts are made from work that happened, never scheduled work
invented for the feed.

The near-term goal is operational: reduce the cost of one post from "assemble
everything by hand" to "read a prepared kit and reply with approval."

## Content tiers and their gates

The pipeline exhausts three tiers of postable material. Each is tied to a gate, so
preparing a post costs nothing extra when the gate fires.

| Tier | Fires at | Material | Destinations |
|---|---|---|---|
| **Process** | behavior round close, behavior promote | postable diagnostic renders (`behavior_postable`), review-packet contact sheets after KC's decision | X, Bluesky |
| **Hero** | detail-pass promote (delivery package) | the final specimen video | X, Instagram (Reels), Bluesky, Shorts, TikTok |
| **Recap** | study close | lineage poster + selected stills + parameters, linking to the Field Station archive | Instagram (carousel), X (thread), Bluesky |

Review-packet material is posted only after KC's selection is recorded, framed as
"selected C" with the evidence. Public reactions are never a selection mechanism
(`DISCORD_PUBLIC_STUDIO_ARCHITECTURE.md`: poll totals are evidence, not authority).

Stays private: seeds and brainstorm threads, Look WIP unless KC opts in per item,
anything without cleared rights, uninformative dead ends. The site-inclusion gates
in `site_inclusions.py` / `seed_publication.py` already encode these rules; social
publishing adopts the same rights and actor gates rather than inventing parallel ones.

### Platform registers

- **X** — the build-in-public surface. Process and hero posts, technical captions,
  the 4:5 postable standard. Threads for study recaps.
- **Bluesky** — cross-post of the X content; the generative-art community is active
  there and the marginal cost is one more checkbox.
- **Instagram** — hero Reels (9:16) and feed/carousel posts (4:5): lineage posters,
  stills, recaps. Captions keep the technical voice; claim-disciplined provenance is
  a differentiator there, and the long caption limit allows the full summary.
- **YouTube Shorts** — free rider on the 9:16 hero cut.
- **TikTok** — experiment. Hero and recap video only. Discovery there is
  feed-driven rather than follower-driven, so the dormant account is not a
  handicap; expect immediate-motion pieces to travel and slow monochrome studies
  not to. Review after a few studies.

## Derivative matrix

Two encodes cover all five destinations. Both are H.264, CRF 18, 30 fps,
`+faststart`, no audio — the postable contract from `behavior_postable.py`
generalized to two sizes.

| Derivative | Size | Serves | Duration limits checked |
|---|---|---|---|
| `feed` | 1080×1350 (4:5) | X, Bluesky, Instagram feed | X 2:20 (standard account), Bluesky 3:00 |
| `vertical` | 1080×1920 (9:16) | Instagram Reels, Shorts, TikTok | Reels/Shorts 3:00, TikTok well above |

Safe zones are a design-time concern, not an encode concern: TikTok and Reels
overlay the right-hand action rail and a bottom caption band over the video, so
overlay/HUD elements in a 9:16 composition stay clear of roughly the right 120 px
and bottom 320 px. The overlay generator's 9:16 preset and safe-zone guide toggle
cover this at detail-pass time; a TikTok-sized guide variant is a small follow-up
there (its reserved areas are slightly larger than Instagram's).

A true 9:16 hero cut comes from a 9:16 overlay config at the detail pass. Padding a
4:5 delivery into the vertical frame is a legitimate fallback and the receipt
records which one happened.

## Captions

Caption drafts are generated from the study card (`study_card.py`), the validated
source of truth for titles, subtitles, summaries, bullets, and parameters. All
generated text follows `TECHNICAL_VOICE.md` and must pass
`display_text.validate_display_text`; generation fails loudly on a violation
rather than posting around it. Per-platform shapes:

- **X / Bluesky:** number, title, subtitle, one summary sentence — trimmed to fit
  280 / 300 characters. No hashtags.
- **Instagram:** full summary, bullets, headline parameters, hashtag block.
- **Shorts:** title line plus a short description.
- **TikTok:** short description plus hashtag block.

**Caption content rule (KC direction, 2026-08-31, Study 001):** caption prose
describes the system — the mechanism, what guides the agents, and the process.
Production and render metadata (frame counts, fps, resolution, encode settings,
solver and seed provenance) never appear in caption prose. Reproduction
identifiers (agents, seed, solver, fields) belong in the params line;
render facts stay in receipts. Prefer tight phrasing over completeness. This is
an editorial rule applied when authoring the study card, not a mechanical check.

Alt text is drafted from the card's title, subtitle, and summary. Every caption and
alt text is a **draft**: KC edits or approves the exact text at posting time, and
the mechanical validator does not replace the final human read for AI cadence.

## Automation phases

Every phase preserves the two-step publication rule from `STUDIO_PROTOCOL.md`:
prepare and validate a local package, then KC explicitly approves the exact
destination, media, and text.

### Phase 1 — post kit builder (shipped 2026-08-31)

`python -m houdini_ai.post_kit` builds a complete post kit from a source render
and a study card: both derivatives, per-platform caption drafts, alt text, a
Discord-postable `post-kit.md` summary, and `post-kit.receipt.json` with content
hashes, durations, and per-platform constraint checks. KC (or Hermes in the Study
thread) hand-posts from the kit; posting is a two-minute job instead of an
assembly job. First candidates: Study 001's delivery video and lineage poster.

### Phase 2 — approval loop and posting adapter

- A `publication` record type: destination, posted URL, media sha256, caption
  verbatim, and KC's approval message reference. This makes the existing
  `readiness:published` editorial state real (today nothing ever sets it) and
  gives `publish:x` / `publish:instagram` tags a consumer.
- Discord approval loop: the kit lands in a private channel; KC replies
  `post x`, `post ig`, `edit: …`, or `skip`; the reply is preserved verbatim as
  the approval record.
- Posting adapter behind the approval: preferred route is self-hosted **Postiz**
  (one open-source adapter covering all five platforms, credentials outside
  source control); direct platform APIs are the fallback. The adapter acts only
  on an approval record naming the exact kit artifacts — never by scanning for
  postable files, mirroring the publication boundary in
  `DISCORD_PUBLIC_STUDIO_ARCHITECTURE.md`.

### Phase 3 — queue and cadence support

- `studio post-queue`: list built kits and their approval/post state.
- A weekly nudge alongside the seed digest when built kits are waiting, so bursty
  production drips out as a steady feed. The queue smooths output; it never
  generates demand for content.
- Post-performance notes captured as ordinary process observations, feeding the
  TikTok review and platform-set decisions.

## Boundaries that do not move

1. No automatic upload, ever. The adapter posts only on an explicit KC approval
   of the exact media, text, and destination.
2. Public exposure is irreversible. Rights are cleared before anything with
   third-party material goes out.
3. Captions never overstate: claims stay identifiable as measured, derived,
   observed, hypothesized, or referenced (`TECHNICAL_VOICE.md`).
4. Canonical records live in `studio/` and the study vaults. Platform posts are
   projections; the Field Station archive is the durable public record they link
   back to.
