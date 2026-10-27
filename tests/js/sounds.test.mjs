import { test } from "node:test";
import assert from "node:assert";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const src = readFileSync(resolve(root, "ebbin/web/sounds.js"), "utf8");

function load() {
  const log = { osc: 0, resumed: 0, masterGains: [] };
  const param = () => ({
    value: 0,
    setValueAtTime() {}, linearRampToValueAtTime() {}, exponentialRampToValueAtTime() {},
  });
  class Ctx {
    constructor() { this.currentTime = 0; this.state = "suspended"; this.destination = {}; }
    resume() { log.resumed++; this.state = "running"; return Promise.resolve(); }
    createOscillator() {
      log.osc++;
      return { frequency: param(), connect: (n) => n, start() {}, stop() {}, type: "" };
    }
    createGain() {
      const g = { gain: param(), connect: (n) => n };
      log.masterGains.push(g);
      return g;
    }
  }
  const window = { AudioContext: Ctx, setTimeout: (f) => f() };
  new Function("window", src)(window);
  return { window, log };
}

test("exposes ebbinSound and ebbinPlaySeq", () => {
  const { window } = load();
  assert.equal(typeof window.ebbinSound, "function");
  assert.equal(typeof window.ebbinPlaySeq, "function");
});

test("all keys dispatch without throwing and make sound", () => {
  const { window, log } = load();
  for (const k of ["good", "again", "hard", "combo:5", "combo:14", "level", "done", "pomo", "mastered"]) {
    const before = log.osc;
    assert.doesNotThrow(() => window.ebbinSound(k, 0.5), k);
    assert.ok(log.osc > before, `${k} produced oscillators`);
  }
  assert.ok(log.resumed >= 1);
});

test("level has 3 plinks only (no cascade)", () => {
  const { window, log } = load();
  window.ebbinSound("level", 1);
  assert.equal(log.osc, 6); // 3 plinks x (triangle + sine)
});

test("unknown key is a no-op", () => {
  const { window, log } = load();
  assert.doesNotThrow(() => window.ebbinSound("nope", 1));
  assert.equal(log.osc, 0);
});

test("ebbinPlaySeq plays every key", () => {
  const { window, log } = load();
  window.ebbinPlaySeq(["good", "level"], 0.7);
  assert.equal(log.osc, 3 + 6);
});
