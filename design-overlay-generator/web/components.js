// Overlay components. Each registers with the core (overlay.js) and declares
// its own params + schema; the panel UI is generated from these schemas.
// Registration order = draw order.
//
// schema entry types: "number" {min,max,step}, "bool", "select" {options},
// "series" (select over study.series keys), "text".
(function () {
  "use strict";
  const R = window.OVERLAY.registerComponent;

  // ------------------------------------------------------------------- frame
  R({
    id: "frame",
    label: "frame marks",
    defaults: {
      bracketLen: 16, gap: 0, flip: false,
      regTopBottom: true, regTopBottomSize: 6,
      regLeftRight: true, regLeftRightSize: 6,
      colorBar: false,
    },
    schema: [
      { key: "bracketLen", label: "bracket length", type: "number", min: 0, max: 60, step: 1 },
      { key: "gap", label: "corner gap", type: "number", min: 0, max: 40, step: 1 },
      { key: "flip", label: "flip outward", type: "bool" },
      { key: "regTopBottom", label: "registration top/bottom", type: "bool" },
      { key: "regTopBottomSize", label: "registration top/bottom size", type: "number", min: 1, max: 60, step: 1 },
      { key: "regLeftRight", label: "registration left/right", type: "bool" },
      { key: "regLeftRightSize", label: "registration left/right size", type: "number", min: 1, max: 60, step: 1 },
      { key: "colorBar", label: "color bar", type: "bool" },
    ],
    draw({ ctx, L, P, p }) {
      const { W, H, u, m } = L, len = p.bracketLen * u, gap = p.gap * u, dir = p.flip ? -1 : 1;
      ctx.strokeStyle = P.ink; ctx.lineWidth = Math.max(1, u);
      for (const [x, y, sx0, sy0] of [[m, m, 1, 1], [W - m, m, -1, 1], [m, H - m, 1, -1], [W - m, H - m, -1, -1]]) {
        const sx = sx0 * dir, sy = sy0 * dir;
        ctx.beginPath();
        ctx.moveTo(x + sx * (gap + len), y); ctx.lineTo(x + sx * gap, y);
        ctx.moveTo(x, y + sy * gap); ctx.lineTo(x, y + sy * (gap + len));
        ctx.stroke();
      }
      {
        // print-sheet style: a crosshair target at each edge midpoint.
        ctx.strokeStyle = P.faint;
        if (p.regTopBottom) {
          const cl = p.regTopBottomSize * u;
          for (const y of [m, H - m]) {
            ctx.beginPath();
            ctx.moveTo(W / 2 - cl, y); ctx.lineTo(W / 2 + cl, y);
            ctx.moveTo(W / 2, y - cl); ctx.lineTo(W / 2, y + cl);
            ctx.stroke();
          }
        }
        if (p.regLeftRight) {
          const cl = p.regLeftRightSize * u;
          for (const x of [m, W - m]) {
            ctx.beginPath();
            ctx.moveTo(x - cl, H / 2); ctx.lineTo(x + cl, H / 2);
            ctx.moveTo(x, H / 2 - cl); ctx.lineTo(x, H / 2 + cl);
            ctx.stroke();
          }
        }
      }
      if (p.colorBar) {
        // print-production color/density bar: a row of the palette's own tones.
        const sw = 7 * u, sh = 7 * u;
        const swatches = P.chips || [P.ink, P.faint, P.ghost, P.accent];
        const totalW = swatches.length * sw;
        const bx = W / 2 - totalW / 2, by = H - m + 10 * u;
        for (let i = 0; i < swatches.length; i++) {
          ctx.fillStyle = swatches[i];
          ctx.fillRect(bx + i * sw, by, sw, sh);
        }
      }
    },
  });

  // ------------------------------------------------------------------- ruler
  R({
    id: "ruler",
    label: "edge ruler",
    defaults: { divisions: 4, tickLen: 10, labels: true, avoidStudy: true, mirror: false, opacity: 1 },
    schema: [
      { key: "divisions", label: "divisions per grid row", type: "number", min: 1, max: 10, step: 1 },
      { key: "tickLen", label: "tick length", type: "number", min: 4, max: 30, step: 1 },
      { key: "labels", label: "labels", type: "bool" },
      { key: "avoidStudy", label: "avoid study block", type: "bool" },
      { key: "mirror", label: "mirror to right edge", type: "bool" },
      { key: "opacity", label: "opacity", type: "number", min: 0, max: 1, step: 0.05 },
    ],
    // Every tick — major and minor — is a position on the shared placement
    // grid (L.grid): majors sit exactly on grid row lines, minors evenly
    // subdivide each grid cell by `divisions`. Density is configurable here
    // without breaking grid alignment. Optionally mirrored to the right
    // edge, ticks facing inward and labels sitting to the left of them.
    draw({ ctx, L, P, p, shared, h }) {
      const { u, m, W } = L, g = L.grid, div = Math.max(1, p.divisions | 0);
      const skip = p.avoidStudy ? shared.studySpan : null;
      const majorLen = p.tickLen * u, minorLen = majorLen * 0.5, labelOff = 13 * u;
      ctx.save();
      ctx.globalAlpha = p.opacity;
      ctx.strokeStyle = P.faint; ctx.fillStyle = P.faint;
      ctx.lineWidth = Math.max(1, u);
      h.miniFont(ctx, 8 * u);
      ctx.textBaseline = "middle";

      const drawSide = (x0, dir, align) => {
        ctx.textAlign = align;
        const tick = (y, major) => {
          if (y <= L.m || y >= L.H - L.m) return;
          if (skip && y > skip[0] && y < skip[1]) return;
          const len = major ? majorLen : minorLen;
          ctx.beginPath();
          ctx.moveTo(x0, y); ctx.lineTo(x0 + dir * len, y);
          ctx.stroke();
          if (major && p.labels) ctx.fillText(h.pad(Math.round(y / u), 3), x0 + dir * labelOff, y);
        };
        for (let j = 0; j < g.rows; j++) {
          for (let k = 0; k < div; k++) tick(g.y(j) + (k / div) * g.rh, k === 0);
        }
        tick(g.y(g.rows), true);
      };

      drawSide(m, 1, "left");
      if (p.mirror) drawSide(W - m, -1, "right");
      ctx.restore();
    },
  });

  // -------------------------------------------------------------------- bbox
  R({
    id: "bbox",
    label: "subject tracking",
    defaults: { brackets: true, bracketLen: 12, gap: 0, flip: false, coords: true, scanline: true },
    schema: [
      { key: "brackets", label: "corner brackets", type: "bool" },
      { key: "bracketLen", label: "bracket length", type: "number", min: 0, max: 60, step: 1 },
      { key: "gap", label: "corner gap", type: "number", min: 0, max: 40, step: 1 },
      { key: "flip", label: "flip outward", type: "bool" },
      { key: "coords", label: "coords readout", type: "bool" },
      { key: "scanline", label: "accent scanline", type: "bool" },
    ],
    draw({ ctx, L, P, study, frame, p, h }) {
      const bb = study.bbox && study.bbox[frame % (study.bbox.length || 1)];
      if (!bb) return;
      const { W, H, u, m } = L;
      const x0 = bb[0] * W, y0 = bb[1] * H, x1 = bb[2] * W, y1 = bb[3] * H;
      ctx.lineWidth = Math.max(1, u);
      if (p.brackets) {
        const len = p.bracketLen * u, gap = p.gap * u, dir = p.flip ? -1 : 1;
        ctx.strokeStyle = P.faint;
        for (const [x, y, sx0, sy0] of [[x0, y0, 1, 1], [x1, y0, -1, 1], [x0, y1, 1, -1], [x1, y1, -1, -1]]) {
          const sx = sx0 * dir, sy = sy0 * dir;
          ctx.beginPath();
          ctx.moveTo(x + sx * (gap + len), y); ctx.lineTo(x + sx * gap, y);
          ctx.moveTo(x, y + sy * gap); ctx.lineTo(x, y + sy * (gap + len));
          ctx.stroke();
        }
      }
      if (p.coords) {
        h.miniFont(ctx, 8 * u);
        ctx.fillStyle = P.faint; ctx.textAlign = "left"; ctx.textBaseline = "bottom";
        ctx.fillText("X " + bb[0].toFixed(3) + "  Y " + bb[1].toFixed(3), x0, y0 - 5 * u);
      }
      if (p.scanline) {
        const cy = (y0 + y1) / 2;
        ctx.strokeStyle = P.ghost;
        ctx.beginPath(); ctx.moveTo(m, cy); ctx.lineTo(W - m, cy); ctx.stroke();
        ctx.strokeStyle = P.accent;
        ctx.beginPath(); ctx.moveTo(m, cy); ctx.lineTo(x0 - 6 * u, cy); ctx.stroke();
        ctx.fillStyle = P.accent;
        ctx.fillRect(m, cy - 2 * u, 7 * u, 4 * u);
      }
    },
  });

  // ------------------------------------------------------------ trackCallout
  // Screen-space callouts that follow exported point tracks (study.tracks):
  // a marker at the tracked point, a hairline leader to a micro label, and an
  // optional sparkline of one of the track's value series. Tracks with a null
  // screen entry (offscreen / behind camera) draw nothing that frame.
  const TRACK_CALLOUT_ITEM_DEFAULTS = {
    track: "", dx: 52, dy: -44, marker: "crosshair", markerSize: 7,
    label: true, value: "", spark: true, sparkFrames: 64, trail: 0, accent: true,
  };
  R({
    id: "trackCallout",
    label: "point callouts",
    defaults: { instances: [Object.assign({}, TRACK_CALLOUT_ITEM_DEFAULTS)] },
    schema: [
      {
        key: "instances", label: "callouts", type: "list", min: 1,
        itemDefaults: TRACK_CALLOUT_ITEM_DEFAULTS,
        itemSchema: [
          { key: "track", label: "track", type: "track" },
          { key: "dx", label: "label offset x", type: "number", min: -200, max: 200, step: 2 },
          { key: "dy", label: "label offset y", type: "number", min: -200, max: 200, step: 2 },
          { key: "marker", label: "marker", type: "select", options: ["crosshair", "ring", "dot"] },
          { key: "markerSize", label: "marker size", type: "number", min: 2, max: 30, step: 1 },
          { key: "label", label: "label", type: "bool" },
          { key: "value", label: "value series (blank = first)", type: "text" },
          { key: "spark", label: "sparkline", type: "bool" },
          { key: "sparkFrames", label: "spark window (fr)", type: "number", min: 8, max: 240, step: 4 },
          { key: "trail", label: "trail (fr, 0 = off)", type: "number", min: 0, max: 240, step: 4 },
          { key: "accent", label: "accent marker", type: "bool" },
        ],
      },
    ],
    draw({ ctx, L, P, study, frame, p, h }) {
      const all = study.tracks || {};
      const names = Object.keys(all);
      if (!names.length) return;
      const { W, H, u } = L;
      const instances = (p.instances && p.instances.length ? p.instances : [TRACK_CALLOUT_ITEM_DEFAULTS])
        .map((inst) => Object.assign({}, TRACK_CALLOUT_ITEM_DEFAULTS, inst));
      ctx.lineWidth = Math.max(1, u);
      for (const inst of instances) {
        const name = all[inst.track] ? inst.track : names[0];
        const track = all[name];
        const n = track.screen.length || 1;
        const pos = track.screen[frame % n];
        if (!pos) continue;
        const x = pos[0] * W, y = pos[1] * H;
        const r = inst.markerSize * u;
        const markerColor = inst.accent ? P.accent : P.ink;

        if (inst.trail > 0) {
          ctx.strokeStyle = P.ghost;
          ctx.beginPath();
          let started = false;
          for (let back = Math.min(inst.trail, frame); back >= 0; back--) {
            const past = track.screen[(frame - back) % n];
            if (!past) { started = false; continue; }
            const px = past[0] * W, py = past[1] * H;
            if (started) ctx.lineTo(px, py); else ctx.moveTo(px, py);
            started = true;
          }
          ctx.stroke();
        }

        ctx.strokeStyle = markerColor;
        if (inst.marker === "dot") {
          ctx.fillStyle = markerColor;
          ctx.beginPath(); ctx.arc(x, y, Math.max(1.5 * u, r * 0.3), 0, Math.PI * 2); ctx.fill();
        } else if (inst.marker === "ring") {
          ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke();
        } else {
          ctx.beginPath();
          ctx.moveTo(x - r, y); ctx.lineTo(x - r * 0.35, y);
          ctx.moveTo(x + r * 0.35, y); ctx.lineTo(x + r, y);
          ctx.moveTo(x, y - r); ctx.lineTo(x, y - r * 0.35);
          ctx.moveTo(x, y + r * 0.35); ctx.lineTo(x, y + r);
          ctx.stroke();
        }

        const lx = x + inst.dx * u, ly = y + inst.dy * u;
        const rightward = inst.dx >= 0;
        if (inst.label || inst.spark) {
          ctx.strokeStyle = P.faint;
          ctx.beginPath();
          ctx.moveTo(x + Math.sign(inst.dx || 1) * r, y - (inst.dy < 0 ? r * 0.0 : 0));
          ctx.lineTo(lx, ly);
          ctx.lineTo(lx + (rightward ? 26 : -26) * u, ly);
          ctx.stroke();
        }

        const valueNames = Object.keys(track.values || {});
        const valueName = (track.values || {})[inst.value] ? inst.value : valueNames[0];
        const values = valueName ? track.values[valueName] : null;
        const current = values ? values[frame % values.length] : null;

        if (inst.label) {
          h.miniFont(ctx, 8 * u);
          ctx.textAlign = rightward ? "left" : "right";
          ctx.textBaseline = "bottom";
          ctx.fillStyle = P.ink;
          const readout = name.toUpperCase() +
            (current !== null && current !== undefined ? "  " + current.toFixed(3) : "");
          ctx.fillText(readout, lx + (rightward ? 2 : -2) * u, ly - 3 * u);
        }

        if (inst.spark && values) {
          const sw = 26 * u, sh = 10 * u;
          const sx = lx + (rightward ? 2 * u : -2 * u - sw), sy = ly + 4 * u;
          const window_ = Math.max(8, inst.sparkFrames | 0);
          ctx.strokeStyle = P.faint;
          ctx.beginPath();
          let started = false;
          for (let i = 0; i < window_; i++) {
            const f = frame - (window_ - 1 - i);
            const v = f >= 0 ? values[f % values.length] : null;
            if (v === null || v === undefined) { started = false; continue; }
            const px = sx + (i / (window_ - 1)) * sw, py = sy + sh - v * sh;
            if (started) ctx.lineTo(px, py); else ctx.moveTo(px, py);
            started = true;
          }
          ctx.stroke();
          if (current !== null && current !== undefined) {
            ctx.fillStyle = markerColor;
            ctx.fillRect(sx + sw - 1.5 * u, sy + sh - current * sh - 1.5 * u, 3 * u, 3 * u);
          }
        }
      }
    },
  });

  // ---------------------------------------------------------------- identity
  R({
    id: "identity",
    label: "identity cluster",
    defaults: { showSolver: true, showSeed: true },
    schema: [
      { key: "showSolver", label: "solver line", type: "bool" },
      { key: "showSeed", label: "seed line", type: "bool" },
    ],
    draw({ ctx, L, P, study, p, h }) {
      const { u, m } = L;
      const lines = [
        { t: study.id },
        { t: "HOUDINI-AI // FIELD STUDIES", dim: true },
      ];
      if (p.showSolver) lines.push({ t: "SOLVER " + study.solver.name + "  DT " + study.solver.dt + "  SUB " + study.solver.substeps, dim: true });
      if (p.showSeed) lines.push({ t: "SEED " + study.solver.seed, dim: true });
      h.drawMiniBlock(ctx, L, P, m, m + 6 * u, lines);
    },
  });

  // --------------------------------------------------------------- dotMatrix
  const DOT_MATRIX_ITEM_DEFAULTS = {
    side: "right", gx: 0, gy: 0, cols: 8, rows: 5, epochFrames: 32, density: 0.45,
  };
  R({
    id: "dotMatrix",
    label: "dot matrix",
    defaults: { instances: [Object.assign({}, DOT_MATRIX_ITEM_DEFAULTS)] },
    schema: [
      {
        key: "instances", label: "clusters", type: "list", min: 1,
        itemDefaults: DOT_MATRIX_ITEM_DEFAULTS,
        itemSchema: [
          { key: "side", label: "side", type: "select", options: ["left", "right"] },
          { key: "gx", label: "x (grid col)", type: "number", step: 1 },
          { key: "gy", label: "y (grid row)", type: "number", step: 1 },
          { key: "cols", label: "columns", type: "number", min: 2, max: 100, step: 1 },
          { key: "rows", label: "rows", type: "number", min: 2, max: 100, step: 1 },
          { key: "epochFrames", label: "reshuffle every (fr)", type: "number", min: 1, max: 240, step: 1 },
          { key: "density", label: "density", type: "number", min: 0, max: 1, step: 0.05 },
        ],
      },
    ],
    // Position is grid-snapped: gx/gy are L.grid column/row indices, not raw
    // u-offsets. side flips which grid edge gx counts from and which way the
    // cluster grows — "right" (the default) reproduces the old single
    // top-right cluster exactly: gx=0 anchors flush to the rightmost grid
    // line and grows leftward; "left" anchors from the left and grows right.
    draw({ ctx, L, P, frame, p, shared, h }) {
      const g = L.grid, r = 1.3 * L.u;
      // Dot spacing is the finest even subdivision of a grid cell that
      // still comfortably fits a dot — every dot lands on that submultiple
      // grid line, in both x and y, however far the cluster extends.
      const target = r * 5;
      const gapX = h.gridStep(g.cw, target), gapY = h.gridStep(g.rh, target);
      const instances = (p.instances && p.instances.length ? p.instances : [DOT_MATRIX_ITEM_DEFAULTS])
        .map((inst) => Object.assign({}, DOT_MATRIX_ITEM_DEFAULTS, inst));
      let maxBottom;
      instances.forEach((inst, idx) => {
        const anchorX = inst.side === "right" ? g.x(g.cols - inst.gx) : g.x(inst.gx);
        const originX = inst.side === "right" ? anchorX - (inst.cols - 1) * gapX : anchorX;
        const y = g.y(inst.gy);
        const epoch = Math.floor(frame / Math.max(1, inst.epochFrames));
        for (let i = 0; i < inst.cols; i++) {
          for (let j = 0; j < inst.rows; j++) {
            const on = h.sval(shared.seed, idx * 4013 + i * 97 + j, epoch) < inst.density;
            ctx.fillStyle = on ? P.ink : P.ghost;
            ctx.beginPath();
            ctx.arc(originX + i * gapX, y + j * gapY, r, 0, Math.PI * 2);
            ctx.fill();
          }
        }
        const bottom = y + inst.rows * gapY;
        maxBottom = maxBottom === undefined ? bottom : Math.max(maxBottom, bottom);
      });
      shared.trBottom = maxBottom; // top-right column stacking (dial, etc.)
    },
  });

  // -------------------------------------------------------------------- dial
  R({
    id: "dial",
    label: "series dial",
    defaults: { series: "cohesion", radius: 28, showValue: true },
    schema: [
      { key: "series", label: "series", type: "series" },
      { key: "radius", label: "radius", type: "number", min: 10, max: 80, step: 1 },
      { key: "showValue", label: "value readout", type: "bool" },
    ],
    draw({ ctx, L, P, study, frame, p, shared, h }) {
      const { W, u, m } = L, r = p.radius * u;
      const s = study.series[p.series] || Object.values(study.series)[0] || [0];
      const v = s[frame % s.length];
      const cx = W - m - 30 * u;
      const cy = (shared.trBottom !== undefined ? shared.trBottom : m + 8 * u) + r + 16 * u;
      ctx.lineWidth = Math.max(1, u);
      for (let i = 0; i < 40; i++) {
        const a = (i / 40) * Math.PI * 2 - Math.PI / 2;
        const on = i / 40 <= v;
        const r0 = r - (i % 5 === 0 ? 7 : 4) * u;
        ctx.strokeStyle = on ? P.ink : P.ghost;
        ctx.beginPath();
        ctx.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0);
        ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
        ctx.stroke();
      }
      const na = v * Math.PI * 2 - Math.PI / 2;
      ctx.strokeStyle = P.accent;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(na) * (r - 9 * u), cy + Math.sin(na) * (r - 9 * u));
      ctx.stroke();
      h.miniFont(ctx, 8.5 * u);
      ctx.fillStyle = P.faint; ctx.textAlign = "center"; ctx.textBaseline = "top";
      ctx.fillText(p.series.toUpperCase(), cx, cy + r + 6 * u);
      let bottom = cy + r + 18 * u;
      if (p.showValue) {
        ctx.fillStyle = P.ink;
        ctx.fillText(v.toFixed(3), cx, bottom);
        bottom += 12 * u;
      }
      shared.trBottom = bottom;
    },
  });

  // -------------------------------------------------------------- studyBlock
  R({
    id: "studyBlock",
    label: "study block",
    defaults: {
      anchor: "auto", kicker: true, accent: true, subtitle: true,
      gapTop: 0, kickerMarginSide: 2, gapKickerNumeral: 0, numeralMarginSide: -4,
      gapNumeralAccent: 0, accentMarginSide: 0, accentWidth: 46, gapAccentTitle: 0,
      titleMarginSide: 0, gapTitleSubtitle: 0, variationLine: true,
      variationSize: 11, variationMarginSide: 0, gapVariationSubtitle: 0,
      sourceLine: false, dateLine: true, subtitleMarginSide: 0, subtitleWidth: 240,
    },
    schema: [
      { key: "anchor", label: "anchor", type: "select", options: ["auto", "top", "bottom"] },
      { key: "kicker", label: "kicker label", type: "bool" },
      { key: "accent", label: "accent bar", type: "bool" },
      { key: "subtitle", label: "subtitle lines", type: "bool" },
      { key: "gapTop", label: "gap margin (y): top", type: "number", min: -40, max: 60, step: 1 },
      { key: "kickerMarginSide", label: "kicker margin (x)", type: "number", min: -40, max: 40, step: 1 },
      { key: "gapKickerNumeral", label: "gap margin (y): kicker → numeral", type: "number", min: -40, max: 60, step: 1 },
      { key: "numeralMarginSide", label: "numeral margin (x)", type: "number", min: -40, max: 40, step: 1 },
      { key: "gapNumeralAccent", label: "gap margin (y): numeral → accent", type: "number", min: -40, max: 60, step: 1 },
      { key: "accentMarginSide", label: "accent margin (x)", type: "number", min: -40, max: 40, step: 1 },
      { key: "accentWidth", label: "accent width", type: "number", min: 4, max: 200, step: 1 },
      { key: "gapAccentTitle", label: "gap margin (y): accent → title", type: "number", min: -40, max: 60, step: 1 },
      { key: "titleMarginSide", label: "title margin (x)", type: "number", min: -40, max: 40, step: 1 },
      { key: "gapTitleSubtitle", label: "gap margin (y): title → subtitle", type: "number", min: -40, max: 60, step: 1 },
      { key: "variationLine", label: "behavior / variation line", type: "bool" },
      { key: "variationSize", label: "variation size (u)", type: "number", min: 6, max: 40, step: 0.5 },
      { key: "variationMarginSide", label: "variation margin (x)", type: "number", min: -40, max: 40, step: 1 },
      { key: "gapVariationSubtitle", label: "gap margin (y): variation → subtitle", type: "number", min: -40, max: 60, step: 1 },
      { key: "sourceLine", label: "source line", type: "bool" },
      { key: "dateLine", label: "date line", type: "bool" },
      { key: "subtitleMarginSide", label: "subtitle margin (x)", type: "number", min: -40, max: 40, step: 1 },
      { key: "subtitleWidth", label: "subtitle wrap width", type: "number", min: 80, max: 500, step: 5 },
    ],
    // Every line has its own left-margin offset (side of x=m) and every gap
    // between lines is additive on top of the original fixed spacing —
    // defaults reproduce the exact old hardcoded offsets/spacing, so nothing
    // moves until these are touched.
    draw({ ctx, L, P, study, p, shared, T, h }) {
      const { u, m } = L;
      const numSize = T.numeralSize * u, titleSize = T.titleSize * u;
      const anchor = shared.anchor || (p.anchor === "auto" ? h.studyBlockAnchor(study) : p.anchor);
      const x = m;
      let y = h.studyBlockSpan(L, anchor)[0] + 14 * u + p.gapTop * u;

      if (p.kicker) {
        h.miniFont(ctx, 9 * u);
        ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
        ctx.fillStyle = P.faint;
        ctx.fillText("FIELD STUDY", x + p.kickerMarginSide * u, y);
        y += p.gapKickerNumeral * u;
      }

      const numSizePx = Math.round(numSize); // whole pixels: crisper, esp. for pixel fonts
      ctx.font = numSizePx + "px " + T.numeral;
      try { ctx.letterSpacing = (numSizePx * T.numeralTracking).toFixed(2) + "px"; } catch (e) {}
      ctx.fillStyle = P.ink;
      ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
      ctx.fillText(h.pad(study.number, 3), x + p.numeralMarginSide * u, y + numSize * 0.82);
      try { ctx.letterSpacing = "0px"; } catch (e) {}
      y += numSize * 0.92 + p.gapNumeralAccent * u;

      if (p.accent) {
        ctx.fillStyle = P.accent;
        ctx.fillRect(x + p.accentMarginSide * u, y, p.accentWidth * u, 2.5 * u);
      }
      y += 16 * u + p.gapAccentTitle * u;

      const titleSizePx = Math.round(titleSize); // whole pixels: crisper, esp. for pixel fonts
      ctx.font = "700 " + titleSizePx + "px " + T.display;
      try { ctx.letterSpacing = (titleSizePx * T.titleTracking).toFixed(2) + "px"; } catch (e) {}
      ctx.fillStyle = P.ink;
      ctx.fillText(study.title.toUpperCase(), x + p.titleMarginSide * u, y + titleSize);
      try { ctx.letterSpacing = "0px"; } catch (e) {}
      y += titleSize + 12 * u + p.gapTitleSubtitle * u;

      // Three-axis index line: behavior + variation numbers from the study's
      // variation record (absent on the sample study and legacy exports).
      // Display voice like the title, at its own configurable size.
      if (p.variationLine && study.variation &&
          study.variation.behavior_number !== undefined && study.variation.number !== undefined) {
        const idx = "BHVR " + h.pad(study.variation.behavior_number, 3) +
          " / VAR " + h.pad(study.variation.number, 3);
        const varSizePx = Math.round(p.variationSize * u);
        ctx.font = "700 " + varSizePx + "px " + T.display;
        try { ctx.letterSpacing = (varSizePx * T.titleTracking).toFixed(2) + "px"; } catch (e) {}
        ctx.fillStyle = P.ink;
        ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
        ctx.fillText(idx, x + p.variationMarginSide * u, y + p.variationSize * u);
        try { ctx.letterSpacing = "0px"; } catch (e) {}
        y += p.variationSize * u + 12 * u + p.gapVariationSubtitle * u;
      }

      if (p.subtitle) {
        h.miniFont(ctx, 8.5 * u);
        const maxWidth = p.subtitleWidth * u;
        const lines = [
          ...h.wrapMini(ctx, study.subtitle.toUpperCase(), maxWidth),
          // Off by default: a source worth citing (arXiv id) earns the line;
          // exporters that fill source with the study folder name do not.
          ...(p.sourceLine ? h.wrapMini(ctx, "SRC " + study.source, maxWidth) : []),
          ...(p.dateLine && study.date ? [study.date] : []),
        ].map((t) => ({ t, dim: true }));
        h.drawMiniBlock(ctx, L, P, x + p.subtitleMarginSide * u, y, lines);
      }
    },
  });

  // --------------------------------------------------------------- specTable
  R({
    id: "specTable",
    label: "spec table",
    defaults: { width: 215, cycleSec: 3, highlight: true },
    schema: [
      { key: "width", label: "width", type: "number", min: 120, max: 400, step: 5 },
      { key: "cycleSec", label: "highlight cycle (s)", type: "number", min: 0.5, max: 20, step: 0.5 },
      { key: "highlight", label: "row highlight", type: "bool" },
    ],
    draw({ ctx, L, P, study, frame, p, shared, h }) {
      const { W, H, u, m } = L;
      const rows = study.params, rowH = 14 * u, tw = p.width * u;
      const x = W - m - tw, y0 = H - m - rows.length * rowH - 26 * u;
      const hi = Math.floor(frame / (study.fps * p.cycleSec)) % rows.length;

      h.miniFont(ctx, 9 * u);
      ctx.textBaseline = "middle";
      ctx.textAlign = "left";
      ctx.fillStyle = P.faint;
      ctx.fillText("SOLVER PARAMETERS", x, y0 - 10 * u);

      for (let i = 0; i < rows.length; i++) {
        const ry = y0 + i * rowH;
        if (p.highlight && i === hi) {
          ctx.fillStyle = P.ghost;
          ctx.fillRect(x - 6 * u, ry, tw + 12 * u, rowH);
          ctx.fillStyle = P.accent;
          ctx.fillRect(x - 6 * u, ry, 2 * u, rowH);
        }
        h.miniFont(ctx, 9 * u);
        ctx.fillStyle = p.highlight && i === hi ? P.ink : P.faint;
        ctx.textAlign = "left";
        ctx.fillText(rows[i][0], x, ry + rowH / 2);
        ctx.textAlign = "right";
        ctx.fillStyle = P.ink;
        ctx.fillText(rows[i][1], x + tw, ry + rowH / 2);
      }
      shared.tableTop = y0 - 20 * u;
    },
  });

  // -------------------------------------------------------------------- bars
  R({
    id: "bars",
    label: "series bars",
    defaults: { series: "energy", bins: 48, width: 150, height: 34, label: "" },
    schema: [
      { key: "series", label: "series", type: "series" },
      { key: "bins", label: "bins", type: "number", min: 8, max: 120, step: 1 },
      { key: "width", label: "width", type: "number", min: 60, max: 400, step: 5 },
      { key: "height", label: "height", type: "number", min: 10, max: 120, step: 2 },
      { key: "label", label: "label (blank = auto)", type: "text" },
    ],
    draw({ ctx, L, P, study, frame, p, shared, h }) {
      const { W, H, u, m } = L;
      const s = study.series[p.series] || Object.values(study.series)[0] || [0];
      const w = p.width * u, ht = p.height * u, n = Math.max(2, p.bins | 0);
      const x = W - m - w;
      const y = shared.tableTop !== undefined ? shared.tableTop - ht - 18 * u : H - m - ht - 26 * u;
      const bw = w / n;
      for (let i = 0; i < n; i++) {
        const f = frame - (n - 1 - i);
        const v = f >= 0 ? s[f % s.length] : 0;
        const bh = Math.max(1, v * ht);
        ctx.fillStyle = i === n - 1 ? P.accent : P.faint;
        ctx.fillRect(x + i * bw, y + ht - bh, Math.max(1, bw * 0.55), bh);
      }
      ctx.strokeStyle = P.ghost; ctx.lineWidth = Math.max(1, u);
      ctx.strokeRect(x, y, w, ht);
      h.miniFont(ctx, 8 * u);
      ctx.fillStyle = P.faint; ctx.textAlign = "left"; ctx.textBaseline = "bottom";
      ctx.fillText(p.label || p.series.toUpperCase() + " / t", x, y - 4 * u);
    },
  });

  // ------------------------------------------------------------ summaryBlock
  // The study card's long summary as a narrow wrapped micro-type column,
  // grid-snapped like dotMatrix. Hidden when the study has no summary.
  R({
    id: "summaryBlock",
    label: "summary column",
    defaults: { side: "left", gx: 0, gy: 10, widthCols: 3, heading: "FIELD NOTE", rule: true },
    schema: [
      { key: "side", label: "side", type: "select", options: ["left", "right"] },
      { key: "gx", label: "x (grid col)", type: "number", step: 1 },
      { key: "gy", label: "y (grid row)", type: "number", step: 1 },
      { key: "widthCols", label: "width (grid cols)", type: "number", min: 1, max: 8, step: 1 },
      { key: "heading", label: "heading (blank = none)", type: "text" },
      { key: "rule", label: "heading rule", type: "bool" },
    ],
    draw({ ctx, L, P, study, p, T, h }) {
      if (!study.summary) return;
      const { u } = L, g = L.grid;
      const width = p.widthCols * g.cw;
      const x = p.side === "right" ? g.x(g.cols - p.gx) - width : g.x(p.gx);
      let y = g.y(p.gy);
      h.miniFont(ctx, 8.5 * u);
      ctx.textAlign = "left"; ctx.textBaseline = "top";
      const lh = T.miniLineHeight * u * (T.miniSize / 8.5);
      if (p.heading) {
        ctx.fillStyle = P.ink;
        ctx.fillText(p.heading, x, y);
        if (p.rule) {
          ctx.strokeStyle = P.ghost; ctx.lineWidth = Math.max(1, u);
          ctx.beginPath();
          ctx.moveTo(x, y + lh * 0.9); ctx.lineTo(x + width, y + lh * 0.9);
          ctx.stroke();
        }
        y += lh * 1.5;
      }
      ctx.fillStyle = P.faint;
      for (const line of h.wrapMini(ctx, study.summary, width)) {
        ctx.fillText(line, x, y);
        y += lh;
      }
    },
  });

  // ------------------------------------------------------------- bulletBlock
  // Study-card bullets as tick-marked micro lines, grid-snapped. Hidden when
  // the study has no bullets.
  R({
    id: "bulletBlock",
    label: "bullet block",
    defaults: { side: "left", gx: 0, gy: 6, widthCols: 3, tick: "·", accentTicks: true },
    schema: [
      { key: "side", label: "side", type: "select", options: ["left", "right"] },
      { key: "gx", label: "x (grid col)", type: "number", step: 1 },
      { key: "gy", label: "y (grid row)", type: "number", step: 1 },
      { key: "widthCols", label: "width (grid cols)", type: "number", min: 1, max: 8, step: 1 },
      { key: "tick", label: "tick", type: "select", options: ["·", "▸", "+", "-"] },
      { key: "accentTicks", label: "accent ticks", type: "bool" },
    ],
    draw({ ctx, L, P, study, p, T, h }) {
      const bullets = study.bullets || [];
      if (!bullets.length) return;
      const { u } = L, g = L.grid;
      const width = p.widthCols * g.cw;
      const x = p.side === "right" ? g.x(g.cols - p.gx) - width : g.x(p.gx);
      let y = g.y(p.gy);
      h.miniFont(ctx, 8.5 * u);
      ctx.textAlign = "left"; ctx.textBaseline = "top";
      const lh = T.miniLineHeight * u * (T.miniSize / 8.5);
      const indent = 12 * u;
      for (const bullet of bullets) {
        ctx.fillStyle = p.accentTicks ? P.accent : P.faint;
        ctx.fillText(p.tick, x, y);
        ctx.fillStyle = P.ink;
        for (const line of h.wrapMini(ctx, bullet.toUpperCase(), width - indent)) {
          ctx.fillText(line, x + indent, y);
          y += lh;
        }
        y += lh * 0.35;
      }
    },
  });

  // ------------------------------------------------------------------ footer
  R({
    id: "footer",
    label: "frame counter",
    defaults: { blink: true },
    schema: [
      { key: "blink", label: "blink dot", type: "bool" },
    ],
    draw({ ctx, L, P, study, frame, p, h }) {
      const { H, u, m } = L;
      h.microFont(ctx, 9 * u);
      ctx.textAlign = "left"; ctx.textBaseline = "bottom";
      ctx.fillStyle = P.ink;
      ctx.fillText(
        "FR " + h.pad(frame, 4) + "/" + h.pad(study.frames, 4) +
        "   TC " + h.timecode(frame, study.fps) +
        "   " + study.fps + " FPS", m, H - m + 16 * u);
      if (p.blink && frame % study.fps < study.fps / 2) {
        ctx.fillStyle = P.accent;
        ctx.beginPath();
        ctx.arc(m - 8 * u, H - m + 12 * u, 2.4 * u, 0, Math.PI * 2);
        ctx.fill();
      }
    },
  });

  // --------------------------------------------------------------------- tag
  R({
    id: "tag",
    label: "rotated edge tag",
    defaults: { text: "" },
    schema: [
      { key: "text", label: "text (blank = auto)", type: "text" },
    ],
    draw({ ctx, L, P, study, p, h }) {
      const { W, H, u, m } = L;
      const text = p.text || (study.title + " // " + study.solver.name).toUpperCase();
      ctx.save();
      ctx.translate(W - m + 14 * u, H - m);
      ctx.rotate(-Math.PI / 2);
      h.microFont(ctx, 8.5 * u);
      ctx.fillStyle = P.faint; ctx.textAlign = "left"; ctx.textBaseline = "middle";
      ctx.fillText(text, 0, 0);
      ctx.restore();
    },
  });

  // ------------------------------------------------------------- scatterRects
  const SCATTER_RECT_ITEM_DEFAULTS = { gx: 1, gy: 1, width: 1, height: 1, mirror: false };
  R({
    id: "scatterRects",
    label: "detail rects",
    defaults: { opacity: 1, instances: [Object.assign({}, SCATTER_RECT_ITEM_DEFAULTS)] },
    schema: [
      { key: "opacity", label: "opacity", type: "number", min: 0, max: 1, step: 0.05 },
      {
        key: "instances", label: "rects", type: "list", min: 1,
        itemDefaults: SCATTER_RECT_ITEM_DEFAULTS,
        itemSchema: [
          { key: "gx", label: "x (grid col)", type: "number", step: 1 },
          { key: "gy", label: "y (grid row)", type: "number", step: 1 },
          { key: "width", label: "width (grid spaces)", type: "number", step: 0.05 },
          { key: "height", label: "height (grid spaces)", type: "number", step: 0.05 },
          { key: "mirror", label: "mirror across center", type: "bool" },
        ],
      },
    ],
    // Each rect's top-left corner is grid-snapped (gx/gy = L.grid column/row
    // index); width/height are fractions of one grid cell (1 = a full grid
    // space, 0.1 = a tenth of one), so size scales with the grid itself.
    // Always filled, no stroke. mirror draws a second copy reflected across
    // the canvas's vertical center line (x = W/2), not a left/right anchor.
    draw({ ctx, L, P, p }) {
      const g = L.grid;
      const instances = (p.instances && p.instances.length ? p.instances : [SCATTER_RECT_ITEM_DEFAULTS])
        .map((inst) => Object.assign({}, SCATTER_RECT_ITEM_DEFAULTS, inst));
      ctx.save();
      ctx.globalAlpha = p.opacity;
      ctx.fillStyle = P.ghost;
      for (const inst of instances) {
        const x = g.x(inst.gx), y = g.y(inst.gy);
        const w = inst.width * g.cw, ih = inst.height * g.rh;
        ctx.fillRect(x, y, w, ih);
        if (inst.mirror) ctx.fillRect(L.W - x - w, y, w, ih);
      }
      ctx.restore();
    },
  });

  // ------------------------------------------------------------------- grid
  // Pure guide layer: visualizes L.grid (see overlay.js makeGrid), the shared
  // placement grid every other component may snap to. cols/rows here ARE the
  // live grid definition — resolved in drawOverlay()'s pre-pass even when
  // this guide is hidden, so snapping keeps working with the guide off.
  R({
    id: "grid",
    label: "layout grid",
    defaults: {
      enabled: false, cols: 12, rows: 16, marginPct: 5.5, square: false,
      showCols: true, showRows: true, showMargin: true, dashed: true, opacity: 1,
    },
    schema: [
      { key: "marginPct", label: "margin %", type: "number", min: 0, max: 20, step: 0.5 },
      { key: "cols", label: "columns", type: "number", min: 1, max: 32, step: 1 },
      { key: "rows", label: "rows", type: "number", min: 1, max: 32, step: 1 },
      { key: "square", label: "square cells", type: "bool" },
      { key: "showCols", label: "show columns", type: "bool" },
      { key: "showRows", label: "show rows", type: "bool" },
      { key: "showMargin", label: "margin outline", type: "bool" },
      { key: "dashed", label: "dashed lines", type: "bool" },
      { key: "opacity", label: "opacity", type: "number", min: 0, max: 1, step: 0.05 },
    ],
    draw({ ctx, L, P, p }) {
      const g = L.grid;
      if (!g) return;
      ctx.save();
      ctx.globalAlpha = p.opacity;
      ctx.strokeStyle = P.ghost;
      ctx.lineWidth = Math.max(1, L.u * 0.6);
      if (p.dashed) ctx.setLineDash([L.u * 3, L.u * 3]);
      const yTop = g.y(0), yBottom = g.y(g.rows), xLeft = g.x(0), xRight = g.x(g.cols);
      if (p.showCols) {
        for (let i = 0; i <= g.cols; i++) {
          const x = g.x(i);
          ctx.beginPath(); ctx.moveTo(x, yTop); ctx.lineTo(x, yBottom); ctx.stroke();
        }
      }
      if (p.showRows) {
        for (let j = 0; j <= g.rows; j++) {
          const y = g.y(j);
          ctx.beginPath(); ctx.moveTo(xLeft, y); ctx.lineTo(xRight, y); ctx.stroke();
        }
      }
      ctx.setLineDash([]);
      if (p.showMargin) {
        ctx.strokeStyle = P.faint;
        ctx.strokeRect(L.m, L.m, L.W - 2 * L.m, L.H - 2 * L.m);
      }
      ctx.restore();
    },
  });
})();
