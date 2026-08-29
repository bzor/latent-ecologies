from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any, Mapping

from .projection import _relative_public_path


_STYLE = """
:root{color-scheme:dark;--ink:#d9ded8;--dim:#858e87;--line:#303732;--signal:#d7ff66;--field:#0b0e0c}
*{box-sizing:border-box}body{margin:0;background:var(--field);color:var(--ink);font:16px/1.55 Arial,sans-serif}
main{max-width:980px;margin:auto;padding:8vw 5vw}header{border-bottom:1px solid var(--line);padding-bottom:4rem}
h1{font:400 clamp(3rem,9vw,8rem)/.88 Georgia,serif;margin:.4rem 0 1.5rem}.kicker,.claim-status{color:var(--signal);font:11px monospace;letter-spacing:.18em}.summary{max-width:46rem;color:var(--dim);font-size:1.25rem}
section{padding:3rem 0;border-bottom:1px solid var(--line)}video,img{width:100%;max-height:72vh;background:#000}.claims{display:grid;gap:1rem}.claim{border-left:2px solid var(--signal);padding:.6rem 1rem;background:#101411}.claim p{margin:.35rem 0}.meta{color:var(--dim);font:12px monospace}
""".strip()


def build_index(records: list[Mapping[str, Any]], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    cards = []
    for record in records:
        record_id = _relative_public_path(f"{record.get('id', '')}.html")
        cards.append(
            f'<article class="claim"><div class="claim-status">FIELD NOTE</div>'
            f'<h2><a href="{escape(record_id)}">{escape(str(record.get("title", "Untitled")))}</a></h2>'
            f'<p>{escape(str(record.get("summary", "")))}</p></article>'
        )
    index = output_dir / "index.html"
    index.write_text(
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Bzor Field Station</title>"
        f"<style>{_STYLE}a{{color:var(--ink)}}</style></head><body><main><header>"
        '<div class="kicker">BZOR COMPUTATIONAL STUDIO</div><h1>Field Station</h1>'
        '<p class="summary">Observations and artifacts from plausible alternate natures.</p>'
        f'</header><section><div class="claims">{"".join(cards)}</div></section></main></body></html>\n',
        encoding="utf-8",
    )
    return index


def build_field_note(record: Mapping[str, Any], output_dir: Path) -> Path:
    """Build one static local field-note page from an already public-safe projection."""
    output_dir.mkdir(parents=True, exist_ok=True)
    record_id = _relative_public_path(record.get("id", "field-note"))
    if "/" in record_id:
        raise ValueError("record id must be a contained relative name")
    artifact_html = []
    for artifact in record.get("artifacts", []):
        path = _relative_public_path(artifact.get("path"))
        role = escape(str(artifact.get("role", "artifact")))
        if Path(path).suffix.lower() in {".mp4", ".mov", ".webm"}:
            media = f'<video controls preload="metadata" src="{escape(path)}"></video>'
        elif Path(path).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            media = f'<img src="{escape(path)}" alt="{role}">'
        else:
            media = f'<a href="{escape(path)}">Open {role}</a>'
        artifact_html.append(f'<article><div class="kicker">{role.upper()}</div>{media}</article>')
    claims = []
    for claim in record.get("claims", []):
        status = str(claim.get("status", ""))
        claims.append(
            '<article class="claim">'
            f'<div class="claim-status">{escape(status.upper())}</div>'
            f'<p>{escape(str(claim.get("text", "")))}</p></article>'
        )
    title = escape(str(record.get("title", record.get("id", "Field note"))))
    page = output_dir / f"{record_id}.html"
    page.write_text(
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{title}</title>"
        f"<style>{_STYLE}</style></head><body><main><header><div class=\"kicker\">BZOR FIELD STATION</div>"
        f"<h1>{title}</h1><p class=\"summary\">{escape(str(record.get('summary', '')))}</p></header>"
        f"<section>{''.join(artifact_html)}</section><section><div class=\"kicker\">FIELD CLAIMS</div>"
        f"<div class=\"claims\">{''.join(claims)}</div></section>"
        f"<p class=\"meta\">License: {escape(str(record.get('license', 'unspecified')))}</p>"
        "</main></body></html>\n",
        encoding="utf-8",
    )
    return page
