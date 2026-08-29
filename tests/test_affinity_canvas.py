import json
import subprocess
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from houdini_ai.affinity_presets import affinity_config_from_preset
from houdini_ai.review_studio import make_handler
from houdini_ai.studio_api import StudioAPI


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "website" / "affinity-core.js"


def run_node(script: str) -> dict:
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


class AffinityCanvasCoreTests(unittest.TestCase):
    def test_instrument_shell_exposes_behavior_controls_and_portable_saving(self) -> None:
        studio_html = (ROOT / "website" / "index.html").read_text(encoding="utf-8")
        html = (ROOT / "website" / "affinity.html").read_text(encoding="utf-8")
        script = (ROOT / "website" / "affinity.js").read_text(encoding="utf-8")
        styles = (ROOT / "website" / "affinity.css").read_text(encoding="utf-8")

        self.assertIn('id="affinityCanvas"', html)
        for control in (
            "agentCount", "contraction", "attraction", "repulsion", "softening", "rewireProbability",
            "rewiresPerEvent", "seed", "stepsPerFrame", "pointSize", "trailAlpha", "viewportScale",
        ):
            self.assertIn(f'id="{control}"', html)
        self.assertIn("BEHAVIOR PARAMETERS", html)
        self.assertIn("DISPLAY ONLY", html)
        self.assertIn('id="savePreset"', html)
        self.assertIn('id="presetTitle" maxlength="200" value="Affinity candidate" required', html)
        self.assertIn('id="downloadPreset"', html)
        self.assertIn('id="savedPresets"', html)
        self.assertLess(html.index('/affinity-core.js'), html.index('/affinity.js'))
        self.assertIn("requestAnimationFrame", script)
        self.assertIn("stepSimulation", script)
        self.assertIn("makePreset", script)
        self.assertIn("/api/studio/affinity-presets", script)
        self.assertIn("X-Studio-Mutation-Token", script)
        self.assertIn("execution_authorized", script)
        self.assertIn("ResizeObserver", script)
        self.assertIn("affinity-stage", styles)
        self.assertIn("control-grid", styles)
        self.assertIn('class="instrument-link" href="/affinity.html"', studio_html)

    def test_core_matches_source_equation_and_is_deterministic(self) -> None:
        value = run_node(
            f"""
            const core = require({json.dumps(CORE.as_posix())});
            const parameters = {{contraction:0.995, attraction:0.02, repulsion:0.01, softening:0.01}};
            const state = {{
              positions:new Float64Array([1,0, 3,0, 1,4]),
              friends:new Uint32Array([1,1,2]),
              enemies:new Uint32Array([2,1,2]),
              count:3,
              dimensions:2
            }};
            const stepped = core.stepState(state, parameters, null);
            const rewired = core.stepState({{
              positions:new Float64Array([0,10,20]),
              friends:new Uint32Array([0,0,1]),
              enemies:new Uint32Array([0,0,1]),
              count:3,
              dimensions:1
            }}, parameters, {{point:0, friend:1, enemy:2}});
            const settings = {{...core.DEFAULT_SETTINGS, agent_count:32, seed:122095, rewire_probability:0.17}};
            const first = core.createSimulation(settings);
            const second = core.createSimulation(settings);
            const changed = core.createSimulation({{...settings, seed:122096}});
            for(let i=0;i<20;i++){{core.stepSimulation(first); core.stepSimulation(second); core.stepSimulation(changed);}}
            const preset = core.makePreset(settings, core.DEFAULT_DISPLAY, {{title:'Energetic turnover', note:'candidate only'}});
            let blankTitleRejected = false;
            try {{ core.makePreset(settings, core.DEFAULT_DISPLAY, {{title:'   '}}); }} catch(error) {{ blankTitleRejected = true; }}
            console.log(JSON.stringify({{
              source:Array.from(stepped.positions),
              rewired:Array.from(rewired.positions),
              friends:Array.from(rewired.friends),
              enemies:Array.from(rewired.enemies),
              first:Array.from(first.positions.slice(0,12)),
              second:Array.from(second.positions.slice(0,12)),
              changed:Array.from(changed.positions.slice(0,12)),
              preset,
              blankTitleRejected
            }}));
            """
        )

        self.assertAlmostEqual(value["source"][0], 1.0149004975124378, places=12)
        self.assertAlmostEqual(value["source"][1], -0.009975062344139652, places=12)
        self.assertEqual(value["source"][2:4], [2.985, 0])
        self.assertEqual(value["source"][4:6], [0.995, 3.98])
        self.assertAlmostEqual(value["rewired"][0], 0.009985017481269357, places=12)
        self.assertAlmostEqual(value["rewired"][1], 9.94000999000999, places=12)
        self.assertEqual(value["friends"], [1, 0, 1])
        self.assertEqual(value["enemies"], [2, 0, 1])
        self.assertEqual(value["first"], value["second"])
        self.assertNotEqual(value["first"], value["changed"])
        self.assertEqual(value["preset"]["schema_version"], 1)
        self.assertEqual(value["preset"]["mechanism"], "nonlocal-affinity-v1")
        self.assertEqual(value["preset"]["project_id"], "study-003-nonlocal-affinity-dance")
        self.assertEqual(value["preset"]["dimensions"], 2)
        self.assertEqual(value["preset"]["parameters"]["attraction"], 0.02)
        self.assertEqual(value["preset"]["preview"]["agent_count"], 32)
        self.assertEqual(value["preset"]["production_hint"]["state"], "candidate")
        self.assertFalse(value["preset"]["production_hint"]["execution_authorized"])
        self.assertTrue(value["blankTitleRejected"])
        downloaded_config = affinity_config_from_preset(value["preset"], agent_count=20000, dimensions=3, steps=600)
        self.assertEqual(downloaded_config.agent_count, 20000)
        self.assertEqual(downloaded_config.dimensions, 3)
        self.assertEqual(downloaded_config.rewire_gate_exclusive_max, 171)

    def test_studio_saves_validated_private_inert_presets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            api = StudioAPI(Path(directory))
            value = {
                "schema_version": 1,
                "mechanism": "nonlocal-affinity-v1",
                "project_id": "study-003-nonlocal-affinity-dance",
                "title": "Higher relationship turnover",
                "note": "Candidate discovered in the Canvas instrument.",
                "dimensions": 2,
                "seed": 122095,
                "parameters": {
                    "contraction": 0.995,
                    "attraction": 0.02,
                    "repulsion": 0.01,
                    "softening": 0.01,
                },
                "rewiring": {
                    "probability_per_simulation_step": 0.25,
                    "rewires_per_event": 1,
                    "ordering": "before-synchronous-position-update",
                },
                "preview": {
                    "agent_count": 1000,
                    "steps_per_display_frame": 2,
                    "rng": "mulberry32-v1",
                    "initialization": "uniform-square-minus-one-to-one",
                },
                "display": {
                    "point_size": 1.5,
                    "trail_alpha": 0.16,
                    "viewport_scale": 1.25,
                    "show_links": False,
                },
                "production_hint": {
                    "state": "candidate",
                    "execution_authorized": False,
                    "integration_authority": "houdini-vex",
                },
            }

            record = api.save_affinity_preset(value)

            self.assertTrue(record["id"].startswith("affinity-preset-"))
            self.assertEqual(record["state"], "candidate")
            self.assertEqual(record["visibility"], "private")
            self.assertFalse(record["production_hint"]["execution_authorized"])
            self.assertIn("created_at", record)
            self.assertEqual(api.list_records("affinity-presets")["items"], [record])
            self.assertTrue(
                (Path(directory) / "work" / "studio" / "affinity-presets" / f'{record["id"]}.json').is_file()
            )
            value["production_hint"]["execution_authorized"] = True
            with self.assertRaisesRegex(ValueError, "execution_authorized"):
                api.save_affinity_preset(value)

            config = affinity_config_from_preset(record, agent_count=12000, dimensions=3, steps=480)
            self.assertEqual(config.agent_count, 12000)
            self.assertEqual(config.dimensions, 3)
            self.assertEqual(config.steps, 480)
            self.assertEqual(config.seed, 122095)
            self.assertEqual(config.parameters.attraction, 0.02)
            self.assertEqual(config.rewire_gate_denominator, 1000)
            self.assertEqual(config.rewire_gate_exclusive_max, 251)
            multi_record = json.loads(json.dumps(record))
            multi_record["rewiring"]["rewires_per_event"] = 4
            multi_config = affinity_config_from_preset(multi_record, agent_count=12000, dimensions=3, steps=480)
            self.assertEqual(multi_config.rewires_per_event, 4)

    def test_affinity_preset_http_round_trip_is_protected_and_inert(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "website").mkdir()
            (root / "website" / "index.html").write_text("studio", encoding="utf-8")
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(root, mutation_token="preset-token"))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            payload = {
                "schema_version": 1,
                "mechanism": "nonlocal-affinity-v1",
                "project_id": "study-003-nonlocal-affinity-dance",
                "title": "HTTP candidate",
                "note": "No execution.",
                "dimensions": 2,
                "seed": 9,
                "parameters": {"contraction": 0.995, "attraction": 0.02, "repulsion": 0.01, "softening": 0.01},
                "rewiring": {"probability_per_simulation_step": 0.1, "rewires_per_event": 1, "ordering": "before-synchronous-position-update"},
                "preview": {"agent_count": 100, "steps_per_display_frame": 1, "rng": "mulberry32-v1", "initialization": "uniform-square-minus-one-to-one"},
                "display": {"point_size": 1.5, "trail_alpha": 0.16, "viewport_scale": 1.25, "show_links": False},
                "production_hint": {"state": "candidate", "execution_authorized": False, "integration_authority": "houdini-vex"},
            }
            try:
                request = urllib.request.Request(
                    base + "/api/studio/affinity-presets",
                    data=json.dumps(payload).encode(),
                    headers={
                        "Content-Type": "application/json",
                        "Origin": base,
                        "X-Studio-Mutation-Token": "preset-token",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(request) as response:
                    self.assertEqual(response.status, 201)
                    record = json.load(response)
                self.assertFalse(record["production_hint"]["execution_authorized"])
                with urllib.request.urlopen(base + "/api/studio/affinity-presets") as response:
                    listed = json.load(response)
                self.assertEqual(listed["items"], [record])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
