import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const helperPath = new URL("./src/caseFifthBatchParity.mjs", import.meta.url);
const helperSource = fs.existsSync(helperPath) ? fs.readFileSync(helperPath, "utf8") : "";
const helper = fs.existsSync(helperPath) ? await import(helperPath) : null;
const page = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("案件提醒消费层拒绝提醒日期晚于截止日期", () => {
  assert.ok(helper, "caseFifthBatchParity.mjs must be importable");
  assert.match(helperSource, /getCaseReminderDateValidationError/);
  assert.equal(helper.getCaseReminderDateValidationError("2026-08-02", "2026-08-03"), "");
  assert.equal(helper.getCaseReminderDateValidationError("2026-08-03", "2026-08-03"), "");
  assert.equal(helper.getCaseReminderDateValidationError("2026-08-04", "2026-08-03"), "提醒日期不能晚于截止日期");
  assert.equal(helper.getCaseReminderDateValidationError("", "2026-08-03"), "");
  assert.equal(helper.getCaseReminderDateValidationError({ format: () => "2026-08-04" }, { format: () => "2026-08-03" }), "提醒日期不能晚于截止日期");
  assert.match(page, /caseFifthBatchParity\.mjs/);
  assert.match(page, /getCaseReminderDateValidationError/);
});

test("案件任务详情保留旧系统默认 15 条分页", () => {
  assert.ok(helper, "caseFifthBatchParity.mjs must be importable");
  assert.match(helperSource, /CASE_TASK_PAGE_SIZE_OPTIONS/);
  assert.deepEqual(helper.CASE_TASK_PAGE_SIZE_OPTIONS, [10, 15, 20, 50, 100]);
  const pagination = helper.getCaseTaskPagination();
  assert.equal(pagination.defaultPageSize, 15);
  assert.deepEqual(pagination.pageSizeOptions, [10, 15, 20, 50, 100]);
  assert.equal(pagination.showSizeChanger, true);
  assert.equal(pagination.showTotal(7), "共 7 项");
  assert.match(page, /caseFifthBatchParity\.mjs/);
  assert.match(page, /getCaseTaskPagination/);
  assert.match(page, /pagination=\{getCaseTaskPagination\(\)\}/);
});
