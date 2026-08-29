"""Detail-pass promote stages: overlay sequence rendering, compositing, receipts.

Implements the build items of docs/DETAIL_PASS_PROMOTE.md. The overlay itself is
KC's design-overlay-generator; this module drives its deterministic renderer
headlessly (web/capture.html), composites the result over a verified render with
FFmpeg, and binds everything into a promote receipt.

CLI: python -m houdini_ai.detail_promote --help
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OVERLAY_ROOT = PROJECT_ROOT / "design-overlay-generator"
DEFAULT_CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
CAPTURE_INPUT_NAME = "capture-input.js"
FRAME_PATTERN = "overlay-%06d.png"

_ASPECT = re.compile(r"(\d+)\s*[x×]\s*(\d+)")


def discover_chrome(environ: Mapping[str, str] | None = None) -> Path | None:
    env = os.environ if environ is None else environ
    configured = env.get("CHROME_BIN")
    if configured and Path(configured).is_file():
        return Path(configured)
    if DEFAULT_CHROME.is_file():
        return DEFAULT_CHROME
    found = shutil.which("chrome") or shutil.which("chromium")
    return Path(found) if found else None


def parse_aspect(aspect: str) -> tuple[int, int]:
    """Extract WxH from an overlay aspect preset name like '9:16 — 1080×1920'."""
    match = _ASPECT.search(aspect or "")
    if not match:
        raise ValueError(f"aspect {aspect!r} does not contain a WxH resolution")
    return int(match.group(1)), int(match.group(2))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def variation_package_names(study: Mapping[str, Any]) -> dict[str, str]:
    """Return flat Delivery names derived from the sidecar's stable variation."""
    variation = study.get("variation")
    if not isinstance(variation, Mapping):
        raise ValueError("study.json has no variation object")
    stem = variation.get("file_stem")
    if not isinstance(stem, str) or not re.fullmatch(r"var_[0-9]{3}_[a-z0-9]+(?:-[a-z0-9]+)*", stem):
        raise ValueError("study.json variation file_stem is not canonical")
    return {
        "delivery": f"{stem}.delivery.mp4",
        "overlay_frames": f"{stem}.overlay_frames",
        "receipt": f"{stem}.delivery.json",
    }


