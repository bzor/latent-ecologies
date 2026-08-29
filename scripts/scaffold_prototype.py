"""Scaffold a browser behavior prototype into a Study vault.

Creates studies/<study>/01_behavior/01_work/prototypes/<proto-id>/ with an
index.html wired to the shared behavior-playground harness, a kernel stub, and
an empty presets/ directory. See docs/THREEJS_PROTOTYPE_ROUTE.md.

    python scripts/scaffold_prototype.py study_003_nonlocal-affinity-dance swirl-fields
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1]

KERNEL_STUB = '''// Behavior prototype kernel: {proto_id}
// Contract: behavior-playground/CLAUDE.md. Deterministic only — all randomness
// from BP.mulberry32(params.seed); no Date.now(), no Math.random().
(function (root) {{
  "use strict";
  root.BP.registerKernel({{
    id: "{proto_id}",
    title: "{title}",
    mechanism: "{proto_id}-v1",
    mechanismVersion: 1,
    studyId: "{study_id}",
    initialization: "describe-the-initialization-convention",
    ordering: "describe-the-update-ordering",
    view: "{view}",
    defaults: {{
      seed: 122095,
      count: 500,
      point_size: 2, // identity: false below
    }},
    schema: [
      {{ key: "count", label: "count", type: "int", min: 2, max: 10000, step: 1 }},
      {{ key: "point_size", label: "point size", type: "number", min: 0.5, max: 12, step: 0.5, identity: false }},
    ],
    init(params) {{
      const rng = root.BP.mulberry32(params.seed);
      const positions = new Float64Array(params.count * 2);
      for (let index = 0; index < positions.length; index += 1) positions[index] = rng() * 2 - 1;
      return {{ positions, rng, count: params.count }};
    }},
    step(sim, params) {{
      // advance one simulation step, mutating sim
    }},
    draw(view, sim, params) {{
      const ctx = view.ctx;
      ctx.fillStyle = "#000";
      ctx.fillRect(0, 0, view.size, view.size);
      ctx.fillStyle = "#e8ede9";
      const scale = view.size / 2.5;
      const center = view.size / 2;
      for (let point = 0; point < sim.count; point += 1) {{
        ctx.fillRect(
          center + sim.positions[point * 2] * scale - params.point_size / 2,
          center + sim.positions[point * 2 + 1] * scale - params.point_size / 2,
          params.point_size,
          params.point_size
        );
      }}
    }},
  }});
}})(typeof globalThis !== "undefined" ? globalThis : this);
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study", help="study directory name under studies/, e.g. study_003_nonlocal-affinity-dance")
    parser.add_argument("proto_id", help="kebab-case prototype id")
    parser.add_argument("--title", help="display title (defaults to the prototype id)")
    parser.add_argument("--three", action="store_true", help="use the three.js view instead of canvas2d")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args()

    root = args.root.resolve()
    playground_web = root / "behavior-playground" / "web"
    study_dir = root / "studies" / args.study
    if not study_dir.is_dir():
        raise SystemExit(f"study directory not found: {study_dir}")
    proto_dir = study_dir / "01_behavior" / "01_work" / "prototypes" / args.proto_id
    if proto_dir.exists():
        raise SystemExit(f"prototype already exists: {proto_dir}")

    (proto_dir / "presets").mkdir(parents=True)
    relative_web = Path(
        *([".."] * len(proto_dir.relative_to(root).parts)),
        *playground_web.relative_to(root).parts,
    ).as_posix()
    template = (playground_web / "template.html").read_text(encoding="utf-8")
    html = template.replace("__PLAYGROUND_WEB__", relative_web)
    html = html.replace("<title>Behavior prototype</title>", f"<title>{args.proto_id} — behavior prototype</title>")
    if args.three:
        html = html.replace(
            f'<!-- <script src="{relative_web}/vendor/three.min.js"></script> -->',
            f'<script src="{relative_web}/vendor/three.min.js"></script>',
        )
    (proto_dir / "index.html").write_text(html, encoding="utf-8")
    study_id = args.study.replace("study_", "study-", 1).replace("_", "-", 1)
    (proto_dir / "kernel.js").write_text(
        KERNEL_STUB.format(
            proto_id=args.proto_id,
            title=args.title or args.proto_id,
            study_id=study_id,
            view="three" if args.three else "canvas2d",
        ),
        encoding="utf-8",
    )
    print(proto_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
