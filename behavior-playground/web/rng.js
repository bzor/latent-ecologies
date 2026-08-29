// mulberry32-v1 — the studio's canonical prototype RNG.
// Must remain bit-identical to website/affinity-core.js createRng and the
// Python Mulberry32 in houdini/build_nonlocal_affinity_hda.py. Never change
// this without versioning the identity contract.
(function (root) {
  "use strict";
  const BP = (root.BP = root.BP || {});
  BP.RNG_ID = "mulberry32-v1";
  BP.mulberry32 = function (seed) {
    let state = seed >>> 0;
    return function random() {
      state = (state + 0x6d2b79f5) >>> 0;
      let value = state;
      value = Math.imul(value ^ (value >>> 15), value | 1);
      value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
      return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
    };
  };
  if (typeof module === "object" && module.exports) module.exports = BP;
})(typeof globalThis !== "undefined" ? globalThis : this);
