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

test("案件文件类型消费层按 parent_code 构造可选父子树", () => {
  assert.ok(helper, "caseFifthBatchParity.mjs must be importable");
  const tree = helper.buildCaseFileTypeTreeOptions([
    { value: "CASE", label: "案件文件", code: "CASE", parent_code: "" },
    { value: "SUBJECT", label: "主体及委托资料", code: "SUBJECT", parent_code: "CASE" },
    { value: "COURT", label: "法院诉讼文书", code: "COURT", parent_code: "CASE" },
    { value: "COMMON", label: "普通附件", code: "COMMON", parent_code: "" },
  ]);
  assert.equal(tree.length, 2);
  assert.deepEqual(tree[0].options.map((item) => item.value), ["SUBJECT", "COURT"]);
  assert.equal(helper.resolveCaseFileTypeSelection("COURT", tree), "COURT");
  assert.equal(helper.resolveCaseFileTypeSelection("missing", tree), "CASE");
  assert.match(page, /buildCaseFileTypeTreeOptions/);
  assert.match(page, /resolveCaseFileTypeSelection/);
});

test("案件归档列表消费层按旧待审/已审/已拒绝分页默认值返回配置", () => {
  assert.ok(helper, "caseFifthBatchParity.mjs must be importable");
  assert.equal(helper.getCaseArchivePagination("case-archive-pending").pageSize, 15);
  assert.equal(helper.getCaseArchivePagination("case-archive-done").pageSize, 10);
  assert.equal(helper.getCaseArchivePagination("case-archive-refused").pageSize, 10);
  assert.deepEqual(helper.getCaseArchivePagination("case-archive-pending").pageSizeOptions, [10, 15, 20, 50, 100]);
  assert.equal(helper.getCaseArchivePagination("case-archive-pending").showTotal(3), "共有3条");
  assert.match(page, /getCaseArchivePagination/);
});

test("解档申请消费层在请求前拒绝少于两个字的原因", () => {
  assert.ok(helper, "caseFifthBatchParity.mjs must be importable");
  assert.equal(helper.getCaseUnarchiveRequestValidationError(""), "请输入至少2个字的解档原因");
  assert.equal(helper.getCaseUnarchiveRequestValidationError("退"), "请输入至少2个字的解档原因");
  assert.equal(helper.getCaseUnarchiveRequestValidationError("补充材料"), "");
  assert.match(page, /getCaseUnarchiveRequestValidationError/);
});
