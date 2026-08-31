from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "work/studio/chromatic/scar-tissue-direction-v1"
ITEMS = (
    ("MINERAL WOUND", ROOT / "work/studio/chromatic/scar-tissue-mineral-wound-v1/frames/frame-0150.png"),
    ("BIOLUMINAL DEPTH", ROOT / "work/studio/chromatic/scar-tissue-bioluminal-depth-v1/frames/frame-0150.png"),
    ("ORCHID SIGNAL", ROOT / "work/studio/chromatic/scar-tissue-orchid-signal-v1/frames/frame-0150.png"),
)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    images = [Image.open(path).convert("RGB") for _, path in ITEMS]
    width, height = images[0].size
    header = 46
    sheet = Image.new("RGB", (width * len(images), height + header), (12, 12, 14))
    draw = ImageDraw.Draw(sheet)
    for index, ((label, _), image) in enumerate(zip(ITEMS, images)):
        sheet.paste(image, (index * width, header))
        draw.text((index * width + 16, 15), label, fill=(235, 235, 232))
        if index:
            draw.line((index * width, 0, index * width, height + header), fill=(70, 70, 74), width=2)
    output = OUTPUT / "comparison.png"
    sheet.save(output, optimize=True)
    receipt = {
        "schema_version": 1,
        "track": "chromatic",
        "source_behavior_component_id": "component-behavior-b3bcc837c3e2",
        "source_look_component_id": "component-look-6013004ba32c",
        "frame": 150,
        "variants": [label.lower().replace(" ", "-") for label, _ in ITEMS],
        "geometry_changed": False,
        "camera_changed": False,
        "lighting_changed": False,
        "artifact": {
            "path": output.name,
            "bytes": output.stat().st_size,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        },
    }
    (OUTPUT / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
