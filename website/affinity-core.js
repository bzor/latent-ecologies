(function (root, factory) {
  const core = factory();
  if (typeof module === "object" && module.exports) module.exports = core;
  else root.AffinityCore = core;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const DEFAULT_SETTINGS = Object.freeze({
    agent_count: 1000,
    seed: 122095,
    contraction: 0.995,
    attraction: 0.02,
    repulsion: 0.01,
    softening: 0.01,
    rewire_probability: 0.099,
    rewires_per_event: 1,
    steps_per_frame: 1,
  });

  const DEFAULT_DISPLAY = Object.freeze({
    point_size: 1.5,
    trail_alpha: 0.16,
    viewport_scale: 1.25,
    show_links: false,
  });

  function finiteNumber(value, name) {
    const number = Number(value);
    if (!Number.isFinite(number)) throw new Error(`${name} must be finite`);
    return number;
  }

  function integer(value, name, minimum, maximum) {
    const number = finiteNumber(value, name);
    if (!Number.isInteger(number) || number < minimum || number > maximum) {
      throw new Error(`${name} must be an integer from ${minimum} to ${maximum}`);
    }
    return number;
  }

  function normalizeSettings(value) {
    const source = {...DEFAULT_SETTINGS, ...(value || {})};
    const settings = {
      agent_count: integer(source.agent_count, "agent_count", 2, 10000),
      seed: integer(source.seed, "seed", 0, 0xffffffff),
      contraction: finiteNumber(source.contraction, "contraction"),
      attraction: finiteNumber(source.attraction, "attraction"),
      repulsion: finiteNumber(source.repulsion, "repulsion"),
      softening: finiteNumber(source.softening, "softening"),
      rewire_probability: finiteNumber(source.rewire_probability, "rewire_probability"),
      rewires_per_event: integer(source.rewires_per_event, "rewires_per_event", 1, 64),
      steps_per_frame: integer(source.steps_per_frame, "steps_per_frame", 1, 32),
    };
    if (settings.contraction < 0.8 || settings.contraction > 1.05) throw new Error("contraction is out of range");
    if (settings.attraction < 0 || settings.attraction > 0.25) throw new Error("attraction is out of range");
    if (settings.repulsion < 0 || settings.repulsion > 0.25) throw new Error("repulsion is out of range");
    if (settings.softening <= 0 || settings.softening > 1) throw new Error("softening is out of range");
    if (settings.rewire_probability < 0 || settings.rewire_probability > 1) throw new Error("rewire_probability is out of range");
    return settings;
  }

  function createRng(seed) {
    let state = seed >>> 0;
    return function random() {
      state = (state + 0x6d2b79f5) >>> 0;
      let value = state;
      value = Math.imul(value ^ (value >>> 15), value | 1);
      value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
      return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
    };
  }

  function createSimulation(value) {
    const settings = normalizeSettings(value);
    const rng = createRng(settings.seed);
    const count = settings.agent_count;
    const positions = new Float64Array(count * 2);
    const friends = new Uint32Array(count);
    const enemies = new Uint32Array(count);
    for (let index = 0; index < positions.length; index += 1) positions[index] = rng() * 2 - 1;
    for (let point = 0; point < count; point += 1) friends[point] = Math.floor(rng() * count);
    for (let point = 0; point < count; point += 1) enemies[point] = Math.floor(rng() * count);
    return {
      settings,
      positions,
      next_positions: new Float64Array(positions.length),
      friends,
      enemies,
      count,
      dimensions: 2,
      rng,
      step_count: 0,
      rewire_count: 0,
      displacement_mean: 0,
    };
  }

  function stepState(state, parameters, rewire) {
    const count = integer(state.count, "count", 1, 10000000);
    const dimensions = integer(state.dimensions, "dimensions", 1, 16);
    if (state.positions.length !== count * dimensions) throw new Error("position length does not match state shape");
    if (state.friends.length !== count || state.enemies.length !== count) throw new Error("relationship length mismatch");
    const softening = finiteNumber(parameters.softening, "softening");
    if (softening <= 0) throw new Error("softening must be positive");
    const friends = new Uint32Array(state.friends);
    const enemies = new Uint32Array(state.enemies);
    if (rewire) {
      const point = integer(rewire.point, "rewire.point", 0, count - 1);
      friends[point] = integer(rewire.friend, "rewire.friend", 0, count - 1);
      enemies[point] = integer(rewire.enemy, "rewire.enemy", 0, count - 1);
    }
    const updated = new Float64Array(state.positions.length);
    for (let point = 0; point < count; point += 1) {
      const friend = friends[point];
      const enemy = enemies[point];
      let friendLength2 = 0;
      let enemyLength2 = 0;
      const base = point * dimensions;
      const friendBase = friend * dimensions;
      const enemyBase = enemy * dimensions;
      for (let axis = 0; axis < dimensions; axis += 1) {
        const friendOffset = state.positions[friendBase + axis] - state.positions[base + axis];
        const enemyOffset = state.positions[enemyBase + axis] - state.positions[base + axis];
        friendLength2 += friendOffset * friendOffset;
        enemyLength2 += enemyOffset * enemyOffset;
      }
      const friendDenominator = softening + Math.sqrt(friendLength2);
      const enemyDenominator = softening + Math.sqrt(enemyLength2);
      for (let axis = 0; axis < dimensions; axis += 1) {
        const position = state.positions[base + axis];
        const friendOffset = state.positions[friendBase + axis] - position;
        const enemyOffset = state.positions[enemyBase + axis] - position;
        updated[base + axis] = parameters.contraction * position
          + parameters.attraction * friendOffset / friendDenominator
          - parameters.repulsion * enemyOffset / enemyDenominator;
      }
    }
    return {positions: updated, friends, enemies, count, dimensions};
  }

  function stepSimulation(simulation) {
    const settings = simulation.settings;
    const count = simulation.count;
    if (simulation.rng() < settings.rewire_probability) {
      for (let index = 0; index < settings.rewires_per_event; index += 1) {
        const point = Math.floor(simulation.rng() * count);
        simulation.friends[point] = Math.floor(simulation.rng() * count);
        simulation.enemies[point] = Math.floor(simulation.rng() * count);
        simulation.rewire_count += 1;
      }
    }
    let displacement = 0;
    for (let point = 0; point < count; point += 1) {
      const base = point * 2;
      const friendBase = simulation.friends[point] * 2;
      const enemyBase = simulation.enemies[point] * 2;
      const x = simulation.positions[base];
      const y = simulation.positions[base + 1];
      const fdx = simulation.positions[friendBase] - x;
      const fdy = simulation.positions[friendBase + 1] - y;
      const edx = simulation.positions[enemyBase] - x;
      const edy = simulation.positions[enemyBase + 1] - y;
      const friendDenominator = settings.softening + Math.hypot(fdx, fdy);
      const enemyDenominator = settings.softening + Math.hypot(edx, edy);
      const nextX = settings.contraction * x
        + settings.attraction * fdx / friendDenominator
        - settings.repulsion * edx / enemyDenominator;
      const nextY = settings.contraction * y
        + settings.attraction * fdy / friendDenominator
        - settings.repulsion * edy / enemyDenominator;
      simulation.next_positions[base] = nextX;
      simulation.next_positions[base + 1] = nextY;
      displacement += Math.hypot(nextX - x, nextY - y);
    }
    const prior = simulation.positions;
    simulation.positions = simulation.next_positions;
    simulation.next_positions = prior;
    simulation.step_count += 1;
    simulation.displacement_mean = displacement / count;
    return simulation;
  }

  function measure(simulation) {
    let radiusMean = 0;
    let radiusMax = 0;
    for (let point = 0; point < simulation.count; point += 1) {
      const radius = Math.hypot(simulation.positions[point * 2], simulation.positions[point * 2 + 1]);
      radiusMean += radius;
      if (radius > radiusMax) radiusMax = radius;
    }
    return {
      step: simulation.step_count,
      rewires: simulation.rewire_count,
      radial_mean: radiusMean / simulation.count,
      radial_extent: radiusMax,
      displacement_mean: simulation.displacement_mean,
    };
  }

  function makePreset(settingsValue, displayValue, metadata) {
    const settings = normalizeSettings(settingsValue);
    const display = {...DEFAULT_DISPLAY, ...(displayValue || {})};
    const meta = metadata || {};
    const title = String(meta.title || "").trim();
    if (!title) throw new Error("preset title is required");
    return {
      schema_version: 1,
      mechanism: "nonlocal-affinity-v1",
      project_id: "study-003-nonlocal-affinity-dance",
      title,
      note: String(meta.note || "").trim(),
      dimensions: 2,
      seed: settings.seed,
      parameters: {
        contraction: settings.contraction,
        attraction: settings.attraction,
        repulsion: settings.repulsion,
        softening: settings.softening,
      },
      rewiring: {
        probability_per_simulation_step: settings.rewire_probability,
        rewires_per_event: settings.rewires_per_event,
        ordering: "before-synchronous-position-update",
      },
      preview: {
        agent_count: settings.agent_count,
        steps_per_display_frame: settings.steps_per_frame,
        rng: "mulberry32-v1",
        initialization: "uniform-square-minus-one-to-one",
      },
      display: {
        point_size: finiteNumber(display.point_size, "point_size"),
        trail_alpha: finiteNumber(display.trail_alpha, "trail_alpha"),
        viewport_scale: finiteNumber(display.viewport_scale, "viewport_scale"),
        show_links: Boolean(display.show_links),
      },
      production_hint: {
        state: "candidate",
        execution_authorized: false,
        integration_authority: "houdini-vex",
      },
    };
  }

  return {
    DEFAULT_SETTINGS,
    DEFAULT_DISPLAY,
    normalizeSettings,
    createRng,
    createSimulation,
    stepState,
    stepSimulation,
    measure,
    makePreset,
  };
});
