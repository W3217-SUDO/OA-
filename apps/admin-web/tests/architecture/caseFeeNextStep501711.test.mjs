import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const page = readFileSync(new URL("../../src/legal/CaseCenterPage.tsx", import.meta.url), "utf8");
const actions = readFileSync(new URL("../../src/legal/services/financeActions.tsx", import.meta.url), "utf8");

test("501711: 修改费用弹窗关闭后卸载，残留必填项不再卡住新增费用的下一步", () => {
  const modal = page.slice(page.indexOf("open={Boolean(editingFeeRow)}"), page.indexOf("<Form form={feeForm} layout=\"vertical\">"));
  assert.match(modal, /destroyOnHidden/);
  const drawer = page.slice(page.indexOf("case-fee-create-drawer"), page.indexOf("case-fee-drawer-footer"));
  assert.match(drawer, /destroyOnHidden/, "新增费用抽屉关闭后也卸载，费用行不再挡修改费用的保存");
});

test("501711: 新增费用只校验费用行，校验失败要提示，提交中按钮显示加载", () => {
  const body = actions.slice(actions.indexOf("const createCaseFee = async"), actions.indexOf("const submitCreatedCaseFeePayments"));
  assert.match(body, /validateFields\(\[\["items"\]\], \{ recursive: true \}\)/);
  assert.match(body, /请先完善费用信息/);
  assert.match(body, /setCaseFeeSubmitting\(true\)/);
  assert.match(body, /finally[\s\S]*setCaseFeeSubmitting\(false\)/);
});
