"""Generate a static read-only Study site from a safe publication manifest."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .publication_manifest import build_publication_manifest
from .public_media import materialize_public_media, write_atomic
from .studio_store import StudioStore


_STYLES = """:root {
  color-scheme: dark;
  --ink: #eef2ee;
  --muted: #9ca9a3;
  --line: rgba(238, 242, 238, 0.14);
  --panel: rgba(21, 28, 27, 0.86);
  --accent: #a8ffcf;
  --background: #080d0c;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif;
}
* { box-sizing: border-box; }
html { background: var(--background); }
body {
  margin: 0;
  min-height: 100vh;
  color: var(--ink);
  background:
    radial-gradient(circle at 18% 0%, rgba(57, 107, 89, 0.22), transparent 40rem),
    linear-gradient(180deg, #0b1210 0%, var(--background) 62%);
}
main { width: min(1180px, calc(100% - 2rem)); margin: 0 auto; padding: 5rem 0 8rem; }
header { max-width: 850px; margin-bottom: 4rem; }
.eyebrow { color: var(--accent); font-size: 0.76rem; letter-spacing: 0.16em; text-transform: uppercase; }
h1 { margin: 0.7rem 0 1rem; font-size: clamp(2.6rem, 7vw, 6.4rem); line-height: 0.92; letter-spacing: -0.055em; }
.status { color: var(--muted); font-size: 0.95rem; }
.timeline { display: grid; gap: 3rem; }
section { border-top: 1px solid var(--line); padding-top: 1.1rem; }
.section-label { color: var(--muted); font-size: 0.73rem; letter-spacing: 0.14em; text-transform: uppercase; }
article { margin-top: 1.4rem; padding: clamp(1rem, 3vw, 2rem); border: 1px solid var(--line); background: var(--panel); border-radius: 1.2rem; box-shadow: 0 1.5rem 5rem rgba(0, 0, 0, 0.28); }
article h2 { margin: 0 0 0.65rem; font-size: clamp(1.4rem, 3vw, 2.5rem); letter-spacing: -0.025em; }
article p { max-width: 72ch; color: #c7d0cb; line-height: 1.65; }
figure { margin: 1.5rem 0 0; }
img, video { display: block; width: 100%; max-height: 78vh; object-fit: contain; border-radius: 0.7rem; background: #030605; }
figcaption { margin-top: 0.65rem; color: var(--muted); font-size: 0.82rem; }
.empty { color: var(--muted); border: 1px dashed var(--line); padding: 2rem; border-radius: 1rem; }
footer { margin-top: 5rem; padding-top: 1.4rem; border-top: 1px solid var(--line); color: var(--muted); font-size: 0.8rem; }
@media (max-width: 640px) { main { padding-top: 3rem; } article { border-radius: 0.8rem; } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; animation: none !important; } }
"""


def _media_markup(item: dict[str, Any]) -> str:
    media = item["media"]
    path = html.escape(str(media["public_path"]), quote=True)
    title = html.escape(str(item["title"]), quote=True)
    alt = html.escape(str(item["alt_text"]), quote=True)
    if media["kind"] == "image":
        body = f'<img src="{path}" alt="{alt}" loading="lazy">'
    elif media["kind"] == "video":
        mime = html.escape(str(media["mime"]), quote=True)
        body = f'<video controls preload="metadata" aria-label="{alt}"><source src="{path}" type="{mime}"></video>'
    else:
        body = f'<a href="{path}">Open {title}</a>'
    return f"<figure>{body}<figcaption>{alt}</figcaption></figure>"


def _render(manifest: dict[str, Any]) -> str:
    study = manifest["study"]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in manifest["items"]:
        grouped.setdefault(str(item["section"]), []).append(item)
    sections: list[str] = []
    for section, items in grouped.items():
        cards = []
        for item in items:
            cards.append(
                "<article>"
                f"<h2>{html.escape(str(item['title']))}</h2>"
                f"<p>{html.escape(str(item['caption']))}</p>"
                f"{_media_markup(item)}"
                "</article>"
            )
        sections.append(
            f'<section aria-labelledby="section-{html.escape(section, quote=True)}">'
            f'<div class="section-label" id="section-{html.escape(section, quote=True)}">{html.escape(section)}</div>'
            f"{''.join(cards)}</section>"
        )
    timeline = "".join(sections) or '<p class="empty">No public milestones have been included yet.</p>'
    return "<!doctype html>\n" + f"""<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="A curated computational art study by KC Austin.">
  <title>{html.escape(str(study['title']))}</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <main>
    <header>
      <div class="eyebrow">Bzor Computational Studio · {html.escape(str(manifest['mode']))} study</div>
      <h1>{html.escape(str(study['title']))}</h1>
      <div class="status">{html.escape(str(study['state']))} · {html.escape(str(study['current_phase']))}</div>
    </header>
    <div class="timeline">{timeline}</div>
    <footer>Curated from verified milestones. Routine working files remain in the private Studio vault.</footer>
  </main>
</body>
</html>
"""


def build_public_site(store: StudioStore, root: Path, study_id: str, output_directory: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    output_directory = Path(output_directory).resolve()
    manifest = build_publication_manifest(store, root, study_id)
    media_receipts = materialize_public_media(store, root, manifest, output_directory)
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    write_atomic(output_directory / "manifest.json", manifest_bytes)
    write_atomic(output_directory / "index.html", _render(manifest).encode("utf-8"))
    write_atomic(output_directory / "styles.css", _STYLES.encode("utf-8"))
    return {
        "study_id": study_id,
        "manifest_id": manifest["id"],
        "manifest_sha256": manifest["content_sha256"],
        "item_count": len(manifest["items"]),
        "media": media_receipts,
        "output": output_directory.as_posix(),
        "network_actions": 0,
    }
