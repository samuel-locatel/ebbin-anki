/* Ebbin synthesized coin sounds (ported from docs/mockups/sounds-v2.html). */
(function (window) {
  "use strict";
  var ctx = null;
  var master = null;

  function audio() {
    if (!ctx) {
      var Ctor = window.AudioContext || window.webkitAudioContext;
      ctx = new Ctor();
      master = ctx.createGain();
      master.connect(ctx.destination);
    }
    if (ctx.state === "suspended" && ctx.resume) ctx.resume();
    return ctx;
  }

  function tone(type, f0, f1, dur, vol, t0, attack) {
    t0 = t0 || 0;
    attack = attack === undefined ? 0.004 : attack;
    var c = audio(), t = c.currentTime + t0, o = c.createOscillator(), g = c.createGain();
    o.type = type;
    o.frequency.setValueAtTime(f0, t);
    if (f1) o.frequency.exponentialRampToValueAtTime(f1, t + dur);
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(vol, t + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g).connect(master);
    o.start(t);
    o.stop(t + dur + 0.02);
  }

  var st = function (n) { return Math.pow(2, n / 12); };
  var B = 880;

  function coin(f, t, v, tail) {
    f = f === undefined ? B : f;
    t = t || 0;
    v = v === undefined ? 1 : v;
    tail = tail === undefined ? 0.28 : tail;
    tone("triangle", f, 0, 0.09, 0.25 * v, t);
    tone("triangle", f * 1.5, 0, tail, 0.25 * v, t + 0.07);
    tone("sine", f * 3, 0, tail * 0.7, 0.06 * v, t + 0.07);
  }

  function plink(f, t, v, d) {
    t = t || 0;
    v = v === undefined ? 1 : v;
    d = d === undefined ? 0.22 : d;
    tone("triangle", f, 0, d, 0.22 * v, t);
    tone("sine", f * 2, 0, d * 0.6, 0.05 * v, t);
  }

  var S = {
    good: function () { coin(); },
    again: function () { tone("triangle", B * 0.5, B * 0.42, 0.18, 0.18); },
    hard: function () {
      tone("triangle", B * st(-5), 0, 0.07, 0.22);
      tone("triangle", B * st(-5) * 1.5, 0, 0.14, 0.2, 0.06);
    },
    level: function () {
      plink(B * st(7), 0);
      plink(B * st(7), 0.12);
      plink(B * st(12), 0.24, 1.2, 0.5);
    },
    done: function () {
      var seq = [0, 4, 7, 12, 7, 12, 16, 12, 16, 19, 16, 24];
      for (var i = 0; i < 12; i++) coin(B * st(seq[i]), i * 0.075, 0.55, 0.16);
      [0, 4, 7, 12].forEach(function (n) {
        tone("triangle", B * st(n + 12) / 2, 0, 1.2, 0.07, 0.95, 0.02);
      });
    },
    pomo: function () {
      tone("triangle", B * st(4), 0, 1.1, 0.2, 0, 0.005);
      tone("sine", B * st(16), 0, 0.6, 0.04, 0);
      tone("triangle", B, 0, 1.4, 0.2, 0.45, 0.005);
      tone("sine", B * 2, 0, 0.8, 0.04, 0.45);
    },
    mastered: function () { coin(B * st(12), 0, 1, 0.12); },
  };

  function play(key) {
    if (typeof key !== "string") return;
    if (key.indexOf("combo:") === 0) {
      var n = parseInt(key.slice(6), 10);
      if (!(n >= 1)) return;
      coin(B * st((n - 1) % 12), 0, 1, 0.2);
      return;
    }
    if (Object.prototype.hasOwnProperty.call(S, key)) S[key]();
  }

  function clampVol(v) {
    v = typeof v === "number" ? v : 0.8;
    return Math.max(0, Math.min(1, v));
  }

  window.ebbinSound = function (key, volume) {
    var known = typeof key === "string" &&
      (key.indexOf("combo:") === 0 || Object.prototype.hasOwnProperty.call(S, key));
    if (!known) return;
    audio();
    master.gain.value = clampVol(volume);
    play(key);
  };

  window.ebbinPlaySeq = function (keys, volume) {
    (keys || []).forEach(function (k, i) {
      if (i === 0) window.ebbinSound(k, volume);
      else window.setTimeout(function () { window.ebbinSound(k, volume); }, i * 120);
    });
  };
})(window);
