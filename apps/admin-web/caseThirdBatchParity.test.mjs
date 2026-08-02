import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const helper = fs.readFileSync(path.join(root, "src", "caseSecondBatchParity.ts"), "utf8");
const page = fs.readFileSync(path.join(root, "src", "CaseCenterPage.tsx"), "utf8");

test("execution status parity exposes the legacy status matrix and payload builder", () => {
  assert.match(helper, /CASE_EXECUTION_STATUSES/);
  assert.match(helper, /一审待执行/);
  assert.match(helper, /执行结案/);
  assert.match(helper, /buildCaseExecutionStatusPayload/);
  assert.match(helper, /comment/);
});

test("case page wires dedicated execution status editing with legacy success and failure copy", () => {
  assert.match(page, /buildCaseExecutionStatusPayload/);
  assert.match(page, /executionStatusEditing/);
  assert.match(page, /\/cases\/execution-status/);
  assert.match(page, /修改成功！/);
  assert.match(page, /修改失败！/);
  assert.match(page, /CASE_EXECUTION_STATUSES/);
});

test("progress and phase actions keep write capability and merged/archive guards", () => {
  assert.match(page, /can_update_progress/);
  assert.match(page, /已合并/);
  assert.match(page, /归档中、已归档或已合并案件不能维护案件进展/);
  assert.match(page, /案件进展保存失败/);
  assert.match(page, /key === "phase"/);
});
