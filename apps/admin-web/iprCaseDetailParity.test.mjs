import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const helper = await import(new URL("./src/iprCaseDetailParity.mjs", import.meta.url));
const page = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

test("IPR customer payload requires a selected customer and selected primary", () => {
  assert.equal(helper.getIprCaseCustomerValidationError({ customerIds: [], primaryCustomerId: null }), "请至少选择一个客户并指定主客户");
  assert.equal(helper.getIprCaseCustomerValidationError({ customerIds: [3, 3], primaryCustomerId: 9 }), "请从已选客户中指定一个主客户");
  assert.equal(helper.getIprCaseCustomerValidationError({ customerIds: [3, 3], primaryCustomerId: 3 }), "");
  assert.deepEqual(helper.buildIprCaseCustomerPayload({ customerIds: [3, 3, 7], primaryCustomerId: 3 }), { customer_ids: [3, 7], primary_customer_id: 3 });
});

test("IPR contact and law-firm payloads trim and deduplicate selections", () => {
  assert.deepEqual(helper.buildIprCaseContactPayload({ customerId: 7, documentContactIds: [" c1 ", "c1", ""], technologyContactIds: ["t1", " t1 "] }), {
    customer_id: 7,
    document_contact_ids: ["c1"],
    technology_contact_ids: ["t1"],
  });
  assert.deepEqual(helper.buildIprCaseLawFirmPayload({ lawFirmIds: [5, 5, 2] }), { law_firm_ids: [5, 2] });
});

test("IPR destructive actions expose distinct confirmation copy", () => {
  for (const kind of ["log", "file", "reminder", "assisted-fee"]) {
    const prompt = helper.getIprCaseDeletionConfirmation(kind, "示例");
    assert.equal(prompt.okText, "确认删除");
    assert.equal(prompt.cancelText, "取消");
    assert.match(prompt.title, /删除/);
    assert.match(prompt.content, /示例/);
  }
  assert.match(page, /getIprCaseDeletionConfirmation/);
  assert.match(page, /buildIprCaseCustomerPayload/);
  assert.match(page, /buildIprCaseContactPayload/);
  assert.match(page, /buildIprCaseLawFirmPayload/);
});

test("IPR API errors preserve backend detail and provide status fallbacks", async () => {
  assert.equal(
    helper.getIprApiErrorMessage({ response: { status: 409, data: { detail: "重复文档：不允许上传" } } }, "上传失败"),
    "重复文档：不允许上传",
  );
  assert.equal(
    helper.getIprApiErrorMessage({ response: { status: 403, data: {} } }, "删除失败"),
    "当前账号无权执行此操作",
  );
  for (const status of [401, 404, 409, 422]) {
    assert.equal(
      helper.getIprApiErrorMessage({ response: { status, data: { detail: `后端错误 ${status}` } } }, "操作失败"),
      `后端错误 ${status}`,
    );
  }
  assert.equal(
    helper.getIprSectionLoadError("files", { response: { status: 500, data: {} } }),
    "案件文档加载失败",
  );
  assert.equal(
    helper.getIprSectionLoadError("logs", { response: { data: { detail: "日志查询被拒绝" } } }),
    "日志查询被拒绝",
  );
  assert.match(page, /getIprApiErrorMessage\(e, "上传案件文档失败"\)/);
  assert.match(page, /getIprApiErrorMessage\(e, "删除案件文档失败"\)/);
  assert.match(page, /setIprSectionError\("files", error\)/);
  assert.match(page, /setIprSectionError\("logs", error\)/);
  assert.match(page, /setIprSectionError\("reminders", error\)/);
  assert.match(page, /setIprSectionError\("assistedFees", error\)/);
});

test("IPR category changes clear an incompatible selected type", async () => {
  assert.equal(helper.getIprCompatibleFileCategory({
    category: "申请文件",
    caseKinds: ["专利"],
    fileTypes: [{ name: "申请文件", case_kinds: ["商标"] }],
  }), undefined);
  assert.equal(helper.getIprCompatibleFileCategory({
    category: "申请文件",
    caseKinds: ["专利"],
    fileTypes: [{ name: "申请文件", case_kinds: ["专利"] }],
  }), "申请文件");
  assert.match(page, /getIprCompatibleFileCategory/);
});

test("IPR deadline offset follows dayjs year-month-day order", async () => {
  assert.equal(helper.buildIprDeadlineFromOffset({ baseDate: "2024-01-31", years: 0, months: 1, days: 0 }), "2024-02-29");
  assert.equal(helper.buildIprDeadlineFromOffset({ baseDate: "2024-02-29", years: 1, months: 0, days: 0 }), "2025-02-28");
  assert.equal(helper.buildIprDeadlineFromOffset({ baseDate: "2024-03-01", years: 0, months: 0, days: -1 }), "2024-02-29");
  assert.equal(helper.buildIprDeadlineFromOffset({ baseDate: "", years: 1, months: 1, days: 1 }), "");
  assert.match(page, /buildIprDeadlineFromOffset/);
});
