import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

test("frontend baseline states legacy parity and extension boundaries", () => {
  const source = readFileSync(new URL("../src/App.vue", import.meta.url), "utf8");
  assert.match(source, /旧系统菜单、路由、字段与权限必须逐项对齐/);
  assert.match(source, /钉钉和智能体将作为扩展能力接入/);
});
