# Local review studio

The first website milestone is a local production interface over generated jobs.
It discovers review and lookdev artifacts, plays motion tests, compares iterations,
shows provenance and simulation parameters, and records bounded feedback under
`work/reviews/`.

Start it from the repository root:

```powershell
python -m houdini_ai review
```

Then open <http://127.0.0.1:8765>. The server binds locally by default and has no
command-execution endpoint. It can write only validated review records; it cannot
modify VEX, manifests, HIP files, or launch Houdini. Generated feedback remains outside
Git until a collaborator translates an accepted decision into versioned source and a
lab-log entry.

Current capabilities:

- Study and job discovery from effective configs and receipts.
- Inline MP4 playback with byte-range seeking and still-image inspection.
- Artifact comparison across jobs.
- Run parameters and source provenance.
- Comments attached to an artifact and optional video timecode.
- `keep`, `reject`, `iterate`, and `approved-look` decisions.
- Open/resolved review state.

The public field notebook will reuse these artifact and review contracts after local
studio practice has stabilized.
