import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const page = fs.readFileSync(path.join(root, "src", "CaseCenterPage.tsx"), "utf8");

test("case detail keeps the legacy reminder and log creators in the right panel", () => {
  assert.match(page, /case-detail-side-panel/);
  assert.match(page, /case-detail-side-title[^\n]*案件提醒[^\n]*新增/);
  assert.match(page, /case-detail-side-title[^\n]*案件日志[^\n]*新增日志[^\n]*新增退费日志/);
});

test("reminder and log creators use persistent case endpoints", () => {
  assert.match(page, /\/cases\/\$\{viewingCounselCase\.id\}\/reminders/);
  assert.match(page, /\/cases\/\$\{viewingCounselCase\.id\}\/logs/);
  assert.match(page, /案件提醒已创建/);
  assert.match(page, /案件日志已保存/);
  assert.match(page, /退费日志已保存/);
});
