import json
import subprocess
import unittest
from pathlib import Path

from houdini_ai.studio_schema import validate_record


ROOT = Path(__file__).resolve().parents[1]
KERNEL = (
    ROOT
    / "studies"
    / "001-memory-field"
    / "01_behavior"
    / "01_work"
    / "prototypes"
    / "refractory-route"
    / "kernel.js"
)
BANK = KERNEL.parent / "preset-bank.js"
EXPLORER = KERNEL.parent / "explorer.js"


def run_node(script: str) -> dict:
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


class MemoryFieldPrototypeTests(unittest.TestCase):
    def test_canvas_uses_fluid_stage_and_has_a_100_percent_toggle(self) -> None:
        value = run_node(
            f"""
            const kernel = require({json.dumps(KERNEL.as_posix())});
            console.log(JSON.stringify({{fluidView: kernel.fluidView}}));
            """
        )
        self.assertTrue(value["fluidView"])
        source = EXPLORER.read_text(encoding="utf-8")
        self.assertIn('"100%"', source)
        self.assertIn("canvas-100", source)
        self.assertIn("viewport-toggle", source)

    def test_every_causal_default_is_exposed_to_presets(self) -> None:
        value = run_node(
            f"""
            const kernel = require({json.dumps(KERNEL.as_posix())});
            const display = new Set(kernel.schema.filter((entry) => entry.identity === false).map((entry) => entry.key));
            const causalDefaults = Object.keys(kernel.defaults)
              .filter((key) => key !== "seed" && !display.has(key))
              .sort();
            const identityKeys = kernel.schema
              .filter((entry) => entry.identity !== false)
              .map((entry) => entry.key)
              .sort();
            console.log(JSON.stringify({{ causalDefaults, identityKeys }}));
            """
        )
        self.assertEqual(value["identityKeys"], value["causalDefaults"])

    def test_generated_landscape_artifacts_match_the_bank(self) -> None:
        root = KERNEL.parent
        index = (root / "index.html").read_text(encoding="utf-8")
        self.assertLess(index.index("./kernel.js"), index.index("./preset-bank.js"))
        self.assertLess(index.index("./preset-bank.js"), index.index("./explorer.js"))

        metrics_path = root / "analysis" / "preset-metrics.json"
        catalog_path = root / "PRESET_CATALOG.md"
        self.assertTrue(metrics_path.is_file())
        self.assertTrue(catalog_path.is_file())
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        self.assertEqual(metrics["horizon"], 120)
        self.assertEqual(len(metrics["presets"]), 50)
        self.assertEqual(len({item["stateDigest"] for item in metrics["presets"]}), 50)
        self.assertTrue(all(item["events"]["scarCrossings"] > 0 for item in metrics["presets"]))
        self.assertTrue(all(item["events"]["healedReentries"] > 0 for item in metrics["presets"]))
        self.assertEqual(len(list((root / "presets" / "bank").glob("*.preset.json"))), 50)
        catalog = catalog_path.read_text(encoding="utf-8")
        self.assertIn("`Space`: slight", catalog)
        self.assertIn("50 · Scale and grain · Ultra-fine archive", catalog)

    def test_explorer_navigation_and_mutation_are_deterministic_and_safe(self) -> None:
        self.assertTrue(EXPLORER.is_file(), f"explorer is missing: {EXPLORER}")
        value = run_node(
            f"""
            const explorer = require({json.dumps(EXPLORER.as_posix())});
            const bank = require({json.dumps(BANK.as_posix())});
            const source = bank.presets[12].preset;
            const a = explorer.mutatePreset(source, 12, 4);
            const b = explorer.mutatePreset(source, 12, 4);
            const changed = Object.keys(source.parameters)
              .filter((key) => source.parameters[key] !== a.parameters[key]);
            console.log(JSON.stringify({{
              a, b, changed,
              found: explorer.findPresetIndex(source, bank.presets),
              right: explorer.nextIndex(49, 1, 50),
              left: explorer.nextIndex(0, -1, 50),
            }}));
            """
        )
        self.assertEqual(value["a"], value["b"])
        self.assertEqual(value["right"], 0)
        self.assertEqual(value["left"], 49)
        self.assertEqual(value["found"], 12)
        self.assertGreaterEqual(len(value["changed"]), 2)
        self.assertLessEqual(len(value["changed"]), 5)
        self.assertEqual(value["a"]["seed"], value["b"]["seed"])
        self.assertEqual(validate_record("prototype-preset", value["a"]), [])
        source = EXPLORER.read_text(encoding="utf-8")
        for token in ("ArrowRight", "ArrowLeft", 'event.code === "Space"'):
            self.assertIn(token, source)

    def test_preset_bank_has_fifty_valid_unique_candidates_and_full_parameter_analysis(self) -> None:
        self.assertTrue(BANK.is_file(), f"preset bank is missing: {BANK}")
        value = run_node(
            f"""
            const kernel = require({json.dumps(KERNEL.as_posix())});
            const bank = require({json.dumps(BANK.as_posix())});
            const identityKeys = kernel.schema
              .filter((entry) => entry.identity !== false)
              .map((entry) => entry.key)
              .sort();
            const variedKeys = identityKeys.filter((key) =>
              new Set(bank.presets.map((item) => item.preset.parameters[key])).size > 1
            );
            console.log(JSON.stringify({{bank, identityKeys, variedKeys}}));
            """
        )
        bank = value["bank"]
        self.assertEqual(len(bank["presets"]), 50)
        self.assertEqual(len({item["id"] for item in bank["presets"]}), 50)
        self.assertEqual(len({item["preset"]["title"] for item in bank["presets"]}), 50)
        self.assertEqual(sorted(bank["parameterAnalysis"]), value["identityKeys"])
        self.assertEqual(value["variedKeys"], value["identityKeys"])
        combinations = set()
        for item in bank["presets"]:
            self.assertEqual(validate_record("prototype-preset", item["preset"]), [])
            self.assertTrue(item["family"])
            self.assertTrue(item["expected"])
            self.assertTrue(item["risk"])
            combinations.add(json.dumps(item["preset"]["parameters"], sort_keys=True))
        self.assertEqual(len(combinations), 50)

    def test_defaults_use_dense_preview_scale(self) -> None:
        value = run_node(
            f"""
            const kernel = require({json.dumps(KERNEL.as_posix())});
            console.log(JSON.stringify(kernel.defaults));
            """
        )
        self.assertEqual(value["agent_count"], 512)
        self.assertEqual(value["grid_width"], 128)
        self.assertGreaterEqual(value["grid_height"], 192)
        self.assertLessEqual(value["grid_height"], 224)
        self.assertLess(value["field_point_size"], 0.012)

    def test_dense_run_uses_bounded_spatial_neighbor_checks(self) -> None:
        value = run_node(
            f"""
            const kernel = require({json.dumps(KERNEL.as_posix())});
            const params = {{
              ...kernel.defaults,
              agent_count: 512,
              grid_width: 128,
              grid_height: 213,
            }};
            const sim = kernel.init(params);
            const started = performance.now();
            for (let frame = 0; frame < 20; frame++) kernel.step(sim, params);
            console.log(JSON.stringify({{
              elapsed_ms: performance.now() - started,
              diagnostics: sim.diagnostics,
            }}));
            """
        )
        self.assertIn("diagnostics", value)
        self.assertIn("neighbor_checks", value["diagnostics"])
        naive_checks = 512 * 511 * 20
        self.assertLess(value["diagnostics"]["neighbor_checks"], naive_checks * 0.2)
        self.assertLess(value["elapsed_ms"], 4000)

    def test_default_run_is_deterministic_and_completes_route_lifecycle(self) -> None:
        self.assertTrue(KERNEL.is_file(), f"prototype kernel is missing: {KERNEL}")
        value = run_node(
            f"""
            const crypto = require("crypto");
            const kernel = require({json.dumps(KERNEL.as_posix())});
            function run() {{
              const params = {{...kernel.defaults}};
              const sim = kernel.init(params);
              for (let frame = 0; frame < 360; frame++) kernel.step(sim, params);
              const state = Buffer.concat([
                Buffer.from(sim.positions.buffer), Buffer.from(sim.velocities.buffer),
                Buffer.from(sim.resource.buffer), Buffer.from(sim.fresh.buffer),
                Buffer.from(sim.scar.buffer), Buffer.from(sim.traceDir.buffer),
                Buffer.from(sim.modes.buffer),
              ]);
              return {{
                digest: crypto.createHash("sha256").update(state).digest("hex"),
                events: sim.events,
                modes: Array.from(sim.modeCounts),
                resourceMin: Math.min(...sim.resource),
                resourceMax: Math.max(...sim.resource),
                freshMax: Math.max(...sim.fresh),
                scarMax: Math.max(...sim.scar),
                receipt: kernel.identityReceipt(sim, params),
              }};
            }}
            console.log(JSON.stringify({{a: run(), b: run()}}));
            """
        )
        first, second = value["a"], value["b"]
        self.assertEqual(first["digest"], second["digest"])
        self.assertEqual(first["events"], second["events"])
        self.assertGreater(first["events"]["route_births"], 0)
        self.assertGreater(first["events"]["scar_threshold_crossings"], 0)
        self.assertGreater(first["events"]["route_abandonments"], 0)
        self.assertGreater(first["events"]["healed_reentries"], 0)
        self.assertGreater(first["freshMax"], 0.05)
        self.assertGreater(first["scarMax"], 0.05)
        self.assertGreater(first["resourceMax"] - first["resourceMin"], 0.1)
        self.assertEqual(first["receipt"]["rng"], "mulberry32-v1")
        self.assertEqual(first["receipt"]["seed"], 18432)
        self.assertEqual(first["receipt"]["agent_count"], 512)
        self.assertEqual(len(first["receipt"]["initial_agents"]), 512)
        self.assertIn("velocity", first["receipt"]["initial_agents"][0])
        self.assertIn("energy", first["receipt"]["initial_agents"][0])
        self.assertEqual(len(first["receipt"]["initial_agents"][0]["velocity"]), 2)
        self.assertEqual(len(first["receipt"]["resource_patches"]), 5)
        self.assertIn("initial_field", first["receipt"])
        self.assertEqual(len(first["receipt"]["initial_field"]["resource"]), 128 * 213)

    def test_default_run_activates_every_agent_mode(self) -> None:
        value = run_node(
            f"""
            const kernel = require({json.dumps(KERNEL.as_posix())});
            const params = {{...kernel.defaults}};
            const sim = kernel.init(params);
            for (let frame = 0; frame < 360; frame++) kernel.step(sim, params);
            console.log(JSON.stringify({{entries: sim.events.mode_entry_counts}}));
            """
        )
        self.assertIn("entries", value)
        self.assertEqual(len(value["entries"]), 4)
        for mode, count in enumerate(value["entries"]):
            self.assertGreater(count, 0, f"mode {mode} was never entered")

    def test_preset_is_valid_and_changed_seed_is_distinct(self) -> None:
        value = run_node(
            f"""
            const crypto = require("crypto");
            const kernel = require({json.dumps(KERNEL.as_posix())});
            const BP = require({json.dumps((ROOT / 'behavior-playground' / 'web' / 'harness.js').as_posix())});
            function digest(seed) {{
              const params = {{...kernel.defaults, seed}};
              const sim = kernel.init(params);
              for (let frame = 0; frame < 120; frame++) kernel.step(sim, params);
              return crypto.createHash("sha256").update(Buffer.from(sim.positions.buffer)).digest("hex");
            }}
            const preset = BP.presetFromKernel(kernel, kernel.defaults, 2, {{
              title: "Refractory Route baseline",
              note: "Default deterministic browser candidate",
            }});
            console.log(JSON.stringify({{
              preset,
              defaultDigest: digest(kernel.defaults.seed),
              changedDigest: digest(kernel.defaults.seed + 1),
            }}));
            """
        )
        self.assertEqual(validate_record("prototype-preset", value["preset"]), [])
        self.assertEqual(value["preset"]["study_id"], "study-001-memory-field")
        self.assertEqual(value["preset"]["production_hint"]["integration_authority"], "houdini-vex")
        self.assertFalse(value["preset"]["production_hint"]["execution_authorized"])
        self.assertNotEqual(value["defaultDigest"], value["changedDigest"])
        self.assertNotIn("field_mode", value["preset"]["parameters"])
        self.assertEqual(value["preset"]["display"]["field_mode"], "composite")

    def test_kernel_contains_no_untracked_randomness(self) -> None:
        code = "\n".join(
            line for line in KERNEL.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("//")
        )
        self.assertNotIn("Math.random(", code)
        self.assertNotIn("Date.now(", code)


if __name__ == "__main__":
    unittest.main()
