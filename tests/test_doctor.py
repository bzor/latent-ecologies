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
            Tool("hgpuinfo", None, "not found", False),
        ]
        _, errors = inspect_workstation({})
        self.assertEqual(len(errors), 4)
        self.assertIn("set HOUDINI_BIN", errors[0])
        self.assertIn("set FFMPEG_BIN", errors[-1])

    @patch("houdini_ai.doctor.run_probe", return_value=(True, "version output"))
    @patch("houdini_ai.doctor.discover_tools")
    def test_available_tools_pass(self, discover, _probe) -> None:
        discover.return_value = [Tool(name, Path(name), "test") for name in ("hython", "hbatch", "ffmpeg", "ffprobe", "hgpuinfo")]
        lines, errors = inspect_workstation({})
        self.assertEqual(errors, [])
        self.assertTrue(any("hython probe: OK" in line for line in lines))
        self.assertEqual(_probe.call_count, 5)

    @patch("houdini_ai.doctor.discover_tools")
    @patch("houdini_ai.doctor.run_probe")
    def test_each_failed_probe_is_actionable(self, run, discover) -> None:
        discover.return_value = [Tool(name, Path(name), "test") for name in ("hython", "hbatch", "ffmpeg", "ffprobe", "hgpuinfo")]
        run.side_effect = [
            (False, "license error"),
            (False, "timeout"),
            (False, "exit 1"),
            (False, "timeout"),
            (False, "timeout"),
        ]
        _, errors = inspect_workstation({})
        self.assertEqual(len(errors), 4)
        self.assertTrue(any("hython" in error for error in errors))
        self.assertTrue(any("hbatch" in error for error in errors))
        self.assertTrue(any("ffmpeg" in error for error in errors))
        self.assertTrue(any("ffprobe" in error for error in errors))

    @patch("houdini_ai.doctor.subprocess.run", side_effect=__import__("subprocess").TimeoutExpired("tool", 1))
    def test_probe_timeout_is_a_failure(self, _run) -> None:
        from houdini_ai.doctor import run_probe

        ok, output = run_probe(("tool",), timeout=1)
        self.assertFalse(ok)
        self.assertIn("timed out", output)

    @patch(
        "houdini_ai.doctor.run_probe",
        side_effect=[
            (True, "karma_node_types: karma"),
            (True, "hbatch test"),
            (True, "OpenCL Device Example CPU\nOpenCL Type CPU\nGlobal Memory 32768 MB\nOpenCL Device Example GPU\nOpenCL Type GPU\nGlobal Memory 16384 MB\nOpenCL Device Example GPU\nOpenCL Type GPU\nGlobal Memory 16384 MB"),
            (True, "ffmpeg version test"),
            (True, "ffprobe version test"),
        ],
    )
    @patch("houdini_ai.doctor.discover_tools")
    def test_render_devices_are_summarized(self, discover, _probe) -> None:
        discover.return_value = [Tool(name, Path(name), "test") for name in ("hython", "hbatch", "ffmpeg", "ffprobe", "hgpuinfo")]
        lines, errors = inspect_workstation({})
        self.assertEqual(errors, [])
        self.assertIn("  CPU: Example CPU (32768 MB)", lines)
        self.assertIn("  GPU: Example GPU (16384 MB)", lines)
        self.assertEqual(lines.count("  GPU: Example GPU (16384 MB)"), 1)

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
