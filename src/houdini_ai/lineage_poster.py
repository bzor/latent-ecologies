"""Render a study-completion lineage poster from a declarative spec.

A completed Study earns a closing artifact: one poster in the studio's
instrument language (hairline furniture, micro-type, one large typographic
moment, restrained accent) tracing the pipeline the specimen travelled —
behavior, look, render, detail pass, package — with real dates, measurements,
and checksums as the design material. The generator is study-agnostic: all
facts arrive via a spec JSON assembled from canonical records, so the poster
never invents data. Rendering reuses the overlay generator's headless-Chrome
path and font library.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image

POSTER_SIZE = (1080, 1350)
POSTER_SCALE = 2

REPO_ROOT = Path(__file__).resolve().parents[2]
FONT_DIR = REPO_ROOT / "design-overlay-generator" / "web" / "fonts"
_FONTS = {
    "numeral": "Isonorm Monospaced Regular.otf",
    "display": "Isonorm Regular.otf",
    "mono": "IosevkaTermNerdFontMono-Light.ttf",
}

REQUIRED_SPEC_FIELDS = ("study", "palette", "stages")


def _discover_chrome() -> Path:
    from .detail_promote import discover_chrome

    chrome = discover_chrome()
    if chrome is None:
        raise FileNotFoundError("Chrome was not found (set CHROME_BIN)")
    return chrome


def validate_spec(spec: Mapping[str, Any]) -> list[str]:
    errors = []
    for field in REQUIRED_SPEC_FIELDS:
        if field not in spec:
            errors.append(f"spec.{field} is required")
    study = spec.get("study", {})
    for field in ("number", "title"):
        if not study.get(field) and study.get(field) != 0:
            errors.append(f"spec.study.{field} is required")
    palette = spec.get("palette", {})
    for field in ("ground", "ink", "accent"):
        value = palette.get(field, "")
        if not (isinstance(value, str) and value.startswith("#")):
            errors.append(f"spec.palette.{field} must be a hex color")
    stages = spec.get("stages", [])
    if not isinstance(stages, list) or not stages:
        errors.append("spec.stages must be a non-empty list")
    else:
        for index, stage in enumerate(stages):
            if not stage.get("label"):
                errors.append(f"spec.stages[{index}].label is required")
    plate = spec.get("plate")
    if plate and not Path(str(plate.get("image", ""))).is_file():
        errors.append("spec.plate.image must be an existing file")
    return errors


def _font_faces() -> str:
    faces = []
    for name, filename in _FONTS.items():
        path = FONT_DIR / filename
        if path.is_file():
            faces.append(
                f"@font-face{{font-family:'{name}';src:url('{path.resolve().as_uri()}')}}"
            )
    return "".join(faces)


def _stage_html(stage: Mapping[str, Any], accent: str) -> str:
    label = html.escape(str(stage.get("label", "")))
    date = html.escape(str(stage.get("date", "")))
    gate = bool(stage.get("gate"))
    facts = "".join(
        f"<div class='fact'>{html.escape(str(fact))}</div>" for fact in stage.get("facts", [])
    )
    digest = stage.get("hash")
    hash_html = f"<span class='hash'>{html.escape(str(digest))}</span>" if digest else ""
    marker = "<span class='node gate'></span>" if gate else "<span class='node'></span>"
    date_html = f"<span class='date'>{date}</span>" if date else ""
    return (
        f"<div class='stage'>{marker}<div class='stage-body'>"
        f"<div class='stage-head'><span class='stage-label'>{label}</span>{date_html}{hash_html}</div>"
        f"{facts}</div></div>"
    )


def build_poster_html(spec: Mapping[str, Any]) -> str:
    study = spec["study"]
    palette = spec["palette"]
    ground, ink, accent = palette["ground"], palette["ink"], palette["accent"]
    number = f"{int(study['number']):03d}"
    title = html.escape(str(study["title"]).upper())
    subtitle = html.escape(str(study.get("subtitle", "")))
    completed = html.escape(str(study.get("completed", "")))
    credit = html.escape(str(study.get("credit", "BZOR COMPUTATIONAL STUDIO")))
    variation = html.escape(str(study.get("variation", "")))

    plate_html = ""
    plate = spec.get("plate")
    if plate:
        image_uri = Path(str(plate["image"])).resolve().as_uri()
        caption = html.escape(str(plate.get("caption", "")))
        plate_html = (
            f"<div class='plate'><img src='{image_uri}' alt=''>"
            f"<div class='plate-caption'>{caption}</div></div>"
        )

    stages_html = "".join(_stage_html(stage, accent) for stage in spec["stages"])
    footer_lines = "".join(
        f"<div>{html.escape(str(line))}</div>" for line in spec.get("footer", [])
    )

    width, height = POSTER_SIZE
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
{_font_faces()}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{width}px;height:{height}px;overflow:hidden}}
body{{background:{ground};color:{ink};font-family:'mono',Consolas,monospace;position:relative}}
.frame{{position:absolute;inset:26px;pointer-events:none}}
.frame i{{position:absolute;width:14px;height:14px;border:0 solid {ink}}}
.frame i:nth-child(1){{top:0;left:0;border-top-width:1px;border-left-width:1px}}
.frame i:nth-child(2){{top:0;right:0;border-top-width:1px;border-right-width:1px}}
.frame i:nth-child(3){{bottom:0;left:0;border-bottom-width:1px;border-left-width:1px}}
.frame i:nth-child(4){{bottom:0;right:0;border-bottom-width:1px;border-right-width:1px}}
.reg{{position:absolute;background:{ink};opacity:.55}}
.reg.h{{width:9px;height:1px}}.reg.v{{width:1px;height:9px}}
.micro{{font-size:10px;letter-spacing:.06em;line-height:1.5;opacity:.75}}
.top{{position:absolute;top:44px;left:54px;right:54px;display:flex;justify-content:space-between}}
.top .right{{text-align:right}}
.content{{position:absolute;top:96px;left:54px;right:54px;bottom:150px;display:flex;gap:44px}}
.left-col{{width:436px;display:flex;flex-direction:column}}
.numeral{{font-family:'numeral','display',Consolas,monospace;font-size:250px;line-height:.86;letter-spacing:-.03em;margin-top:6px}}
.title{{font-family:'display',Consolas,monospace;font-size:32px;letter-spacing:.14em;margin-top:20px}}
.variation{{font-size:12px;letter-spacing:.1em;opacity:.75;margin-top:8px}}
.subtitle{{font-size:13px;line-height:1.55;margin-top:16px;max-width:380px;opacity:.9}}
.rule{{height:1px;background:{ink};opacity:.4;margin:26px 0 22px}}
.plate{{margin-top:auto}}
.plate img{{width:100%;display:block;border:1px solid {ink}}}
.plate-caption{{font-size:9px;letter-spacing:.08em;opacity:.7;margin-top:8px;line-height:1.5}}
.rail{{flex:1;position:relative;padding-left:26px;margin-top:10px;display:flex;flex-direction:column}}
.rail::before{{content:'';position:absolute;left:4px;top:8px;bottom:8px;width:1px;background:{ink};opacity:.45}}
.rail-title{{font-size:11px;letter-spacing:.28em;margin-bottom:26px;margin-left:-26px;opacity:.8}}
.stages{{flex:1;display:flex;flex-direction:column;justify-content:space-evenly;padding-bottom:34px}}
.stage{{position:relative}}
.node{{position:absolute;left:-26px;top:3px;width:7px;height:7px;border:1px solid {ink};background:{ground}}}
.node.gate{{background:{accent};border-color:{accent}}}
.stage-head{{display:flex;align-items:baseline;gap:12px}}
.stage-label{{font-family:'display',Consolas,monospace;font-size:15px;letter-spacing:.2em}}
.date{{font-size:10px;opacity:.7}}
.hash{{font-size:10px;color:{accent};margin-left:auto;letter-spacing:.05em}}
.fact{{font-size:11px;line-height:1.6;opacity:.82;margin-top:3px}}
.footer{{position:absolute;left:54px;right:54px;bottom:52px;border-top:1px solid {ink};padding-top:14px;display:flex;justify-content:space-between;align-items:flex-end}}
.footer .lines{{font-size:9.5px;letter-spacing:.06em;line-height:1.7;opacity:.8}}
.footer .complete{{font-family:'display',Consolas,monospace;font-size:13px;letter-spacing:.3em;color:{accent};text-align:right}}
.accentbar{{position:absolute;left:54px;top:96px;width:34px;height:5px;background:{accent}}}
</style></head><body>
<div class="frame"><i></i><i></i><i></i><i></i></div>
<div class="reg h" style="top:26px;left:50%"></div><div class="reg v" style="top:26px;left:50%"></div>
<div class="reg h" style="bottom:26px;left:50%"></div><div class="reg v" style="bottom:26px;left:50%"></div>
<div class="reg h" style="top:50%;left:26px"></div><div class="reg h" style="top:50%;right:26px"></div>
<div class="top micro"><div>{credit}</div><div class="right">STUDY {number} · SPECIMEN LINEAGE</div></div>
<div class="accentbar"></div>
<div class="content">
  <div class="left-col">
    <div class="numeral">{number}</div>
    <div class="title">{title}</div>
    <div class="variation">{variation}</div>
    <div class="subtitle">{subtitle}</div>
    <div class="rule"></div>
    {plate_html}
  </div>
  <div class="rail">
    <div class="rail-title">PIPELINE RECORD</div>
    <div class="stages">{stages_html}</div>
  </div>
</div>
<div class="footer"><div class="lines">{footer_lines}</div><div class="complete">PIPELINE<br>COMPLETE<br>{completed}</div></div>
</body></html>
"""


