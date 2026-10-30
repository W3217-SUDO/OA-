// BUG20261030002（范明明 2026-10-30）：官方费用申请付款必须填缴费截止日期。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { buildExternalPaymentRequestPayload } from "../src/casePaymentUnitParity.mjs";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");

test("申请付款带上缴费截止日期", () => {
  assert.equal(buildExternalPaymentRequestPayload({ amount: 100, deadline: "2026-11-05" }).deadline, "2026-11-05");
  assert.equal(buildExternalPaymentRequestPayload({ amount: 100, deadline: { format: () => "2026-11-06" } }).deadline, "2026-11-06");
  assert.equal("deadline" in buildExternalPaymentRequestPayload({ amount: 100 }), false);
});

test("新增费用第2步和申请付款抽屉都有缴费截止日期，官费必填", () => {
  const page = read("../src/legal/CaseCenterPage.tsx");
  assert.equal(page.match(/<span>付款备注<\/span><span>缴费截止日期<\/span>/g)?.length, 2);
  assert.match(page, /required: paymentRequestFee\?\.data\.fee_type === "官方费用", message: "官方费用请填写缴费截止日期"/);
  const actions = read("../src/legal/services/financeActions.tsx");
  assert.match(actions, /fee_type === "官方费用" && !item\.deadline/);
  assert.match(actions, /deadline: String\(row\.data\.deadline \|\| ""\)\.slice\(0, 10\)/);
});
