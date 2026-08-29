import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from houdini_ai.studio_schema import validate_record


ROOT = Path(__file__).resolve().parents[1]
PLAYGROUND = ROOT / "behavior-playground"
WEB = PLAYGROUND / "web"
KERNEL = PLAYGROUND / "reference" / "affinity" / "kernel.js"
CORE = ROOT / "website" / "affinity-core.js"


def run_node(script: str) -> dict:
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


class Mulberry32Reference:
    """Independent Python mulberry32-v1, mirroring houdini/build_nonlocal_affinity_hda.py."""

    def __init__(self, value: int) -> None:
        self.state = value & 0xFFFFFFFF

    @staticmethod
    def imul(left: int, right: int) -> int:
        return ((left & 0xFFFFFFFF) * (right & 0xFFFFFFFF)) & 0xFFFFFFFF

    def random(self) -> float:
        self.state = (self.state + 0x6D2B79F5) & 0xFFFFFFFF
        value = self.state
        value = self.imul(value ^ (value >> 15), value | 1)
        value ^= (value + self.imul(value ^ (value >> 7), value | 61)) & 0xFFFFFFFF
        value &= 0xFFFFFFFF
        return ((value ^ (value >> 14)) & 0xFFFFFFFF) / 4294967296.0


class BehaviorPlaygroundTests(unittest.TestCase):
    def test_fluid_view_dimensions_fill_available_stage_and_preserve_forced_capture_size(self) -> None:
        value = run_node(
            f"""
            const BP = require({json.dumps((WEB / "harness.js").as_posix())});
            console.log(JSON.stringify({{
              fluid: BP.computeViewDimensions(1234, 678, null),
              forced: BP.computeViewDimensions(1234, 678, 900),
              clamped: BP.computeViewDimensions(40, 80, null),
            }}));
            """
        )
        self.assertEqual(value["fluid"], {"width": 1234, "height": 678})
        self.assertEqual(value["forced"], {"width": 900, "height": 900})
        self.assertEqual(value["clamped"], {"width": 200, "height": 200})

    def test_rng_matches_affinity_core_and_python_reference(self) -> None:
        value = run_node(
            f"""
            const BP = require({json.dumps((WEB / "rng.js").as_posix())});
            const core = require({json.dumps(CORE.as_posix())});
            const mine = BP.mulberry32(122095);
            const theirs = core.createRng(122095);
            const bp = [], legacy = [];
            for (let i = 0; i < 16; i++) {{ bp.push(mine()); legacy.push(theirs()); }}
            console.log(JSON.stringify({{bp, legacy, id: BP.RNG_ID}}));
            """
        )
        self.assertEqual(value["id"], "mulberry32-v1")
        self.assertEqual(value["bp"], value["legacy"])
        python_rng = Mulberry32Reference(122095)
        for expected in value["bp"]:
            self.assertEqual(python_rng.random(), expected)

    def test_reference_kernel_matches_affinity_core_exactly(self) -> None:
        value = run_node(
            f"""
            const core = require({json.dumps(CORE.as_posix())});
            const kernel = require({json.dumps(KERNEL.as_posix())});
            const BP = require({json.dumps((WEB / "harness.js").as_posix())});
            const params = {{...kernel.defaults, agent_count: 64, rewire_probability: 0.2, seed: 40771}};
            const sim = kernel.init(params);
            const direct = core.createSimulation({{
              agent_count: 64, seed: 40771, contraction: params.contraction,
              attraction: params.attraction, repulsion: params.repulsion,
              softening: params.softening, rewire_probability: 0.2,
              rewires_per_event: params.rewires_per_event,
            }});
            for (let i = 0; i < 48; i++) {{ kernel.step(sim, params); core.stepSimulation(direct); }}
            const preset = BP.presetFromKernel(kernel, params, 2, {{title: "Parity check", note: "node parity test"}});
            console.log(JSON.stringify({{
              kernelPositions: Array.from(sim.positions),
              directPositions: Array.from(direct.positions),
              kernelRewires: sim.rewire_count,
              directRewires: direct.rewire_count,
              preset,
            }}));
            """
        )
        self.assertEqual(value["kernelPositions"], value["directPositions"])
        self.assertEqual(value["kernelRewires"], value["directRewires"])
        self.assertGreater(value["kernelRewires"], 0)

        preset = value["preset"]
        self.assertEqual(validate_record("prototype-preset", preset), [])
        self.assertEqual(preset["mechanism"], "nonlocal-affinity-v1")
        self.assertEqual(preset["identity"]["rng"], "mulberry32-v1")
        self.assertEqual(preset["seed"], 40771)
        self.assertEqual(preset["parameters"]["rewire_probability"], 0.2)
        self.assertIn("point_size", preset["display"])
        self.assertNotIn("point_size", preset["parameters"])
        self.assertNotIn("seed", preset["parameters"])
        self.assertFalse(preset["production_hint"]["execution_authorized"])

        armed = json.loads(json.dumps(preset))
        armed["production_hint"]["execution_authorized"] = True
        self.assertTrue(any("execution_authorized" in error for error in validate_record("prototype-preset", armed)))
        unknown = json.loads(json.dumps(preset))
        unknown["shell"] = "rm -rf"
        self.assertTrue(validate_record("prototype-preset", unknown))

    def test_static_determinism_and_wiring_contract(self) -> None:
        for path in (WEB / "harness.js", WEB / "rng.js", KERNEL):
            code = "\n".join(
                line for line in path.read_text(encoding="utf-8").splitlines()
                if not line.lstrip().startswith("//")
            )
            self.assertNotIn("Math.random(", code, path.name)
            self.assertNotIn("Date.now(", code, path.name)
        page = (PLAYGROUND / "reference" / "affinity" / "index.html").read_text(encoding="utf-8")
        self.assertLess(page.index("rng.js"), page.index("harness.js"))
        self.assertLess(page.index("harness.js"), page.index("affinity-core.js"))
        self.assertLess(page.index("affinity-core.js"), page.index("kernel.js"))
        template = (WEB / "template.html").read_text(encoding="utf-8")
        self.assertGreaterEqual(template.count("__PLAYGROUND_WEB__"), 3)
        self.assertIn('<!-- <script src="__PLAYGROUND_WEB__/vendor/three.min.js"></script> -->', template)
        three = WEB / "vendor" / "three.min.js"
        self.assertGreater(three.stat().st_size, 100_000)
        self.assertNotEqual(three.read_bytes()[:1], b"<")

    def test_scaffold_creates_wired_prototype(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "behavior-playground" / "web").mkdir(parents=True)
            (root / "behavior-playground" / "web" / "template.html").write_text(
                (WEB / "template.html").read_text(encoding="utf-8"), encoding="utf-8"
            )
            (root / "studies" / "study_777_test-thing").mkdir(parents=True)
            command = [
                sys.executable, str(ROOT / "scripts" / "scaffold_prototype.py"),
                "study_777_test-thing", "test-proto", "--root", str(root),
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)

            proto = root / "studies" / "study_777_test-thing" / "01_behavior" / "01_work" / "prototypes" / "test-proto"
            html = (proto / "index.html").read_text(encoding="utf-8")
            kernel = (proto / "kernel.js").read_text(encoding="utf-8")
            self.assertTrue((proto / "presets").is_dir())
            self.assertIn('src="../../../../../../behavior-playground/web/rng.js"', html)
            self.assertIn('src="./kernel.js"', html)
            self.assertNotIn("__PLAYGROUND_WEB__", html)
            self.assertIn("<!-- <script", html)
            self.assertIn('mechanism: "test-proto-v1"', kernel)
            self.assertIn('studyId: "study-777-test-thing"', kernel)
            self.assertIn("BP.mulberry32(params.seed)", kernel)

            rerun = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(rerun.returncode, 0)

            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "scaffold_prototype.py"),
                 "study_777_test-thing", "solid-proto", "--three", "--root", str(root)],
                check=True, capture_output=True, text=True,
            )
            solid = root / "studies" / "study_777_test-thing" / "01_behavior" / "01_work" / "prototypes" / "solid-proto"
            three_html = (solid / "index.html").read_text(encoding="utf-8")
            self.assertIn('<script src="../../../../../../behavior-playground/web/vendor/three.min.js"></script>', three_html)
            self.assertIn('view: "three"', (solid / "kernel.js").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
