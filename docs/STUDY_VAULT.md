# Canonical Study vault

## Decision

`studies/` is the canonical human-facing vault for all Study-owned material. `work/` is disposable machine workspace. `studio/` is reserved for system-wide records and reusable components.

A canonical Study directory starts with its sortable number and recognizable slug:

```text
studies/study_003_nonlocal-affinity-dance/
```

The canonical record ID remains `study-003-nonlocal-affinity-dance`; directory naming does not change record identity or Discord bindings.

## Required directory contract

```text
study_NNN_slug/
├── 00_study/
├── 01_behavior/
├── 02_look/
├── 03_specimen/
├── 04_delivery/
├── 90_shared/
└── 99_archive/
```

Behavior keeps the numbered lifecycle sections because it contains branching simulations and a
formal promotion gate:

```text
00_brief/      intent, frozen inputs, constraints, acceptance criteria
01_work/       editable sources plus mutable branches, caches, and incomplete attempts
02_review/     bounded previews, comparisons, contact sheets, and review manifests
03_selected/   immutable KC-approved handoffs and promoted artifacts
```

Look, Specimen, and Delivery are deliberately flat. Their authoritative files and compact metadata
sit directly in the phase directory:

```text
02_look/
├── var_001_primary-treatment.look_r001.hiplc
├── var_001_primary-treatment.look.json
├── var_002_fibrous-remodeling.look_r001.hiplc
├── look-render.mp4            preview encode, beside the HIP rather than under renders/
├── locked/                    archival HIP snapshots for checksum binding
├── renders/                   rendered frames and the render receipt
└── README.md

03_specimen/
├── var_001_primary-treatment.specimen.json
├── var_001_primary-treatment.overlay-config.json
└── var_001_primary-treatment.preview.mp4

04_delivery/
├── var_001_primary-treatment.delivery.mp4
├── var_001_primary-treatment.delivery.json
└── var_001_primary-treatment.overlay_frames/  only when retained
```

## Variations

Every Study owns `00_study/variations.json` and starts with variation `001`, even when it currently
has only one treatment. A variation has a permanent number, a descriptive title, a canonical ID,
state, optional Behavior selection, and optional parent variation. Several sibling variations may
remain active or held; choosing a current production target never deletes or demotes the others.

The canonical filename stem is:

```text
var_NNN_title-slug
```

Variation and revision are separate axes. `var_002_fibrous-remodeling.look_r003.hiplc` is revision
3 of creative variation 2. A save revision never consumes a new variation number. Look, Specimen,
and Delivery filenames must carry the same variation stem; use a directory only for a bounded
package such as a retained frame sequence.

Register a sibling treatment before creating its files:

```powershell
houdini-ai studio study-variation-add study-002-scar-tissue 4 "Slow Load-selected Maturation" --no-make-current
```

This prints the exact filename stem to use. Existing receipt-bound artifacts keep their historical
names; all newly generated later-phase artifacts use the variation convention.

KC versions a Look by saving a new `_rNNN` HIP in the same flat directory. Colour, material,
lighting, camera, and framing decisions all remain in the artist-owned Look HIP. Once KC locks the
authoritative HIP and rendering completes, the variation advances directly to Specimen/detail work.

Receipts live beside the artifact they describe rather than in a separate phase directory.

Rendered frames stay in `02_look/renders/` with their render receipt. The encoded preview
sits directly in `02_look/` as `look-render.mp4`, so KC reaches the watchable result without
opening the frame directory, and the overlay config's `render.video` points at that same file.
Frames and preview encodes are heavy and stay local under the ignore rules; the receipts,
`look.json`, and the lock receipt are versioned.

Do not silently replace a selection or variation. Preserve its numbered identity and add a sibling.

## Storage roles

- **`studies/`** — canonical Study-owned sources, evidence, selections, and packages.
- **`work/`** — rebuildable caches, temporary job staging, server logs, and legacy material awaiting verified migration.
- **`studio/`** — Seed Bank, cross-Study catalog records, reusable components, schemas, and conversation bindings.

No approved artifact may exist only beneath `work/`.

## Creating a vault

The Study record must already exist in the local Studio store:

```powershell
houdini-ai studio study-init study-003-nonlocal-affinity-dance
```

The operation is idempotent. It creates missing directories and initial metadata but does not replace authored files.

## Migration rules

1. Copy first; do not delete the legacy source.
2. Verify every copied file by SHA-256.
3. Record source, destination, size, and checksum in `00_study/migration-manifest.json`.
4. Put uncurated history in the phase's `01_work/legacy_handoffs/`.
5. Put registered review evidence in `02_review/migrated_verified/`.
6. Put promoted artifacts in versioned directories beneath `03_selected/`.
7. Update `00_study/artifact-index.json`.
8. Delete or archive legacy material only in a separately approved cleanup after verification.

The artifact catalog scans Behavior's `02_review/` and `03_selected/`, plus the flat Specimen and
Delivery directories. It does not expose Behavior `01_work/` or the artist-owned Look HIP.
