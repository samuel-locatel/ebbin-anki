/* Ebbin import dialog: renders views built by ebbin/ui/importview.py.
   All file/deck names reach the DOM through textContent. */
(function (window) {
  "use strict";
  var cfg = { dark_theme: "night" };
  var busy = false;

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }
  function send(cmd) { window.ebbinSend("ebbinimp:" + cmd); }

  function button(label, cmd, disabled) {
    var b = el("button", "e-btn i-btn", label);
    if (disabled) b.disabled = true;
    else b.onclick = function () { send(cmd); };
    return b;
  }

  function table(heads, rows, cells) {
    var t = el("table", "i-table");
    var tr = el("tr");
    heads.forEach(function (h) { tr.appendChild(el("th", "e-hand", h)); });
    t.appendChild(tr);
    rows.forEach(function (r) {
      var row = el("tr", r.ok === false || r.failed ? "bad" : "");
      cells(r).forEach(function (c, i) {
        var td = el("td", i > 0 && typeof c === "number" ? "num" : "", String(c));
        row.appendChild(td);
      });
      t.appendChild(row);
    });
    return t;
  }

  function render(view) {
    window.ebbinSketch.ensureFilters();
    var root = document.getElementById("ebbin-import");
    root.className = "ebbin " + window.ebbinSketch.themeClass(cfg.dark_theme);
    root.textContent = "";
    var win = el("div", "e-win");
    var head = el("div", "e-row");
    head.appendChild(el("span", "e-hand p-title", view.stage === "results" ? "resultado" : "importar lotes"));
    var tools = el("div", "i-tools");
    if (view.stage !== "results") {
      tools.appendChild(button("Escolher arquivos…", "pick_files"));
      tools.appendChild(button("Escolher pasta…", "pick_folder"));
    }
    head.appendChild(tools);
    win.appendChild(head);

    if (view.stage === "empty") {
      win.appendChild(el("p", "e-muted", "Nenhum arquivo escolhido ainda."));
    } else if (view.stage === "preview") {
      var wrap = el("div", "i-scroll");
      wrap.appendChild(table(["Arquivo", "Tipo de nota", "Deck", "Notas", "Situação"], view.rows,
        function (r) { return [r.name, r.notetype, r.deck, r.notes, r.status]; }));
      win.appendChild(wrap);
      win.appendChild(el("div", "i-total", view.total_text));
      if (view.note) win.appendChild(el("div", "e-hint", view.note));
      var foot = el("div", "i-foot");
      foot.appendChild(button(view.button, "import", !view.can_import));
      win.appendChild(foot);
    } else if (view.stage === "importing") {
      win.appendChild(el("p", "e-hand i-wait", "importando…"));
    } else if (view.stage === "results") {
      var wrap2 = el("div", "i-scroll");
      wrap2.appendChild(table(["Arquivo", "Novas", "Já existiam", "Erros"], view.rows,
        function (r) { return [r.name, r.new, r.existing, r.errors]; }));
      win.appendChild(wrap2);
      win.appendChild(el("div", "i-total", view.total_text));
      if (view.warning) win.appendChild(el("div", "e-hint warn", view.warning));
      var f2 = el("div", "i-foot");
      f2.appendChild(button("Importar outros…", "pick_files"));
      f2.appendChild(button("Fechar", "close"));
      win.appendChild(f2);
    }
    root.appendChild(win);
  }

  window.ebbinImport = {
    setConfig: function (c) { cfg = c; },
    setTheme: function (cls) {
      var root = document.getElementById("ebbin-import");
      if (root) root.className = "ebbin " + cls;
    },
    show: render,
  };
})(window);
