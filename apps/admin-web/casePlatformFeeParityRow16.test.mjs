import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const platformStart = source.indexOf('{key:"platform-fees",label:"平台费用"');
const platformEnd = source.indexOf('{key:"internal-fees"', platformStart);
const platformPanel = source.slice(platformStart, platformEnd);
const feeDrawerStart = source.indexOf('<Drawer\n        open={Boolean(feeCase)}');
const feeDrawerEnd = source.indexOf("</Drawer>", feeDrawerStart);
const feeDrawer = source.slice(feeDrawerStart, feeDrawerEnd);

test("row 16 keeps platform fee creation scoped to platform contracts", () => {
  assert.match(source, /params: \{ expense_scope: expenseScope \}/);
  assert.match(source, /当前案件客户名下没有\$\{expenseScope\}合同，无法新增\$\{expenseScope\}费用/);
  assert.match(platformPanel, /openCaseFeeBySubtype\("平台",key\)/);
});

test("row 16 gives platform fees the four legacy fee entries without commission", () => {
  for (const label of ["新增官费", "新增第三方费用", "新增代理费", "新增其他费用"]) {
    assert.match(platformPanel, new RegExp(label));
  }
  assert.doesNotMatch(platformPanel, /新建提成/);
});

test("row 16 shares the empty state and other operations with law-firm fees", () => {
  assert.match(platformPanel, /renderCaseFeeEmptyState\("平台"\)/);
  assert.match(platformPanel, />其他操作<\/Button>/);
  for (const label of ["法院退费", "申请付款", "申请开票", "修改", "删除", "标记不缴费"]) {
    assert.match(platformPanel, new RegExp(label));
  }
});

test("row 16 platform creation no longer requires a material type", () => {
  assert.doesNotMatch(feeDrawer, /关联材料类型/);
  assert.doesNotMatch(feeDrawer, /source_file_type/);
});
