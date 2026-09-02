import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");
const appSource = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("contract investigation wizard preserves the legacy three-step source and assignment flow", () => {
  const pageStart = source.indexOf('title="新建调查任务"');
  const pageEnd = source.indexOf('title="选择城市"', pageStart);
  const page = source.slice(pageStart, pageEnd);

  assert.ok(pageStart > 0 && pageEnd > pageStart);
  assert.match(page, /"新建调查任务", "选择分配人", "完成分配"/);
  assert.match(page, /label="权利人"[\s\S]*investigating\?\.data\.customer_name[\s\S]*investigating\?\.customer/);
  assert.match(page, /label="合同编号"[\s\S]*investigating\?\.serial_no/);
  assert.match(page, /label="合同名称"[\s\S]*investigating\?\.title/);
  assert.match(page, /label="线索是否客户审核"/);
  assert.match(page, /label="授权期限"/);
  assert.match(page, /label="分配人"[\s\S]*<Select disabled options=\{investigationSupervisor/);
  assert.match(page, /<Divider titlePlacement="start">调查信息<\/Divider>/);
  assert.match(page, /调查任务分配完成/);
  assert.match(page, /investigationError[\s\S]*<Alert type="error" showIcon message=\{investigationError\}/);
  assert.match(source, /setInvestigationDraftValues\(values\)/);
  assert.match(source, /const values = \{ \.\.\.investigationDraftValues, \.\.\.assignmentValues \}/);
});

test("contract investigation opens as a dedicated dynamic work page", () => {
  assert.match(source, /contract-investigation-\$\{r\.id\}-\$\{encodeURIComponent\(r\.serial_no\)\}/);
  assert.match(source, /rootClassName=\{isContractInvestigationView \? "contract-detail-static-root"/);
  assert.match(source, /!isContractDetailView && !isContractInvestigationView/);
  assert.match(appSource, /normalizedKey\.startsWith\("contract-investigation-"\)\) return "新建调查任务"/);
  assert.match(appSource, /active\.startsWith\("contract-investigation-"\)/);
});
