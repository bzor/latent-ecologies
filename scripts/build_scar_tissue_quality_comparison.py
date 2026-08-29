from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "work/studio/cinematography/scar-tissue-quality-abc-v1"
SOURCES = [
    ("A", "HOLISTIC ESTABLISHING", ROOT / "work/studio/cinematography/quality-scar-tissue-a-tight-isometric-v1/frames/frame-0135.png"),
    ("B", "LOW ENVIRONMENTAL", ROOT / "work/studio/cinematography/quality-scar-tissue-b-low-field-v1/frames/frame-0135.png"),
    ("C", "INTIMATE LOCAL", ROOT / "work/studio/cinematography/quality-scar-tissue-c-intimate-v1/frames/frame-0135.png"),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    images = [Image.open(path).convert("RGB") for _, _, path in SOURCES]
    width, height = images[0].size
    label_height = 46
    canvas = Image.new("RGB", (width * 3, height + label_height), (9, 12, 18))
    draw = ImageDraw.Draw(canvas)
    records = []
    for index, ((label, title, path), image) in enumerate(zip(SOURCES, images)):
        x = index * width
        canvas.paste(image, (x, label_height))
        draw.text((x + 14, 10), f"{label}  {title}", fill=(235, 244, 255))
        records.append({"label": label, "title": title, "path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)})
    target = OUTPUT / "comparison.png"
    canvas.save(target)
    receipt = {"frame": 135, "dimensions": list(canvas.size), "samples_per_pixel": 16, "sources": records,
               "comparison": {"path": target.name, "bytes": target.stat().st_size, "sha256": sha(target)}}
    (OUTPUT / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(target.resolve())


if __name__ == "__main__":
    main()
