import { test } from "node:test";
import assert from "node:assert";
import { execFileSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const src = execFileSync(
  resolve(root, ".venv/bin/python"),
  ["-c", "from ebbin.core.easycap import block; print(block(1.5,4))"],
  { cwd: root, encoding: "utf8" },
);
const run = (states) => new Function("states", src)(states);
const rev = (n) => ({ normal: { review: { scheduledDays: n } } });
const filt = (n) => ({ filtered: { rescheduling: { originalState: { review: { scheduledDays: n } } } } });

test("caps easy to 1.5x good", () => {
  const s = { good: rev(7), easy: rev(60) };
  run(s);
  assert.strictEqual(s.easy.normal.review.scheduledDays, 11);
});
test("does not raise easy", () => {
  const s = { good: rev(2), easy: rev(3) };
  run(s);
  assert.strictEqual(s.easy.normal.review.scheduledDays, 3);
});
test("keeps easy at least good+1", () => {
  const s = { good: rev(1), easy: rev(9) };
  run(s);
  assert.strictEqual(s.easy.normal.review.scheduledDays, 2);
});
test("good in learning uses first_max_days", () => {
  const s = { good: { normal: { learning: {} } }, easy: rev(9) };
  run(s);
  assert.strictEqual(s.easy.normal.review.scheduledDays, 4);
});
test("filtered rescheduling capped the same", () => {
  const s = { good: filt(7), easy: filt(60) };
  run(s);
  assert.strictEqual(s.easy.filtered.rescheduling.originalState.review.scheduledDays, 11);
});
test("missing easy review untouched", () => {
  const s = { good: rev(7), easy: { normal: { learning: {} } } };
  run(s);
  assert.deepStrictEqual(s.easy, { normal: { learning: {} } });
});
