from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "work/studio/cinematography/scar-tissue-camera-directions-v3"
ITEMS = (
    ("A — TIGHT ISOMETRIC", ROOT / "work/studio/cinematography/scar-tissue-a-tight-isometric-v1/frames/frame-0150.png"),
    ("B — LOW FIELD", ROOT / "work/studio/cinematography/scar-tissue-b-low-grazing-v8/frames/frame-0150.png"),
    ("C — INTIMATE TRACKING", ROOT / "work/studio/cinematography/scar-tissue-c-intimate-tracking-v2/frames/frame-0150.png"),
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
        "track": "cinematography",
        "source_behavior_component_id": "component-behavior-b3bcc837c3e2",
        "source_look_component_id": "component-look-6013004ba32c",
        "source_palette_component_id": "component-palette-a52433fdb147",
        "frame": 150,
        "variants": ["tight-isometric", "low-grazing", "intimate-tracking"],
        "geometry_changed": False,
        "palette_changed": False,
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