def overlay_source_version(overlay_root: Path = OVERLAY_ROOT) -> str:
    """Deterministic version of the overlay renderer: hash of its web sources.

    Pins the exact overlay code into promote receipts so a package can be
    rebuilt bit-for-bit. Per-run capture-input.js is excluded.
    """
    web = overlay_root / "web"
    digest = hashlib.sha256()
    for path in sorted(web.glob("*")):
        if not path.is_file() or path.name == CAPTURE_INPUT_NAME:
            continue
        if path.suffix.lower() not in {".js", ".html", ".css"}:
            continue
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def validate_study_sidecar(study: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        variation_package_names(study)
    except ValueError:
        errors.append("study.json is missing canonical variation identity")
    for key in ("id", "title", "fps", "frames"):
        if key not in study:
            errors.append(f"study.json is missing {key!r}")
    frames = study.get("frames")
    if not isinstance(frames, int) or frames < 1:
        errors.append("study.json frames must be a positive integer")
        return errors
    for name, values in (study.get("series") or {}).items():
        if len(values) != frames:
            errors.append(f"series {name!r} has {len(values)} values for {frames} frames")
    bbox = study.get("bbox") or []
    if bbox and len(bbox) != frames:
        errors.append(f"bbox has {len(bbox)} entries for {frames} frames")
    for label, track in (study.get("tracks") or {}).items():
        for key in ("screen", "depth"):
            entries = track.get(key) or []
            if len(entries) != frames:
                errors.append(f"track {label!r} {key} has {len(entries)} entries for {frames} frames")
        for name, values in (track.get("values") or {}).items():
            if len(values) != frames:
                errors.append(f"track {label!r} value {name!r} has {len(values)} entries for {frames} frames")
    bullets = study.get("bullets", [])
    if not isinstance(bullets, list) or any(not isinstance(item, str) for item in bullets):
        errors.append("bullets must be a list of strings")
    return errors


def validate_overlay_config(config: Mapping[str, Any], study: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if config.get("studyId") != study.get("id"):
        errors.append(
            f"overlay config studyId {config.get('studyId')!r} does not match study.json id {study.get('id')!r}"
        )
    try:
        parse_aspect(str(config.get("aspect", "")))
    except ValueError as error:
        errors.append(str(error))
    if not isinstance(config.get("components"), Mapping):
        errors.append("overlay config has no components object")
    return errors


def verify_overlay_frame(path: Path, width: int, height: int) -> list[str]:
    if not path.is_file() or path.stat().st_size == 0:
        return [f"{path.name}: missing or empty"]
    errors: list[str] = []
    try:
        with Image.open(path) as image:
            if image.size != (width, height):
                errors.append(f"{path.name}: size {image.size} != {(width, height)}")
            if image.mode != "RGBA":
                errors.append(f"{path.name}: mode {image.mode} is not RGBA")
            else:
                alpha = image.getchannel("A")
                if alpha.getextrema()[1] == 0:
                    errors.append(f"{path.name}: fully transparent (no overlay content)")
    except OSError as error:
        errors.append(f"{path.name}: {error}")
    return errors


def write_capture_input(study: Mapping[str, Any], config: Mapping[str, Any], overlay_root: Path = OVERLAY_ROOT) -> Path:
    path = overlay_root / "web" / CAPTURE_INPUT_NAME
    payload = json.dumps({"study": study, "config": config}, sort_keys=True)
    path.write_text(f"window.CAPTURE_INPUT = {payload};\n", encoding="utf-8")
    return path


def _capture_command(
    chrome: Path,
    overlay_root: Path,
    frame: int,
    width: int,
    height: int,
    output: Path,
    user_data_dir: Path,
    budget_ms: int,
) -> list[str]:
    page = (overlay_root / "web" / "capture.html").resolve()
    url = page.as_uri() + f"?frame={frame}&w={width}&h={height}"
    return [
        str(chrome),
        "--headless=new",
        "--disable-gpu",
        "--allow-file-access-from-files",
        "--hide-scrollbars",
        "--default-background-color=00000000",
        f"--virtual-time-budget={budget_ms}",
        f"--user-data-dir={user_data_dir}",
        f"--window-size={width},{height}",
        f"--screenshot={output}",
        url,
    ]


def render_overlay_sequence(
    study: Mapping[str, Any],
    config: Mapping[str, Any],
    output_dir: Path,
    *,
    overlay_root: Path = OVERLAY_ROOT,
    chrome: Path | None = None,
    jobs: int = 4,
    budget_ms: int = 10000,
    frame_count: int | None = None,
    log=print,
) -> dict[str, Any]:
    """Render the overlay PNG sequence (alpha) headlessly. Resumable: frames
    that already exist and verify are not re-rendered."""
    study_errors = validate_study_sidecar(study)
    config_errors = validate_overlay_config(config, study)
    if study_errors or config_errors:
        raise ValueError("; ".join(study_errors + config_errors))
    chrome = chrome or discover_chrome()
    if chrome is None:
        raise FileNotFoundError("Chrome executable was not found (set CHROME_BIN)")
    width, height = parse_aspect(str(config["aspect"]))
    frames = int(frame_count if frame_count is not None else study["frames"])
    output_dir.mkdir(parents=True, exist_ok=True)
    capture_input = write_capture_input(study, config, overlay_root)
    rendered: list[int] = []
    reused: list[int] = []
    # Resumability is only valid against identical inputs: stamp a hash of
    # (study, config, overlay source) and re-render everything when it changes.
    inputs_hash = hashlib.sha256(
        json.dumps({"study": study, "config": config}, sort_keys=True).encode("utf-8")
        + overlay_source_version(overlay_root).encode("utf-8")
    ).hexdigest()
    stamp = output_dir / "render-inputs.sha256"
    inputs_match = stamp.is_file() and stamp.read_text(encoding="utf-8").strip() == inputs_hash
    try:
        pending = []
        for frame in range(frames):
            path = output_dir / (FRAME_PATTERN % frame)
            if inputs_match and not verify_overlay_frame(path, width, height):
                reused.append(frame)
            else:
                pending.append(frame)
        stamp.write_text(inputs_hash + "\n", encoding="utf-8")

        def render_frame(frame: int) -> None:
            path = output_dir / (FRAME_PATTERN % frame)
            with tempfile.TemporaryDirectory(prefix="dog-chrome-") as profile:
                command = _capture_command(
                    chrome, overlay_root, frame, width, height, path.resolve(), Path(profile), budget_ms
                )
                subprocess.run(command, check=True, capture_output=True, text=True, timeout=budget_ms / 1000 + 120)
            errors = verify_overlay_frame(path, width, height)
            if errors:
                raise RuntimeError(f"frame {frame} failed verification: {errors}")
            rendered.append(frame)

        if pending:
            log(f"rendering {len(pending)} overlay frames ({len(reused)} already valid)")
            with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
                for _ in pool.map(render_frame, pending):
                    pass
    finally:
        capture_input.unlink(missing_ok=True)
    return {
        "frames": frames,
        "width": width,
        "height": height,
        "rendered": sorted(rendered),
        "reused_existing": reused,
        "pattern": FRAME_PATTERN,
        "overlay_source_version": overlay_source_version(overlay_root),
    }


def _discover_ffmpeg(name: str) -> Path:
    from .doctor import discover_tools

    tool = next((tool for tool in discover_tools() if tool.name == name), None)
    if tool is None or tool.path is None:
        raise FileNotFoundError(f"{name} was not found (set FFMPEG_BIN)")
    return tool.path


def composite_overlay(
    render_input: Path,
    overlay_dir: Path,
    output: Path,
    *,
    fps: float,
    frames: int,
    render_start_number: int | None = None,
    ffmpeg: Path | None = None,
    crf: int = 14,
) -> dict[str, Any]:
    """Composite the overlay sequence over the verified render with FFmpeg.

    render_input is either an encoded video or a printf-style PNG pattern
    (with render_start_number). The overlay sequence must match the render's
    frame count and resolution; FFmpeg's overlay filter fails hard otherwise.
    """
    ffmpeg = ffmpeg or _discover_ffmpeg("ffmpeg")
    missing = [
        frame for frame in range(frames)
        if not (overlay_dir / (FRAME_PATTERN % frame)).is_file()
    ]
    if missing:
        raise FileNotFoundError(f"overlay sequence is missing {len(missing)} frames (first: {missing[0]})")
    output.parent.mkdir(parents=True, exist_ok=True)
    render_args = ["-i", str(render_input)]
    if render_start_number is not None:
        render_args = ["-framerate", str(fps), "-start_number", str(render_start_number), "-i", str(render_input)]
    command = [
        str(ffmpeg), "-y", "-loglevel", "error",
        *render_args,
        "-framerate", str(fps), "-start_number", "0", "-i", str(overlay_dir / FRAME_PATTERN),
        "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto",
        "-frames:v", str(frames),
        "-c:v", "libx264", "-preset", "slow", "-crf", str(crf),
        # aq-mode 3 spends bits on smooth/dark gradients, the studio's most
        # banding-prone content; the render's own dither survives the encode.
        "-x264-params", "aq-mode=3:aq-strength=1.0",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(output),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("composite produced no output")
    return {"output": str(output), "bytes": output.stat().st_size, "sha256": sha256_file(output)}


def build_promote_receipt(
    *,
    study_path: Path,
    config_path: Path,
    render_input: Path,
    render_receipt_path: Path | None,
    overlay_result: Mapping[str, Any],
    composite_result: Mapping[str, Any],
    overlay_root: Path = OVERLAY_ROOT,
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "kind": "detail-promote-receipt",
        "state": "post-ready",
        "inputs": {
            "study_json": {"path": str(study_path), "sha256": sha256_file(study_path)},
            "overlay_config": {"path": str(config_path), "sha256": sha256_file(config_path)},
            "render_input": {
                "path": str(render_input),
                "sha256": sha256_file(render_input) if render_input.is_file() else None,
            },
        },
        "overlay": dict(overlay_result),
        "composite": dict(composite_result),
        "overlay_source_version": overlay_source_version(overlay_root),
    }
    if render_receipt_path is not None:
        receipt["inputs"]["render_receipt"] = {
            "path": str(render_receipt_path),
            "sha256": sha256_file(render_receipt_path),
        }
    return receipt


def run_promote(
    *,
    study_path: Path,
    config_path: Path,
    render_input: Path,
    output_dir: Path,
    render_receipt_path: Path | None = None,
    render_start_number: int | None = None,
    frame_count: int | None = None,
    jobs: int = 4,
    log=print,
) -> dict[str, Any]:
    """Full promote: validate → render overlay sequence → composite → receipt.

    Never uploads anything; the post-ready package lands in output_dir.
    """
    study = json.loads(study_path.read_text(encoding="utf-8"))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    names = variation_package_names(study)
    overlay_dir = output_dir / names["overlay_frames"]
    overlay_result = render_overlay_sequence(
        study, config, overlay_dir, jobs=jobs, frame_count=frame_count, log=log
    )
    final_path = output_dir / names["delivery"]
    composite_result = composite_overlay(
        render_input,
        overlay_dir,
        final_path,
        fps=float(study["fps"]),
        frames=int(overlay_result["frames"]),
        render_start_number=render_start_number,
    )
    receipt = build_promote_receipt(
        study_path=study_path,
        config_path=config_path,
        render_input=render_input,
        render_receipt_path=render_receipt_path,
        overlay_result=overlay_result,
        composite_result=composite_result,
    )
    receipt_path = output_dir / names["receipt"]
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log(f"post-ready: {final_path}")
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detail-pass promote: overlay render, composite, receipt.")
    parser.add_argument("--study", type=Path, required=True, help="study.json sidecar")
    parser.add_argument("--config", type=Path, required=True, help="exported overlay-config.json")
    parser.add_argument("--render", type=Path, required=True, help="verified render video or printf PNG pattern")
    parser.add_argument("--render-receipt", type=Path, help="render receipt to bind into the promote receipt")
    parser.add_argument("--render-start-number", type=int, help="start number when --render is a PNG pattern")
    parser.add_argument("--out", type=Path, required=True, help="output package directory")
    parser.add_argument("--frames", type=int, help="override frame count (defaults to study.json frames)")
    parser.add_argument("--jobs", type=int, default=4, help="parallel Chrome captures")
    args = parser.parse_args(argv)
    run_promote(
        study_path=args.study,
        config_path=args.config,
        render_input=args.render,
        output_dir=args.out,
        render_receipt_path=args.render_receipt,
        render_start_number=args.render_start_number,
        frame_count=args.frames,
        jobs=args.jobs,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
