// Headless single-frame capture: apply (study, config) from capture-input.js
// (fallback: SAMPLE_STUDY + defaults), wait for the configured fonts, draw one
// deterministic overlay frame on a transparent canvas, and stop. Rendering is
// the same pure drawOverlay() the preview uses, so captures are pixel-identical
// to what KC saw. Config semantics (defaults, deep-merge, TYPE application)
// mirror app.js — keep the two in sync when config shape changes.
(function () {
  "use strict";

  const PRESETS = {
    "9:16 | 1080x1920": [1080, 1920],
    "4:5 | 1080x1350": [1080, 1350],
    "1:1 | 1080x1080": [1080, 1080],
    "16:9 | 1920x1080": [1920, 1080],
  };
  const DEFAULT_ASPECT = "9:16 | 1080x1920";
  const LEGACY_ASPECTS = {
    "9:16 \u2014 1080\u00d71920": "9:16 | 1080x1920",
    "4:5 \u2014 1080\u00d71350": "4:5 | 1080x1350",
    "1:1 \u2014 1080\u00d71080": "1:1 | 1080x1080",
    "16:9 \u2014 1920\u00d71080": "16:9 | 1920x1080",
  };
  const FONT_FALLBACK = {
    numeral: '"Consolas",monospace',
    display: '"Arial",sans-serif',
    mini: '"Consolas",monospace',
    micro: '"Consolas",monospace',
  };

  const OV = window.OVERLAY;
  const input = window.CAPTURE_INPUT || {};
  const study = input.study || window.SAMPLE_STUDY;

  function defaultConfig() {
    return {
      studyId: study.id,
      aspect: DEFAULT_ASPECT,
      palette: Object.keys(OV.PALETTES)[0],
      type: {
        numeral: "Isonorm Monospaced", numeralSize: 110, numeralTracking: -0.085,
        display: "Blender Pro Bold", titleSize: 21, titleTracking: 0.14,
        mini: "Iosevka Mono Light", miniSize: 8.5, miniTracking: 0.08, miniLineHeight: 12,
        miniMarginSide: 0, miniMarginTop: 0,
        micro: "Iosevka Mono Light", microSize: 8.5, microTracking: 0.08,
      },
      components: OV.defaultComponents(),
    };
  }
  function merge(base, over) {
    if (!over || typeof over !== "object") return base;
    for (const k of Object.keys(over)) {
      if (base[k] && typeof base[k] === "object" && !Array.isArray(base[k]) &&
          over[k] && typeof over[k] === "object" && !Array.isArray(over[k])) {
        merge(base[k], over[k]);
      } else if (over[k] !== undefined) {
        base[k] = over[k];
      }
    }
    return base;
  }

  const CONFIG = merge(defaultConfig(), input.config || null);
  CONFIG.aspect = LEGACY_ASPECTS[CONFIG.aspect] || CONFIG.aspect;
  const q = new URLSearchParams(window.location.search);
  const frame = Math.max(0, Number(q.get("frame")) | 0);
  const preset = PRESETS[CONFIG.aspect] || PRESETS[DEFAULT_ASPECT];
  const W = Number(q.get("w")) || preset[0];
  const H = Number(q.get("h")) || preset[1];

  const families = [];
  for (const slot of ["numeral", "display", "mini", "micro"]) {
    const fam = CONFIG.type[slot];
    OV.TYPE[slot] = '"' + fam + '",' + FONT_FALLBACK[slot];
    families.push(fam);
  }
  for (const key of [
    "numeralSize", "numeralTracking", "titleSize", "titleTracking",
    "miniSize", "miniTracking", "miniLineHeight", "miniMarginSide", "miniMarginTop",
    "microSize", "microTracking",
  ]) {
    if (CONFIG.type[key] !== undefined) OV.TYPE[key] = CONFIG.type[key];
  }

  const canvas = document.getElementById("stage");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d");

  function draw() {
    ctx.clearRect(0, 0, W, H);
    OV.drawOverlay(ctx, W, H, study, {
      frame,
      palette: CONFIG.palette,
      components: CONFIG.components,
    });
    document.title = "capture:done:" + frame;
  }

  Promise.all(families.map((fam) => document.fonts.load('20px "' + fam + '"').catch(() => {})))
    .then(() => document.fonts.ready)
    .then(draw, draw);
})();
