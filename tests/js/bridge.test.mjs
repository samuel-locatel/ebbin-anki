import { test } from "node:test";
import assert from "node:assert";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const src = readFileSync(resolve(root, "ebbin/web/sketch.js"), "utf8");

// Anki defines window.pycmd only after QWebChannel connects (DocumentReady, async),
// so messages sent while the page loads must wait for it instead of being dropped.
function load() {
  const timers = [];
  const window = { setTimeout: (f) => timers.push(f) };
  new Function("window", src)(window);
  const runTimers = (rounds = 5) => { for (let i = 0; i < rounds && timers.length; i++) { const due = timers.splice(0); due.forEach((f) => f()); } };
  return { window, runTimers };
}

test("ebbinSend delivers immediately when pycmd exists", () => {
  const { window } = load();
  const sent = [];
  window.pycmd = (m) => sent.push(m);
  window.ebbinSend("a");
  assert.deepStrictEqual(sent, ["a"]);
});

test("ebbinSend queues until pycmd appears, keeping order and callbacks", () => {
  const { window, runTimers } = load();
  const sent = [];
  const got = [];
  window.ebbinSend("first", (r) => got.push(r));
  window.ebbinSend("second");
  runTimers(); // bridge still not ready: nothing sent, nothing lost
  assert.deepStrictEqual(sent, []);
  window.pycmd = (m, cb) => { sent.push(m); if (cb) cb("ok:" + m); };
  window.ebbinSend("third");
  runTimers();
  assert.deepStrictEqual(sent, ["first", "second", "third"]);
  assert.deepStrictEqual(got, ["ok:first"]);
});
