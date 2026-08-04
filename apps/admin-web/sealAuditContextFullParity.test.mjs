import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const page = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
const oldAudit = fs.readFileSync(
  path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "../../../旧系统归档源码/SH.CRM.WEB/Areas/AWS/Views/OfficialDocumentAudit/PartialView/Audit.cshtml",
  ),
  "utf8",
);

function sliceBetween(source, startToken, endToken) {
  const start = source.indexOf(startToken);
  assert.notEqual(start, -1, "missing source anchor: " + startToken);
  const end = source.indexOf(endToken, start + startToken.length);
  assert.notEqual(end, -1, "missing source end anchor: " + endToken);
  return source.slice(start, end);
}

test("legacy audit panel exposes the full request context before the decision", () => {
  assert.match(
    oldAudit,
    /是否电章：[\s\S]*?印章类型：[\s\S]*?是否打印盖章：[\s\S]*?盖章份数：[\s\S]*?用印备注：/,
  );
  const approvalContext = sliceBetween(
    page,
    'action?.type === "approve" || action?.type === "reject"',
    "<Form form={actionForm}",
  );
  assert.match(approvalContext, /label: "合同编号"[\s\S]*?action\.row\.data\.contract_no/);
  assert.match(approvalContext, /label: "印章类型"[\s\S]*?action\.row\.data\.seal_type/);
  assert.match(approvalContext, /label: "是否电章"[\s\S]*?action\.row\.data\.is_electronic_seal/);
  assert.match(approvalContext, /label: "是否打印盖章"[\s\S]*?action\.row\.data\.is_offline_print/);
  assert.match(approvalContext, /label: "盖章份数"[\s\S]*?action\.row\.data\.(print_quantity|copies)/);
  assert.match(approvalContext, /label: "用印备注"[\s\S]*?action\.row\.data\.remark[\s\S]*?action\.row\.description/);
});
