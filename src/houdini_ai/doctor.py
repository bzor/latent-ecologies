from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


@dataclass(frozen=True)
class Tool:
    name: str
    path: Path | None
    source: str
    required: bool = True


def _configured_tool(value: str | None, names: Sequence[str]) -> Path | None:
    if not value:
        return None
    path = Path(os.path.expandvars(value)).expanduser()
    if path.is_file():
        return path.resolve()
    if path.is_dir():
        return next((candidate.resolve() for name in names if (candidate := path / name).is_file()), None)
    found = shutil.which(value)
    return Path(found).resolve() if found else None


def _sidefx_roots() -> list[Path]:
    if os.name != "nt":
        return []
    base = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Side Effects Software"
    if not base.is_dir():
        return []
    versions: list[tuple[tuple[int, ...], Path]] = []
    for path in base.glob("Houdini *"):
        match = re.fullmatch(r"Houdini (\d+(?:\.\d+)+)", path.name)
        if match:
            versions.append((tuple(int(part) for part in match.group(1).split(".")), path))
    return [path for _, path in sorted(versions, reverse=True)]


def discover_tools(environ: Mapping[str, str] | None = None) -> list[Tool]:
    env = os.environ if environ is None else environ
    houdini_bin = env.get("HOUDINI_BIN")
    roots = _sidefx_roots() if environ is None else []

    def find_houdini(name: str) -> Tool:
        executable = f"{name}.exe" if os.name == "nt" else name
        configured = _configured_tool(houdini_bin, (executable, name))
        if configured:
            return Tool(name, configured, "HOUDINI_BIN")
        found = shutil.which(executable) or shutil.which(name)
        if found:
            return Tool(name, Path(found).resolve(), "PATH")
        standard = next((root / "bin" / executable for root in roots if (root / "bin" / executable).is_file()), None)
        return Tool(name, standard.resolve() if standard else None, "standard SideFX install" if standard else "not found")

    def find_media(name: str, required: bool = True) -> Tool:
        executable = f"{name}.exe" if os.name == "nt" else name
        configured_value = env.get("FFMPEG_BIN")
        configured = _configured_tool(configured_value, (executable, name))
        if configured:
            # FFMPEG_BIN may name either executable; always select the requested
            # sibling rather than accidentally treating ffprobe as ffmpeg.
            if configured.stem.lower() != name:
                sibling = configured.with_name(executable)
                configured = sibling if sibling.is_file() else None
            if configured:
                return Tool(name, configured, "FFMPEG_BIN", required)
        found = shutil.which(executable) or shutil.which(name)
        return Tool(name, Path(found).resolve() if found else None, "PATH" if found else "not found", required)

    return [find_houdini("hython"), find_houdini("hbatch"), find_media("ffmpeg"), find_media("ffprobe")]


def run_probe(command: Sequence[str], timeout: int = 60) -> tuple[bool, str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    return result.returncode == 0, output


def inspect_workstation(environ: Mapping[str, str] | None = None) -> tuple[list[str], list[str]]:
    tools = discover_tools(environ)
    lines = [f"platform: {platform.platform()}"]
    errors: list[str] = []
    for tool in tools:
        lines.append(f"{tool.name}: {tool.path or 'NOT FOUND'} [{tool.source}]")
        if tool.required and tool.path is None:
            variable = "HOUDINI_BIN" if tool.name in {"hython", "hbatch"} else "FFMPEG_BIN"
            errors.append(f"{tool.name} is required; install it or set {variable} to its executable or bin directory")

    by_name = {tool.name: tool for tool in tools}
    hython = by_name["hython"].path
    if hython:
        script = (
            "import hou,sys; "
            "print('houdini_build:', hou.applicationVersionString()); "
            "print('python:', sys.version.split()[0]); "
            "print('license:', hou.licenseCategory().name()); "
            "lop=hou.nodeTypeCategories().get('Lop'); "
            "nodes=lop.nodeTypes() if lop else {}; "
            "karma=sorted(n for n in nodes if 'karma' in n.lower()); "
            "print('lop_nodes:', len(nodes)); "
            "print('karma_node_types:', ','.join(karma) if karma else 'NONE')"
        )
        ok, output = run_probe((str(hython), "-c", script))
        lines.append("houdini probe: " + ("OK" if ok else "FAILED"))
        lines.extend(f"  {line}" for line in output.splitlines()[-8:])
        if not ok:
            errors.append("hython could not initialize Houdini; check licensing and the diagnostic output above")
        elif "karma_node_types: NONE" in output:
            errors.append("Houdini initialized but no Karma LOP node types are available")

    ffmpeg = by_name["ffmpeg"].path
    if ffmpeg:
        ok, output = run_probe((str(ffmpeg), "-version"), timeout=10)
        first = output.splitlines()[0] if output else "no version output"
        lines.append(f"ffmpeg probe: {'OK' if ok else 'FAILED'} ({first})")
        if not ok:
            errors.append("ffmpeg was found but could not be executed")
    return lines, errors
