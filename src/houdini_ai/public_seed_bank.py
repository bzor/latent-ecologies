"""Generate a static read-only public Seed Bank."""

from __future__ import annotations

import hashlib
import html
import ipaddress
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .display_text import validate_display_text
from .public_media import write_atomic
from .studio_schema import validate_record
from .studio_store import StudioStore


_STYLES = """:root { color-scheme: dark; --bg:#080d0c; --ink:#eef2ee; --muted:#9ca9a3; --line:rgba(238,242,238,.14); --accent:#a8ffcf; font-family:Inter,ui-sans-serif,system-ui,sans-serif; }
* { box-sizing:border-box; } body { margin:0; color:var(--ink); background:radial-gradient(circle at 20% 0,rgba(57,107,89,.24),transparent 38rem),var(--bg); }
main { width:min(1120px,calc(100% - 2rem)); margin:auto; padding:5rem 0 8rem; } a { color:inherit; } .eyebrow { color:var(--accent); text-transform:uppercase; letter-spacing:.16em; font-size:.75rem; }
h1 { font-size:clamp(3rem,9vw,7rem); letter-spacing:-.06em; line-height:.9; margin:.7rem 0 1rem; } .intro { color:var(--muted); max-width:65ch; line-height:1.6; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(270px,1fr)); gap:1rem; margin-top:3rem; } .card { display:block; text-decoration:none; border:1px solid var(--line); border-radius:1rem; padding:1.3rem; background:rgba(18,25,23,.84); }
.card:hover { border-color:rgba(168,255,207,.55); } .state,.tags { color:var(--muted); font-size:.78rem; text-transform:uppercase; letter-spacing:.09em; } .card h2 { margin:.7rem 0; font-size:1.5rem; } .card p, article p { color:#c7d0cb; line-height:1.65; }
article { max-width:780px; margin-top:3rem; } .references { margin-top:2rem; padding-top:1.5rem; border-top:1px solid var(--line); } li { margin:.7rem 0; } footer { margin-top:5rem; border-top:1px solid var(--line); padding-top:1rem; color:var(--muted); font-size:.8rem; }
@media(max-width:640px){main{padding-top:3rem}}
"""


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:60] or "untitled"


def _canonical_digest(value: object) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _validate(kind: str, record: dict[str, Any]) -> None:
    errors = validate_record(kind, record)
    if errors:
        raise ValueError("; ".join(errors))


def _is_safe_public_reference(url: object) -> bool:
    if not isinstance(url, str):
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return False
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".local"):
        return False
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return True
    return address.is_global


def build_seed_manifest(store: StudioStore) -> dict[str, Any]:
    inclusions, errors = store.list("seed-inclusions")
    if errors:
        raise ValueError("; ".join(item["error"] for item in errors))
    seeds: list[dict[str, Any]] = []
    for inclusion in inclusions:
        _validate("seed-inclusion", inclusion)
        if inclusion["state"] != "site-live":
            continue
        if inclusion["rights_status"] != "cleared" or inclusion["ever_public"] is not True:
            raise ValueError(f"public Seed inclusion is not publication-safe: {inclusion['id']}")
        seed = store.read("ideas", str(inclusion["seed_id"]))
        _validate("idea", seed)
        required = ("short_summary", "long_summary", "reference_links", "tags")
        if any(field not in seed for field in required):
            raise ValueError(f"published Seed is incomplete: {seed['id']}")
        display_errors: list[str] = []
        for field in ("title", "short_summary", "long_summary"):
            display_errors.extend(validate_display_text(str(seed[field]), field))
        for index, link in enumerate(seed["reference_links"]):
            display_errors.extend(validate_display_text(str(link["title"]), f"reference_links[{index}].title"))
            if link.get("note"):
                display_errors.extend(validate_display_text(str(link["note"]), f"reference_links[{index}].note"))
        if display_errors:
            raise ValueError("; ".join(display_errors))
        for link in seed["reference_links"]:
            if not _is_safe_public_reference(link.get("url")):
                raise ValueError(f"unsafe public Seed reference URL in {seed['id']}")
        suffix = str(seed["id"]).rsplit("-", 1)[-1]
        item: dict[str, Any] = {
            "id": seed["id"],
            "title": seed["title"],
            "short_summary": seed["short_summary"],
            "long_summary": seed["long_summary"],
            "reference_links": seed["reference_links"],
            "tags": seed["tags"],
            "state": seed["state"],
            "public_path": f"seed-{_slug(str(seed['title']))}-{suffix}.html",
        }
        study_id = seed.get("promoted_study_id")
        if isinstance(study_id, str):
            study = store.read("studies", study_id)
            _validate("study", study)
            item["promoted_study"] = {"id": study["id"], "title": study["title"]}
        seeds.append(item)
    seeds.sort(key=lambda item: (str(item["title"]).lower(), str(item["id"])))
    content = {"schema_version": 1, "seeds": seeds}
    digest = _canonical_digest(content)
    manifest = {**content, "id": f"seed-manifest-{digest[:20]}", "content_sha256": f"sha256:{digest}"}
    _validate("seed-publication-manifest", manifest)
    return manifest


