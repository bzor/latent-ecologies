import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from houdini_ai import review_packet as rp

try:
    FFMPEG = rp._discover_ffmpeg()
except FileNotFoundError:
    FFMPEG = None


def write_still(path: Path, color: tuple[int, int, int], size: tuple[int, int] = (320, 180)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)
    return path


def write_video(path: Path, color: str, frames: int = 12) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(FFMPEG),
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s=320x180:r=12:d={frames / 12}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
    )
    return path


def video_size(video: Path) -> tuple[int, int]:
    with tempfile.TemporaryDirectory() as raw:
        frame = Path(raw) / "probe.png"
        subprocess.run(
            [str(FFMPEG), "-y", "-loglevel", "error", "-i", str(video), "-frames:v", "1", str(frame)],
            check=True,
        )
        with Image.open(frame) as image:
            return image.size


class ResolveCandidateTests(unittest.TestCase):
    def test_directory_prefers_motion_video_and_contact_sheet(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            round_dir = Path(raw) / "01_round"
            write_still(round_dir / "contact-sheet.png", (40, 40, 40))
            write_still(round_dir / "stills" / "late.png", (50, 50, 50))
            write_still(round_dir / "frames" / "frame-0001.png", (10, 10, 10))
            (round_dir / "aux.mp4").parent.mkdir(parents=True, exist_ok=True)
            (round_dir / "aux.mp4").write_bytes(b"stub")
            (round_dir / "motion-timelapse.mp4").write_bytes(b"stub")
            candidate = rp.resolve_candidate("A", "round-one", round_dir)
            self.assertEqual(candidate.video.name, "motion-timelapse.mp4")
            self.assertEqual(candidate.still.name, "late.png")

    def test_directory_falls_back_to_last_frame(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            round_dir = Path(raw) / "round"
            write_still(round_dir / "frames" / "frame-0001.png", (10, 10, 10))
            write_still(round_dir / "frames" / "frame-0002.png", (20, 20, 20))
            candidate = rp.resolve_candidate("A", "frames-only", round_dir)
            self.assertIsNone(candidate.video)
            self.assertEqual(candidate.still.name, "frame-0002.png")

    def test_empty_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaises(FileNotFoundError):
                rp.resolve_candidate("A", "empty", Path(raw))

    def test_parse_candidates_assigns_letters_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            first = write_still(Path(raw) / "first.png", (1, 1, 1))
            second = write_still(Path(raw) / "second.png", (2, 2, 2))
            candidates = rp.parse_candidates([f"one={first}", f"two={second}"])
            self.assertEqual([candidate.letter for candidate in candidates], ["A", "B"])

    def test_parse_candidates_rejects_malformed_spec(self) -> None:
        with self.assertRaises(ValueError):
            rp.parse_candidates(["missing-path"])


class StillPacketTests(unittest.TestCase):
    def test_packet_from_stills_needs_no_ffmpeg(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            candidates = [
                rp.resolve_candidate("A", "calm", write_still(root / "calm.png", (30, 60, 90))),
                rp.resolve_candidate("B", "frenetic", write_still(root / "frenetic.png", (90, 60, 30))),
            ]
            outputs = rp.build_packet(
                root / "packet",
                candidates,
                title="Test round",
                question="Which regime should continue?",
            )
            self.assertNotIn("comparison_video", outputs)
            with Image.open(outputs["contact_sheet"]) as sheet:
                self.assertEqual(sheet.width, rp.CELL_SIZE[0] * 2)
            caption = outputs["caption"].read_text(encoding="utf-8")
            self.assertIn("**A** — calm", caption)
            self.assertIn("Reply with a letter (A–B)", caption)
            receipt = json.loads(outputs["receipt"].read_text(encoding="utf-8"))
            self.assertEqual(len(receipt["candidates"]), 2)
            self.assertIsNone(receipt["candidates"][0]["video"])


@unittest.skipUnless(FFMPEG, "FFmpeg is not available")
class VideoPacketTests(unittest.TestCase):
    def test_packet_from_videos_builds_labelled_grid(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            candidates = [
                rp.resolve_candidate("A", "control", write_video(root / "control.mp4", "gray")),
                rp.resolve_candidate("B", "split-core", write_video(root / "split.mp4", "darkred")),
                rp.resolve_candidate("C", "orbital", write_video(root / "orbital.mp4", "navy")),
            ]
            outputs = rp.build_packet(
                root / "packet",
                candidates,
                title="C2 compact options",
                question="Which compact option advances?",
            )
            self.assertTrue(outputs["comparison_video"].stat().st_size > 0)
            width, height = video_size(outputs["comparison_video"])
            self.assertEqual(width, rp.CELL_SIZE[0] * 3)
            self.assertEqual(height, rp.CELL_SIZE[1] + rp.LABEL_BAR_HEIGHT)
            receipt = json.loads(outputs["receipt"].read_text(encoding="utf-8"))
            self.assertIn("comparison_video", receipt["artifacts"])

    def test_four_candidates_stack_two_by_two(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            colors = ["gray", "darkred", "navy", "darkgreen"]
            candidates = [
                rp.resolve_candidate(letter, f"option-{letter.lower()}", write_video(root / f"{letter}.mp4", color))
                for letter, color in zip("ABCD", colors)
            ]
            outputs = rp.build_packet(root / "packet", candidates, title="Grid", question="Pick one.")
            width, height = video_size(outputs["comparison_video"])
            self.assertEqual(width, rp.CELL_SIZE[0] * 2)
            self.assertEqual(height, (rp.CELL_SIZE[1] + rp.LABEL_BAR_HEIGHT) * 2)


if __name__ == "__main__":
    unittest.main()
