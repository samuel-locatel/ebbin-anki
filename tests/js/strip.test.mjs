import { test } from "node:test";
import assert from "node:assert";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const src = readFileSync(resolve(root, "ebbin/web/strip.js"), "utf8");
const window = {};
new Function("window", src)(window);
const s = window.ebbinStrip;

test("mmss", () => {
  assert.equal(s.mmss(1200), "20:00");
  assert.equal(s.mmss(65), "01:05");
  assert.equal(s.mmss(-3), "00:00");
});

test("fmtNum uses pt-BR dots", () => {
  assert.equal(s.fmtNum(1180), "1.180");
  assert.equal(s.fmtNum(360), "360");
});

test("week dot class", () => {
  assert.equal(s.dayClass("done"), "e-day done");
  assert.equal(s.dayClass("today"), "e-day today");
  assert.equal(s.dayClass("off"), "e-day off");
  assert.equal(s.dayClass("weird"), "e-day off");
});

test("bar percents", () => {
  const p = s.barPercents({ into: 180, needed: 360, xp_before_today: 90 });
  assert.equal(p.a, 25);
  assert.equal(p.b, 25);
  const q = s.barPercents({ into: 50, needed: 100, xp_before_today: 0 });
  assert.equal(q.a, 0);
  assert.equal(q.b, 50);
});

test("streak text", () => {
  assert.equal(s.streakText({ current: 12, freezes: 0 }), "12 dias seguidos");
  assert.equal(s.streakText({ current: 12, freezes: 1 }), "12 dias seguidos · 1 congelamento");
  assert.equal(s.streakText({ current: 3, freezes: 2 }), "3 dias seguidos · 2 congelamentos");
  assert.equal(s.streakText({ current: 1, freezes: 0 }), "1 dia seguido");
});

test("pomodoro button", () => {
  assert.deepEqual(s.pomoButton({ phase: "idle", remaining_s: 0 }, 1200),
    { label: "⏱ começar 20:00", cmd: "pomo_start" });
  assert.deepEqual(s.pomoButton({ phase: "focus", remaining_s: 754 }, 1200),
    { label: "⏸ 12:34", cmd: "pomo_pause" });
  assert.deepEqual(s.pomoButton({ phase: "paused", remaining_s: 100 }, 1200),
    { label: "▶ 01:40", cmd: "pomo_resume" });
});

test("stripHints drops hints from partial updates", () => {
  const p = s.stripHints({ level: 3, hints: [], pomodoro: { phase: "idle" } });
  assert.equal("hints" in p, false);
  assert.equal(p.level, 3);
});
