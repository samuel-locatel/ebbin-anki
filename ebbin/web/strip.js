/* Ebbin deck-browser strip (design B). Rendered client-side with textContent only. */
(function (window) {
  "use strict";
  var TABS = [["Hoje", null], ["Métricas", "metrics"], ["Objetivos", "objectives"], ["Ajustes", "settings"]];
  var view = null, cfg = { focus_s: 1200, dark_theme: "night" }, root = null;

  function mmss(s) {
    s = Math.max(0, Math.round(s));
    var m = Math.floor(s / 60), r = s % 60;
    return (m < 10 ? "0" : "") + m + ":" + (r < 10 ? "0" : "") + r;
  }

  function fmtNum(n) { // pt-BR thousands separator, independent of ICU
    return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  }

  function dayClass(state) {
    return "e-day" + (state === "done" || state === "today" || state === "off" ? " " + state : " off");
  }

  // Bar split: ink = before today, terra = gained today (within the current level), in percent.
  function barPercents(v) {
    var needed = Math.max(1, v.needed || 1);
    var into = Math.max(0, Math.min(v.into || 0, needed));
    var before = Math.max(0, Math.min(v.xp_before_today || 0, into));
    return { a: before / needed * 100, b: (into - before) / needed * 100 };
  }

  function streakText(s) {
    var n = (s && s.current) || 0;
    var t = n + (n === 1 ? " dia seguido" : " dias seguidos");
    var f = (s && s.freezes) || 0;
    if (f > 0) t += " · " + f + (f === 1 ? " congelamento" : " congelamentos");
    return t;
  }

  // What the pomodoro button shows and which bridge command a click sends.
  function pomoButton(p, focusS) {
    var phase = p ? p.phase : "idle";
    if (phase === "focus" || phase === "short" || phase === "long")
      return { label: "⏸ " + mmss(p.remaining_s), cmd: "pomo_pause" };
    if (phase === "paused") return { label: "▶ " + mmss(p.remaining_s), cmd: "pomo_resume" };
    return { label: "⏱ começar " + mmss(focusS), cmd: "pomo_start" };
  }

  function h(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function send(cmd) { window.ebbinSend("ebbin:" + cmd); }

  function renderPomo() {
    var btn = root && root.querySelector(".e-pomobtn");
    if (!btn || !view) return;
    var b = pomoButton(view.pomodoro, cfg.focus_s);
    btn.textContent = b.label;
    btn.onclick = function () {
      window.ebbinSend("ebbin:" + b.cmd, function (p) { if (p) api.update({ pomodoro: p }); });
    };
  }

  function render() {
    if (!root || !view) return;
    if (window.ebbinSketch) window.ebbinSketch.ensureFilters();
    var cls = window.ebbinSketch ? window.ebbinSketch.themeClass(cfg.dark_theme) : "";
    root.className = "ebbin" + (cls ? " " + cls : "");
    root.textContent = "";
    var win = h("div", "e-win e-chalky");
    if (view.stamp_xp > 0) win.appendChild(h("div", "e-stamp", "+" + fmtNum(view.stamp_xp) + " XP"));

    var tabs = h("div", "e-tabs");
    TABS.forEach(function (t) {
      var s = h("span", t[1] ? "" : "on", t[0]);
      if (t[1]) s.onclick = function () { send("open_window:" + t[1]); };
      tabs.appendChild(s);
    });
    var imp = h("span", "", "importar");
    imp.style.marginLeft = "auto";
    imp.onclick = function () { send("open_import"); };
    tabs.appendChild(imp);
    win.appendChild(tabs);

    var lv = h("div", "e-row");
    lv.style.marginTop = "18px";
    var left = h("div");
    var tag = h("span", "e-tag"); tag.appendChild(h("span", "", "nível " + view.level));
    left.appendChild(tag);
    left.appendChild(h("span", "e-muted", " · " + view.rank));
    lv.appendChild(left);
    lv.appendChild(h("span", "e-muted", fmtNum(view.into) + " / " + fmtNum(view.needed) + " XP"));
    win.appendChild(lv);

    var pct = barPercents(view), bar = h("div", "e-bar e-chalky");
    bar.appendChild(h("div", "frame"));
    var a = h("div", "a"), b = h("div", "b");
    a.style.width = pct.a + "%";
    b.style.left = "calc(" + pct.a + "% + 4px)";
    b.style.width = pct.b + "%";
    bar.appendChild(a); bar.appendChild(b);
    win.appendChild(bar);

    var wk = h("div", "e-row"); wk.style.marginTop = "16px";
    var days = h("div", "e-days");
    (view.week || []).forEach(function (d) {
      var e = h("span", dayClass(d.state)); e.appendChild(h("b", "", d.label)); days.appendChild(e);
    });
    wk.appendChild(days);
    wk.appendChild(h("span", "e-hand", streakText(view.streak)));
    wk.lastChild.style.fontSize = "26px";
    win.appendChild(wk);

    var ms = h("div");
    ms.style.cssText = "margin-top:18px;padding-top:14px;border-top:1px solid var(--line)";
    var mrow = h("div", "e-row");
    var list = h("div"); list.style.flex = "1";
    (view.missions || []).forEach(function (m) {
      var r = h("div", "e-mis");
      r.appendChild(h("span", "e-circ", m.done ? "✓" : ""));
      r.appendChild(h("span", "", m.text));
      r.appendChild(h("span", "p e-muted", m.progress + "/" + m.target));
      list.appendChild(r);
    });
    mrow.appendChild(list);
    var pb = h("button", "e-lnk e-pomobtn"); pb.type = "button";
    mrow.appendChild(pb);
    ms.appendChild(mrow);
    if (view.objective) {
      var ob = h("div", "e-muted", view.objective); ob.style.marginTop = "10px"; ms.appendChild(ob);
    }
    win.appendChild(ms);

    (view.hints || []).forEach(function (hint) {
      var r = h("div", "e-hint " + (hint.kind || ""));
      r.appendChild(h("span", "", hint.text));
      var x = h("button", "x", "✕"); x.type = "button"; x.title = "dispensar";
      x.onclick = function () {
        send("dismiss:" + hint.id);
        view.hints = view.hints.filter(function (o) { return o.id !== hint.id; });
        if (r.parentNode) r.parentNode.removeChild(r);
      };
      r.appendChild(x);
      win.appendChild(r);
    });
    root.appendChild(win);
    renderPomo();
  }

  // Hints are only ever set by init(); partial updates must not overwrite (or erase) them.
  function stripHints(partial) {
    var p = Object.assign({}, partial); delete p.hints; return p;
  }

  var api = {
    stripHints: stripHints,
    mmss: mmss, fmtNum: fmtNum, dayClass: dayClass, barPercents: barPercents,
    streakText: streakText, pomoButton: pomoButton,
    init: function (payload) {
      root = document.getElementById("ebbin-strip");
      cfg = Object.assign({}, cfg, { focus_s: payload.focus_s, dark_theme: payload.dark_theme });
      view = payload.view;
      render();
    },
    // Merge a (possibly partial) view. Only the pomodoro button text changes every second,
    // so a pomodoro-only change never rebuilds the strip.
    update: function (partial) {
      if (!root || !view || !partial) return;
      partial = stripHints(partial);
      var rest = Object.assign({}, partial); delete rest.pomodoro;
      var structural = Object.keys(rest).length > 0;
      view = Object.assign(view, partial);
      if (structural) render(); else renderPomo();
    },
  };
  window.ebbinStrip = api;
})(window);
