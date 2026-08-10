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
        if found:
            return Tool(name, Path(found).resolve(), "PATH", required)
        if os.name == "nt" and environ is None:
            local_app_data = os.environ.get("LOCALAPPDATA")
            packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages" if local_app_data else None
            if packages and packages.is_dir():
                matches = sorted(packages.glob(f"Gyan.FFmpeg_*/*/bin/{executable}"), reverse=True)
                if matches:
                    return Tool(name, matches[0].resolve(), "WinGet package", required)
        return Tool(name, None, "not found", required)

    tools = [find_houdini("hython"), find_houdini("hbatch"), find_media("ffmpeg"), find_media("ffprobe")]
    hython = tools[0]
    hgpuinfo_name = "hgpuinfo.exe" if os.name == "nt" else "hgpuinfo"
    hgpuinfo = hython.path.with_name(hgpuinfo_name) if hython.path else None
    tools.append(Tool("hgpuinfo", hgpuinfo if hgpuinfo and hgpuinfo.is_file() else None, "Houdini bin", False))
    return tools


def run_probe(command: Sequence[str], timeout: int = 60) -> tuple[bool, str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    return result.returncode == 0, output


def _probe_tool(tool: Tool, arguments: Sequence[str], timeout: int) -> tuple[bool, str]:
    if tool.path is None:
        return False, "not found"
    return run_probe((str(tool.path), *arguments), timeout=timeout)


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
    hython = by_name["hython"]
    if hython.path:
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
        ok, output = _probe_tool(hython, ("-c", script), timeout=60)
        lines.append("hython probe: " + ("OK" if ok else "FAILED"))
        lines.extend(f"  {line}" for line in output.splitlines()[-8:])
        if not ok:
            errors.append("hython could not initialize Houdini; check licensing and the diagnostic output above")
        elif "karma_node_types: NONE" in output:
            errors.append("Houdini initialized but no Karma LOP node types are available")

    hbatch = by_name["hbatch"]
    if hbatch.path:
        ok, output = _probe_tool(hbatch, ("-c", "quit"), timeout=60)
        lines.append("hbatch probe: " + ("OK" if ok else "FAILED"))
        lines.extend(f"  {line}" for line in output.splitlines()[-4:])
        if not ok:
            errors.append("hbatch was found but could not initialize Houdini")

    hgpuinfo = by_name["hgpuinfo"]
    if hgpuinfo.path:
        ok, output = _probe_tool(hgpuinfo, ("-c", "-l"), timeout=30)
        lines.append("render devices: " + ("OK" if ok else "UNAVAILABLE"))
        if ok:
            devices: list[tuple[str, str, str]] = []
            current: dict[str, str] = {}
            for line in output.splitlines():
                match = re.match(r"(?:\[\*HFS )?(OpenCL Device|OpenCL Type|Global Memory)\*?\]?\s+(.+)", line.strip())
                if not match:
                    continue
                key, value = match.groups()
                if key == "OpenCL Device" and current.get("OpenCL Device"):
                    devices.append((current["OpenCL Type"], current["OpenCL Device"], current.get("Global Memory", "unknown memory")))
                    current = {}
                current[key] = value.strip()
            if current.get("OpenCL Device") and current.get("OpenCL Type"):
                devices.append((current["OpenCL Type"], current["OpenCL Device"], current.get("Global Memory", "unknown memory")))
            devices = list(dict.fromkeys(devices))
            if devices:
                for device_type, name, memory in devices:
                    lines.append(f"  {device_type}: {name} ({memory})")
            else:
                lines.append("  no OpenCL devices reported")
        else:
            lines.append("  hgpuinfo could not enumerate devices; Karma CPU rendering may still be available")
    else:
        lines.append("render devices: hgpuinfo not found; Karma CPU rendering may still be available")

    for name in ("ffmpeg", "ffprobe"):
        tool = by_name[name]
        if not tool.path:
            continue
        ok, output = _probe_tool(tool, ("-version",), timeout=10)
        first = output.splitlines()[0] if output else "no version output"
        lines.append(f"{name} probe: {'OK' if ok else 'FAILED'} ({first})")
        if not ok:
            errors.append(f"{name} was found but could not be executed")
    return lines, errors
