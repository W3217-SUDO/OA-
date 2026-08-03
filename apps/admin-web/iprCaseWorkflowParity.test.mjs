import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const helper = await import(new URL("./src/iprCaseWorkflowParity.mjs", import.meta.url));
const page = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

const base = {
  role: "owner",
  status: "草稿",
  applicationNo: "CN20260001",
  approved: true,
  comment: "",
};

test("IPR submit validates draft status and application number before the API", () => {
  assert.equal(helper.getIprCaseActionValidationError({ ...base, action: "submit" }), "");
  assert.equal(helper.getIprCaseActionValidationError({ ...base, action: "submit", status: "在办" }), "当前状态不能提交知识产权立案审核");
  assert.equal(helper.getIprCaseActionValidationError({ ...base, action: "submit", applicationNo: "  " }), "提交立案审核前必须填写申请号或注册号");
});

test("IPR review validates reviewer role, pending status, and rejection reason", () => {
  const review = { ...base, action: "review", status: "待立案审核", role: "manager" };
  assert.equal(helper.getIprCaseActionValidationError({ ...review, role: "user" }), "仅管理员或管理人员可以审核知识产权立案");
  assert.equal(helper.getIprCaseActionValidationError({ ...review, status: "草稿" }), "该知识产权案件不在待立案审核状态");
  assert.equal(helper.getIprCaseActionValidationError({ ...review, approved: false, comment: "  " }), "驳回必须填写原因");
  assert.equal(helper.getIprCaseActionValidationError({ ...review, approved: false, comment: "材料不足" }), "");
});

test("IPR close and reopen validate lifecycle state and role", () => {
  assert.equal(helper.getIprCaseActionValidationError({ ...base, action: "close", status: "在办" }), "");
  assert.equal(helper.getIprCaseActionValidationError({ ...base, action: "close", status: "草稿" }), "仅在办知识产权案件可以结案");
  assert.equal(helper.getIprCaseActionValidationError({ ...base, action: "reopen", status: "已结案", role: "user" }), "仅管理员或管理人员可以重新开启知识产权案件");
  assert.equal(helper.getIprCaseActionValidationError({ ...base, action: "reopen", status: "草稿", role: "admin" }), "仅已结案知识产权案件可以重新开启");
});

test("IPR action payload trims comments and keeps review approval explicit", () => {
  assert.deepEqual(helper.buildIprCaseActionPayload({ action: "review", approved: false, comment: "  材料不足  " }), { approved: false, comment: "材料不足" });
  assert.deepEqual(helper.buildIprCaseActionPayload({ action: "review", approved: true, comment: "  同意  " }), { approved: true, comment: "同意" });
  assert.deepEqual(helper.buildIprCaseActionPayload({ action: "submit", comment: "  " }), { comment: "" });
  assert.match(page, /getIprCaseActionValidationError/);
  assert.match(page, /buildIprCaseActionPayload/);
});
