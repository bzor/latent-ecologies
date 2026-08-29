# Discord public Study implementation log — 2026-08-16

## Completed autonomously

- Superseded the earlier hybrid web-review plan with the Discord-controlled, read-only public Study plan.
- Added and tested canonical Study records with independent local focus.
- Migrated the two real legacy sessions non-destructively:
  - `pilot-study-003` → `study-003-nonlocal-affinity-dance`;
  - `scar-tissue` retains `scar-tissue`.
- Verified both legacy session JSON files remained byte-identical after migration.
- Added private Discord thread binding records and bind/resolve CLI commands.
- Added idempotent activity receipts with pending/completed/failed states and exact context collision checks.
- Added private site-inclusion records, explicit rights review, KC-confirmed live transitions, retirement history, and separation from creative promotion.
- Added a deterministic deny-by-default public manifest with current checksum, catalog, Study, rights, and exposure-history validation.
- Added bounded content-addressed public media materialization.
- Added a static semantic HTML/CSS Study generator with no scripts, forms, login, mutation endpoint, or network action.
- Built a real local Study 003 shell at `work/public-site/study-003-nonlocal-affinity-dance/`; it intentionally contains zero milestones.

## Deferred judgment calls

1. **Real Discord binding — resolved**
   - Created the `studies` Discord forum and `Study 003 — Non-Local Affinity` post after KC granted the bounded bot-role permissions.
   - Verified the live forum/thread relationship and wrote the private canonical conversation binding.

2. **Initial public milestones**
   - No specific Study 003 artifact has yet been explicitly selected for site inclusion in a captured Discord decision.
   - No site-inclusion record was created for a real artifact.
   - The local preview remains an empty living Study shell.

3. **Rights clearance for real artifacts**
   - The system now requires a recorded rights decision before `site-live`.
   - No real artifact was marked rights-cleared without review.

4. **Hosting architecture**
   - Vercel, Supabase Storage, another object store, and static-only hosting remain unselected.
   - No account was connected, no credentials were read, and no remote resource was created.

5. **Media optimization policy**
   - The local proof copies verified source bytes to content-addressed paths.
   - Codec ladders, poster generation, image resizing, bandwidth targets, and video hosting limits remain deferred until real media inventory and hosting constraints are measured.

6. **Study 003 public title — resolved**
   - Human-facing title is `Study 003 — Non-Local Affinity`.
   - Stable internal ID `study-003-nonlocal-affinity-dance` remains unchanged to preserve artifact, path, session, and receipt lineage.
   - A public slug may omit the legacy word without rewriting canonical history.

7. **Interrupted activity recovery**
   - A pending or failed idempotent activity refuses automatic replay.
   - Automated recovery policy is deferred; the current behavior fails visibly and preserves the receipt for inspection.

8. **Visual browser inspection**
   - HTTP verification returned `200 OK` and the expected safe manifest.
   - Chrome visual inspection was blocked by the local “Allow remote debugging” confirmation while KC was away.
   - The temporary loopback server was shut down immediately after verification.

9. **Current local Review Studio UX**
   - It remains available as a private fallback and was not publicly exposed or rewritten in this slice.
   - No login, custom chat, public mutation API, or web admin controls were added.

10. **Seed Bank — implemented locally**
   - Created Discord `seed-bank` forum with lifecycle tags.
   - Extended stable `idea-*` records into complete private Seeds with bounded updates and idempotent Study promotion.
   - Added separate rights-gated Seed inclusion records and a static read-only public Seed Bank generator.
   - Existing incomplete Ideas remain private and are not automatically rewritten or published.

## Explicit non-actions

- No Seed or Study artifact published publicly.
- No real artifact included or marked live.
- No public deployment, upload, domain change, commit, push, deletion, or database migration.
- No Vercel, Supabase, or paid API action.
- No secrets recorded.
