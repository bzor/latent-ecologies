"""Add editable semantic palette primvars to existing Scar Tissue field caches."""
from __future__ import annotations

import argparse
from pathlib import Path

import hou


def update(cache_dir: Path, derived_dir: Path) -> None:
    for frame in range(1, 1261):
        source = hou.Geometry(); source.loadFromFile(str(cache_dir / f"vex-state.{frame:04d}.bgeo.sc"))
        field_source = source.points()[256:]
        derived = hou.Geometry(); path = derived_dir / f"field.{frame:04d}.bgeo.sc"; derived.loadFromFile(str(path))
        if derived.findPointAttrib("state_index") is None:
            derived.addAttrib(hou.attribType.Point, "state_index", 0.0)
        if derived.findPointAttrib("state_strength") is None:
            derived.addAttrib(hou.attribType.Point, "state_strength", 0.0)
        for source_point, target in zip(field_source, derived.points()):
            state = int(source_point.attribValue("scar_state"))
            idle = int(source_point.attribValue("scar_idle"))
            recency = 1.0 - max(0.0, min(1.0, idle / 96.0))
            strength = 0.72 + 0.28 * recency if state == 0 else 0.88 + 0.12 * recency
            target.setAttribValue("state_index", state * 0.5)
            target.setAttribValue("state_strength", strength)
        derived.saveToFile(str(path))
    print(derived_dir.resolve())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cache", type=Path)
    parser.add_argument("derived", type=Path)
    args = parser.parse_args()
    update(args.cache.resolve(), args.derived.resolve())


if __name__ == "__main__": main()
