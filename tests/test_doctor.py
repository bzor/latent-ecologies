import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from houdini_ai.doctor import Tool, discover_tools, inspect_workstation


class DoctorTests(unittest.TestCase):
    @patch("houdini_ai.doctor.discover_tools")
    def test_missing_required_tools_are_actionable(self, discover) -> None:
        discover.return_value = [
            Tool("hython", None, "not found"),
            Tool("hbatch", None, "not found"),
            Tool("ffmpeg", None, "not found"),
            Tool("ffprobe", None, "not found"),
        ]
        _, errors = inspect_workstation({})
        self.assertEqual(len(errors), 4)
        self.assertIn("set HOUDINI_BIN", errors[0])
        self.assertIn("set FFMPEG_BIN", errors[-1])

    @patch("houdini_ai.doctor.run_probe", return_value=(True, "version output"))
    @patch("houdini_ai.doctor.discover_tools")
    def test_available_tools_pass(self, discover, _probe) -> None:
        discover.return_value = [Tool(name, Path(name), "test") for name in ("hython", "hbatch", "ffmpeg", "ffprobe")]
        lines, errors = inspect_workstation({})
        self.assertEqual(errors, [])
        self.assertTrue(any("houdini probe: OK" in line for line in lines))

    @unittest.skipUnless(__import__("os").name == "nt", "Windows executable names")
    def test_ffmpeg_executable_resolves_ffprobe_sibling(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ffmpeg = root / "ffmpeg.exe"
            ffprobe = root / "ffprobe.exe"
            ffmpeg.touch()
            ffprobe.touch()
            tools = {tool.name: tool for tool in discover_tools({"FFMPEG_BIN": str(ffmpeg), "PATH": ""})}
            self.assertEqual(tools["ffmpeg"].path, ffmpeg.resolve())
            self.assertEqual(tools["ffprobe"].path, ffprobe.resolve())


if __name__ == "__main__":
    unittest.main()
