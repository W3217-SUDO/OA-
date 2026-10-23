import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), 'utf8');
const casePage = read('../src/legal/CaseCenterPage.tsx');
const financeActions = read('../src/legal/services/financeActions.tsx');

test('内部费用申请付款步骤在明细表单卸载后仍按内部费用布局展示', () => {
  // 申请付款步骤不渲染 items 表单；不保留取值会退回律所收款单位布局，导致退费提成无法提交内部请款。
  assert.match(casePage, /Form\.useWatch\("items", \{ form: feeForm, preserve: true \}\)/);
  assert.match(casePage, /const activeFeeContractScope = editingFeeRow \? feeExpenseScope : String\(feeItems\[0\]\?\.expense_scope \|\| ""\);/);
});

test('律师代理费（退费）不能从案件律所费用发起付款管理请款', () => {
  const openPaymentRequest = financeActions.slice(financeActions.indexOf('const openPaymentRequest'), financeActions.indexOf('const submitPaymentRequest'));
  const guard = openPaymentRequest.indexOf('row.data.refund_fee === true && row.data.fee_type === "代理费"');
  assert.ok(guard > 0, '缺少律师代理费（退费）拦截');
  assert.ok(guard < openPaymentRequest.indexOf('loadCasePaymentTypes'), '必须在加载付款单位前拦截');
  assert.match(openPaymentRequest, /新建提成\(选择费用\)/);
});

test('新建提成即同时提交付款申请，结果提示不再要求另点申请付款', () => {
  assert.match(casePage, /提成 \$\{caseCommissionResult\.application_no\} 已生成并提交付款申请/);
  assert.match(financeActions, /提成 \$\{data\.application_no\} 已生成并提交付款申请/);
  assert.doesNotMatch(casePage + financeActions, /再在内部费用中申请付款|请在内部费用中申请付款/);
});
