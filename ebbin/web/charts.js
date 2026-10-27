/* Ebbin hand-drawn SVG charts. Geometry helpers are pure (tested in tests/js/charts.test.mjs);
   builders create nodes with createElementNS and set labels via textContent only. */
(function (window) {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";

  // ---- pure geometry ----------------------------------------------------------------
  function r1(n) { return Math.round(n * 10) / 10; }

  /** Linear map d0..d1 -> r0..r1 (clamped). A flat domain maps to the range midpoint. */
  function scale(d0, d1, r0, r1_) {
    return function (v) {
      if (d1 === d0) return (r0 + r1_) / 2;
      var f = (v - d0) / (d1 - d0);
      f = Math.max(0, Math.min(1, f));
      return r0 + (r1_ - r0) * f;
    };
  }

  function isNum(v) { return typeof v === "number" && isFinite(v); }

  /** Path `d` for points [{x,y}|null]; null breaks the line. smooth -> quadratic midpoints. */
  function pathD(points, smooth) {
    var d = "", run = [];
    function flush() {
      if (run.length === 0) return;
      d += (d ? " " : "") + "M" + r1(run[0].x) + " " + r1(run[0].y);
      if (run.length === 1) { d += " L" + r1(run[0].x) + " " + r1(run[0].y); run = []; return; }
      for (var i = 1; i < run.length; i++) {
        if (smooth && i < run.length - 1) {
          var mx = (run[i].x + run[i + 1].x) / 2, my = (run[i].y + run[i + 1].y) / 2;
          d += " Q" + r1(run[i].x) + " " + r1(run[i].y) + " " + r1(mx) + " " + r1(my);
        } else {
          d += " L" + r1(run[i].x) + " " + r1(run[i].y);
        }
      }
      run = [];
    }
    points.forEach(function (p) { if (p) run.push(p); else flush(); });
    flush();
    return d;
  }

  /** Series of numbers|null -> points in a w*h box (inner padding pad; padL = left margin). */
  function seriesPoints(values, w, h, pad, vmin, vmax, padL) {
    var n = values.length;
    var sx = scale(0, Math.max(1, n - 1), isNum(padL) ? padL : pad, w - pad);
    var sy = scale(vmin, vmax, h - pad, pad);
    return values.map(function (v, i) { return isNum(v) ? { x: sx(i), y: sy(v) } : null; });
  }

  function extent(values, floor0) {
    var nums = values.filter(isNum);
    if (!nums.length) return [0, 1];
    var lo = floor0 ? Math.min(0, Math.min.apply(null, nums)) : Math.min.apply(null, nums);
    var hi = Math.max.apply(null, nums);
    if (hi === lo) hi = lo + 1;
    return [lo, hi];
  }

  /** Round axis ticks covering lo..hi with about n intervals (steps 1/2/2,5/5 × 10^k). */
  function niceTicks(lo, hi, n, integer) {
    if (!(hi > lo)) hi = lo + 1;
    var raw = (hi - lo) / (n || 4), mag = Math.pow(10, Math.floor(Math.log10(raw))), step = 10 * mag;
    [1, 2, 2.5, 5].some(function (k) {
      var c = k * mag;
      if (c >= raw && (!integer || c % 1 === 0)) { step = c; return true; }
      return false;
    });
    if (integer) step = Math.max(1, step);
    var tlo = Math.floor(lo / step + 1e-9) * step, thi = Math.ceil(hi / step - 1e-9) * step, ticks = [];
    for (var v = tlo; v <= thi + step / 2; v += step) ticks.push(Math.round(v * 1e6) / 1e6);
    return { lo: ticks[0], hi: ticks[ticks.length - 1], ticks: ticks };
  }

  /** Hatch density 0..3 for minutes relative to the busiest day. */
  function hatchLevel(minutes, max) {
    if (!(minutes > 0) || !(max > 0)) return 0;
    return Math.max(1, Math.min(3, Math.ceil((minutes / max) * 3)));
  }

  /** Cells (oldest first) -> grid positions. Rows are weekdays (0 = segunda); columns are calendar
      weeks, the first one padded by the first cell's weekday. Without `weekday`, 7-day chunks. */
  function heatmapLayout(cells, size, gap) {
    var lead = cells.length && isNum(cells[0].weekday) ? cells[0].weekday : 0;
    var max = 0;
    cells.forEach(function (c) { if (c.minutes > max) max = c.minutes; });
    return cells.map(function (c, i) {
      var col = Math.floor((i + lead) / 7), row = isNum(c.weekday) ? c.weekday : i % 7;
      return { x: col * (size + gap), y: row * (size + gap), level: hatchLevel(c.minutes, max),
               met: !!c.met, minutes: c.minutes, day: c.day };
    });
  }

  /** Bars: values (numbers|null) -> rects inside w*h with baseline at h-pad (padL = left margin). */
  function barsLayout(values, w, h, pad, vmax, padL) {
    var left = isNum(padL) ? padL : pad;
    var n = values.length || 1, slot = (w - left - pad) / n, bw = slot * 0.62;
    var sy = scale(0, vmax > 0 ? vmax : 1, 0, h - 2 * pad);
    return values.map(function (v, i) {
      var bh = isNum(v) ? sy(v) : 0;
      return { x: r1(left + i * slot + (slot - bw) / 2), y: r1(h - pad - bh), w: r1(bw), h: r1(bh),
               slotX: r1(left + i * slot), slotW: r1(slot) };
    });
  }

  function pct(v) { return isNum(v) ? Math.round(v * 100) + "%" : "–"; }

  function leaf(name) { var p = String(name).split("::"); return p[p.length - 1]; }

  // ---- svg building -----------------------------------------------------------------
  function node(tag, attrs, text) {
    var n = document.createElementNS(NS, tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { n.setAttribute(k, String(attrs[k])); });
    if (text !== undefined) n.textContent = text;
    return n;
  }

  function root(w, h, label) {
    var s = node("svg", { viewBox: "0 0 " + w + " " + h, width: "100%", role: "img",
                          "aria-label": label || "gráfico", class: "e-chart" });
    s.style.maxWidth = w + "px";
    var defs = node("defs");
    [[1, 7], [2, 4.5], [3, 3]].forEach(function (l) {
      var p = node("pattern", { id: "e-hatch" + l[0], width: l[1], height: l[1], patternUnits: "userSpaceOnUse",
                                patternTransform: "rotate(-50)" });
      p.appendChild(node("line", { x1: 0, y1: 0, x2: 0, y2: l[1], stroke: "var(--ink)", "stroke-width": 2 }));
      defs.appendChild(p);
    });
    var pt = node("pattern", { id: "e-hatchT", width: 4.5, height: 4.5, patternUnits: "userSpaceOnUse",
                               patternTransform: "rotate(-50)" });
    pt.appendChild(node("line", { x1: 0, y1: 0, x2: 0, y2: 4.5, stroke: "var(--terra)", "stroke-width": 2.2 }));
    defs.appendChild(pt);
    s.appendChild(defs);
    return s;
  }

  function label(x, y, text, anchor, cls) {
    var t = node("text", { x: r1(x), y: r1(y), "text-anchor": anchor || "start", class: cls || "e-ct" }, text);
    return t;
  }

  var AXIS_W = 44;

  /** Recessive gridlines + value labels on the left; returns the tick range actually drawn. */
  function yAxis(s, w, h, pad, ticks, fmt) {
    var sy = scale(ticks.lo, ticks.hi, h - pad, pad);
    ticks.ticks.forEach(function (v, i) {
      var y = r1(sy(v));
      if (i > 0) s.appendChild(node("line", { x1: AXIS_W, y1: y, x2: w - pad, y2: y, stroke: "var(--line)",
                                              "stroke-width": 1, "stroke-dasharray": "2 5" }));
      s.appendChild(label(AXIS_W - 7, y + 4, fmt(v), "end", "e-ct e-ct-s"));
    });
  }

  function tip(el, text) { if (text) el.appendChild(node("title", null, text)); return el; }

  function heatmap(cells) {
    var size = 20, gap = 5, lay = heatmapLayout(cells, size, gap);
    var lead = cells.length && isNum(cells[0].weekday) ? cells[0].weekday : 0;
    var cols = Math.ceil((cells.length + lead) / 7) || 1, left = 16;
    var w = left + cols * (size + gap), h = 7 * (size + gap);
    var s = root(w, h, "calendário de estudo, últimas 12 semanas");
    s.style.maxWidth = "440px";
    "stqqssd".split("").forEach(function (ch, r) {
      s.appendChild(label(0, r * (size + gap) + size - 5, ch, "start", "e-ct e-ct-s"));
    });
    var g = node("g", { style: "filter:url(#e-rough2)", transform: "translate(" + left + ",0)" });
    lay.forEach(function (c) {
      g.appendChild(node("rect", { x: c.x, y: c.y, width: size, height: size, rx: 3, fill: "none",
                                   stroke: "var(--line)", "stroke-width": 1.4 }));
      if (c.level > 0) {
        g.appendChild(node("rect", { x: c.x + 1, y: c.y + 1, width: size - 2, height: size - 2,
                                     fill: "url(#e-hatch" + c.level + ")" }));
      }
      if (c.met) g.appendChild(node("circle", { cx: c.x + size / 2, cy: c.y + size / 2, r: 3.4, fill: "var(--terra)" }));
    });
    s.appendChild(g);
    lay.forEach(function (c) {
      var t = node("title", null, Math.round(c.minutes) + " min" + (c.met ? " · desafio cumprido" : ""));
      var hit = node("rect", { x: c.x + left, y: c.y, width: size, height: size, fill: "transparent" });
      hit.appendChild(t);
      s.appendChild(hit);
    });
    return s;
  }

  /** items: [{label, value 0..1, text, sub?}] -> horizontal hatched bars, label left, text right. */
  function barList(items) {
    var rowH = 34, w = 560, lw = 170, bx = lw + 8, bw = w - bx - 90, h = Math.max(1, items.length) * rowH;
    var s = root(w, h, "lista de barras");
    items.forEach(function (it, i) {
      var y = i * rowH;
      s.appendChild(label(0, y + 21, it.label, "start", "e-ct"));
      var f = isNum(it.value) ? Math.max(0, Math.min(1, it.value)) : 0;
      var g = node("g", { style: "filter:url(#e-rough2)" });
      g.appendChild(node("rect", { x: bx, y: y + 8, width: bw, height: 16, rx: 8, fill: "none",
                                   stroke: "var(--ink)", "stroke-width": 1.8 }));
      if (f > 0) g.appendChild(node("rect", { x: bx + 3, y: y + 11, width: Math.max(2, (bw - 6) * f), height: 10,
                                              fill: "url(#e-hatch2)" }));
      s.appendChild(g);
      s.appendChild(label(w, y + 21, it.text, "end", "e-ct e-ct-b"));
    });
    return s;
  }

  function fmtDefault(v) { return String(Math.round(v * 100) / 100).replace(".", ","); }

  /** series: numbers|null. opts: {width,height,min,max,zero,smooth,refs:[{value,label}],labels:[],
      yfmt(v) for axis values, integer (whole-number ticks), tip(i, v) for the hover text} */
  function line(series, opts) {
    opts = opts || {};
    var w = opts.width || 560, h = opts.height || 150, pad = 18;
    var ext = extent(series.concat((opts.refs || []).map(function (r) { return r.value; })), opts.zero);
    var ticks = niceTicks(isNum(opts.min) ? opts.min : ext[0], isNum(opts.max) ? opts.max : ext[1], 4, opts.integer);
    var vmin = ticks.lo, vmax = ticks.hi;
    var s = root(w, h, opts.title || "gráfico de linha");
    var sy = scale(vmin, vmax, h - pad, pad);
    yAxis(s, w, h, pad, ticks, opts.yfmt || fmtDefault);
    s.appendChild(node("line", { x1: AXIS_W, y1: h - pad, x2: w - pad, y2: h - pad, stroke: "var(--line)", "stroke-width": 1.4 }));
    (opts.refs || []).forEach(function (r) {
      s.appendChild(node("line", { x1: AXIS_W, y1: r1(sy(r.value)), x2: w - pad, y2: r1(sy(r.value)),
                                   stroke: "var(--terra)", "stroke-width": 1.8, "stroke-dasharray": "7 5" }));  // no rough filter: a 0-height bbox makes it vanish
      if (r.label) s.appendChild(label(w - pad, sy(r.value) - 5, r.label, "end", "e-ct e-ct-t"));
    });
    var pts = seriesPoints(series, w, h, pad, vmin, vmax, AXIS_W);
    var d = pathD(pts, !!opts.smooth);
    if (d) s.appendChild(node("path", { d: d, fill: "none", stroke: opts.color || "var(--ink)", "stroke-width": 2.4,
                                        "stroke-linecap": "round", "stroke-linejoin": "round",
                                        style: "filter:url(#e-rough2)" }));
    pts.forEach(function (p, i) {
      if (p && series.length <= 16) s.appendChild(node("circle", { cx: r1(p.x), cy: r1(p.y), r: 2.6, fill: opts.color || "var(--ink)" }));
    });
    if (opts.labels) opts.labels.forEach(function (l, i) {
      if (l !== "" && l != null) s.appendChild(label(pts[i] ? pts[i].x : AXIS_W + i * (w - AXIS_W - pad) / Math.max(1, series.length - 1), h - 3, l, "middle", "e-ct e-ct-s"));
    });
    var fmt = opts.yfmt || fmtDefault;
    pts.forEach(function (p, i) {
      if (p) s.appendChild(tip(node("circle", { cx: r1(p.x), cy: r1(p.y), r: 9, fill: "transparent" }),
                               opts.tip ? opts.tip(i, series[i]) : fmt(series[i])));
    });
    return s;
  }

  /** values: numbers|null. opts: {width,height,max,labels:[],terra:bool,yfmt(v),integer,tip(i, v)} */
  function bars(values, opts) {
    opts = opts || {};
    var w = opts.width || 560, h = opts.height || 120, pad = 16;
    var ext = extent(values, true);
    var ticks = niceTicks(0, isNum(opts.max) ? opts.max : ext[1], 4, opts.integer);
    var s = root(w, h, opts.title || "gráfico de barras");
    yAxis(s, w, h, pad, ticks, opts.yfmt || fmtDefault);
    s.appendChild(node("line", { x1: AXIS_W, y1: h - pad, x2: w - pad, y2: h - pad, stroke: "var(--line)", "stroke-width": 1.4 }));
    var lay = barsLayout(values, w, h, pad, ticks.hi, AXIS_W);
    var g = node("g", { style: "filter:url(#e-rough2)" });
    lay.forEach(function (b, i) {
      if (b.h > 0) g.appendChild(node("rect", { x: b.x, y: b.y, width: b.w, height: b.h,
                                                fill: "url(#" + (opts.terra ? "e-hatchT" : "e-hatch2") + ")",
                                                stroke: opts.terra ? "var(--terra)" : "var(--ink)", "stroke-width": 1.6 }));
    });
    s.appendChild(g);
    if (opts.labels) lay.forEach(function (b, i) {
      var l = opts.labels[i];
      if (l !== "" && l != null) s.appendChild(label(b.x + b.w / 2, h - 3, l, "middle", "e-ct e-ct-s"));
    });
    var fmt = opts.yfmt || fmtDefault;
    lay.forEach(function (b, i) {
      if (!isNum(values[i])) return;
      s.appendChild(tip(node("rect", { x: b.slotX, y: pad, width: b.slotW, height: h - 2 * pad, fill: "transparent" }),
                        opts.tip ? opts.tip(i, values[i]) : fmt(values[i])));
    });
    return s;
  }

  window.ebbinCharts = {
    scale: scale, pathD: pathD, seriesPoints: seriesPoints, extent: extent, hatchLevel: hatchLevel,
    heatmapLayout: heatmapLayout, barsLayout: barsLayout, niceTicks: niceTicks, pct: pct, leaf: leaf,
    heatmap: heatmap, barList: barList, line: line, bars: bars,
  };
})(window);
