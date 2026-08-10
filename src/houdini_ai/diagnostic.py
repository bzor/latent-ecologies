from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping

from PIL import Image


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_diagnostic_png(path: Path, expected_size: tuple[int, int] = (320, 180)) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"diagnostic image is missing: {path}")
    try:
        with Image.open(path) as image:
            image.load()
            if image.format != "PNG":
                raise RuntimeError(f"diagnostic image is {image.format}, expected PNG")
            if image.size != expected_size:
                raise RuntimeError(f"diagnostic image is {image.size}, expected {expected_size}")
            if image.mode != "RGBA":
                raise RuntimeError(f"diagnostic image mode is {image.mode}, expected RGBA")
            extrema = image.getextrema()
            if not any(low != high for low, high in extrema[:3]):
                raise RuntimeError("diagnostic image is visually blank")
            alpha = extrema[3]
            if alpha[1] == 0:
                raise RuntimeError("diagnostic image is fully transparent")
            return {
                "format": image.format,
                "width": image.width,
                "height": image.height,
                "mode": image.mode,
                "channel_extrema": [list(values) for values in extrema],
            }
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"diagnostic image is not a readable PNG: {path}: {exc}") from exc


def _source_revision(root: Path) -> str:
    if revision := os.environ.get("GITHUB_SHA"):
        return revision
    try:
        result = subprocess.run(
            ("git", "-C", str(root), "rev-parse", "HEAD"),
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _tool_version(name: str) -> str:
    executable = shutil.which(name)
    if not executable:
        return "not found"
    try:
        result = subprocess.run(
            (executable, "-version"), capture_output=True, text=True, timeout=10, check=False
        )
        output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
        return output.splitlines()[0] if output else f"exit {result.returncode}; no version output"
    except (OSError, subprocess.SubprocessError) as exc:
        return f"unavailable: {exc}"


def build_receipt(
    root: Path,
    image_path: Path,
    hip_path: Path,
    image_metadata: Mapping[str, Any],
    houdini_metadata: Mapping[str, str],
) -> dict[str, Any]:
    project_config = json.loads((root / "config" / "project.json").read_text(encoding="utf-8"))
    study = json.loads((root / "studies" / "001-memory-field" / "study.json").read_text(encoding="utf-8"))
    return {
        "receipt_version": 1,
        "source_revision": _source_revision(root),
        "schema_version": study["schema_version"],
        "effective_config": {
            "project": project_config,
            "diagnostic": {"frame": 1, "renderer": "Karma CPU", "resolution": [320, 180], "samples_per_pixel": 4},
        },
        "tools": {
            "houdini": dict(houdini_metadata),
            "python": platform.python_version(),
            "ffmpeg": _tool_version("ffmpeg"),
            "ffprobe": _tool_version("ffprobe"),
        },
        "os": {"platform": platform.platform(), "python_implementation": platform.python_implementation()},
        "artifacts": {
            "hip": {"path": hip_path.relative_to(root).as_posix(), "sha256": sha256_file(hip_path)},
            "image": {
                "path": image_path.relative_to(root).as_posix(),
                "sha256": sha256_file(image_path),
                **dict(image_metadata),
            },
        },
    }


def write_receipt(path: Path, receipt: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
