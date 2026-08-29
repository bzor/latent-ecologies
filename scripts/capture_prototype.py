"""Deterministically capture a behavior prototype frame with headless Chrome.

Used for posting preset comparisons to the Study thread. The harness applies
the preset from the URL, steps synchronously to the requested frame, and pauses,
so the capture is pixel-identical to the same preset and frame in the live page.

    python scripts/capture_prototype.py behavior-playground/reference/affinity/index.html \
        --preset path/to/candidate.preset.json --frame 240 --out capture.png
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("page", type=Path, help="prototype index.html")
    parser.add_argument("--preset", type=Path, help="prototype-preset JSON to apply (defaults to kernel defaults)")
    parser.add_argument("--frame", type=int, default=240, help="simulation step to capture")
    parser.add_argument("--size", type=int, default=900, help="square canvas size in pixels")
    parser.add_argument("--out", type=Path, required=True, help="output PNG path")
    parser.add_argument("--timeout", type=int, default=120, help="seconds before the capture is abandoned")
    args = parser.parse_args()

    page = args.page.resolve()
    if not page.is_file():
        raise SystemExit(f"prototype page not found: {page}")
    query = [f"frame={args.frame}", f"size={args.size}", "autoplay=0"]
    if args.preset:
        preset = json.loads(args.preset.read_text(encoding="utf-8"))
        encoded = base64.urlsafe_b64encode(json.dumps(preset).encode("utf-8")).decode("ascii")
        query.append(f"p={encoded}")
    url = page.as_uri() + "?" + "&".join(query)

    chrome = os.environ.get("CHROME_BIN", DEFAULT_CHROME)
    args.out.resolve().parent.mkdir(parents=True, exist_ok=True)
    command = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--use-angle=swiftshader",
        "--allow-file-access-from-files",
        "--hide-scrollbars",
        "--virtual-time-budget=8000",
        f"--window-size={args.size + 320},{args.size + 60}",
        f"--screenshot={args.out.resolve()}",
        url,
    ]
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=args.timeout)
    if not args.out.is_file() or args.out.stat().st_size == 0:
        raise SystemExit("capture produced no image")
    print(args.out.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
