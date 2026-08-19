import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const helper = await import(new URL("./src/caseWorkflowFrontendParity.mjs", import.meta.url));
const page = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("hearing payload formats dayjs-like date and time values", () => {
  const payload = helper.buildCaseHearingPayload({
    case_record_id: 7,
    hearing_date: { format: (pattern) => pattern === "YYYY-MM-DD" ? "2026-08-12" : "unexpected" },
    hearing_time: { format: (pattern) => pattern === "HH:mm" ? "09:30" : "unexpected" },
    court: "Court A",
  });
  assert.equal(payload.case_record_id, 7);
  assert.equal(payload.hearing_date, "2026-08-12");
  assert.equal(payload.hearing_time, "09:30");
  assert.match(page, /buildCaseHearingPayload/);
});

test("hearing payload validation covers every required field", () => {
  assert.equal(helper.getCaseHearingValidationError({}), "请选择关联案件");
  assert.equal(helper.getCaseHearingValidationError({ case_record_id: 7 }), "请选择开庭日期");
  assert.equal(helper.getCaseHearingValidationError({ case_record_id: 7, hearing_date: "2026-08-12" }), "请选择开庭时间");
  assert.equal(helper.getCaseHearingValidationError({ case_record_id: 7, hearing_date: "2026-08-12", hearing_time: "09:30" }), "请输入开庭法院");
  assert.equal(helper.getCaseHearingValidationError({ case_record_id: 7, hearing_date: "2026-08-12", hearing_time: "09:30", court: "Court A" }), "");
  assert.match(page, /getCaseHearingValidationError/);
});

test("hearing deletion is restricted to administrators", () => {
  assert.equal(helper.getCaseHearingDeleteValidationError("admin"), "");
  assert.equal(helper.getCaseHearingDeleteValidationError("manager"), "仅管理员可以删除排期");
  assert.equal(helper.getCaseHearingDeleteValidationError("user"), "仅管理员可以删除排期");
  assert.match(page, /getCaseHearingDeleteValidationError/);
  assert.match(page, /\/hearings\//);
});

test("archive review validates role and pending status before the API", () => {
  assert.equal(helper.getCaseArchiveReviewValidationError({ role: "user", status: "待归档审核" }), "只有管理员或部门负责人可以审核归档");
  assert.equal(helper.getCaseArchiveReviewValidationError({ role: "admin", status: "执行" }), "只有待归档审核案件可以审核");
  assert.equal(helper.getCaseArchiveReviewValidationError({ role: "manager", status: "待归档审核" }), "");
  assert.equal(helper.getCaseArchiveReviewValidationError({ role: "manager", status: "亏损内审" }), "");
  assert.equal(helper.getCaseArchiveReviewValidationError({ role: "admin", status: "亏损审核" }), "");
  assert.match(page, /getCaseArchiveReviewValidationError/);
});

test("unarchive review validates pending state, self-review, and rejection reason", () => {
  const base = { role: "manager", status: "已归档", requestStatus: "待审批", requestedBy: "owner", currentUsername: "reviewer", approved: true, comment: "" };
  assert.equal(helper.getCaseUnarchiveReviewValidationError({ ...base, role: "user" }), "只有管理员或部门负责人可以审批解档");
  assert.equal(helper.getCaseUnarchiveReviewValidationError({ ...base, requestStatus: "已通过" }), "该案件没有待审批的解档申请");
  assert.equal(helper.getCaseUnarchiveReviewValidationError({ ...base, requestedBy: "reviewer" }), "解档申请人不能审批自己的申请");
  assert.equal(helper.getCaseUnarchiveReviewValidationError({ ...base, approved: false }), "驳回时必须填写至少2个字的原因");
  assert.equal(helper.getCaseUnarchiveReviewValidationError({ ...base, approved: false, comment: "退" }), "驳回时必须填写至少2个字的原因");
  assert.equal(helper.getCaseUnarchiveReviewValidationError({ ...base, approved: false, comment: "材料不足" }), "");
  assert.deepEqual(helper.buildCaseUnarchiveReviewPayload({ approved: false, comment: "  材料不足  " }), { approved: false, comment: "材料不足" });
  assert.deepEqual(helper.buildCaseUnarchiveReviewPayload({ approved: true, comment: "  同意解档并恢复办理  " }), { approved: true, comment: "同意解档并恢复办理" });
  assert.match(page, /getCaseUnarchiveReviewValidationError/);
  assert.match(page, /buildCaseUnarchiveReviewPayload/);
  assert.match(page, /openUnarchiveReview/);
});
