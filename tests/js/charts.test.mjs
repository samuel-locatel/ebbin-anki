import { test } from "node:test";
import assert from "node:assert";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const src = readFileSync(resolve(root, "ebbin/web/charts.js"), "utf8");
const window = {};
new Function("window", src)(window);
const c = window.ebbinCharts;

test("scale maps, clamps and handles flat domain", () => {
  const s = c.scale(0, 10, 100, 0);
  assert.equal(s(0), 100);
  assert.equal(s(10), 0);
  assert.equal(s(5), 50);
  assert.equal(s(99), 0);
  assert.equal(c.scale(3, 3, 0, 10)(3), 5);
});

test("pathD breaks on nulls and supports single points", () => {
  assert.equal(c.pathD([{ x: 0, y: 0 }, { x: 10, y: 5 }]), "M0 0 L10 5");
  assert.equal(c.pathD([{ x: 0, y: 0 }, null, { x: 4, y: 4 }, { x: 8, y: 2 }]), "M0 0 L0 0 M4 4 L8 2");
  assert.equal(c.pathD([]), "");
  assert.equal(c.pathD([{ x: 0, y: 0 }, { x: 10, y: 10 }, { x: 20, y: 0 }], true), "M0 0 Q10 10 15 5 L20 0");
});

test("seriesPoints spans the box and skips nulls", () => {
  const p = c.seriesPoints([0, null, 10], 100, 50, 10, 0, 10);
  assert.deepEqual(p, [{ x: 10, y: 40 }, null, { x: 90, y: 10 }]);
});

test("hatchLevel is 0 without minutes and 1..3 by density", () => {
  assert.equal(c.hatchLevel(0, 60), 0);
  assert.equal(c.hatchLevel(5, 0), 0);
  assert.equal(c.hatchLevel(1, 60), 1);
  assert.equal(c.hatchLevel(30, 60), 2);
  assert.equal(c.hatchLevel(60, 60), 3);
});

test("heatmapLayout uses 7 rows per week column", () => {
  const cells = Array.from({ length: 14 }, (_, i) => ({ day: i, minutes: i === 8 ? 10 : 0, met: i === 8 }));
  const lay = c.heatmapLayout(cells, 20, 5);
  assert.deepEqual([lay[0].x, lay[0].y], [0, 0]);
  assert.deepEqual([lay[7].x, lay[7].y], [25, 0]);
  assert.deepEqual([lay[8].x, lay[8].y], [25, 25]);
  assert.equal(lay[8].level, 3);
  assert.equal(lay[8].met, true);
  assert.equal(lay[1].level, 0);
});

test("barsLayout scales to max and baseline", () => {
  const l = c.barsLayout([0, 5, 10, null], 100, 60, 10, 10);
  assert.equal(l[0].h, 0);
  assert.equal(l[2].h, 40);
  assert.equal(l[2].y, 10);
  assert.equal(l[3].h, 0);
  assert.equal(l[1].h, 20);
});

test("extent and formatting helpers", () => {
  assert.deepEqual(c.extent([null, null]), [0, 1]);
  assert.deepEqual(c.extent([3, 3]), [3, 4]);
  assert.deepEqual(c.extent([5, 9], true), [0, 9]);
  assert.equal(c.pct(0.756), "76%");
  assert.equal(c.pct(null), "–");
  assert.equal(c.leaf("A::B::Civil"), "Civil");
});

test("heatmapLayout aligns columns to calendar weeks when weekday is given", () => {
  // starts on Thursday (3): 4 cells fill the first column (Thu..Sun), then Monday opens column 1
  const cells = Array.from({ length: 6 }, (_, i) => ({ day: i, minutes: 1, met: false, weekday: (3 + i) % 7 }));
  const lay = c.heatmapLayout(cells, 20, 5);
  assert.deepEqual(lay.map((l) => [l.x / 25, l.y / 25]), [[0, 3], [0, 4], [0, 5], [0, 6], [1, 0], [1, 1]]);
});

test("niceTicks covers the range with round steps", () => {
  assert.deepEqual(c.niceTicks(0, 1, 4).ticks, [0, 0.25, 0.5, 0.75, 1]);
  const t = c.niceTicks(0, 37, 4);
  assert.deepEqual(t.ticks, [0, 10, 20, 30, 40]);
  assert.deepEqual([t.lo, t.hi], [0, 40]);
  const s = c.niceTicks(10.2, 14.8, 4);
  assert.equal(s.lo <= 10.2 && s.hi >= 14.8, true);
  assert.deepEqual(s.ticks, [10, 12, 14, 16]);
});

test("niceTicks with integer steps never repeats a whole number", () => {
  assert.deepEqual(c.niceTicks(0, 1, 4, true).ticks, [0, 1]);
  assert.deepEqual(c.niceTicks(0, 3, 4, true).ticks, [0, 1, 2, 3]);
  assert.deepEqual(c.niceTicks(0, 9, 4, true).ticks, [0, 5, 10]);
});

test("geometry leaves a left margin for the y axis labels", () => {
  const p = c.seriesPoints([0, 10], 100, 50, 10, 0, 10, 40);
  assert.deepEqual(p, [{ x: 40, y: 40 }, { x: 90, y: 10 }]);
  const b = c.barsLayout([10], 100, 60, 10, 10, 40);
  assert.equal(b[0].x >= 40, true);
  assert.equal(b[0].x + b[0].w <= 90, true);
});
