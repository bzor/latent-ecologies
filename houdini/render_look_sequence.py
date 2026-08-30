"""Bounded, resumable render of a Look HIP's Karma ROP (artist-led handoff §7).

Loads the HIP read-only, renders the USD Render ROP over the frame range in
contiguous runs, skipping frames whose PNG already exists and passes a cheap
validity check (PNG magic + minimum size). Interruption-safe: rerun the same
command and only missing/invalid frames render again. Writes a render receipt
beside the frames binding the HIP checksum.

    hython houdini/render_look_sequence.py <look.hiplc> --start 205 --end 650

Resume is only safe for a scene whose geometry is deterministic across processes.
A live-HDA scene re-cooks its solver from the start frame on every run, and a
multi-threaded solver drifts at float level between processes, so frames rendered
in different runs sit on slightly different trajectories. The seam is invisible
per-frame and reads as a one-frame pop in motion. A single-frame run is the worst
case: it agrees with neither neighbour.

This script therefore reports how many runs a render took and refuses to pretend a
stitched sequence is equivalent to a continuous one. Use --require-contiguous for a
delivery render, and verify the result with scripts/verify_render_sequence.py. See
docs/RENDER_INTEGRITY.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import hou

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MIN_BYTES = 8 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def frame_valid(path: Path) -> bool:
    try:
        if not path.is_file() or path.stat().st_size < MIN_BYTES:
            return False
        with path.open("rb") as stream:
            return stream.read(8) == PNG_MAGIC
    except OSError:
        return False


def contiguous_runs(frames: list[int]) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    for frame in frames:
        if runs and frame == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], frame)
        else:
            runs.append((frame, frame))
    return runs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hip", type=Path)
    parser.add_argument("--rop", default="/stage/OUT_KARMA")
    parser.add_argument("--picture-node", default="/stage/RENDER_KARMA_SETTINGS")
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument(
        "--require-contiguous",
        action="store_true",
        help="refuse to render unless every requested frame is pending, so the run has no seams",
    )
    args = parser.parse_args()

    hip = args.hip.resolve()
    hip_sha = sha256_file(hip)
    hou.hipFile.load(str(hip).replace("\\", "/"), suppress_save_prompt=True, ignore_load_warnings=True)
    rop = hou.node(args.rop)
    picture_parm = hou.parm(args.picture_node + "/picture")
    if rop is None or picture_parm is None:
        print(f"RENDER-FAILED missing node {args.rop if rop is None else args.picture_node}", flush=True)
        return 1

    frames = list(range(args.start, args.end + 1))
    frame_paths = {frame: Path(picture_parm.evalAtFrame(frame)) for frame in frames}
    pending = [frame for frame in frames if not frame_valid(frame_paths[frame])]
    skipped = len(frames) - len(pending)
    runs = contiguous_runs(pending)
    print(f"render plan: {len(pending)} to render, {skipped} already valid", flush=True)

    single_run = len(runs) == 1 and skipped == 0
    if not single_run and pending:
        print(
            f"WARNING seam risk: this render covers {len(runs)} run(s) and reuses {skipped} "
            "existing frame(s). Frames from different runs sit on slightly different solver "
            "trajectories and produce a visible one-frame pop where they join. Delete the "
            "range and re-render it in one pass for a delivery. See docs/RENDER_INTEGRITY.md.",
            flush=True,
        )
        if args.require_contiguous:
            print(
                f"RENDER-REFUSED --require-contiguous given but {skipped} frame(s) already valid "
                f"and pending frames form {len(runs)} run(s)",
                flush=True,
            )
            return 2

    started = time.time()
    failed: list[int] = []
    for run_start, run_end in runs:
        print(f"rendering frames {run_start}-{run_end}", flush=True)
        try:
            rop.render(frame_range=(run_start, run_end), verbose=False)
        except hou.OperationFailed as error:
            print(f"run {run_start}-{run_end} raised: {error}", flush=True)
        for frame in range(run_start, run_end + 1):
            if frame_valid(frame_paths[frame]):
                print(f"frame {frame} ok", flush=True)
            else:
                failed.append(frame)
                print(f"frame {frame} INVALID", flush=True)

    receipt = {
        "schema_version": 1,
        "kind": "look-render-receipt",
        "hip": {"path": str(hip), "sha256": hip_sha},
        "rop": args.rop,
        "frame_range": [args.start, args.end],
        "frames": len(frames),
        "rendered_this_run": len(pending) - len(failed),
        "reused_existing": skipped,
        "runs": len(runs),
        "run_ranges": [list(run) for run in runs],
        "single_contiguous_run": single_run,
        "seam_risk": not single_run,
        "failed_frames": failed,
        "elapsed_seconds": round(time.time() - started, 1),
        "picture_pattern": picture_parm.unexpandedString(),
        "files": {
            frame_paths[frame].name: {
                "bytes": frame_paths[frame].stat().st_size,
                "sha256": sha256_file(frame_paths[frame]),
            }
            for frame in frames
            if frame_valid(frame_paths[frame])
        },
    }
    receipt_path = frame_paths[frames[0]].parent / "render-receipt.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if failed:
        print(f"RENDER-FAILED invalid_frames={len(failed)} first={failed[0]}", flush=True)
        return 1
    print(f"RENDER-COMPLETE frames={len(frames)} receipt={receipt_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
