/* Ebbin skin: keeps the skin classes (ebbin-skin, page, night/slate) on <body>.
   Anki's reviewer rewrites body.className on every card and Anki toggles nightMode on
   theme changes, so a MutationObserver re-applies them whenever the class attribute changes. */
(function (window) {
  "use strict";
  var THEMES = ["night", "slate"];
  var cfg = { body_class: "", dark_theme: "night" };
  var observer = null;

  // Pure: which classes to add/remove so `current` carries `bodyClass` + `theme` only.
  function classDiff(current, bodyClass, theme) {
    var want = String(bodyClass || "").split(/\s+/).filter(Boolean);
    if (!want.length) return { add: [], remove: [] };
    if (theme) want.push(theme);
    return {
      add: want.filter(function (c) { return current.indexOf(c) < 0; }),
      remove: THEMES.filter(function (c) { return c !== theme && current.indexOf(c) >= 0; }),
    };
  }

  function apply() {
    var b = document.body;
    if (!b) return;
    var theme = window.ebbinSketch ? window.ebbinSketch.themeClass(cfg.dark_theme) : "";
    var d = classDiff(Array.prototype.slice.call(b.classList), cfg.body_class, theme);
    // Only touch the attribute when something differs, or the observer would loop.
    d.add.forEach(function (c) { b.classList.add(c); });
    d.remove.forEach(function (c) { b.classList.remove(c); });
  }

  window.ebbinSkin = {
    classDiff: classDiff,
    init: function (c) {
      for (var k in c) cfg[k] = c[k];
      if (window.ebbinSketch) window.ebbinSketch.ensureFilters();
      apply();
      if (!observer && window.MutationObserver && document.body) {
        observer = new MutationObserver(apply);
        observer.observe(document.body, { attributes: true, attributeFilter: ["class"] });
      }
    },
    setTheme: function (darkTheme) {
      if (darkTheme) cfg.dark_theme = darkTheme;
      apply();
    },
  };
})(window);
