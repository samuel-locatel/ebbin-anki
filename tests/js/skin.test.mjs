import { test } from "node:test";
import assert from "node:assert";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const src = readFileSync(resolve(root, "ebbin/web/skin.js"), "utf8");
const window = {};
new Function("window", src)(window);
const s = window.ebbinSkin;

test("adds the skin classes and the theme", () => {
  assert.deepEqual(s.classDiff(["card", "card1", "nightMode"], "ebbin-skin ebbin-reviewer", "night"),
    { add: ["ebbin-skin", "ebbin-reviewer", "night"], remove: [] });
});

test("nothing to do when already applied (no observer loop)", () => {
  assert.deepEqual(s.classDiff(["ebbin-skin", "ebbin-bottom", "slate", "nightMode"], "ebbin-skin ebbin-bottom", "slate"),
    { add: [], remove: [] });
});

test("switching theme removes the stale one", () => {
  assert.deepEqual(s.classDiff(["ebbin-skin", "ebbin-decks", "night"], "ebbin-skin ebbin-decks", "slate"),
    { add: ["slate"], remove: ["night"] });
  assert.deepEqual(s.classDiff(["ebbin-skin", "ebbin-decks", "night", "slate"], "ebbin-skin ebbin-decks", ""),
    { add: [], remove: ["night", "slate"] });
});

test("re-adds the classes Anki's reviewer wiped from body.className", () => {
  assert.deepEqual(s.classDiff(["card", "card2", "isMac"], "ebbin-skin ebbin-reviewer", ""),
    { add: ["ebbin-skin", "ebbin-reviewer"], remove: [] });
});

test("no body class means skin off: touch nothing", () => {
  assert.deepEqual(s.classDiff(["night"], "", "night"), { add: [], remove: [] });
});
