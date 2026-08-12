import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

test("frontend preserves the legacy shell and parity boundary", () => {
  const source = readFileSync(new URL("../src/App.vue", import.meta.url), "utf8");
  assert.match(source, /legacy-shell/);
  assert.match(source, /旧系统等价重建/);
  assert.match(source, /钉钉与智能体/);
});

test("frontend reads the legacy menu tree instead of a hand-maintained menu", () => {
  const source = readFileSync(new URL("../src/App.vue", import.meta.url), "utf8");
  assert.match(source, /\/api\/v1\/legacy\/authorization\/staff\/1\/menu-tree/);
  assert.match(source, /MenuCode/);
  assert.match(source, /ParentMenuId/);
});
