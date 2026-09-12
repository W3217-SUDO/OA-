import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const modal = fs.readFileSync(new URL("./src/tp/TaskActionModals.tsx", import.meta.url), "utf8");
const center = fs.readFileSync(new URL("./src/tp/TaskCenterPage.tsx", import.meta.url), "utf8");

test("handoff exposes an optional end date instead of replacing the existing deadline", () => {
  assert.match(modal, /label="交接结束时间" name="end_at"/);
  assert.match(modal, /<DatePicker showTime/);
  assert.match(modal, /placeholder="请选择日期和时间"/);
});

test("handoff serializes only the optional date and preserves recipient/comment compatibility", () => {
  assert.match(center, /values\.end_at = values\.end_at \? values\.end_at\.format\("YYYY-MM-DDTHH:mm:ss"\) : undefined/);
  assert.match(center, /await api\.post\(`\/tasks\/\$\{handoff\.id\}\/handoff`, values\)/);
  assert.match(center, /setFieldsValue\(\{ recipient: "", comment: "", end_at: undefined \}\)/);
});
