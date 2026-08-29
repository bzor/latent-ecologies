(() => {
  "use strict";

  const core = window.AffinityCore;
  if (!core) throw new Error("AffinityCore failed to load");
  const byId = id => document.getElementById(id);
  const canvas = byId("affinityCanvas");
  const context = canvas.getContext("2d", {alpha: false});

  let settings = {...core.DEFAULT_SETTINGS, rewire_probability: 0.099};
  let display = {...core.DEFAULT_DISPLAY};
  let simulation = core.createSimulation(settings);
  let playing = true;
  let mutationToken = null;
  let lastFrameTime = performance.now();
  let fpsSmoothed = 0;
  let clearRequested = true;

  const behaviorControls = [
    ["agentCount", "agent_count", true, 0],
    ["contraction", "contraction", false, 4],
    ["attraction", "attraction", false, 3],
    ["repulsion", "repulsion", false, 3],
    ["softening", "softening", false, 3],
    ["rewireProbability", "rewire_probability", false, 3],
    ["rewiresPerEvent", "rewires_per_event", false, 0],
    ["stepsPerFrame", "steps_per_frame", false, 0],
  ];
  const displayControls = [
    ["pointSize", "point_size", 1],
    ["trailAlpha", "trail_alpha", 2],
    ["viewportScale", "viewport_scale", 2],
  ];

  function formatValue(value, places) {
    return places === 0 ? String(Math.round(value)) : Number(value).toFixed(places);
  }

  function syncControls() {
    behaviorControls.forEach(([id, key, , places]) => {
      byId(id).value = settings[key];
      byId(`${id}Value`).textContent = formatValue(settings[key], places);
    });
    byId("seed").value = settings.seed;
    displayControls.forEach(([id, key, places]) => {
      byId(id).value = display[key];
      byId(`${id}Value`).textContent = formatValue(display[key], places);
    });
    byId("showLinks").checked = display.show_links;
  }

  function resetSimulation() {
    settings = core.normalizeSettings(settings);
    simulation = core.createSimulation(settings);
    clearRequested = true;
    updateMetrics();
  }

  behaviorControls.forEach(([id, key, rebuild, places]) => {
    const input = byId(id);
    input.addEventListener("input", () => {
      const value = places === 0 ? Number.parseInt(input.value, 10) : Number.parseFloat(input.value);
      settings = {...settings, [key]: value};
      byId(`${id}Value`).textContent = formatValue(value, places);
      if (!rebuild) simulation.settings = core.normalizeSettings(settings);
    });
    if (rebuild) input.addEventListener("change", resetSimulation);
  });

  displayControls.forEach(([id, key, places]) => {
    const input = byId(id);
    input.addEventListener("input", () => {
      display = {...display, [key]: Number.parseFloat(input.value)};
      byId(`${id}Value`).textContent = formatValue(display[key], places);
      if (key === "viewport_scale") clearRequested = true;
    });
  });
  byId("showLinks").addEventListener("change", event => {
    display = {...display, show_links: event.target.checked};
  });
  byId("seed").addEventListener("change", event => {
    settings = {...settings, seed: Math.max(0, Math.min(0xffffffff, Number.parseInt(event.target.value, 10) || 0))};
    resetSimulation();
  });

  byId("playPause").addEventListener("click", () => {
    playing = !playing;
    byId("playPause").textContent = playing ? "Pause" : "Play";
    byId("runState").textContent = playing ? "RUNNING" : "PAUSED";
  });
  byId("singleStep").addEventListener("click", () => {
    core.stepSimulation(simulation);
    updateMetrics();
  });
  byId("resetSame").addEventListener("click", resetSimulation);
  byId("newSeed").addEventListener("click", () => {
    const seed = crypto.getRandomValues(new Uint32Array(1))[0];
    settings = {...settings, seed};
    byId("seed").value = seed;
    resetSimulation();
  });
  byId("sourceDefaults").addEventListener("click", () => {
    settings = {...core.DEFAULT_SETTINGS, rewire_probability: 0.099};
    display = {...core.DEFAULT_DISPLAY};
    syncControls();
    resetSimulation();
  });

  function resizeCanvas() {
    const rectangle = canvas.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.max(1, Math.round(rectangle.width * ratio));
    const height = Math.max(1, Math.round(rectangle.height * ratio));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
      clearRequested = true;
    }
  }
  new ResizeObserver(resizeCanvas).observe(canvas);
  resizeCanvas();

  function draw() {
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    const width = canvas.width / ratio;
    const height = canvas.height / ratio;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    if (clearRequested || display.trail_alpha >= 0.999) {
      context.fillStyle = "#090b09";
      context.fillRect(0, 0, width, height);
      clearRequested = false;
    } else {
      context.fillStyle = `rgba(9,11,9,${display.trail_alpha})`;
      context.fillRect(0, 0, width, height);
    }
    const scale = Math.min(width, height) / (2 * display.viewport_scale);
    const centerX = width / 2;
    const centerY = height / 2;
    if (display.show_links) {
      const sampleCount = Math.min(32, simulation.count);
      context.lineWidth = 0.65;
      for (let point = 0; point < sampleCount; point += 1) {
        const origin = point * 2;
        const friend = simulation.friends[point] * 2;
        const enemy = simulation.enemies[point] * 2;
        context.strokeStyle = "rgba(185,255,39,.22)";
        context.beginPath();
        context.moveTo(centerX + simulation.positions[origin] * scale, centerY - simulation.positions[origin + 1] * scale);
        context.lineTo(centerX + simulation.positions[friend] * scale, centerY - simulation.positions[friend + 1] * scale);
        context.stroke();
        context.strokeStyle = "rgba(255,79,154,.18)";
        context.beginPath();
        context.moveTo(centerX + simulation.positions[origin] * scale, centerY - simulation.positions[origin + 1] * scale);
        context.lineTo(centerX + simulation.positions[enemy] * scale, centerY - simulation.positions[enemy + 1] * scale);
        context.stroke();
      }
    }
    context.fillStyle = "rgba(239,238,224,.92)";
    const radius = Math.max(0.3, display.point_size);
    for (let point = 0; point < simulation.count; point += 1) {
      const base = point * 2;
      const x = centerX + simulation.positions[base] * scale;
      const y = centerY - simulation.positions[base + 1] * scale;
      context.fillRect(x - radius / 2, y - radius / 2, radius, radius);
    }
  }

  function updateMetrics() {
    const metrics = core.measure(simulation);
    byId("stepMetric").textContent = `STEP ${metrics.step.toLocaleString()}`;
    byId("motionMetric").textContent = metrics.displacement_mean.toFixed(6);
    byId("radiusMetric").textContent = metrics.radial_mean.toFixed(4);
    byId("extentMetric").textContent = metrics.radial_extent.toFixed(4);
    byId("rewireMetric").textContent = metrics.rewires.toLocaleString();
  }

  function animationFrame(now) {
    const elapsed = Math.max(1, now - lastFrameTime);
    const instantaneousFps = 1000 / elapsed;
    fpsSmoothed = fpsSmoothed ? fpsSmoothed * 0.9 + instantaneousFps * 0.1 : instantaneousFps;
    lastFrameTime = now;
    if (playing) {
      for (let index = 0; index < settings.steps_per_frame; index += 1) core.stepSimulation(simulation);
    }
    draw();
    if (simulation.step_count % 5 === 0 || !playing) updateMetrics();
    byId("fpsMetric").textContent = fpsSmoothed.toFixed(0);
    requestAnimationFrame(animationFrame);
  }

  async function api(path, options) {
    const response = await fetch(path, options);
    const value = await response.json();
    if (!response.ok) throw new Error(value.error || `HTTP ${response.status}`);
    return value;
  }

  function currentPreset() {
    const preset = core.makePreset(settings, display, {
      title: byId("presetTitle").value,
      note: byId("presetNote").value,
    });
    if (preset.production_hint.execution_authorized !== false) throw new Error("execution_authorized must remain false");
    return preset;
  }

  function slug(value) {
    return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60) || "affinity-preset";
  }

  byId("downloadPreset").addEventListener("click", () => {
    try {
      const preset = currentPreset();
      const blob = new Blob([`${JSON.stringify(preset, null, 2)}\n`], {type: "application/json"});
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `${slug(preset.title)}.json`;
      link.click();
      URL.revokeObjectURL(link.href);
      byId("saveStatus").textContent = "Portable JSON downloaded. No execution was authorized.";
    } catch (error) {
      showError(error);
    }
  });

  byId("savePreset").addEventListener("click", async () => {
    const status = byId("saveStatus");
    status.classList.remove("error");
    status.textContent = "Saving private candidate…";
    try {
      const record = await api("/api/studio/affinity-presets", {
        method: "POST",
        headers: {"Content-Type": "application/json", "X-Studio-Mutation-Token": mutationToken},
        body: JSON.stringify(currentPreset()),
      });
      status.textContent = `Saved ${record.id}. Candidate only; Houdini was not launched.`;
      await loadPresetList();
    } catch (error) {
      showError(error);
    }
  });

  function showError(error) {
    const status = byId("saveStatus");
    status.classList.add("error");
    status.textContent = `ERROR: ${error.message}`;
  }

  function applyPreset(record) {
    settings = core.normalizeSettings({
      agent_count: record.preview.agent_count,
      seed: record.seed,
      contraction: record.parameters.contraction,
      attraction: record.parameters.attraction,
      repulsion: record.parameters.repulsion,
      softening: record.parameters.softening,
      rewire_probability: record.rewiring.probability_per_simulation_step,
      rewires_per_event: record.rewiring.rewires_per_event,
      steps_per_frame: record.preview.steps_per_display_frame,
    });
    display = {...core.DEFAULT_DISPLAY, ...record.display};
    byId("presetTitle").value = record.title;
    byId("presetNote").value = record.note;
    syncControls();
    resetSimulation();
    byId("saveStatus").textContent = `Loaded ${record.id} at step 0 with seed ${record.seed}.`;
  }

  async function loadPresetList() {
    const response = await api("/api/studio/affinity-presets");
    const container = byId("savedPresets");
    container.replaceChildren();
    const items = [...response.items].sort((left, right) => String(right.created_at).localeCompare(String(left.created_at)));
    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "muted";
      empty.textContent = "No candidates saved yet.";
      container.append(empty);
      return;
    }
    items.forEach(record => {
      const card = document.createElement("article");
      card.className = "preset-card";
      const title = document.createElement("strong");
      title.textContent = record.title;
      const detail = document.createElement("p");
      detail.textContent = `seed ${record.seed} · rewire ${record.rewiring.probability_per_simulation_step} · ${record.preview.agent_count} preview points`;
      const note = document.createElement("p");
      note.textContent = record.note || "No observation recorded.";
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = "Load settings";
      button.addEventListener("click", () => applyPreset(record));
      card.append(title, detail, note, button);
      container.append(card);
    });
  }

  byId("refreshPresets").addEventListener("click", () => loadPresetList().catch(showError));

  async function initialize() {
    syncControls();
    const bootstrap = await api("/api/studio/session");
    mutationToken = bootstrap.mutation_token;
    await loadPresetList();
    requestAnimationFrame(animationFrame);
  }

  initialize().catch(error => {
    showError(error);
    byId("runState").textContent = "STARTUP ERROR";
  });
})();
