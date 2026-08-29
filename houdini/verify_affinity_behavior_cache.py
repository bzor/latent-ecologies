"""Verify staged affinity Behavior caches in a fresh Hython process."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import hou


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(source_path: Path, *, sample_only: bool, output_path: Path | None = None) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    source = json.loads(source_path.resolve().read_text(encoding="utf-8"))
    receipt_path = root / source["extensions"]["studio/cache-receipt"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    paths = [root / path for path in source["cache_paths"]]
    frames = [int(path.name.split(".")[1]) for path in paths]
    if sample_only:
        indices = [0, len(paths) // 2, len(paths) - 1]
    else:
        indices = list(range(len(paths)))
    errors: list[str] = []
    checked_frames: list[int] = []
    point_counts: list[int] = []
    relationship_changes: list[dict[str, int]] = []
    previous_friends: tuple[int, ...] | None = None
    previous_enemies: tuple[int, ...] | None = None
    for index in indices:
        path = paths[index]
        frame = frames[index]
        record = receipt["cache_files"][index]
        record_errors: list[str] = []
        if not path.is_file():
            record_errors.append("missing cache")
            errors.extend(f"frame {frame}: {message}" for message in record_errors)
            continue
        if path.stat().st_size != record["bytes"] or sha256(path) != record["sha256"]:
            record_errors.append("byte count or sha256 mismatch")
        geometry = hou.Geometry()
        try:
            geometry.loadFromFile(str(path.resolve()).replace("\\", "/"))
        except hou.Error as error:
            record_errors.append(f"Houdini load failed: {error}")
            errors.extend(f"frame {frame}: {message}" for message in record_errors)
            continue
        count = len(geometry.points())
        point_counts.append(count)
        checked_frames.append(frame)
        names = sorted(attribute.name() for attribute in geometry.pointAttribs())
        if count != 100000:
            record_errors.append(f"point count {count} != 100000")
        if names != ["P", "enemy", "friend"]:
            record_errors.append(f"point attributes {names}")
        positions = geometry.pointFloatAttribValues("P")
        if len(positions) != count * 3 or any(not math.isfinite(value) for value in positions):
            record_errors.append("P is missing or non-finite")
        friends = tuple(geometry.pointIntAttribValues("friend"))
        enemies = tuple(geometry.pointIntAttribValues("enemy"))
        if len(friends) != count or len(enemies) != count:
            record_errors.append("relationship attribute size mismatch")
        elif any(value < 0 or value >= count for value in friends + enemies):
            record_errors.append("relationship index out of range")
        if not sample_only and previous_friends is not None and previous_enemies is not None:
            change = {
                "frame": frame,
                "friend_changes": sum(a != b for a, b in zip(previous_friends, friends)),
                "enemy_changes": sum(a != b for a, b in zip(previous_enemies, enemies)),
            }
            if change["friend_changes"] or change["enemy_changes"]:
                relationship_changes.append(change)
        previous_friends, previous_enemies = friends, enemies
        errors.extend(f"frame {frame}: {message}" for message in record_errors)
    report = {
        "schema_version": 1,
        "mode": "sample" if sample_only else "all",
        "source": source_path.resolve().as_posix(),
        "frame_range": [frames[0], frames[-1]],
        "source_frame_count": len(frames),
        "checked_frame_count": len(checked_frames),
        "checked_frames": checked_frames if sample_only else [checked_frames[0], checked_frames[-1]],
        "point_counts": point_counts if sample_only else sorted(set(point_counts)),
        "relationship_changes": relationship_changes,
        "last_relationship_change_frame": relationship_changes[-1]["frame"] if relationship_changes else None,
        "total_friend_changes": sum(item["friend_changes"] for item in relationship_changes),
        "total_enemy_changes": sum(item["enemy_changes"] for item in relationship_changes),
        "errors": errors,
    }
    if errors:
        raise RuntimeError(json.dumps(report, sort_keys=True))
    if output_path is not None:
        output_path.resolve().write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--sample-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    verify(args.source, sample_only=args.sample_only, output_path=args.output)


if __name__ == "__main__":
    main()
