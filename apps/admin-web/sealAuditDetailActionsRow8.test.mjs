import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const page = fs.readFileSync("src/SealCenterPage.tsx", "utf8");

test("audit number opens the detail drawer instead of preselecting approval", () => {
  const start = page.indexOf("const openSealNumber");
  const end = page.indexOf("const closeDetail", start);
  const source = page.slice(start, end);

  assert.match(source, /void openDetail\(row\)/);
  assert.doesNotMatch(source, /setAction\(\{ type: "approve"/);
});

test("audit detail keeps remark, opinion and both decisions in one drawer", () => {
  const title = page.indexOf('"用印审核"');
  const start = page.lastIndexOf("<Drawer", title);
  const end = page.indexOf("</Drawer>", start);
  const source = page.slice(start, end);

  assert.match(source, /"用印审核"/);
  assert.match(source, /label: "用印备注"|label: "\\u7528\\u5370\\u5907\\u6ce8"/);
  assert.match(source, /label="审批意见"/);
  assert.match(source, /runDetailApproval\(true\)/);
  assert.match(source, />\s*通过\s*<\/Button>/);
  assert.match(source, /runDetailApproval\(false\)/);
  assert.match(source, />\s*拒绝\s*<\/Button>/);
  assert.match(source, /onClick=\{closeDetail\}>取消/);
});

test("detail decisions use the real API and keep rejection reason validation", () => {
  const start = page.indexOf("const runDetailApproval");
  const end = page.indexOf("const openAuditList", start);
  const source = page.slice(start, end);

  assert.match(source, /postSeal\(`\/seals\/applications\/\$\{detail\.id\}\/approve`/);
  assert.match(source, /approved,/);
  assert.match(source, /comment,/);
  assert.match(source, /if \(!approved && !comment\)/);
  assert.match(source, /拒绝时必须填写原因/);
  assert.match(source, /await load\(\)/);
});
