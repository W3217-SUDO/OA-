// 279951（审核部 shenhe 11-02 确认）：回款(工行/中信/中行/招商) 上传先留本页“未导入”，勾选“导入”才进回款管理，“删除”只删未导入。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");

test("四个银行回款页走未导入流水列表，已导入时显示原到账列表", () => {
  const view = read("../src/finance/FinanceCenterView.tsx");
  assert.match(view, /<BankReceiptFlowRoute routesView=\{originalRoutesView\} financeScope=\{props\.financeScope\} \/>/);
  const route = read("../src/finance/BankReceiptFlowRoute.tsx");
  assert.match(route, /useState<BankPageFlowStatus>\("未导入"\)/);
  assert.match(route, /if \(status === "已导入"\)/);
  assert.match(route, /!query\.routeConfig\?\.upload \|\| financeScope === "unclassified"/);
  assert.match(route, /fixedBank=\{bank\}/);
  const scope = read("../src/finance/bankReceiptScope.ts");
  assert.match(scope, /\(icbc\|citic\|boc\|cmb\|gdicbc\)/); // 501588：国定工行同工行
});

test("查询、上传、导入、删除排在一排，导入删除用银行原始流水同一套接口", () => {
  const lines = read("../src/finance/BankFlowPage.tsx");
  const row = lines.slice(lines.indexOf('htmlType="submit">查询'), lines.indexOf("清空\n"));
  for (const label of ["onUpload && <Button", "{generateLabel}", "删除"]) assert.ok(row.includes(label), label);
  assert.match(lines, /const generateLabel = fixedBank \? "导入" : "生成到账单"/);
  assert.match(lines, /api\.post\(`\/finance\/bank-flows\/\$\{kind\}`/);
  assert.match(lines, /bank: fixedBank \|\| filters\.bank/);
});

test("上传确认后通知本页刷新未导入列表", () => {
  const actions = read("../src/finance/services/workflowActions.tsx");
  assert.match(actions, /response\.data\.target === "bank_flows"\) window\.dispatchEvent\(new Event\(BANK_FLOW_UPLOADED_EVENT\)\)/);
  assert.match(actions, /在本页“未导入”里勾选后点“导入”进回款管理/);
});