def _links_markup(links: list[dict[str, Any]]) -> str:
    if not links:
        return "<p>No external references are currently attached.</p>"
    rows = []
    for link in links:
        title = html.escape(str(link["title"]))
        url = html.escape(str(link["url"]), quote=True)
        note = f": {html.escape(str(link['note']))}" if link.get("note") else ""
        rows.append(f'<li><a href="{url}" rel="noopener noreferrer">{title}</a>{note}</li>')
    return f"<ul>{''.join(rows)}</ul>"


def _detail(seed: dict[str, Any]) -> str:
    tags = " · ".join(html.escape(str(tag)) for tag in seed["tags"])
    study = ""
    if seed.get("promoted_study"):
        promoted = seed["promoted_study"]
        study = f"<p><strong>Promoted Study:</strong> {html.escape(str(promoted['title']))}</p>"
    return "<!doctype html>\n" + f"""<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(str(seed['title']))} · Seed Bank</title><link rel="stylesheet" href="styles.css"></head><body><main><a href="index.html">← Seed Bank</a><article><div class="eyebrow">{html.escape(str(seed['state']))} Seed</div><h1>{html.escape(str(seed['title']))}</h1><div class="tags">{tags}</div><p>{html.escape(str(seed['long_summary']))}</p>{study}<section class="references"><h2>References</h2>{_links_markup(seed['reference_links'])}</section></article><footer>Curated from the private Bzor Computational Studio Seed Bank.</footer></main></body></html>"""


def _index(manifest: dict[str, Any]) -> str:
    cards = []
    for seed in manifest["seeds"]:
        tags = " · ".join(html.escape(str(tag)) for tag in seed["tags"])
        cards.append(f'<a class="card" href="{html.escape(str(seed["public_path"]), quote=True)}"><div class="state">{html.escape(str(seed["state"]))}</div><h2>{html.escape(str(seed["title"]))}</h2><p>{html.escape(str(seed["short_summary"]))}</p><div class="tags">{tags}</div></a>')
    body = "".join(cards) or '<p class="intro">No Seeds have been made public yet.</p>'
    return "<!doctype html>\n" + f"""<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Ideas incubating in the Bzor Computational Studio."><title>Seed Bank · Bzor Computational Studio</title><link rel="stylesheet" href="styles.css"></head><body><main><div class="eyebrow">Bzor Computational Studio</div><h1>Seed Bank</h1><p class="intro">Ideas, references, and unresolved questions before they become production Studies.</p><div class="grid">{body}</div><footer>Seeds are published selectively; raw brainstorming remains private.</footer></main></body></html>"""


def build_public_seed_bank(store: StudioStore, root: Path, output_directory: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    output = Path(output_directory).resolve()
    if not _inside(output, root / "work" / "public-site"):
        raise ValueError("public Seed Bank output must remain beneath work/public-site")
    manifest = build_seed_manifest(store)
    write_atomic(output / "manifest.json", (json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
    write_atomic(output / "styles.css", _STYLES.encode("utf-8"))
    write_atomic(output / "index.html", _index(manifest).encode("utf-8"))
    for seed in manifest["seeds"]:
        write_atomic(output / seed["public_path"], _detail(seed).encode("utf-8"))
    return {"manifest_id": manifest["id"], "manifest_sha256": manifest["content_sha256"], "seed_count": len(manifest["seeds"]), "output": output.as_posix(), "network_actions": 0}
