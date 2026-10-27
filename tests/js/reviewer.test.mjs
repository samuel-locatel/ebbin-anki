import { test } from "node:test";
import assert from "node:assert";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const src = readFileSync(resolve(root, "ebbin/web/reviewer.js"), "utf8");
const window = {};
new Function("window", src)(window);
const r = window.ebbin;

test("fmtNum uses pt-BR thousands dots", () => {
  assert.equal(r.fmtNum(1284), "1.284");
  assert.equal(r.fmtNum(1234567), "1.234.567");
  assert.equal(r.fmtNum(999), "999");
  assert.equal(r.fmtNum(0), "0");
  assert.equal(r.fmtNum(undefined), "0");
});

test("xpText", () => {
  assert.equal(r.xpText(1299), "1.299 XP");
  assert.equal(r.xpText(15), "15 XP");
});

test("progress label while the goal is open", () => {
  assert.equal(r.progressLabel({ done: 21, target: 37, left: 16, met: false }), "21 de 37 · faltam 16");
  assert.equal(r.progressLabel({ done: 0, target: 1200, left: 1200, met: false }), "0 de 1.200 · faltam 1.200");
});

test("progress label once the main mission is done", () => {
  assert.equal(r.progressLabel({ done: 37, target: 37, left: 0, met: true }), "meta batida");
  assert.equal(r.progressLabel({ done: 3, target: 5, left: 2, met: true }), "meta batida");
  assert.equal(r.progressLabel({ done: 37, target: 37, left: 0, met: false }), "37 de 37 · faltam 0");
  assert.equal(r.progressLabel(null), "");
});

test("bar width scales the inner track (minus the 8px inset)", () => {
  assert.equal(r.barWidth(56.8), "calc((100% - 8px) * 0.568)");
  assert.equal(r.barWidth(150), "calc((100% - 8px) * 1)");
  assert.equal(r.barWidth(-3), "calc((100% - 8px) * 0)");
  assert.equal(r.barWidth(undefined), "calc((100% - 8px) * 0)");
});
