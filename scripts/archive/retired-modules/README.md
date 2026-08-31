# Retired modules — 2026-08-31 ceremony audit

Package modules and tests retired by the 2026-08-31 ceremony audit
(`.hermes/plans/2026-08-31_ceremony-audit.md`). Preserved for reference; no longer
importable as `houdini_ai.*` and their CLI commands are removed.

- `studio_sessions.py` — creative-session workspaces, superseded by canonical
  Studies (`studies.py`) and per-study `00_study/status.json`.
- `pilot_study_003.py` — one-shot Study 003 bootstrap, executed.
- `golden_specimens.py` — one-shot scar-tissue golden-specimen registration, executed.
- `look_execution.py` — the autonomous Look execution workflow retired by
  `docs/VISION.md`; contract preserved at `docs/archive/LOOK_EXECUTION_AGENT.md`.
  Must not be re-wired without KC explicitly reopening that research direction.
- `test_*.py` — their test suites, moved alongside.
- Retired record stores live under `studio/archive/` (`sessions/`, `session-state/`).
