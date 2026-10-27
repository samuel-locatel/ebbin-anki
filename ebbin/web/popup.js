/* Ebbin end-of-session pop-up: renders the view-model built by ebbin/ui/popupdata.py. */
(function (window) {
  "use strict";
  var DURATION = 900;
  var cfg = { sounds_enabled: true, volume: 0.8, dark_theme: "night" };
  var raf = null;
  var timers = [];

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  function sound(key, vol) {
    if (cfg.sounds_enabled && window.ebbinSound) {
      try { window.ebbinSound(key, vol); } catch (e) { /* audio unavailable */ }
    }
  }

  function close() { window.ebbinSend("ebbinpopup:close"); }

  function clear() {
    if (raf) { window.cancelAnimationFrame(raf); raf = null; }
    timers.forEach(function (t) { window.clearTimeout(t); });
    timers = [];
  }

  // Natural content height (without the 100vh stretch) -> Python resizes the dialog to fit,
  // so "Fechar" is never clipped. Re-sent once the bundled fonts have loaded.
  function reportHeight() {
    var root = document.getElementById("ebbin-popup");
    if (!root) return;
    var prev = root.style.minHeight;
    root.style.minHeight = "0";
    var h = Math.ceil(root.getBoundingClientRect().height);
    root.style.minHeight = prev;
    if (h > 0) window.ebbinSend("ebbinpopup:height:" + h);
  }

  function widthFor(p) { return "calc((100% - 8px) * " + (p / 100) + ")"; }

  function countUp(node, target, onDone) {
    if (!(target > 0)) { node.textContent = "+" + target; onDone(); return; }
    var start = null, nextTick = 0.08;
    function step(ts) {
      if (start === null) start = ts;
      var f = Math.min(1, (ts - start) / DURATION);
      node.textContent = "+" + Math.round(target * f);
      while (f >= nextTick && nextTick < 1) {
        sound("good", cfg.volume * 0.3);
        nextTick += 0.08;
      }
      if (f < 1) raf = window.requestAnimationFrame(step);
      else { raf = null; onDone(); }
    }
    raf = window.requestAnimationFrame(step);
  }

  function show(view) {
    clear();
    window.ebbinSketch.ensureFilters();
    var root = document.getElementById("ebbin-popup");
    root.className = "ebbin " + window.ebbinSketch.themeClass(cfg.dark_theme);
    root.textContent = "";
    var win = el("div", "e-win e-chalky");

    var head = el("div", "p-head");
    head.appendChild(el("span", "e-hand p-title", "sessão concluída"));
    var x = el("button", "p-x", "✕");
    x.onclick = close;
    head.appendChild(x);
    win.appendChild(head);

    var xp = el("div", "p-xp");
    var big = el("span", "p-big", "+0");
    var sub = el("div", "p-sub");
    sub.appendChild(document.createTextNode("XP nesta sessão"));
    sub.appendChild(document.createElement("br"));
    sub.appendChild(document.createTextNode(view.summary));
    xp.appendChild(big);
    xp.appendChild(sub);
    win.appendChild(xp);

    var lvl = el("div", "p-lvl");
    var tag = el("span", "e-tag");
    tag.appendChild(el("span", "", view.level_text));
    lvl.appendChild(tag);
    lvl.appendChild(el("span", "l", view.remaining_text));
    win.appendChild(lvl);

    var bar = el("div", "e-bar");
    bar.appendChild(el("div", "frame"));
    var a = el("div", "a");
    var b = el("div", "b");
    bar.appendChild(a);
    bar.appendChild(b);
    win.appendChild(bar);
    var legend = el("div", "p-legend");
    legend.appendChild(document.createTextNode("▨ antes   "));
    var g = el("span", "", "▨");
    g.style.color = "var(--terra)";
    legend.appendChild(g);
    legend.appendChild(document.createTextNode(" ganho hoje"));
    win.appendChild(legend);
    var up = el("div", "p-up", "");
    win.appendChild(up);

    a.style.width = widthFor(view.a_pct);
    b.style.left = "calc(" + widthFor(view.a_pct) + " + 4px)";

    if (view.rows.length) {
      var rows = el("div", "p-rows");
      view.rows.forEach(function (r) {
        var row = el("div");
        row.appendChild(el("span", "e-circ", r.mark));
        row.appendChild(document.createTextNode(r.text + (r.delta ? " " : "")));
        if (r.delta) row.appendChild(el("span", "e-muted", r.delta));
        rows.appendChild(row);
      });
      win.appendChild(rows);
    }
    if (view.badge || view.records.length) {
      var extra = el("div", "p-extra");
      if (view.badge) {
        var bt = el("span", "e-tag");
        bt.appendChild(el("span", "", view.badge));
        extra.appendChild(bt);
      }
      view.records.forEach(function (r) { extra.appendChild(el("span", "p-rec", r)); });
      win.appendChild(extra);
    }

    win.appendChild(el("div", "p-foot", view.footer));
    var btnRow = el("div", "p-btn");
    var btn = el("button", "e-btn", "Fechar");
    btn.onclick = close;
    btnRow.appendChild(btn);
    win.appendChild(btnRow);
    root.appendChild(win);
    reportHeight();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(reportHeight);

    // animate: terra part grows while the number counts up
    void b.offsetWidth; // force style calc so width 0 -> target transitions
    window.requestAnimationFrame(function () {
      b.style.width = widthFor(view.b_pct);
    });
    countUp(big, view.xp, function () {
      big.textContent = "+" + view.xp;
      if (view.level_up) {
        up.textContent = view.level_up_text;
        sound("level", cfg.volume);
      }
    });
  }

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") close();
  });

  window.ebbinPopup = {
    setConfig: function (c) { for (var k in c) cfg[k] = c[k]; },
    show: show,
  };
})(window);
