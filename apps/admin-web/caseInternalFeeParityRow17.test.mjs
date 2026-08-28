import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const expected = ["产品购买费", "翻译费", "投资提成", "调档费", "手续费", "任务调期扣款", "服务费(调查)", "服务费(开庭)", "服务费(案源)", "服务费(文书)", "服务费(品管)"];
const internalStart = source.indexOf('activeFeeContractScope === "内部" ? <div className="case-fee-entry-table case-internal-fee-entry-table">');
const internalEnd = source.indexOf(': <div className="case-fee-entry-table">', internalStart);
const internalForm = source.slice(internalStart, internalEnd);

test("row 17 restores all legacy internal fee types", () => {
  for (const subtype of expected) assert.match(source, new RegExp(subtype.replace(/[()]/g, "\\$&")));
  assert.match(source, /activeFeeContractScope === "内部"\s*\? LEGACY_INTERNAL_FEE_SUBTYPES/);
});

test("row 17 internal form matches the legacy columns without a contract", () => {
  for (const heading of ["案号", "费用类型", "支付对象", "基数", "参考提成", "实际金额", "备注", "操作"]) assert.match(internalForm, new RegExp(heading));
  assert.doesNotMatch(internalForm, /contract_record_id|合同号|source_file_type|关联材料类型/);
});

test("row 17 requires a payee and saves the internal fee values", () => {
  assert.match(internalForm, /name=\{\[field\.name, "payee"\]\}/);
  assert.match(internalForm, /请选择收款人/);
  assert.match(internalForm, /name=\{\[field\.name, "base_amount"\]\}/);
  assert.match(internalForm, /name=\{\[field\.name, "reference_commission"\]\}/);
  assert.match(internalForm, /name=\{\[field\.name, "amount"\]\}/);
});

test("row 17 starts blank and groups payment applications by case number", () => {
  assert.match(source, /const initialSubtype = expenseScope === "内部" \? undefined/);
  assert.match(source, /payee: expenseScope === "内部" \? undefined/);
  assert.match(source, /activeFeeContractScope === "内部"[\s\S]*申请付款按照每个案号生成一个申请单/);
  assert.match(source, /paymentRequestFee\?\.data\.expense_scope === "内部"[\s\S]*申请付款按照每个案号生成一个申请单/);
});
