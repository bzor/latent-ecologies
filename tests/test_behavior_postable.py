import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from houdini_ai import behavior_postable as bp

try:
    FFMPEG = bp._discover_ffmpeg()
except FileNotFoundError:
    FFMPEG = None


def write_frames(directory: Path, count: int = 12, color: tuple[int, int, int] = (236, 0, 140)) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for index in range(count):
        Image.new("RGB", (720, 720), color).save(directory / f"frame-{index:04d}.png")
    return directory


def first_frame(video: Path) -> Image.Image:
    with tempfile.TemporaryDirectory() as raw:
        frame = Path(raw) / "probe.png"
        subprocess.run(
            [str(FFMPEG), "-y", "-loglevel", "error", "-i", str(video), "-frames:v", "1", str(frame)],
            check=True,
        )
        with Image.open(frame) as image:
            return image.convert("RGB").copy()


class FramePatternTests(unittest.TestCase):
    def test_resolves_pattern_and_start_number(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            for index in (3, 4, 5):
                Image.new("RGB", (8, 8)).save(directory / f"frame-{index:04d}.png")
            pattern, start, count = bp._frame_pattern(directory)
            self.assertTrue(pattern.endswith("frame-%04d.png"))
            self.assertEqual(start, 3)
            self.assertEqual(count, 3)

    def test_rejects_unnumbered_frames(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            Image.new("RGB", (8, 8)).save(directory / "frame.png")
            with self.assertRaises(ValueError):
                bp._frame_pattern(directory)

    def test_rejects_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaises(FileNotFoundError):
                bp._frame_pattern(Path(raw))


@unittest.skipUnless(FFMPEG, "FFmpeg is not available")
class ConformTests(unittest.TestCase):
    def test_frames_become_postable_portrait(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            frames = write_frames(root / "frames", count=12)
            receipt = bp.conform_postable(frames, root / "postable.mp4", source_fps=12)
            image = first_frame(root / "postable.mp4")
            self.assertEqual(image.size, tuple(bp.POSTABLE_SIZE))
            self.assertAlmostEqual(receipt["duration_seconds"], 1.0)
            self.assertTrue(receipt["x_duration_ok"])
            self.assertTrue((root / "postable.receipt.json").is_file())
            # 720x720 letterboxed into 1080x1350: the pad band must be near-black.
            self.assertLess(sum(image.getpixel((540, 10))), 30)

    def test_monochrome_desaturates_legacy_color(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            frames = write_frames(root / "frames", count=6, color=(236, 0, 140))
            bp.conform_postable(frames, root / "mono.mp4", source_fps=12, monochrome=True)
            image = first_frame(root / "mono.mp4")
            red, green, blue = image.getpixel((540, 675))
            self.assertLess(max(red, green, blue) - min(red, green, blue), 8)

    def test_video_source_keeps_its_timing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source.mp4"
            subprocess.run(
                [
                    str(FFMPEG),
                    "-y",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=white:s=320x180:r=12:d=1",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(source),
                ],
                check=True,
            )
            receipt = bp.conform_postable(source, root / "postable.mp4")
            self.assertIsNone(receipt["duration_seconds"])
            self.assertEqual(first_frame(root / "postable.mp4").size, tuple(bp.POSTABLE_SIZE))
            with self.assertRaisesRegex(ValueError, "frame sequences"):
                bp.conform_postable(source, root / "again.mp4", source_fps=24)


if __name__ == "__main__":
    unittest.main()
