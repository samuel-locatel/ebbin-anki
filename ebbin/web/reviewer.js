/* Ebbin reviewer top bar. Never touches #qa; lives in its own fixed container.
   With the skin on (body.ebbin-skin, see skin.css) it becomes the HUD band: level + total XP,
   today's progress bar, pomodoro and combo. Without it, only the right group shows. */
(function (window) {
  "use strict";
  var CIRC = 2 * Math.PI * 12;
  var cfg = { sounds_enabled: true, volume: 0.8, dark_theme: "night" };
  var root = null, el = {};
  var lastCombo = 0;

  function fmtCombo(n) {
    // multiplier shown with pt-BR decimal comma, e.g. x1,3
    var mult = Math.min(1.5, 1 + 0.05 * n); // mirrors core.rules.combo_multiplier
    return "×" + mult.toFixed(2).replace(/0$/, "").replace(".", ",");
  }

  function mmss(s) {
    s = Math.max(0, Math.round(s));
    var m = Math.floor(s / 60), r = s % 60;
    return (m < 10 ? "0" : "") + m + ":" + (r < 10 ? "0" : "") + r;
  }

  function fmtNum(n) { // pt-BR thousands separator, independent of ICU
    return String(Math.round(n || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  }

  function xpText(total) { return fmtNum(total) + " XP"; }

  // h = huddata.progress(): {done, target, left, met}; met = the main mission is done
  function progressLabel(h) {
    if (!h) return "";
    if (h.met) return "meta batida";
    return fmtNum(h.done) + " de " + fmtNum(h.target) + " · faltam " + fmtNum(h.left);
  }

  function barWidth(pct) {
    var f = Math.max(0, Math.min(100, Number(pct) || 0)) / 100;
    return "calc((100% - 8px) * " + f + ")";
  }

  function skinned() { return document.body.classList.contains("ebbin-skin"); }

  function build() {
    if (root) return;
    if (window.ebbinSketch) window.ebbinSketch.ensureFilters();
    root = document.createElement("div");
    root.className = "ebbin e-topbar";
    root.innerHTML =
      '<div class="e-hud-l"><span class="e-tag"><span class="e-lv"></span></span>' +
      '<span class="e-xp"></span></div>' +
      '<div class="e-prog e-chalky"><div class="frame"></div><div class="a"></div>' +
      '<span class="lab e-hand"></span></div>' +
      '<div class="e-hud-r">' +
      '<span class="e-stop" hidden>ótimo ponto para parar</span>' +
      '<span class="e-mission e-chalky" hidden></span>' +
      '<span class="e-pomo e-chalky" hidden><svg viewBox="0 0 30 30"><circle class="trk" cx="15" cy="15" r="12"/>' +
      '<circle class="prg" cx="15" cy="15" r="12" stroke-dasharray="' + CIRC.toFixed(2) + '" stroke-dashoffset="0"/></svg>' +
      '<span class="t"></span></span>' +
      '<span class="e-combo e-chalky" hidden></span></div>';
    document.body.appendChild(root);
    el.left = root.querySelector(".e-hud-l");
    el.lv = root.querySelector(".e-lv");
    el.xp = root.querySelector(".e-xp");
    el.bar = root.querySelector(".e-prog .a");
    el.lab = root.querySelector(".e-prog .lab");
    el.stop = root.querySelector(".e-stop");
    el.mission = root.querySelector(".e-mission");
    el.pomo = root.querySelector(".e-pomo");
    el.prg = root.querySelector(".prg");
    el.t = root.querySelector(".t");
    el.combo = root.querySelector(".e-combo");
    api.setTheme(window.ebbinSketch ? window.ebbinSketch.themeClass(cfg.dark_theme) : "");
  }

  function showCombo(n) {
    lastCombo = n;
    el.combo.hidden = n < 2;
    if (n >= 2) el.combo.textContent = fmtCombo(n);
  }

  function showPomo(p) {
    if (!p || p.phase === "idle" || !p.total_s) { el.pomo.hidden = true; return; }
    el.pomo.hidden = false;
    var frac = Math.max(0, Math.min(1, p.remaining_s / p.total_s));
    el.prg.setAttribute("stroke-dashoffset", (CIRC * (1 - frac)).toFixed(2));
    el.t.textContent = mmss(p.remaining_s);
    el.pomo.classList.toggle("brk", p.phase === "short" || p.phase === "long" ||
      p.paused_from === "short" || p.paused_from === "long");
  }

  function float(xp) {
    if (!(xp > 0)) return;
    var f = document.createElement("div");
    f.className = "ebbin e-float";
    f.textContent = "+" + xp;
    (skinned() ? el.left : root).appendChild(f); // skin: floats next to the total XP
    window.setTimeout(function () { if (f.parentNode) f.parentNode.removeChild(f); }, 950);
  }

  var api = {
    fmtNum: fmtNum, xpText: xpText, progressLabel: progressLabel, barWidth: barWidth,
    setConfig: function (c) {
      cfg = Object.assign({}, cfg, c || {});
      if (root) api.setTheme(window.ebbinSketch.themeClass(cfg.dark_theme));
    },
    setTheme: function (cls) {
      build();
      root.classList.remove("night", "slate");
      if (cls) root.classList.add(cls);
    },
    update: function (view) {
      build();
      if (!view) return;
      if (typeof view.combo === "number") showCombo(view.combo);
      var main = (view.missions || [])[0];
      el.mission.hidden = !main;
      if (main) el.mission.textContent = main.progress + "/" + main.target;
      if (typeof view.level === "number") el.lv.textContent = "nível " + view.level;
      if (typeof view.total_xp === "number") el.xp.textContent = xpText(view.total_xp);
      if (view.hud) {
        el.bar.style.width = barWidth(view.hud.pct);
        el.lab.textContent = progressLabel(view.hud);
      }
      el.stop.hidden = !view.diminished;
      showPomo(view.pomodoro);
    },
    updatePomo: function (p) {
      build();
      showPomo(p);
    },
    onAnswer: function (evt, view) {
      build();
      if (view) api.update(view);
      if (!evt) return;
      showCombo(evt.combo);
      float(evt.xp);
      if (cfg.sounds_enabled && window.ebbinPlaySeq) {
        var seq = (evt.sounds || []).slice();
        var side = (evt.mission_done || []).some(function (m) { return m !== "main"; });
        var first = seq[0] || "";
        if (side && first !== "good" && first.indexOf("combo:") !== 0) seq.push("good");
        window.ebbinPlaySeq(seq, cfg.volume);
      }
    },
  };
  window.ebbin = api;
})(window);
