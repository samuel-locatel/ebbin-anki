import { test } from "node:test";
import assert from "node:assert";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const src = readFileSync(resolve(root, "ebbin/web/window.js"), "utf8");
const window = {};
new Function("window", src)(window);
const w = window.ebbinWin;
const cfg = JSON.parse(readFileSync(resolve(root, "ebbin/config.json"), "utf8"));

function leaves(o, prefix = "") {
  return Object.entries(o).flatMap(([k, v]) =>
    v && typeof v === "object" ? leaves(v, prefix + k + ".") : [prefix + k]);
}

test("settings form covers every config.json key, with defaults inside range", () => {
  const paths = w.FIELDS.filter((f) => f.path).map((f) => f.path).sort();
  assert.deepEqual(paths, leaves(cfg).sort());
  for (const f of w.FIELDS.filter((f) => f.type === "number" || f.type === "range")) {
    const v = w.getPath(cfg, f.path);
    assert.ok(v >= f.min && v <= f.max, f.path);
  }
});

test("buildConfig nests dotted paths", () => {
  assert.deepEqual(w.buildConfig({ budget_min: 30, "easy_cap.ratio": 2, "easy_cap.enabled": true }),
    { budget_min: 30, easy_cap: { ratio: 2, enabled: true } });
});

test("consistency text", () => {
  const t = w.consistencyText({ met_pct: 0.5714, within_budget: 8, of_days: 10, streak: { current: 3, best: 9 } }, 20);
  assert.equal(t.met, "57% dos dias com desafio");
  assert.equal(t.budget, "8 de 10 dias dentro dos 20 min");
  assert.equal(t.streak, "sequência atual 3 · recorde 9");
});

test("deckItems sorts worst first, nulls last, leaf names", () => {
  const items = w.deckItems([
    { deck: "A::Civil", acc: 0.9, lapses: 1 }, { deck: "B", acc: null, lapses: 0 },
    { deck: "C::Penal", acc: 0.6, lapses: 4 }]);
  assert.deepEqual(items.map((i) => i.label), ["Penal", "Civil", "B"]);
  assert.equal(items[0].text, "60% · 4 lapsos");
  assert.equal(items[1].text, "90% · 1 lapso");
});

test("tagLines, loadNote, stars, objectiveMeta, summaryText", () => {
  assert.equal(w.tagLines([{ a: "x", b: "y", acc_a: 0.8, acc_b: 0.7, sec_a: 12.5, sec_b: null }])[0],
    "x 80% (12,5 s) vs y 70% (–)");
  assert.equal(w.loadNote({ first_over: "05/11" }), "No ritmo atual você passa do orçamento em 05/11");
  assert.match(w.loadNote({ first_over: null }), /Dentro do orçamento/);
  assert.equal(w.stars(2), "★★☆");
  assert.equal(w.objectiveMeta({ countdown: "OAB · 30 dias", new_remaining: 12, pace: 1 }),
    "OAB · 30 dias · 12 novos restantes · 1 novos/dia");
  assert.equal(w.objectiveMeta({ countdown: null, new_remaining: 0, pace: null }), "0 novos restantes");
  assert.equal(w.summaryText({ mastered: 3, study_days: 5, accuracy: 0.75 }), "3 dominados · 5 dias de estudo · 75% de acerto");
  assert.equal(w.summaryText({ mastered: 0, study_days: 0, accuracy: null }), "0 dominados · 0 dias de estudo · sem respostas");
});

test("deck roots: parent implies subdecks", () => {
  assert.deepEqual(w.normalizeRoots(["A::B", "A", "C"]), ["A", "C"]);
  assert.equal(w.coveredBy("A::B::C", ["A"]), true);
  assert.equal(w.coveredBy("AB", ["A"]), false);
  assert.equal(w.isInherited("A::B", ["A"]), true);
  assert.equal(w.isInherited("A", ["A"]), false);
});

test("hour/week labels", () => {
  assert.equal(w.hourLabels().length, 24);
  assert.equal(w.hourLabels()[6], "6");
  assert.equal(w.weekLabels(12)[11], "agora");
});

test("retentionText shows real vs desired", () => {
  assert.equal(w.retentionText({ true_retention: 0.853, desired_retention: 0.9 }), "Retenção real 85% · meta 90%");
});

test("retentionFloor keeps the retention axis close to the data", () => {
  assert.equal(w.retentionFloor([null, 0.82, 0.91]), 0.7);
  assert.equal(w.retentionFloor([null, null]), 0);
  assert.equal(w.retentionFloor([0.05]), 0);
});
