// Overlay core: palettes, type, layout math, shared draw helpers, and the
// component registry. Components register themselves from components.js;
// drawOverlay() iterates the registry in order, skipping disabled ones.
// Rendering stays a pure function of (size, study, frame, config) — no wall
// clocks, no unseeded randomness — so preview and headless output match.
(function () {
  "use strict";

  // ---------------------------------------------------------------- palettes
  const PALETTES = {
    "bone / signal red": {
      ink: "rgba(234,232,226,0.95)", faint: "rgba(234,232,226,0.42)",
      ghost: "rgba(234,232,226,0.16)", accent: "#e8442e",
    },
    "bone / sage": {
      ink: "rgba(234,232,226,0.95)", faint: "rgba(234,232,226,0.42)",
      ghost: "rgba(234,232,226,0.16)", accent: "#8fb5a5",
    },
    "bone / signal yellow": {
      ink: "rgba(234,232,226,0.95)", faint: "rgba(234,232,226,0.42)",
      ghost: "rgba(234,232,226,0.16)", accent: "#f5d327",
    },
    "graphite / signal red": {
      ink: "rgba(26,26,28,0.92)", faint: "rgba(26,26,28,0.42)",
      ghost: "rgba(26,26,28,0.15)", accent: "#e8442e",
    },
    "graphite / cobalt": {
      ink: "rgba(26,26,28,0.92)", faint: "rgba(26,26,28,0.42)",
      ghost: "rgba(26,26,28,0.15)", accent: "#3057d5",
    },
  };

  // Four typographic voices. Sizes in u-units (u = min(W,H)/1000);
  // tracking in em. Mutated by the panel, persisted in the study config.
  // "mini" is the general small-text voice (most components' labels/tables);
  // "micro" is a separate voice reserved for footer + tag, defaulted to the
  // same values so nothing shifts until either is edited independently.
  const TYPE = {
    mini: '"Iosevka Mono Light","Consolas",monospace',
    miniSize: 8.5,
    miniTracking: 0.08,
    miniLineHeight: 12,
    miniMarginSide: 0,
    miniMarginTop: 0,
    micro: '"Iosevka Mono Light","Consolas",monospace',
    microSize: 8.5,
    microTracking: 0.08,
    display: '"Blender Pro Bold","Arial Black","Arial",sans-serif',
    titleSize: 21,
    titleTracking: 0.14,
    numeral: '"Isonorm Monospaced","Consolas",monospace',
    numeralSize: 110,
    numeralTracking: -0.085,
  };
  const MINI_BASE = 8.5; // reference size the per-element mini sizes assume
  const MICRO_BASE = 8.5; // reference size the per-element micro sizes assume

  // ----------------------------------------------------------------- helpers
  function hash32(str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }
  // Stateless seeded value in 0..1 for a (seed, a, b) tuple.
  function sval(seed, a, b) {
    let h = (seed ^ Math.imul(a | 0, 0x9e3779b1) ^ Math.imul((b | 0) + 1, 0x85ebca6b)) >>> 0;
    h = Math.imul(h ^ (h >>> 16), 0x45d9f3b) >>> 0;
    h = Math.imul(h ^ (h >>> 16), 0x45d9f3b) >>> 0;
    return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
  }
  // Finest even subdivision of a grid cell that's still >= minStep — lets a
  // component space repeated elements (dots, marks) so every one of them
  // lands on an exact fraction of a grid cell, however far it extends.
  function gridStep(cellSize, minStep) {
    const n = Math.max(1, Math.floor(cellSize / Math.max(1e-6, minStep)));
    return cellSize / n;
  }
  function pad(n, w) { return String(n).padStart(w, "0"); }
  function timecode(frame, fps) {
    const s = frame / fps;
    return pad(Math.floor(s / 60), 2) + ":" + pad(Math.floor(s % 60), 2) + "." + pad(Math.floor((s % 1) * 100), 2);
  }

  function makeLayout(W, H) {
    const mn = Math.min(W, H);
    return { W, H, u: mn / 1000, m: Math.round(mn * 0.055) };
  }

  // Shared placement grid, evenly dividing the margin box into cols x rows.
  // Attached as L.grid so any component can snap to the same lines the
  // visible "grid" component draws — L.grid.x(i)/y(j) for i in 0..cols,
  // j in 0..rows (inclusive), L.grid.cw/rh for cell size. When square is
  // true, cw/rh are forced equal (the denser requested axis wins), cols/rows
  // are recomputed from that cell size, and any leftover space from that
  // rounding is split evenly on both sides of whichever axis has it (so the
  // grid stays centered in the margin box instead of hugging top/left).
  function makeGrid(L, cols, rows, square) {
    const { W, H, m } = L;
    let cw = (W - 2 * m) / Math.max(1, cols), rh = (H - 2 * m) / Math.max(1, rows);
    let effCols = cols, effRows = rows, ox = 0, oy = 0;
    if (square) {
      const s = Math.min(cw, rh);
      cw = s; rh = s;
      effCols = Math.floor((W - 2 * m) / s);
      effRows = Math.floor((H - 2 * m) / s);
      ox = ((W - 2 * m) - effCols * s) / 2;
      oy = ((H - 2 * m) - effRows * s) / 2;
    }
    return {
      cols: effCols, rows: effRows, cw, rh,
      x: (i) => m + ox + i * cw, y: (j) => m + oy + j * rh,
    };
  }

  // General small-text voice: used by every component except footer/tag.
  function miniFont(ctx, size, weight) {
    // Whole-pixel size: fractional sizes force the rasterizer to blend edges
    // instead of landing on pixel boundaries, which reads as blur — worst on
    // the bitmap/pixel fonts (kroeger, schoenecker), visible on all of them.
    const s = Math.round(size * (TYPE.miniSize / MINI_BASE));
    ctx.font = (weight || 400) + " " + s + "px " + TYPE.mini;
    try { ctx.letterSpacing = (s * TYPE.miniTracking).toFixed(2) + "px"; } catch (e) { /* older browsers */ }
  }

  function drawMiniBlock(ctx, L, P, x, y, lines, align) {
    const { u } = L, lh = TYPE.miniLineHeight * u * (TYPE.miniSize / MINI_BASE);
    const ox = x + TYPE.miniMarginSide * u, oy = y + TYPE.miniMarginTop * u;
    miniFont(ctx, 8.5 * u);
    ctx.textAlign = align || "left"; ctx.textBaseline = "top";
    for (let i = 0; i < lines.length; i++) {
      ctx.fillStyle = lines[i].accent ? P.accent : (lines[i].dim ? P.faint : P.ink);
      ctx.fillText(lines[i].t !== undefined ? lines[i].t : lines[i], ox, oy + i * lh);
    }
    return oy + lines.length * lh;
  }

  // Word-wrap for the mini voice: set the font first (h.miniFont), then wrap
  // text to maxWidth px. Pure measurement — no drawing, no state.
  function wrapMini(ctx, text, maxWidth) {
    const words = String(text || "").split(/\s+/).filter(Boolean);
    const lines = [];
    let line = "";
    for (const word of words) {
      const candidate = line ? line + " " + word : word;
      if (line && ctx.measureText(candidate).width > maxWidth) {
        lines.push(line);
        line = word;
      } else {
        line = candidate;
      }
    }
    if (line) lines.push(line);
    return lines;
  }

  // Separate voice reserved for footer + tag only.
  function microFont(ctx, size, weight) {
    const s = Math.round(size * (TYPE.microSize / MICRO_BASE));
    ctx.font = (weight || 400) + " " + s + "px " + TYPE.micro;
    try { ctx.letterSpacing = (s * TYPE.microTracking).toFixed(2) + "px"; } catch (e) { /* older browsers */ }
  }

  // Average the bbox track: the study block goes in the vertical half the
  // subject occupies least.
  function studyBlockAnchor(study) {
    let cy = 0;
    const bb = study.bbox || [];
    if (!bb.length) return "bottom";
    for (const b of bb) cy += (b[1] + b[3]) / 2;
    cy /= bb.length;
    return cy < 0.5 ? "bottom" : "top";
  }

  // Vertical extent of the study block — shared so other components (ruler)
  // can avoid it.
  function studyBlockSpan(L, anchor) {
    const { H, u, m } = L;
    const numSize = TYPE.numeralSize * u, titleSize = TYPE.titleSize * u;
    const blockH = numSize * 0.78 + titleSize + 46 * u;
    const y = anchor === "top" ? m + 78 * u : H - m - blockH - 34 * u;
    return [y - 14 * u, y + blockH + 14 * u];
  }

  // ---------------------------------------------------------------- registry
  // Component: { id, label, defaults, schema, draw(env) }.
  // env = { ctx, L, P, study, frame, p, shared, T, h } where p is the merged
  // param object and shared carries cross-component layout state.
  const registry = [];
  function registerComponent(def) { registry.push(def); }

  function defaultComponents() {
    const out = {};
    for (const c of registry) out[c.id] = Object.assign({ enabled: true }, c.defaults);
    return out;
  }

  const helpers = {
    hash32, sval, pad, timecode, miniFont, drawMiniBlock, microFont,
    studyBlockAnchor, studyBlockSpan, gridStep, wrapMini,
  };

  // -------------------------------------------------------------- entrypoint
  function drawOverlay(ctx, W, H, study, opts) {
    const frame = opts.frame | 0;
    const P = (typeof opts.palette === "string" ? PALETTES[opts.palette] : opts.palette) ||
      PALETTES[Object.keys(PALETTES)[0]];
    const L = makeLayout(W, H);
    const comps = opts.components || {};
    const shared = { seed: hash32(study.id) };

    // Pre-resolve grid/layout params first — margin affects every anchor
    // below, so this must run before studyBlock or the main draw loop.
    // Read regardless of whether the guide itself is visible, so every
    // component can snap to L.grid and use the shared L.m even with the
    // grid component's own drawing hidden.
    const gdc = registry.find((c) => c.id === "grid");
    const gp = Object.assign(
      { enabled: false, cols: 12, rows: 16, marginPct: 5.5, square: false },
      gdc && gdc.defaults, comps.grid);
    L.m = Math.round(Math.min(L.W, L.H) * (gp.marginPct / 100));
    L.grid = makeGrid(L, gp.cols, gp.rows, gp.square);

    // Pre-resolve study block placement so earlier-drawn components can
    // react to it (ruler tick avoidance, etc.).
    const sbc = registry.find((c) => c.id === "studyBlock");
    if (sbc) {
      const sp = Object.assign({ enabled: true }, sbc.defaults, comps.studyBlock);
      if (sp.enabled) {
        shared.anchor = sp.anchor === "auto" ? studyBlockAnchor(study) : sp.anchor;
        shared.studySpan = studyBlockSpan(L, shared.anchor);
      }
    }

    ctx.save();
    for (const c of registry) {
      const p = Object.assign({ enabled: true }, c.defaults, comps[c.id]);
      if (!p.enabled) continue;
      c.draw({ ctx, L, P, study, frame, p, shared, T: TYPE, h: helpers });
    }
    ctx.restore();
  }

  window.OVERLAY = {
    drawOverlay, PALETTES, TYPE,
    registerComponent, registry, defaultComponents, helpers,
  };
})();
