// Sample study metadata — stands in for the Houdini-exported study.json.
// Deterministically generated so preview frames are reproducible.
(function () {
  function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // Smooth pseudo-random signal: sum of a few seeded sines.
  function makeSignal(rng, octaves) {
    const comps = [];
    for (let i = 0; i < octaves; i++) {
      comps.push({
        amp: rng() * (1 / (i + 1)),
        freq: 0.5 + rng() * 3 * (i + 1),
        phase: rng() * Math.PI * 2,
      });
    }
    return function (t) {
      let v = 0, norm = 0;
      for (const c of comps) { v += c.amp * Math.sin(t * c.freq + c.phase); norm += c.amp; }
      return norm > 0 ? 0.5 + 0.5 * (v / norm) : 0.5; // → 0..1
    };
  }

  const FRAMES = 600;
  const rng = mulberry32(8181);
  const energySig = makeSignal(rng, 4);
  const cohesionSig = makeSignal(rng, 3);
  const densitySig = makeSignal(rng, 5);
  const cxSig = makeSignal(rng, 3);
  const cySig = makeSignal(rng, 3);
  const szSig = makeSignal(rng, 2);

  const t1xSig = makeSignal(rng, 3);
  const t1ySig = makeSignal(rng, 3);
  const t1vSig = makeSignal(rng, 4);
  const t2xSig = makeSignal(rng, 3);
  const t2ySig = makeSignal(rng, 3);
  const t2vSig = makeSignal(rng, 4);

  const series = { energy: [], cohesion: [], density: [] };
  const bbox = [];
  // Tracked points: wander inside the subject bbox, like exported point
  // tracks from houdini/export_overlay_study.py (screen + depth + values).
  const tracks = {
    leader: { screen: [], depth: [], values: { speed: [] } },
    straggler: { screen: [], depth: [], values: { speed: [] } },
  };
  for (let f = 0; f < FRAMES; f++) {
    const t = f / 24; // seconds
    series.energy.push(energySig(t * 0.9));
    series.cohesion.push(cohesionSig(t * 0.5));
    series.density.push(densitySig(t * 1.3));

    // Wandering, breathing subject bbox (normalized screen space).
    const cx = 0.5 + (cxSig(t * 0.25) - 0.5) * 0.28;
    const cy = 0.48 + (cySig(t * 0.2) - 0.5) * 0.22;
    const hw = 0.16 + szSig(t * 0.3) * 0.12;
    const hh = 0.13 + szSig(t * 0.3 + 7) * 0.10;
    const b = [
      Math.max(0.04, cx - hw), Math.max(0.06, cy - hh),
      Math.min(0.96, cx + hw), Math.min(0.94, cy + hh),
    ];
    bbox.push(b);

    const inBox = (xs, ys) => [
      b[0] + (0.15 + 0.7 * xs) * (b[2] - b[0]),
      b[1] + (0.15 + 0.7 * ys) * (b[3] - b[1]),
    ];
    tracks.leader.screen.push(inBox(t1xSig(t * 0.7), t1ySig(t * 0.6)));
    tracks.leader.depth.push(6 + 3 * t1vSig(t * 0.2));
    tracks.leader.values.speed.push(t1vSig(t * 1.1));
    tracks.straggler.screen.push(inBox(t2xSig(t * 0.45), t2ySig(t * 0.5)));
    tracks.straggler.depth.push(7 + 3 * t2vSig(t * 0.25));
    tracks.straggler.values.speed.push(t2vSig(t * 0.8));
  }

  window.SAMPLE_STUDY = {
    id: "STUDY-042",
    number: 42,
    title: "NONLOCAL AFFINITY",
    subtitle: "agent fields with distance-defying attraction",
    source: "arXiv:cond-mat/0611743",
    date: "2026-08-19",
    solver: { name: "POP/VEX", dt: "1/240", substeps: 4, seed: 8181 },
    params: [
      ["AGENTS", "250 000"],
      ["R_ATTRACT", "0.42"],
      ["R_ALIGN", "0.18"],
      ["NOISE η", "0.06"],
      ["DT", "0.0042 s"],
      ["SUBSTEPS", "4"],
      ["INTEGRATOR", "RK2"],
    ],
    summary:
      "Agents form transient alliances with distant partners instead of spatial " +
      "neighbours. Attraction acts along the alliance graph, so coherent bodies " +
      "assemble from points that never touch. Rewiring events break and reform " +
      "the graph on a fixed schedule; the specimen's morphology is the visible " +
      "memory of that hidden topology.",
    bullets: [
      "attraction follows the alliance graph, not distance",
      "scheduled rewires perturb an otherwise contracting system",
      "morphology encodes graph history",
    ],
    credits: "bzor computational studio",
    fps: 24,
    frames: FRAMES,
    series: series,
    bbox: bbox,
    tracks: tracks,
  };
})();
