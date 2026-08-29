// Reference kernel: Non-Local Affinity (Study 003 mechanism).
// The simulation is website/affinity-core.js verbatim — this kernel only adapts
// it to the harness contract, so parity with the proven Canvas instrument and
// the Houdini identity ladder is preserved by construction.
(function (root, factory) {
  const core =
    root.AffinityCore ||
    (typeof module === "object" && module.exports ? require("../../../website/affinity-core.js") : null);
  const kernel = factory(core);
  if (typeof module === "object" && module.exports) module.exports = kernel;
  if (root.BP && typeof root.BP.registerKernel === "function" && typeof document !== "undefined") {
    root.BP.registerKernel(kernel);
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function (core) {
  "use strict";

  return {
    id: "affinity",
    title: "Non-Local Affinity",
    mechanism: "nonlocal-affinity-v1",
    mechanismVersion: 1,
    studyId: "study-003-nonlocal-affinity-dance",
    initialization: "uniform-square-minus-one-to-one",
    ordering: "before-synchronous-position-update",
    view: "canvas2d",
    defaults: {
      seed: 122095,
      agent_count: 1000,
      contraction: 0.995,
      attraction: 0.02,
      repulsion: 0.01,
      softening: 0.01,
      rewire_probability: 0.099,
      rewires_per_event: 1,
      point_size: 1.5,
      trail_alpha: 0.16,
      viewport_scale: 1.25,
      show_links: false,
    },
    schema: [
      { key: "agent_count", label: "agents", type: "int", min: 2, max: 10000, step: 1 },
      { key: "contraction", label: "contraction", type: "number", min: 0.8, max: 1.05, step: 0.001 },
      { key: "attraction", label: "attraction", type: "number", min: 0, max: 0.25, step: 0.001 },
      { key: "repulsion", label: "repulsion", type: "number", min: 0, max: 0.25, step: 0.001 },
      { key: "softening", label: "softening", type: "number", min: 0.0001, max: 1, step: 0.001 },
      { key: "rewire_probability", label: "rewire prob / step", type: "number", min: 0, max: 1, step: 0.001 },
      { key: "rewires_per_event", label: "rewires / event", type: "int", min: 1, max: 64, step: 1 },
      { key: "point_size", label: "point size", type: "number", min: 0.25, max: 12, step: 0.25, identity: false },
      { key: "trail_alpha", label: "trail alpha", type: "number", min: 0, max: 1, step: 0.01, identity: false },
      { key: "viewport_scale", label: "viewport scale", type: "number", min: 0.1, max: 20, step: 0.05, identity: false },
      { key: "show_links", label: "show links", type: "bool", identity: false },
    ],

    init(params) {
      return core.createSimulation({
        agent_count: params.agent_count,
        seed: params.seed,
        contraction: params.contraction,
        attraction: params.attraction,
        repulsion: params.repulsion,
        softening: params.softening,
        rewire_probability: params.rewire_probability,
        rewires_per_event: params.rewires_per_event,
      });
    },

    step(sim) {
      core.stepSimulation(sim);
    },

    draw(view, sim, params) {
      const ctx = view.ctx;
      const size = view.size;
      if (sim.step_count === 0) {
        ctx.fillStyle = "#000";
        ctx.fillRect(0, 0, size, size);
      } else {
        ctx.fillStyle = `rgba(0, 0, 0, ${1 - params.trail_alpha})`;
        ctx.fillRect(0, 0, size, size);
      }
      const scale = size / (2 * params.viewport_scale);
      const center = size / 2;
      if (params.show_links) {
        ctx.strokeStyle = "rgba(88, 196, 150, 0.10)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let point = 0; point < sim.count; point += 1) {
          const friend = sim.friends[point];
          ctx.moveTo(center + sim.positions[point * 2] * scale, center + sim.positions[point * 2 + 1] * scale);
          ctx.lineTo(center + sim.positions[friend * 2] * scale, center + sim.positions[friend * 2 + 1] * scale);
        }
        ctx.stroke();
      }
      ctx.fillStyle = "#e8ede9";
      const radius = params.point_size;
      for (let point = 0; point < sim.count; point += 1) {
        const x = center + sim.positions[point * 2] * scale;
        const y = center + sim.positions[point * 2 + 1] * scale;
        ctx.fillRect(x - radius / 2, y - radius / 2, radius, radius);
      }
    },
  };
});
