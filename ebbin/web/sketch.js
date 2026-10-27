/* Ebbin hand-drawn SVG filters (params from docs/mockups) and theme-class helper. */
(function (window) {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";
  var SVG =
    '<svg xmlns="' + NS + '" width="0" height="0" style="position:absolute" aria-hidden="true">' +
    '<filter id="e-rough"><feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="3"/>' +
    '<feDisplacementMap in="SourceGraphic" scale="3.2"/></filter>' +
    '<filter id="e-rough2"><feTurbulence type="fractalNoise" baseFrequency="0.05" numOctaves="2" seed="8"/>' +
    '<feDisplacementMap in="SourceGraphic" scale="2.2"/></filter>' +
    '<filter id="e-chalk"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="1" seed="2" result="n"/>' +
    '<feColorMatrix in="n" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 -1.6 1.25" result="m"/>' +
    '<feComposite in="SourceGraphic" in2="m" operator="in"/></filter>' +
    "</svg>";

  window.ebbinSketch = {
    ensureFilters: function () {
      if (document.getElementById("ebbin-filters")) return;
      var host = document.createElement("div");
      host.id = "ebbin-filters";
      host.style.cssText = "position:absolute;width:0;height:0;overflow:hidden";
      host.innerHTML = SVG;
      (document.body || document.documentElement).appendChild(host);
    },
    themeClass: function (cfgDark) {
      var b = document.body;
      var dark = !!b && (b.classList.contains("nightMode") || b.classList.contains("night_mode"));
      if (!dark) return "";
      return cfgDark === "slate" ? "slate" : "night";
    },
  };

  // Anki defines pycmd only after QWebChannel connects (async, at DocumentReady), so a
  // message sent while the page loads would be silently lost. Queue until it exists.
  var queue = [];
  function flush() {
    if (!window.pycmd) { window.setTimeout(flush, 30); return; }
    while (queue.length) { var m = queue.shift(); window.pycmd(m[0], m[1]); }
  }
  window.ebbinSend = function (msg, cb) {
    if (window.pycmd && !queue.length) { window.pycmd(msg, cb); return; }
    queue.push([msg, cb]);
    if (queue.length === 1) window.setTimeout(flush, 0);
  };
})(window);
