"""Export a checksum-bound overlay parameter manifest without the Houdini GUI.

Usage:
    hython houdini/export_overlay_manifest_headless.py <locked.hiplc> <node_path>
        [--manifest-path <output.json>]

The HDA's own export button cannot bind a HIP checksum headlessly, because
``hou.hipFile.hasUnsavedChanges()`` reports true in hython immediately after a
clean load. This driver supplies the missing evidence instead: it hashes the HIP
on disk, loads it, presses the HDA's exporter without any other scene mutation,
and then binds the manifest to the pre-load hash after verifying the file is
unchanged. The binding is recorded as ``source.checksum_binding:
"headless-clean-load"``.

Overriding the manifest output path edits one parm on the node before export;
that parm carries no overlay key, so the parameter snapshot is unaffected, and
the HIP on disk is never saved or altered. Run with MSYS_NO_PATHCONV=1 under Git Bash so the node path
survives argument rewriting.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from houdini_ai.overlay_parameter_manifest import bind_headless_overlay_manifest  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("hip", type=Path, help="the locked Look HIP")
    parser.add_argument("node_path", help="path of the behavior HDA node, e.g. /obj/.../BEHAVIOR")
    parser.add_argument("--manifest-path", type=Path, default=None, help="override the node's manifest output path")
    args = parser.parse_args(argv)

    hip = args.hip.resolve()
    if not hip.is_file():
        raise SystemExit(f"HIP not found: {hip}")
    pre_load = "sha256:" + hashlib.sha256(hip.read_bytes()).hexdigest()

    import hou

    hou.hipFile.load(str(hip), suppress_save_prompt=True, ignore_load_warnings=True)
    node = hou.node(args.node_path)
    if node is None:
        raise SystemExit(f"node not found in {hip}: {args.node_path}")

    if args.manifest_path is not None:
        node.parm("overlay_manifest_path").set(str(args.manifest_path.resolve()))
    manifest = node.hdaModule().export_overlay_manifest(node)
    manifest_path = Path(node.parm("overlay_manifest_path").evalAsString())

    bound = bind_headless_overlay_manifest(manifest_path, hip, pre_load)
    print(
        json.dumps(
            {
                "manifest_path": str(manifest_path),
                "hip_sha256": bound["source"]["hip_sha256"],
                "checksum_binding": bound["source"].get("checksum_binding"),
                "parameters": len(manifest["parameters"]),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
