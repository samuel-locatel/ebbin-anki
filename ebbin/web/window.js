/* Ebbin window: Métricas / Objetivos / Ajustes. Pure view helpers are exported on
   ebbinWin for tests; all user strings reach the DOM through textContent. */
(function (window) {
  "use strict";
  var TABS = [["metrics", "Métricas"], ["objectives", "Objetivos"], ["settings", "Ajustes"]];
  var cfg = null, webCfg = { sounds_enabled: true, volume: 0.8, dark_theme: "night" };
  var root = null, body = null, tabEls = {}, current = "metrics";
  var filters = { scope: "active", period: "30d" };
  var pending = {}, seq = 0, token = 0;
  var editing = null; // objective id being edited, "" = new, null = none

  // ---- settings spec (every key of config.json) ---------------------------------------
  var FIELDS = [
    { path: "budget_min", label: "Orçamento diário (min)", type: "number", min: 1, max: 600, step: 1 },
    { group: "Pomodoro" },
    { path: "pomodoro.focus", label: "Foco (min)", type: "number", min: 1, max: 180, step: 1 },
    { path: "pomodoro.short", label: "Pausa curta (min)", type: "number", min: 1, max: 60, step: 1 },
    { path: "pomodoro.long", label: "Pausa longa (min)", type: "number", min: 1, max: 120, step: 1 },
    { path: "pomodoro.cycles", label: "Ciclos até a pausa longa", type: "number", min: 1, max: 12, step: 1 },
    { path: "pomodoro.autostart", label: "Iniciar o pomodoro ao entrar na revisão", type: "bool" },
    { path: "pomodoro.idle_pause_s", label: "Pausar por inatividade (s)", type: "number", min: 10, max: 3600, step: 10 },
    { group: "Botão Fácil" },
    { path: "easy_cap.enabled", label: "Limitar o intervalo do Fácil", type: "bool" },
    { path: "easy_cap.ratio", label: "Razão máxima do Fácil (1,2 a 3,0)", type: "number", min: 1.2, max: 3, step: 0.1 },
    { path: "easy_cap.first_max_days", label: "Máx. de dias no primeiro intervalo", type: "number", min: 1, max: 30, step: 1 },
    { group: "Sons" },
    { path: "sounds.enabled", label: "Sons ligados", type: "bool" },
    { path: "sounds.volume", label: "Volume", type: "range", min: 0, max: 1, step: 0.05, test: true },
    { group: "Aparência" },
    { path: "dark_theme", label: "Tema escuro", type: "radio",
      options: [["night", "Caderno à noite"], ["slate", "Quadro-negro"]] },
    { path: "skin", label: "Visual desenhado em todo o Anki", type: "bool" },
    { group: "Importação" },
    { path: "import.move_after", label: "Mover o arquivo depois de importar", type: "bool" },
    { path: "import.dest", label: "Pasta de destino", type: "text" },
    { path: "import.dupe", label: "Cards duplicados", type: "radio",
      options: [["preserve", "preservar"], ["update", "atualizar"]] },
    { group: "Avançado" },
    { path: "auto_new_per_day", label: "Ajustar novos por dia automaticamente (objetivo ativo)", type: "bool" },
    { path: "mastered_days", label: "Dominado a partir de (dias de estabilidade)", type: "number", min: 1, max: 3650, step: 1 },
    { path: "rescued_r", label: "Resgatado abaixo de (retrievability)", type: "number", min: 0.5, max: 0.99, step: 0.01 },
  ];

  // ---- pure helpers -------------------------------------------------------------------
  function isNum(v) { return typeof v === "number" && isFinite(v); }
  function pct(v) { return isNum(v) ? Math.round(v * 100) + "%" : "–"; }
  function dec(n, d) { return Number(n).toFixed(d === undefined ? 1 : d).replace(".", ","); }
  function leaf(n) { var p = String(n).split("::"); return p[p.length - 1]; }

  function getPath(o, path) { return path.split(".").reduce(function (a, k) { return a == null ? a : a[k]; }, o); }
  function setPath(o, path, v) {
    var ks = path.split("."), last = ks.pop();
    var t = ks.reduce(function (a, k) { if (!a[k] || typeof a[k] !== "object") a[k] = {}; return a[k]; }, o);
    t[last] = v;
  }

  /** field values: {path: value} (numbers already numeric) -> nested config patch. */
  function buildConfig(values) {
    var out = {};
    Object.keys(values).forEach(function (p) { setPath(out, p, values[p]); });
    return out;
  }

  function consistencyText(c, budget) {
    return {
      met: Math.round((c.met_pct || 0) * 100) + "% dos dias com desafio",
      budget: c.within_budget + " de " + c.of_days + " dias dentro dos " + budget + " min",
      streak: "sequência atual " + c.streak.current + " · recorde " + c.streak.best,
    };
  }

  function deckItems(list) {
    return list.slice().sort(function (a, b) {
      if (!isNum(a.acc)) return 1;
      if (!isNum(b.acc)) return -1;
      return a.acc - b.acc;
    }).map(function (d) {
      return { label: leaf(d.deck), value: d.acc, text: pct(d.acc) + " · " + d.lapses + (d.lapses === 1 ? " lapso" : " lapsos") };
    });
  }

  function tagLines(list) {
    return list.map(function (t) {
      return t.a + " " + pct(t.acc_a) + " (" + (isNum(t.sec_a) ? dec(t.sec_a) + " s" : "–") + ") vs " +
        t.b + " " + pct(t.acc_b) + " (" + (isNum(t.sec_b) ? dec(t.sec_b) + " s" : "–") + ")";
    });
  }

  function retentionText(im) {
    return "Retenção real " + pct(im.true_retention) + " · meta " + pct(im.desired_retention);
  }

  function hourLabels() {
    var out = [];
    for (var i = 0; i < 24; i++) out.push(i % 6 === 0 ? String(i) : "");
    return out;
  }

  function loadNote(load) {
    return load.first_over ? "No ritmo atual você passa do orçamento em " + load.first_over
      : "Dentro do orçamento nos próximos 30 dias";
  }

  function weekLabels(n) {
    var out = [];
    for (var i = 0; i < n; i++) out.push(i === n - 1 ? "agora" : (i % 3 === 0 ? "-" + (n - 1 - i) + "s" : ""));
    return out;
  }

  function agoName(ago) { return ago === 0 ? "esta semana" : ago === 1 ? "semana passada" : "há " + ago + " semanas"; }
  function weekName(i, n) { return agoName(n - 1 - i); }

  function secs(v) {
    var r = Math.round(v * 10) / 10;
    return (r % 1 ? dec(r) : String(r)) + " s";
  }

  /** Axis floor for the retention line: 10 points below the worst week, so small changes stay visible. */
  function retentionFloor(series) {
    var nums = series.filter(isNum);
    if (!nums.length) return 0;
    return Math.max(0, (Math.floor(Math.min.apply(null, nums) * 10) - 1) / 10);
  }

  function cards(v) { return v + (v === 1 ? " card" : " cards"); }

  function dayLabels(n) {
    var out = [];
    for (var i = 0; i < n; i++) out.push(i === 0 ? "hoje" : (i % 7 === 0 ? "+" + i + "d" : ""));
    return out;
  }

  function stars(n) { return "★★★".slice(0, n) + "☆☆☆".slice(0, 3 - n); }

  function objectiveMeta(it) {
    var parts = [];
    if (it.countdown) parts.push(it.countdown);
    parts.push(it.new_remaining + " novos restantes");
    if (isNum(it.pace)) parts.push(it.pace + " novos/dia");
    return parts.join(" · ");
  }

  function summaryText(s) {
    return s.mastered + " dominados · " + s.study_days + " dias de estudo · " +
      (isNum(s.accuracy) ? pct(s.accuracy) + " de acerto" : "sem respostas");
  }

  /** Roots with a checked ancestor are redundant (the parent already covers them). */
  function normalizeRoots(roots) {
    var set = {};
    roots.forEach(function (r) { set[r] = true; });
    return roots.filter(function (r) {
      var parts = r.split("::");
      for (var i = 1; i < parts.length; i++) if (set[parts.slice(0, i).join("::")]) return false;
      return true;
    });
  }

  function coveredBy(name, roots) {
    return roots.some(function (r) { return name === r || name.indexOf(r + "::") === 0; });
  }

  function isInherited(name, roots) {
    return coveredBy(name, roots) && roots.indexOf(name) < 0;
  }

  // ---- dom helpers ----------------------------------------------------------------------
  function h(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }
  function btn(label, cls, onclick) {
    var b = h("button", cls || "e-lnk", label);
    b.type = "button";
    b.onclick = onclick;
    return b;
  }
  function clear(n) { n.textContent = ""; }

  function call(cmd, arg, cb) {
    var id = ++seq;
    pending[id] = cb;
    window.ebbinSend("ebbinwin:" + cmd + ":" + JSON.stringify({ id: id, arg: arg === undefined ? null : arg }));
  }

  function receive(id, ok, result) {
    var cb = pending[id];
    delete pending[id];
    if (cb) cb(ok, result);
  }

  // ---- metrics --------------------------------------------------------------------------
  function chips(def, key, rerun) {
    var row = h("div", "w-chips");
    def.forEach(function (o) {
      var c = btn(o[1], "w-chip" + (filters[key] === o[0] ? " on" : ""), function () { filters[key] = o[0]; rerun(); });
      row.appendChild(c);
    });
    return row;
  }

  function section(title) {
    var s = h("section", "w-sec");
    s.appendChild(h("h3", "e-hand e-chalky w-h", title));
    return s;
  }

  function note(text, cls) { return h("div", "w-note " + (cls || "e-muted"), text); }

  function renderMetrics() {
    clear(body);
    var bar = h("div", "w-filters");
    bar.appendChild(chips([["active", "objetivo ativo"], ["all", "tudo"]], "scope", renderMetrics));
    bar.appendChild(chips([["30d", "30 d"], ["12w", "12 sem"], ["all", "tudo"]], "period", renderMetrics));
    body.appendChild(bar);
    var box = h("div", "w-metrics");
    body.appendChild(box);
    box.appendChild(note("carregando…"));
    var my = ++token;
    call("metrics", filters, function (ok, p) {
      if (my !== token || current !== "metrics") return;
      clear(box);
      if (!ok) { box.appendChild(note(String(p), "w-err")); return; }
      if (p.scope_fallback) box.appendChild(note("sem objetivo ativo — mostrando tudo"));
      if (p.empty) { box.appendChild(note("ainda sem dados suficientes")); return; }
      drawMetrics(box, p);
    });
  }

  function drawMetrics(box, p) {
    var C = window.ebbinCharts;
    var s1 = section("Consistência");
    var t = consistencyText(p.consistency, cfg.budget_min);
    s1.appendChild(C.heatmap(p.consistency.calendar));
    [t.met, t.budget, t.streak].forEach(function (x) { s1.appendChild(h("div", "w-line", x)); });
    box.appendChild(s1);

    var s2 = section("O que melhorar");
    var im = p.improve;
    var decks = deckItems(im.by_deck_accuracy);
    s2.appendChild(h("div", "w-sub", "Acerto por deck (pior primeiro)"));
    s2.appendChild(decks.length ? C.barList(decks) : note("nenhum deck com respostas suficientes"));
    var tags = tagLines(im.by_tag_compare);
    if (tags.length) {
      s2.appendChild(h("div", "w-sub", "Comparações por tag"));
      tags.forEach(function (x) { s2.appendChild(h("div", "w-line", x)); });
    }
    if (im.problem_cards.length) {
      s2.appendChild(h("div", "w-sub", "Cards problemáticos"));
      im.problem_cards.forEach(function (pc) {
        var r = h("div", "w-line w-pc");
        r.appendChild(h("span", "", pc.lapses + (pc.lapses === 1 ? " lapso" : " lapsos") + " · card " + pc.cid));
        r.appendChild(btn("editar", "e-lnk w-small", function () { call("browse", pc.cid, function () {}); }));
        s2.appendChild(r);
      });
    }
    s2.appendChild(h("div", "w-sub", retentionText(im)));
    if (im.retention_hint) s2.appendChild(note(im.retention_hint, "w-hint"));
    s2.appendChild(h("div", "w-sub", "Acerto por hora do dia"));
    s2.appendChild(C.bars(im.accuracy_by_hour, { height: 130, max: 1, labels: hourLabels(), title: "acerto por hora",
      yfmt: pct, tip: function (i, v) { return i + "h: " + pct(v) + " de acerto"; } }));
    box.appendChild(s2);

    var s3 = section("Eficiência");
    var ef = p.efficiency;
    s3.appendChild(h("div", "w-sub", "Segundos por card (por semana)"));
    var trend = ef.sec_per_card_trend, lastWeek = trend.length ? trend[trend.length - 1].week : 0;
    s3.appendChild(C.line(trend.map(function (x) { return x.sec; }), { height: 140, title: "segundos por card",
      yfmt: secs, labels: trend.map(function (x, i) {
        var ago = lastWeek - x.week;
        return ago === 0 ? "agora" : (i === 0 || ago % 3 === 0 ? "-" + ago + "s" : "");
      }),
      tip: function (i, v) { return agoName(lastWeek - trend[i].week) + ": " + secs(v) + " por card"; } }));
    if (ef.sec_by_items.length) {
      s3.appendChild(h("div", "w-sub", "Segundos por número de itens"));
      s3.appendChild(C.bars(ef.sec_by_items.map(function (x) { return x.sec; }),
        { height: 120, labels: ef.sec_by_items.map(function (x) { return x.items + (x.items === 1 ? " item" : " itens"); }),
          title: "segundos por itens", yfmt: secs,
          tip: function (i, v) { var x = ef.sec_by_items[i]; return x.items + (x.items === 1 ? " item: " : " itens: ") + secs(v) + " (" + cards(x.n) + ")"; } }));
    }
    if (ef.items_hint) s3.appendChild(note(ef.items_hint, "w-hint"));
    s3.appendChild(h("div", "w-line", dec(ef.mastered_per_hour) + " dominados por hora de estudo"));
    s3.appendChild(h("div", "w-sub", "Cards previstos por dia (próximos 30 dias) e capacidade"));
    s3.appendChild(C.line(ef.load.series, { height: 150, zero: true, integer: true, title: "carga projetada",
      labels: dayLabels(ef.load.series.length), yfmt: String,
      tip: function (i, v) { return (i === 0 ? "hoje" : "daqui a " + i + (i === 1 ? " dia" : " dias")) + ": " + cards(v); },
      refs: [{ value: ef.load.capacity, label: "capacidade (" + ef.load.capacity + "/dia)", dashed: true }] }));
    s3.appendChild(note(loadNote(ef.load), ef.load.first_over ? "w-hint" : "e-muted"));
    box.appendChild(s3);

    var s4 = section("Curva");
    s4.appendChild(h("div", "w-sub", "Retenção por semana"));
    s4.appendChild(C.line(p.curve.retention_series, { height: 150, min: retentionFloor(p.curve.retention_series), max: 1, smooth: true,
      labels: weekLabels(12), color: "var(--green)", title: "retenção por semana", yfmt: pct,
      tip: function (i, v) { return weekName(i, 12) + ": " + pct(v) + " de retenção"; } }));
    s4.appendChild(h("div", "w-sub", "Cards resgatados por semana"));
    s4.appendChild(C.bars(p.curve.rescued_by_week, { height: 120, terra: true, labels: weekLabels(12), title: "resgatados por semana",
      integer: true, yfmt: String, tip: function (i, v) { return weekName(i, 12) + ": " + cards(v) + " resgatados"; } }));
    box.appendChild(s4);
  }

  // ---- objectives -----------------------------------------------------------------------
  var objData = null, objMsg = "", summaries = {};

  function renderObjectives() {
    clear(body);
    body.appendChild(note("carregando…"));
    var my = ++token;
    call("objectives", null, function (ok, p) {
      if (my !== token || current !== "objectives") return;
      if (!ok) { clear(body); body.appendChild(note(String(p), "w-err")); return; }
      objData = p;
      drawObjectives();
    });
  }

  function applyPayload(ok, p, after) {
    if (!ok) { objMsg = String(p); drawObjectives(); return; }
    objMsg = "";
    objData = after ? after(p) : p;
    drawObjectives();
  }

  function confirmButton(label, onConfirm) {
    var armed = false, timer = null;
    var b = btn(label, "e-lnk w-small", function () {
      if (!armed) {
        armed = true; b.textContent = "tem certeza?"; b.classList.add("w-arm");
        timer = window.setTimeout(function () { armed = false; b.textContent = label; b.classList.remove("w-arm"); }, 4000);
        return;
      }
      window.clearTimeout(timer);
      onConfirm();
    });
    return b;
  }

  function objectiveRow(it, active) {
    var r = h("div", "w-obj" + (active ? " active" : ""));
    var top = h("div", "e-row");
    var name = h("span", "w-oname", it.name);
    if (active) name.classList.add("e-tag");
    top.appendChild(name);
    top.appendChild(h("span", "w-stars", it.archived ? "" : stars(it.stars)));
    r.appendChild(top);
    r.appendChild(h("div", "e-muted w-ometa", it.archived ? "arquivado" : objectiveMeta(it)));
    var sum = it.archived ? (it.archived_summary || summaries[it.id]) : summaries[it.id];
    if (sum) r.appendChild(h("div", "w-line", summaryText(sum)));
    var acts = h("div", "w-acts");
    if (!it.archived && !active) acts.appendChild(btn("ativar", "e-lnk w-small", function () {
      call("obj_activate", it.id, function (ok, p) { applyPayload(ok, p); });
    }));
    if (!it.archived) {
      acts.appendChild(btn("editar", "e-lnk w-small", function () { editing = it.id; drawObjectives(); }));
      acts.appendChild(confirmButton("arquivar", function () {
        call("obj_archive", it.id, function (ok, p) {
          if (ok) summaries[it.id] = p.summary;
          applyPayload(ok, p, function (x) { return x.payload; });
        });
      }));
    }
    acts.appendChild(confirmButton("excluir", function () {
      call("obj_delete", it.id, function (ok, p) {
        if (ok && editing === it.id) editing = null;
        applyPayload(ok, p);
      });
    }));
    r.appendChild(acts);
    return r;
  }

  function objectiveForm(it) {
    var f = h("div", "w-form");
    f.appendChild(h("div", "w-sub", it ? "Editar objetivo" : "Novo objetivo"));
    var name = h("input", "w-in"); name.type = "text"; name.placeholder = "nome"; name.value = it ? it.name : "";
    var date = h("input", "w-in"); date.type = "date"; date.value = it && it.exam_date ? it.exam_date : "";
    f.appendChild(labeled("Nome", name));
    f.appendChild(labeled("Data da prova (opcional)", date));
    var roots = it ? it.deck_roots.slice() : [];
    var list = h("div", "w-decks");
    function drawDecks() {
      clear(list);
      objData.decks.forEach(function (d) {
        var row = h("label", "w-deck");
        var depth = d.split("::").length - 1;
        row.style.paddingLeft = depth * 16 + "px";
        var cb = h("input"); cb.type = "checkbox";
        cb.checked = coveredBy(d, roots);
        cb.disabled = isInherited(d, roots);
        cb.onchange = function () {
          if (cb.checked) roots.push(d); else roots = roots.filter(function (x) { return x !== d; });
          roots = normalizeRoots(roots);
          drawDecks();
        };
        row.appendChild(cb);
        row.appendChild(h("span", "", " " + leaf(d)));
        list.appendChild(row);
      });
    }
    drawDecks();
    f.appendChild(labeled("Decks (marcar um deck inclui os subdecks)", list));
    var acts = h("div", "w-acts");
    acts.appendChild(btn("salvar", "e-btn", function () {
      var data = { name: name.value, exam_date: date.value || null, deck_roots: normalizeRoots(roots) };
      if (it) data.id = it.id;
      call("obj_save", data, function (ok, p) { if (ok) editing = null; applyPayload(ok, p); });
    }));
    acts.appendChild(btn("cancelar", "e-lnk", function () { editing = null; objMsg = ""; drawObjectives(); }));
    f.appendChild(acts);
    return f;
  }

  function labeled(text, input) {
    var l = h("div", "w-field");
    l.appendChild(h("div", "e-muted w-flabel", text));
    l.appendChild(input);
    return l;
  }

  function drawObjectives() {
    clear(body);
    if (objMsg) body.appendChild(note(objMsg, "w-err"));
    var items = objData.items;
    var act = items.filter(function (i) { return i.id === objData.active_id && !i.archived; });
    var others = items.filter(function (i) { return i.id !== objData.active_id && !i.archived; });
    var arch = items.filter(function (i) { return i.archived; });
    if (!items.length) body.appendChild(note("nenhum objetivo ainda"));
    act.forEach(function (i) { body.appendChild(objectiveRow(i, true)); });
    others.forEach(function (i) { body.appendChild(objectiveRow(i, false)); });
    if (arch.length) {
      body.appendChild(h("div", "w-sub", "Arquivados"));
      arch.forEach(function (i) { body.appendChild(objectiveRow(i, false)); });
    }
    if (editing !== null) {
      var cur = items.filter(function (i) { return i.id === editing; })[0] || null;
      body.appendChild(objectiveForm(cur));
    } else {
      body.appendChild(btn("+ novo objetivo", "e-lnk", function () { editing = ""; drawObjectives(); }));
    }
  }

  // ---- settings ---------------------------------------------------------------------------
  var inputs = {}, setMsg = null;

  function renderSettings() {
    clear(body);
    inputs = {};
    var form = h("div", "w-settings");
    var group = null;
    FIELDS.forEach(function (f) {
      if (f.group) { group = h("div", "w-group"); group.appendChild(h("h3", "e-hand e-chalky w-h", f.group)); form.appendChild(group); return; }
      var host = group || form;
      var val = getPath(cfg, f.path);
      var row = h("div", "w-frow");
      if (f.type === "bool") {
        var cb = h("input"); cb.type = "checkbox"; cb.checked = !!val; inputs[f.path] = function () { return cb.checked; };
        var l = h("label", "w-check"); l.appendChild(cb); l.appendChild(h("span", "", " " + f.label)); row.appendChild(l);
      } else if (f.type === "radio") {
        row.appendChild(h("div", "w-flabel", f.label));
        var wrap = h("div", "w-radios"), name = "r-" + f.path;
        f.options.forEach(function (o) {
          var rb = h("input"); rb.type = "radio"; rb.name = name; rb.value = o[0]; rb.checked = val === o[0];
          var lb = h("label", "w-check"); lb.appendChild(rb); lb.appendChild(h("span", "", " " + o[1])); wrap.appendChild(lb);
        });
        inputs[f.path] = function () { var c = wrap.querySelector("input:checked"); return c ? c.value : val; };
        row.appendChild(wrap);
      } else {
        row.appendChild(h("div", "w-flabel", f.label));
        var inp = h("input", "w-in");
        inp.type = f.type === "range" ? "range" : (f.type === "text" ? "text" : "number");
        if (f.type !== "text") { inp.min = f.min; inp.max = f.max; inp.step = f.step; }
        inp.value = val;
        inputs[f.path] = function () {
          if (f.type === "text") return inp.value;
          return inp.value === "" ? null : Number(inp.value);
        };
        row.appendChild(inp);
        if (f.test) row.appendChild(btn("testar som", "e-lnk w-small", function () {
          if (window.ebbinSound) { try { window.ebbinSound("good", Number(inp.value)); } catch (e) { /* no audio */ } }
        }));
      }
      host.appendChild(row);
    });
    setMsg = h("div", "w-note");
    form.appendChild(setMsg);
    var acts = h("div", "w-acts");
    acts.appendChild(btn("salvar", "e-btn", saveSettings));
    acts.appendChild(btn("Exportar dados", "e-lnk", function () {
      call("export", null, function (ok, r) { showSet(ok ? (r.saved ? "dados exportados" : "exportação cancelada") : String(r), !ok); });
    }));
    acts.appendChild(confirmButton("Zerar dados do Ebbin", function () {
      call("reset", null, function (ok, r) { showSet(ok ? "dados do Ebbin zerados" : String(r), !ok); });
    }));
    form.appendChild(acts);
    body.appendChild(form);
  }

  function showSet(text, err) {
    if (!setMsg) return;
    setMsg.textContent = text;
    setMsg.className = "w-note " + (err ? "w-err" : "w-ok");
  }

  function saveSettings() {
    var values = {};
    Object.keys(inputs).forEach(function (p) { values[p] = inputs[p](); });
    call("settings_save", buildConfig(values), function (ok, r) {
      if (!ok) { showSet(String(r), true); return; }
      cfg = r.cfg;
      showSet("ajustes salvos", false);
    });
  }

  // ---- shell ------------------------------------------------------------------------------
  function select(tab) {
    if (!tabEls[tab]) tab = "metrics";
    current = tab;
    TABS.forEach(function (t) { tabEls[t[0]].className = t[0] === tab ? "on" : ""; });
    if (!cfg) return;
    if (tab === "metrics") renderMetrics();
    else if (tab === "objectives") renderObjectives();
    else renderSettings();
  }

  function build(tab) {
    window.ebbinSketch.ensureFilters();
    root = document.getElementById("ebbin-win");
    setTheme(window.ebbinSketch.themeClass(webCfg.dark_theme));
    clear(root);
    var win = h("div", "e-win e-chalky w-win");
    var tabs = h("div", "e-tabs");
    TABS.forEach(function (t) {
      var s = h("span", "", t[1]);
      s.onclick = function () { select(t[0]); };
      tabEls[t[0]] = s;
      tabs.appendChild(s);
    });
    win.appendChild(tabs);
    body = h("div", "w-body");
    win.appendChild(body);
    root.appendChild(win);
    current = tab;
    call("init", null, function (ok, r) {
      if (!ok) { body.appendChild(note(String(r), "w-err")); return; }
      cfg = r.cfg;
      webCfg = Object.assign(webCfg, r.web);
      setTheme(window.ebbinSketch.themeClass(webCfg.dark_theme));
      select(current);
    });
    select(tab);
  }

  function setTheme(cls) {
    if (!root) return;
    root.classList.remove("night", "slate");
    if (cls) root.classList.add(cls);
  }

  var api = {
    FIELDS: FIELDS, pct: pct, dec: dec, leaf: leaf, getPath: getPath, buildConfig: buildConfig,
    consistencyText: consistencyText, deckItems: deckItems, tagLines: tagLines, hourLabels: hourLabels,
    loadNote: loadNote, retentionFloor: retentionFloor, retentionText: retentionText, weekLabels: weekLabels, stars: stars, objectiveMeta: objectiveMeta,
    summaryText: summaryText, normalizeRoots: normalizeRoots, coveredBy: coveredBy, isInherited: isInherited,
    init: function (o) { build(o && o.tab ? o.tab : "metrics"); },
    select: select, receive: receive, setTheme: setTheme,
    setConfig: function (c) {
      webCfg = Object.assign(webCfg, c || {});
      if (cfg) { cfg.sounds.enabled = webCfg.sounds_enabled; cfg.sounds.volume = webCfg.volume; cfg.dark_theme = webCfg.dark_theme; }
      setTheme(window.ebbinSketch.themeClass(webCfg.dark_theme));
    },
  };
  window.ebbinWin = api;
})(window);
