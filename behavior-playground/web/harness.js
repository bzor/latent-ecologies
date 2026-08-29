// Behavior playground harness — panel generation, playback, seed control,
// preset export/import, deterministic URL mode for headless capture.
//
// Kernel contract (see behavior-playground/CLAUDE.md):
//   BP.registerKernel({
//     id, title,
//     mechanism, mechanismVersion,          // identity contract
//     initialization, ordering,             // documented conventions
//     view: "canvas2d" | "three",
//     defaults: {seed, ...},                // flat param object, seed required
//     schema: [{key, label, type, min, max, step, options, identity}],
//     init(params) -> simState,             // must derive all randomness from
//     step(simState, params),               //   BP.mulberry32(params.seed)
//     draw(view, simState, params, frame),
//   })
//
// Determinism rule: init/step/draw are pure functions of (params, frame,
// canvas size). No Date.now(), no Math.random() — BP.mulberry32 only.
(function (root) {
  "use strict";
  const BP = (root.BP = root.BP || {});

  // Pure preset construction — shared by the browser export button and the
  // Node-side tests, so the exported record shape cannot drift between them.
  BP.presetFromKernel = function (kernel, params, stepsPerFrame, meta) {
    const parameters = {};
    const display = {};
    for (const entry of kernel.schema) {
      if (entry.key === "seed") continue;
      (entry.identity === false ? display : parameters)[entry.key] = params[entry.key];
    }
    return {
      schema_version: 1,
      kind: "prototype-preset",
      mechanism: kernel.mechanism,
      mechanism_version: kernel.mechanismVersion,
      study_id: kernel.studyId || null,
      title: String((meta && meta.title) || "").trim() || "Untitled candidate",
      note: String((meta && meta.note) || "").trim(),
      seed: params.seed >>> 0,
      identity: {
        rng: BP.RNG_ID || "mulberry32-v1",
        initialization: kernel.initialization,
        ordering: kernel.ordering,
      },
      parameters,
      display,
      playback: { steps_per_display_frame: stepsPerFrame },
      production_hint: {
        state: "candidate",
        execution_authorized: false,
        integration_authority: "houdini-vex",
      },
      state: "candidate",
      visibility: "private",
    };
  };

  BP.computeViewDimensions = function (availableWidth, availableHeight, forcedSize) {
    const clampDimension = (value) => Math.max(200, Math.min(4096, Math.floor(Number(value) || 0)));
    const forced = Number(forcedSize);
    if (forcedSize !== null && forcedSize !== undefined && Number.isFinite(forced) && forced > 0) {
      const size = clampDimension(forced);
      return { width: size, height: size };
    }
    return {
      width: clampDimension(availableWidth),
      height: clampDimension(availableHeight),
    };
  };

  if (typeof document === "undefined") {
    if (typeof module === "object" && module.exports) module.exports = BP;
    return;
  }

  const S = {
    kernel: null,
    params: null,
    sim: null,
    frame: 0,
    playing: false,
    stepsPerFrame: 1,
    view: null,
    controls: {},
  };

  function query() {
    const params = new URLSearchParams(root.location ? root.location.search : "");
    return params;
  }

  function base64UrlDecode(text) {
    const normalized = text.replace(/-/g, "+").replace(/_/g, "/");
    return decodeURIComponent(
      Array.from(atob(normalized), (c) => "%" + c.charCodeAt(0).toString(16).padStart(2, "0")).join("")
    );
  }

  function el(tag, className, parent) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (parent) parent.appendChild(node);
    return node;
  }

  BP.registerKernel = function (kernel) {
    S.kernel = kernel;
    S.params = { ...kernel.defaults };
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", boot);
    } else {
      boot();
    }
  };

  BP.buildPreset = function (meta) {
    return BP.presetFromKernel(S.kernel, S.params, S.stepsPerFrame, meta);
  };

  BP.applyPreset = function (preset) {
    if (preset.mechanism !== S.kernel.mechanism) {
      throw new Error(`preset mechanism ${preset.mechanism} does not match kernel ${S.kernel.mechanism}`);
    }
    const merged = { ...S.kernel.defaults, ...(preset.parameters || {}), ...(preset.display || {}) };
    merged.seed = preset.seed >>> 0;
    S.params = merged;
    if (preset.playback && preset.playback.steps_per_display_frame) {
      S.stepsPerFrame = preset.playback.steps_per_display_frame | 0;
    }
    syncControls();
    reset();
  };

  function reset() {
    S.sim = S.kernel.init({ ...S.params });
    S.frame = 0;
    updateReadout();
    draw();
  }

  function stepOnce() {
    S.kernel.step(S.sim, S.params);
    S.frame += 1;
  }

  function displayFrame() {
    for (let index = 0; index < S.stepsPerFrame; index += 1) stepOnce();
    updateReadout();
    draw();
  }

  function runTo(frame) {
    while (S.frame < frame) stepOnce();
    updateReadout();
    draw();
  }

  function draw() {
    S.kernel.draw(S.view, S.sim, S.params, S.frame);
    if (S.view.type === "three") {
      S.view.renderer.render(S.view.scene, S.view.camera);
    }
  }

  function loop() {
    if (S.playing) displayFrame();
    root.requestAnimationFrame(loop);
  }

  function updateReadout() {
    if (S.controls.readout) {
      S.controls.readout.textContent = `step ${S.frame}`;
    }
  }

  function makeView(canvas, width, height) {
    canvas.width = width;
    canvas.height = height;
    if (S.kernel.view === "three") {
      const renderer = new root.THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
      renderer.setSize(width, height, false);
      const scene = new root.THREE.Scene();
      const camera = new root.THREE.PerspectiveCamera(40, width / height, 0.01, 100);
      camera.position.set(0, 0, 4);
      return { type: "three", canvas, width, height, size: Math.min(width, height), THREE: root.THREE, renderer, scene, camera };
    }
    return { type: "canvas2d", canvas, width, height, size: Math.min(width, height), ctx: canvas.getContext("2d") };
  }

  BP.resizeView = function (width, height) {
    if (!S.view) return;
    const dimensions = BP.computeViewDimensions(width, height, null);
    S.view.width = dimensions.width;
    S.view.height = dimensions.height;
    S.view.size = Math.min(dimensions.width, dimensions.height);
    S.view.canvas.width = dimensions.width;
    S.view.canvas.height = dimensions.height;
    if (S.view.type === "three") {
      S.view.renderer.setSize(dimensions.width, dimensions.height, false);
      S.view.camera.aspect = dimensions.width / dimensions.height;
      S.view.camera.updateProjectionMatrix();
    }
    if (S.sim) draw();
  };

  function identityChanged() {
    reset();
  }

  function controlRow(panel, entry) {
    const row = el("label", "row", panel);
    el("span", "row-label", row).textContent = entry.label || entry.key;
    let input;
    if (entry.type === "bool") {
      input = el("input", "", row);
      input.type = "checkbox";
      input.checked = Boolean(S.params[entry.key]);
      input.addEventListener("change", () => {
        S.params[entry.key] = input.checked;
        entry.identity === false ? draw() : identityChanged();
      });
    } else if (entry.type === "select") {
      input = el("select", "", row);
      for (const option of entry.options || []) {
        const opt = el("option", "", input);
        opt.value = option;
        opt.textContent = option;
      }
      input.value = String(S.params[entry.key]);
      input.addEventListener("change", () => {
        S.params[entry.key] = input.value;
        entry.identity === false ? draw() : identityChanged();
      });
    } else {
      input = el("input", "", row);
      input.type = "number";
      if (entry.min !== undefined) input.min = entry.min;
      if (entry.max !== undefined) input.max = entry.max;
      input.step = entry.step !== undefined ? entry.step : "any";
      input.value = String(S.params[entry.key]);
      input.addEventListener("change", () => {
        const value = Number(input.value);
        if (!Number.isFinite(value)) return;
        S.params[entry.key] = entry.type === "int" ? Math.round(value) : value;
        entry.identity === false ? draw() : identityChanged();
      });
    }
    S.controls[entry.key] = input;
    return row;
  }

  function syncControls() {
    for (const entry of S.kernel.schema) {
      const input = S.controls[entry.key];
      if (!input) continue;
      if (entry.type === "bool") input.checked = Boolean(S.params[entry.key]);
      else input.value = String(S.params[entry.key]);
    }
    if (S.controls.seed) S.controls.seed.value = String(S.params.seed);
    if (S.controls.spf) S.controls.spf.value = String(S.stepsPerFrame);
  }

  function buildPanel(rootEl) {
    const panel = el("aside", "panel", rootEl);
    el("h1", "", panel).textContent = S.kernel.title;
    el("div", "mechanism", panel).textContent =
      `${S.kernel.mechanism} · ${BP.RNG_ID}`;

    const playback = el("section", "group", panel);
    el("h2", "", playback).textContent = "PLAYBACK";
    const transport = el("div", "transport", playback);
    const playButton = el("button", "", transport);
    playButton.textContent = "play";
    playButton.addEventListener("click", () => {
      S.playing = !S.playing;
      playButton.textContent = S.playing ? "pause" : "play";
    });
    const stepButton = el("button", "", transport);
    stepButton.textContent = "step";
    stepButton.addEventListener("click", () => {
      S.playing = false;
      playButton.textContent = "play";
      displayFrame();
    });
    const resetButton = el("button", "", transport);
    resetButton.textContent = "reset";
    resetButton.addEventListener("click", () => reset());
    S.controls.readout = el("div", "readout", playback);
    updateReadout();
    const spfRow = el("label", "row", playback);
    el("span", "row-label", spfRow).textContent = "steps / frame";
    const spf = el("input", "", spfRow);
    spf.type = "number";
    spf.min = 1;
    spf.max = 32;
    spf.step = 1;
    spf.value = String(S.stepsPerFrame);
    spf.addEventListener("change", () => {
      const value = Math.round(Number(spf.value));
      if (value >= 1 && value <= 32) S.stepsPerFrame = value;
    });
    S.controls.spf = spf;

    const identity = el("section", "group", panel);
    el("h2", "", identity).textContent = "BEHAVIOR / IDENTITY";
    const seedRow = el("label", "row", identity);
    el("span", "row-label", seedRow).textContent = "seed";
    const seed = el("input", "", seedRow);
    seed.type = "number";
    seed.min = 0;
    seed.step = 1;
    seed.value = String(S.params.seed);
    seed.addEventListener("change", () => {
      const value = Math.round(Number(seed.value));
      if (value >= 0) {
        S.params.seed = value >>> 0;
        identityChanged();
      }
    });
    S.controls.seed = seed;
    const newSeed = el("button", "row-button", identity);
    newSeed.textContent = "new seed";
    newSeed.addEventListener("click", () => {
      const buffer = new Uint32Array(1);
      root.crypto.getRandomValues(buffer);
      S.params.seed = buffer[0] >>> 0;
      seed.value = String(S.params.seed);
      identityChanged();
    });
    for (const entry of S.kernel.schema) {
      if (entry.key === "seed" || entry.identity === false) continue;
      controlRow(identity, entry);
    }

    const display = el("section", "group", panel);
    el("h2", "", display).textContent = "DISPLAY ONLY";
    for (const entry of S.kernel.schema) {
      if (entry.identity === false) controlRow(display, entry);
    }

    const preset = el("section", "group", panel);
    el("h2", "", preset).textContent = "PRESET";
    const titleRow = el("label", "row", preset);
    el("span", "row-label", titleRow).textContent = "title";
    const title = el("input", "", titleRow);
    title.type = "text";
    title.maxLength = 200;
    title.value = "Candidate";
    const noteRow = el("label", "row", preset);
    el("span", "row-label", noteRow).textContent = "note";
    const note = el("input", "", noteRow);
    note.type = "text";
    note.maxLength = 4000;
    const exportButton = el("button", "row-button", preset);
    exportButton.id = "exportPreset";
    exportButton.textContent = "export preset";
    exportButton.addEventListener("click", () => {
      const record = BP.buildPreset({ title: title.value, note: note.value });
      const blob = new Blob([JSON.stringify(record, null, 2) + "\n"], { type: "application/json" });
      const anchor = document.createElement("a");
      anchor.href = URL.createObjectURL(blob);
      const slug = record.title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "preset";
      anchor.download = `${S.kernel.id}-${slug}.preset.json`;
      anchor.click();
      URL.revokeObjectURL(anchor.href);
    });
    const importInput = el("input", "hidden-input", preset);
    importInput.type = "file";
    importInput.accept = "application/json";
    importInput.id = "importPreset";
    importInput.addEventListener("change", () => {
      const file = importInput.files && importInput.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => BP.applyPreset(JSON.parse(String(reader.result)));
      reader.readAsText(file);
    });
    const importButton = el("button", "row-button", preset);
    importButton.textContent = "import preset";
    importButton.addEventListener("click", () => importInput.click());
    return panel;
  }

  function boot() {
    const rootEl = document.getElementById("playground");
    const q = query();
    buildPanel(rootEl);
    const stage = el("main", "stage", rootEl);
    const canvas = el("canvas", "", stage);
    const forcedSize = q.has("size") ? Number(q.get("size")) : null;
    const fluid = S.kernel.fluidView === true && forcedSize === null;
    if (fluid) {
      rootEl.classList.add("playground-fluid");
      stage.classList.add("stage-fluid");
    }
    const dimensions = fluid
      ? BP.computeViewDimensions(stage.clientWidth, stage.clientHeight, null)
      : BP.computeViewDimensions(900, 900, forcedSize || 900);
    S.view = makeView(canvas, dimensions.width, dimensions.height);

    const encoded = q.get("p");
    if (encoded) {
      BP.applyPreset(JSON.parse(base64UrlDecode(encoded)));
    } else {
      reset();
    }
    const frame = Number(q.get("frame"));
    if (Number.isInteger(frame) && frame > 0) {
      runTo(frame);
    } else if (q.get("autoplay") !== "0" && !encoded) {
      S.playing = true;
    }
    const play = document.querySelector(".transport button");
    if (play && S.playing) play.textContent = "pause";
    if (fluid && typeof root.ResizeObserver === "function") {
      const observer = new root.ResizeObserver(() => {
        BP.resizeView(stage.clientWidth, stage.clientHeight);
      });
      observer.observe(stage);
    }
    root.requestAnimationFrame(loop);
  }

  if (typeof module === "object" && module.exports) module.exports = BP;
})(typeof globalThis !== "undefined" ? globalThis : this);