def render_poster(
    spec: Mapping[str, Any],
    output: Path,
    *,
    chrome: Path | None = None,
    scale: int = POSTER_SCALE,
) -> dict[str, Any]:
    errors = validate_spec(spec)
    if errors:
        raise ValueError("invalid poster spec: " + "; ".join(errors))
    chrome = chrome or _discover_chrome()
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    page = output.with_suffix(".html")
    page.write_text(build_poster_html(spec), encoding="utf-8")

    width, height = POSTER_SIZE
    subprocess.run(
        [
            str(chrome),
            "--headless=new",
            "--disable-gpu",
            "--allow-file-access-from-files",
            "--hide-scrollbars",
            "--virtual-time-budget=5000",
            f"--window-size={width},{height}",
            f"--force-device-scale-factor={scale}",
            f"--screenshot={output}",
            page.resolve().as_uri(),
        ],
        check=True,
        capture_output=True,
    )
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("Chrome did not produce the poster PNG")
    with Image.open(output) as image:
        if image.size != (width * scale, height * scale):
            raise RuntimeError(f"poster rendered at {image.size}, expected {(width * scale, height * scale)}")

    def record_path(path: Path) -> str:
        resolved = path.resolve()
        if resolved.is_relative_to(REPO_ROOT):
            return resolved.relative_to(REPO_ROOT).as_posix()
        return str(resolved)

    data = output.read_bytes()
    receipt = {
        "schema_version": 1,
        "kind": "lineage-poster-receipt",
        "size": [width * scale, height * scale],
        "output": {"path": record_path(output), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()},
        "page": record_path(page),
        "study": dict(spec["study"]),
    }
    receipt_path = output.with_suffix(".receipt.json")
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt["receipt_path"] = str(receipt_path)
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m houdini_ai.lineage_poster",
        description="Render a study-completion lineage poster from a spec JSON.",
    )
    parser.add_argument("spec", type=Path, help="poster spec JSON assembled from canonical records")
    parser.add_argument("--out", required=True, type=Path, help="output .png path")
    args = parser.parse_args(argv)
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    receipt = render_poster(spec, args.out)
    print(json.dumps({k: receipt[k] for k in ("output", "receipt_path")}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
