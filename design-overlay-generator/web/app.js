// App shell: left config panel (generated from component schemas), canvas,
// playback, background compositing preview, and per-study persistence
// (autosave to localStorage + JSON export/import).
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
  const normalizeAspect = (value) => LEGACY_ASPECTS[value] || value;
  const TYPE_SLOTS = [
    { label: "numerals", fam: "numeral", size: "numeralSize", trk: "numeralTracking",
      sizeAttrs: { min: 20, max: 400, step: 2 }, trkAttrs: { min: -0.3, max: 0.3, step: 0.005 } },
    { label: "title", fam: "display", size: "titleSize", trk: "titleTracking",
      sizeAttrs: { min: 8, max: 80, step: 0.5 }, trkAttrs: { min: -0.3, max: 0.5, step: 0.01 } },
    { label: "mini", fam: "mini", size: "miniSize", trk: "miniTracking",
      sizeAttrs: { min: 4, max: 20, step: 0.25 }, trkAttrs: { min: -0.2, max: 0.5, step: 0.01 },
      lh: "miniLineHeight", lhAttrs: { min: 4, max: 24, step: 0.5 },
      marginSide: "miniMarginSide", marginSideAttrs: { min: -40, max: 40, step: 0.5 },
      marginTop: "miniMarginTop", marginTopAttrs: { min: -40, max: 40, step: 0.5 } },
    // Separate voice reserved for footer + tag only — no lh/margin controls
    // since neither uses the multi-line drawMiniBlock renderer.
    { label: "micro (footer/tag)", fam: "micro", size: "microSize", trk: "microTracking",
      sizeAttrs: { min: 4, max: 20, step: 0.25 }, trkAttrs: { min: -0.2, max: 0.5, step: 0.01 } },
  ];
  const FONT_FALLBACK = {
    numeral: '"Consolas",monospace',
    display: '"Arial",sans-serif',
    mini: '"Consolas",monospace',
    micro: '"Consolas",monospace',
  };

  // Active study: a real exported study.json (dropped or imported onto the
  // page, persisted under its own key) replaces the deterministic sample.
  const STUDY_KEY = "dog.activeStudy";
  let study = window.SAMPLE_STUDY;
  try {
    const savedStudy = JSON.parse(localStorage.getItem(STUDY_KEY) || "null");
    if (savedStudy && savedStudy.id && savedStudy.frames) study = savedStudy;
  } catch (e) {}
  const OV = window.OVERLAY;
  const TYPE = OV.TYPE;
  let LS_KEY = "dog.study." + study.id;
  let BG_KEY = LS_KEY + ".bg";
  const $ = (id) => document.getElementById(id);

  const canvas = $("stage");
  const ctx = canvas.getContext("2d");

  // ------------------------------------------------------------------ config
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
      ui: { matte: true, safe: false, fullsize: false },
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

  let CONFIG = defaultConfig();
  try { merge(CONFIG, JSON.parse(localStorage.getItem(LS_KEY) || "null")); } catch (e) {}
  CONFIG.aspect = normalizeAspect(CONFIG.aspect);

  let saveTimer = null;
  function save() {
    localStorage.setItem(LS_KEY, JSON.stringify(CONFIG));
    const el = $("saveStatus");
    el.textContent = "saved " + new Date().toLocaleTimeString();
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => { el.textContent = "autosave on"; }, 2000);
  }
  function touched() { save(); render(); }

  function applyType() {
    for (const slot of TYPE_SLOTS) {
      const fam = CONFIG.type[slot.fam];
      TYPE[slot.fam] = '"' + fam + '",' + FONT_FALLBACK[slot.fam];
      document.fonts.load('20px "' + fam + '"').then(render).catch(() => {});
      TYPE[slot.size] = CONFIG.type[slot.size];
      TYPE[slot.trk] = CONFIG.type[slot.trk];
      if (slot.lh) TYPE[slot.lh] = CONFIG.type[slot.lh];
      if (slot.marginSide) TYPE[slot.marginSide] = CONFIG.type[slot.marginSide];
      if (slot.marginTop) TYPE[slot.marginTop] = CONFIG.type[slot.marginTop];
    }
  }

  // ---------------------------------------------------------------- panel UI
  function option(sel, name) { sel.add(new Option(name, name)); }

  function numInput(value, attrs, oninput) {
    const el = document.createElement("input");
    el.type = "number"; el.className = "num";
    for (const k of ["min", "max", "step"]) if (attrs && attrs[k] !== undefined) el[k] = attrs[k];
    el.value = value;
    el.addEventListener("input", () => oninput(el.value === "" ? value : +el.value));
    return el;
  }

  function buildStudySection() {
    const preset = $("preset"), palette = $("palette");
    for (const name of Object.keys(PRESETS)) option(preset, name);
    for (const name of Object.keys(OV.PALETTES)) option(palette, name);
    preset.value = CONFIG.aspect;
    palette.value = CONFIG.palette;
    preset.addEventListener("change", () => { CONFIG.aspect = preset.value; touched(); });
    palette.addEventListener("change", () => { CONFIG.palette = palette.value; touched(); });
  }

  function buildTypeSection() {
    const host = $("typeSlots");
    host.innerHTML = "";
    for (const slot of TYPE_SLOTS) {
      const row = document.createElement("div");
      row.className = "type-slot";
      const lab = document.createElement("span");
      lab.textContent = slot.label;
      const sel = document.createElement("select");
      for (const f of window.FONT_LIBRARY) option(sel, f.label);
      sel.value = CONFIG.type[slot.fam];
      sel.addEventListener("change", () => {
        CONFIG.type[slot.fam] = sel.value;
        applyType(); touched();
      });
      const size = numInput(CONFIG.type[slot.size], slot.sizeAttrs, (v) => {
        CONFIG.type[slot.size] = v; TYPE[slot.size] = v; touched();
      });
      size.title = "size (u)";
      const trk = numInput(CONFIG.type[slot.trk], slot.trkAttrs, (v) => {
        CONFIG.type[slot.trk] = v; TYPE[slot.trk] = v; touched();
      });
      trk.title = "tracking (em)";
      row.append(lab, sel, size, trk);
      if (slot.lh) {
        const lh = numInput(CONFIG.type[slot.lh], slot.lhAttrs, (v) => {
          CONFIG.type[slot.lh] = v; TYPE[slot.lh] = v; touched();
        });
        lh.title = "line height (u)";
        row.append(lh);
      }
      if (slot.marginSide) {
        const ms = numInput(CONFIG.type[slot.marginSide], slot.marginSideAttrs, (v) => {
          CONFIG.type[slot.marginSide] = v; TYPE[slot.marginSide] = v; touched();
        });
        ms.title = "margin side offset (u)";
        row.append(ms);
      }
      if (slot.marginTop) {
        const mt = numInput(CONFIG.type[slot.marginTop], slot.marginTopAttrs, (v) => {
          CONFIG.type[slot.marginTop] = v; TYPE[slot.marginTop] = v; touched();
        });
        mt.title = "margin top offset (u)";
        row.append(mt);
      }
      host.append(row);
    }
  }

  function paramControl(conf, s) {
    if (s.type === "bool") {
      const el = document.createElement("input");
      el.type = "checkbox"; el.checked = !!conf[s.key];
      el.addEventListener("change", () => { conf[s.key] = el.checked; touched(); });
      return el;
    }
    if (s.type === "select" || s.type === "series" || s.type === "track") {
      const el = document.createElement("select");
      const options = s.type === "series" ? Object.keys(study.series)
        : s.type === "track" ? Object.keys(study.tracks || {})
        : s.options;
      for (const o of options) option(el, o);
      if (options.includes(conf[s.key])) el.value = conf[s.key];
      el.addEventListener("change", () => { conf[s.key] = el.value; touched(); });
      return el;
    }
    if (s.type === "text") {
      const el = document.createElement("input");
      el.type = "text"; el.value = conf[s.key] || "";
      el.addEventListener("input", () => { conf[s.key] = el.value; touched(); });
      return el;
    }
    return numInput(conf[s.key], s, (v) => { conf[s.key] = v; touched(); });
  }

  // Repeatable instance list (schema type "list"): conf[s.key] is an array
  // of item objects, each rendered from s.itemSchema via paramControl.
  // Cloned defensively on every build so it can never alias the component's
  // shared `defaults` array (Object.assign in buildComponentsSection only
  // shallow-copies that reference until something touches it).
  function buildListSection(conf, s) {
    if (!Array.isArray(conf[s.key]) || !conf[s.key].length) {
      conf[s.key] = [Object.assign({}, s.itemDefaults)];
    } else {
      conf[s.key] = conf[s.key].map((it) => Object.assign({}, s.itemDefaults, it));
    }
    const items = conf[s.key];

    const wrap = document.createElement("div");
    wrap.className = "list-param";
    const head = document.createElement("div");
    head.className = "list-head";
    const lab = document.createElement("span");
    lab.textContent = s.label || s.key;
    const add = document.createElement("button");
    add.type = "button"; add.textContent = "+ add";
    add.addEventListener("click", () => {
      items.push(Object.assign({}, s.itemDefaults));
      touched(); buildComponentsSection();
    });
    head.append(lab, add);
    wrap.append(head);

    const min = s.min || 1;
    items.forEach((item, idx) => {
      const box = document.createElement("div");
      box.className = "list-item";
      for (const fs of s.itemSchema) {
        const row = document.createElement("label");
        row.className = "param";
        const flab = document.createElement("span");
        flab.textContent = fs.label || fs.key;
        row.append(flab, paramControl(item, fs));
        box.append(row);
      }
      const btnRow = document.createElement("div");
      btnRow.className = "list-item-btns";
      const cp = document.createElement("button");
      cp.type = "button"; cp.className = "list-copy"; cp.textContent = "⧉ copy";
      cp.addEventListener("click", () => {
        items.splice(idx + 1, 0, Object.assign({}, item));
        touched(); buildComponentsSection();
      });
      btnRow.append(cp);
      if (items.length > min) {
        const rm = document.createElement("button");
        rm.type = "button"; rm.className = "list-remove"; rm.textContent = "− remove";
        rm.addEventListener("click", () => {
          items.splice(idx, 1);
          touched(); buildComponentsSection();
        });
        btnRow.append(rm);
      }
      box.append(btnRow);
      wrap.append(box);
    });
    return wrap;
  }

  function buildComponentsSection() {
    const host = $("componentList");
    const openIds = new Set();
    host.querySelectorAll("details.comp[open]").forEach((d) => openIds.add(d.dataset.compId));
    host.innerHTML = "";
    for (const c of OV.registry) {
      const conf = CONFIG.components[c.id] =
        Object.assign({ enabled: true }, c.defaults, CONFIG.components[c.id]);

      const det = document.createElement("details");
      det.className = "comp";
      det.dataset.compId = c.id;
      det.open = openIds.has(c.id);
      const sum = document.createElement("summary");
      const cb = document.createElement("input");
      cb.type = "checkbox"; cb.checked = conf.enabled !== false;
      cb.addEventListener("click", (e) => e.stopPropagation());
      cb.addEventListener("change", () => { conf.enabled = cb.checked; touched(); });
      const name = document.createElement("span");
      name.textContent = c.label;
      sum.append(cb, name);
      det.append(sum);

      for (const s of c.schema || []) {
        if (s.type === "list") { det.append(buildListSection(conf, s)); continue; }
        const row = document.createElement("label");
        row.className = "param";
        const lab = document.createElement("span");
        lab.textContent = s.label || s.key;
        row.append(lab, paramControl(conf, s));
        det.append(row);
      }
      host.append(det);
    }
  }

  function buildSettingsSection() {
    $("exportBtn").addEventListener("click", () => {
      const blob = new Blob([JSON.stringify(CONFIG, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = study.id.toLowerCase() + "-overlay.json";
      a.click();
      URL.revokeObjectURL(a.href);
    });
    // Canonical promote export: the exact filename the detail-pass promote
    // flow expects in the Study vault (03_specimen/overlay-config.json) —
    // see houdini-ai docs/DETAIL_PASS_PROMOTE.md. Same content as "export",
    // only the canonical name differs.
    $("promoteExportBtn").addEventListener("click", () => {
      const blob = new Blob([JSON.stringify(CONFIG, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "overlay-config.json";
      a.click();
      URL.revokeObjectURL(a.href);
    });
    $("importBtn").addEventListener("click", () => $("importFile").click());
    $("importFile").addEventListener("change", () => {
      const file = $("importFile").files[0];
      if (!file) return;
      importJsonFile(file);
    });
    $("resetBtn").addEventListener("click", () => {
      localStorage.removeItem(LS_KEY);
      localStorage.removeItem(BG_KEY);
      location.reload();
    });
    // Back to the deterministic sample study (does not touch saved configs).
    $("sampleStudyBtn").addEventListener("click", () => {
      localStorage.removeItem(STUDY_KEY);
      location.reload();
    });
  }

  // --------------------------------------------------------------- rendering
  const state = { frame: 0, playing: false, bg: null };

  function drawChecker(W, H) {
    const s = 24;
    for (let y = 0; y < H; y += s) {
      for (let x = 0; x < W; x += s) {
        ctx.fillStyle = ((x + y) / s) % 2 ? "#252528" : "#2c2c30";
        ctx.fillRect(x, y, s, s);
      }
    }
  }
  function drawCover(media, W, H) {
    const mw = media.videoWidth || media.naturalWidth;
    const mh = media.videoHeight || media.naturalHeight;
    if (!mw || !mh) return;
    const sc = Math.max(W / mw, H / mh);
    ctx.drawImage(media, (W - mw * sc) / 2, (H - mh * sc) / 2, mw * sc, mh * sc);
  }
  function drawSafeZones(W, H) {
    ctx.save();
    ctx.strokeStyle = "rgba(80,160,255,0.55)";
    ctx.setLineDash([6, 6]);
    ctx.lineWidth = 1.5;
    ctx.strokeRect(W * 0.86, H * 0.45, W * 0.14 - 2, H * 0.42);
    ctx.strokeRect(2, H * 0.80, W * 0.75, H * 0.20 - 3);
    ctx.fillStyle = "rgba(80,160,255,0.7)";
    ctx.font = "11px monospace";
    ctx.fillText("IG UI", W * 0.86 + 6, H * 0.45 + 16);
    ctx.fillText("CAPTION", 8, H * 0.80 + 16);
    ctx.restore();
  }

  function render() {
    const [W, H] = PRESETS[normalizeAspect(CONFIG.aspect)] || PRESETS[DEFAULT_ASPECT];
    if (canvas.width !== W || canvas.height !== H) { canvas.width = W; canvas.height = H; }
    ctx.clearRect(0, 0, W, H);

    if ($("matte").checked || !state.bg) drawChecker(W, H);
    else drawCover(state.bg, W, H);

    OV.drawOverlay(ctx, W, H, study, {
      frame: state.frame,
      palette: CONFIG.palette,
      components: CONFIG.components,
    });

    if ($("safe").checked) drawSafeZones(W, H);

    $("frame").value = state.frame;
    $("frameLabel").textContent =
      String(state.frame).padStart(4, "0") + " / " + String(study.frames - 1).padStart(4, "0");
  }

  // ---------------------------------------------------------------- playback
  let lastT = 0, acc = 0;
  function tick(t) {
    if (state.playing) {
      acc += (t - lastT) / 1000;
      const dt = 1 / study.fps;
      while (acc >= dt) {
        acc -= dt;
        state.frame = (state.frame + 1) % study.frames;
      }
      render();
    }
    lastT = t;
    requestAnimationFrame(tick);
  }
  function seekVideo() {
    if (state.bg && state.bg.tagName === "VIDEO" && !state.playing) {
      state.bg.currentTime = state.frame / study.fps;
    }
  }

  $("play").addEventListener("click", () => {
    state.playing = !state.playing;
    $("play").textContent = state.playing ? "❚❚ pause" : "▶ play";
    if (state.bg && state.bg.tagName === "VIDEO") {
      state.playing ? state.bg.play() : state.bg.pause();
    }
    if (!state.playing) { seekVideo(); render(); }
  });
  $("frame").addEventListener("input", () => {
    state.frame = +$("frame").value;
    seekVideo();
    render();
  });
  function applyFullsize() {
    document.querySelector("main").classList.toggle("natural", CONFIG.ui.fullsize);
  }
  function buildUiSection() {
    for (const key of ["matte", "safe", "fullsize"]) {
      const el = $(key);
      el.checked = !!CONFIG.ui[key];
      el.addEventListener("change", () => {
        CONFIG.ui[key] = el.checked;
        if (key === "fullsize") applyFullsize();
        touched();
      });
    }
    applyFullsize();
  }

  // --------------------------------------------------------------- drag&drop
  // The dropped media itself is also persisted (as a data URL, under its own
  // localStorage key so the frequent CONFIG autosave stays small) so it's
  // still there on the next visit. Images are typically small enough;
  // large videos can exceed the browser's localStorage quota (~5-10MB) and
  // will simply fail to persist — logged, not fatal.
  function setBackground(type, url) {
    if (type.startsWith("video/")) {
      const v = document.createElement("video");
      v.src = url; v.muted = true; v.loop = true; v.playsInline = true;
      v.addEventListener("loadeddata", () => { state.bg = v; $("dropHint").style.display = "none"; render(); });
      v.addEventListener("timeupdate", () => { if (!state.playing) render(); });
    } else if (type.startsWith("image/")) {
      const img = new Image();
      img.onload = () => { state.bg = img; $("dropHint").style.display = "none"; render(); };
      img.src = url;
    }
  }
  function persistBackground(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        localStorage.setItem(BG_KEY, JSON.stringify({ type: file.type, dataUrl: reader.result }));
      } catch (e) {
        console.warn("background media too large to persist locally", e);
      }
    };
    reader.readAsDataURL(file);
  }
  function loadPersistedBackground() {
    let saved = null;
    try { saved = JSON.parse(localStorage.getItem(BG_KEY) || "null"); } catch (e) {}
    if (saved && saved.type && saved.dataUrl) setBackground(saved.type, saved.dataUrl);
  }

  // Config "render" pointer: the pipeline records where the study's latest
  // render lives ({video, still} paths — absolute or relative to web/), and
  // importing that config auto-loads it as the backdrop: video first, first-
  // frame still as fallback, checker if neither resolves. file:// pages can't
  // scan directories, so "latest" is whatever path the tooling last wrote.
  // Resolve a render-pointer path on either origin. Canonical form is
  // project-relative ("studies/…" or "work/…"); absolute Windows paths are
  // accepted and mapped. Over http (review-studio serving), project paths go
  // through /overlay-media/; over file://, they resolve relative to web/.
  function mediaUrl(p) {
    if (/^(file|https?|data|blob):/.test(p)) return p;
    const http = location.protocol !== "file:";
    if (/^[A-Za-z]:[\\/]/.test(p)) {
      const norm = p.replace(/\\/g, "/");
      if (http) {
        const idx = Math.max(norm.indexOf("/studies/"), norm.indexOf("/work/"));
        if (idx >= 0) return "/overlay-media" + norm.slice(idx);
      }
      return "file:///" + norm;
    }
    if (/^(studies|work)\//.test(p)) return http ? "/overlay-media/" + p : "../../" + p;
    return p; // relative to web/
  }
  function loadRenderSpec(spec) {
    // Loading a pointed-at render means you want to see it: drop the matte.
    // Every step reports into the drop hint so a failing path is visible
    // instead of silently showing nothing.
    const status = (text) => {
      const el = $("dropHint");
      el.style.display = "";
      el.textContent = text;
    };
    const show = (media) => {
      state.bg = media;
      CONFIG.ui.matte = false;
      if ($("matte")) $("matte").checked = false;
      $("dropHint").style.display = "none";
      render();
    };
    const still = () => {
      if (!spec.still) { status("render pointer: no still fallback configured"); return; }
      const url = mediaUrl(spec.still);
      status("render pointer: loading still…");
      const img = new Image();
      img.onload = () => show(img);
      img.onerror = () => {
        console.warn("render still failed to load:", url);
        status("render pointer: still failed to load: " + spec.still);
      };
      img.src = url;
    };
    if (spec.video) {
      status("render pointer: trying video…");
      const v = document.createElement("video");
      // A missing/unreadable video may fire "error" — or fire nothing at all
      // on file:// — so the still fallback also runs on a short timeout.
      // If the video does load late, it simply replaces the still.
      const fallback = setTimeout(still, 2000);
      v.src = mediaUrl(spec.video); v.muted = true; v.loop = true; v.playsInline = true;
      v.addEventListener("loadeddata", () => { clearTimeout(fallback); show(v); seekVideo(); });
      v.addEventListener("timeupdate", () => { if (!state.playing) render(); });
      v.addEventListener("error", () => { clearTimeout(fallback); still(); });
    } else {
      still();
    }
  }

  // Shared JSON import: a study.json (id + frames) becomes the active study;
  // anything else with components is an overlay config. Both apply IN MEMORY
  // immediately — no reload, no storage dependency (localStorage persistence
  // is best-effort, so imports work even where file:// storage is blocked).
  function refreshAfterDataChange() {
    CONFIG.aspect = normalizeAspect(CONFIG.aspect);
    $("preset").value = CONFIG.aspect;
    $("palette").value = CONFIG.palette;
    for (const key of ["matte", "safe", "fullsize"]) $(key).checked = !!CONFIG.ui[key];
    buildTypeSection();
    buildComponentsSection();
    applyType();
    applyFullsize();
    $("frame").max = study.frames - 1;
    if (state.frame > study.frames - 1) state.frame = 0;
    $("studyLabel").textContent = study.id + " | " + study.title;
    render();
    if (CONFIG.render && (CONFIG.render.video || CONFIG.render.still)) loadRenderSpec(CONFIG.render);
  }

  function importJsonFile(file) {
    file.text().then((text) => {
      const data = JSON.parse(text);
      if (data && data.id && data.frames) {
        study = data;
        LS_KEY = "dog.study." + study.id;
        BG_KEY = LS_KEY + ".bg";
        try { localStorage.setItem(STUDY_KEY, text); } catch (e) {}
        // Keep the current config when it already targets this study;
        // otherwise pick up whatever is saved for it (or defaults).
        if (CONFIG.studyId !== study.id) {
          CONFIG = defaultConfig();
          try { merge(CONFIG, JSON.parse(localStorage.getItem(LS_KEY) || "null")); } catch (e) {}
        }
      } else if (data && data.components) {
        CONFIG = merge(defaultConfig(), data);
        try {
          localStorage.setItem(LS_KEY, text);
          if (data.studyId && data.studyId !== study.id) {
            localStorage.setItem("dog.study." + data.studyId, text);
          }
        } catch (e) {}
      } else {
        throw new Error("neither a study.json nor an overlay config");
      }
      refreshAfterDataChange();
    }).catch((e) => alert("import failed: " + (e && e.message ? e.message : e)));
  }

  document.body.addEventListener("dragover", (e) => e.preventDefault());
  document.body.addEventListener("drop", (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    if (!file) return;
    if (/\.json$/i.test(file.name) || file.type === "application/json") {
      importJsonFile(file);
      return;
    }
    setBackground(file.type, URL.createObjectURL(file));
    persistBackground(file);
  });

  // -------------------------------------------------------------- URL params
  // (?ar=1:1&frame=120&palette=...) — also how a headless renderer drives this.
  {
    const q = new URLSearchParams(location.search);
    if (q.has("ar")) {
      const match = Object.keys(PRESETS).find((k) => k.startsWith(q.get("ar")));
      if (match) CONFIG.aspect = match;
    }
    if (q.has("palette") && OV.PALETTES[q.get("palette")]) CONFIG.palette = q.get("palette");
    if (q.has("frame")) state.frame = Math.min(study.frames - 1, Math.max(0, +q.get("frame") || 0));
    if (q.has("bg")) {
      const bg = q.get("bg");
      CONFIG.render = /\.(png|jpe?g|webp|gif)$/i.test(bg) ? { still: bg } : { video: bg };
      CONFIG.ui.matte = false;
    }
  }

  // -------------------------------------------------------------------- init
  $("frame").max = study.frames - 1;
  $("studyLabel").textContent = study.id + " | " + study.title;
  buildStudySection();
  buildTypeSection();
  buildComponentsSection();
  buildSettingsSection();
  buildUiSection();
  applyType();
  render();
  if (CONFIG.render && (CONFIG.render.video || CONFIG.render.still)) loadRenderSpec(CONFIG.render);
  else loadPersistedBackground();
  requestAnimationFrame((t) => { lastT = t; requestAnimationFrame(tick); });
})();
