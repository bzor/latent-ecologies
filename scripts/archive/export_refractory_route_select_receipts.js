// Export deterministic initial-state receipts and parity traces for the
// Study 001 Refractory Route select presets.
//
// The browser prototype is the discovery authority; this exporter freezes each
// select's exact initial identity (agents + resource field) and a short-horizon
// reference trajectory so the VEX-authoritative Behavior HDA can be audited
// against the promoted behavior.
//
// Usage: node scripts/export_refractory_route_select_receipts.js <output-dir>

"use strict";

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const ROOT = path.resolve(__dirname, "..");
const KERNEL = path.join(
  ROOT,
  "studies/001-memory-field/01_behavior/01_work/prototypes/refractory-route/kernel.js"
);
const SELECTS_DIR = path.join(ROOT, "studies/001-memory-field/01_behavior/02_selects");
const PARITY_STEPS = [1, 6, 12, 24];
const STRUCTURAL_HORIZON = 120;

const kernel = require(KERNEL);

function stateDigest(sim) {
  const state = Buffer.concat([
    Buffer.from(sim.positions.buffer),
    Buffer.from(sim.velocities.buffer),
    Buffer.from(sim.resource.buffer),
    Buffer.from(sim.fresh.buffer),
    Buffer.from(sim.scar.buffer),
    Buffer.from(sim.traceDir.buffer),
    Buffer.from(sim.modes.buffer),
  ]);
  return crypto.createHash("sha256").update(state).digest("hex");
}

function fieldStats(sim) {
  let freshMax = 0;
  let scarMax = 0;
  let resourceMin = Infinity;
  let resourceMax = -Infinity;
  for (let cell = 0; cell < sim.resource.length; cell += 1) {
    if (sim.fresh[cell] > freshMax) freshMax = sim.fresh[cell];
    if (sim.scar[cell] > scarMax) scarMax = sim.scar[cell];
    if (sim.resource[cell] < resourceMin) resourceMin = sim.resource[cell];
    if (sim.resource[cell] > resourceMax) resourceMax = sim.resource[cell];
  }
  return { freshMax, scarMax, resourceMin, resourceMax };
}

function exportSelect(presetPath, outputDir) {
  const preset = JSON.parse(fs.readFileSync(presetPath, "utf8"));
  const params = { ...kernel.defaults, ...preset.parameters, seed: preset.seed };
  const sim = kernel.init(params);
  const receipt = kernel.identityReceipt(sim, params);

  const parity = [];
  for (let step = 1; step <= STRUCTURAL_HORIZON; step += 1) {
    kernel.step(sim, params);
    if (PARITY_STEPS.includes(step)) {
      parity.push({
        step,
        positions: Array.from(sim.positions),
        velocities: Array.from(sim.velocities),
        energies: Array.from(sim.energies),
        modes: Array.from(sim.modes),
        field: fieldStats(sim),
      });
    }
  }

  const record = {
    schema_version: 1,
    kind: "refractory-route-select-receipt",
    source_preset: path.basename(presetPath),
    title: preset.title,
    mechanism: preset.mechanism,
    mechanism_version: preset.mechanism_version,
    seed: preset.seed,
    parameters: preset.parameters,
    identity_receipt: receipt,
    parity_trace: {
      note: "reference trajectory from the promoted browser kernel; float64 math stored to float32 state each write",
      steps_per_display_frame: 1,
      snapshots: parity,
    },
    structural_horizon: {
      steps: STRUCTURAL_HORIZON,
      state_sha256: stateDigest(sim),
      field: fieldStats(sim),
      mode_counts: Array.from(sim.modeCounts),
      events: sim.events,
    },
  };
  const stem = path.basename(presetPath).replace(/\.preset\.json$/, "");
  const outputPath = path.join(outputDir, `${stem}.receipt.json`);
  fs.writeFileSync(outputPath, JSON.stringify(record) + "\n");
  return {
    output: outputPath,
    title: preset.title,
    agent_count: params.agent_count,
    grid: [params.grid_width, params.grid_height],
    structural_digest: record.structural_horizon.state_sha256,
    events: record.structural_horizon.events,
  };
}

function main() {
  const outputDir = process.argv[2];
  if (!outputDir) {
    console.error("usage: node export_refractory_route_select_receipts.js <output-dir>");
    process.exit(1);
  }
  fs.mkdirSync(outputDir, { recursive: true });
  const selects = fs
    .readdirSync(SELECTS_DIR)
    .filter((name) => name.endsWith(".preset.json"))
    .sort();
  const summary = selects.map((name) => exportSelect(path.join(SELECTS_DIR, name), outputDir));
  console.log(JSON.stringify({ exported: summary }, null, 2));
}

main();
