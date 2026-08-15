import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("row 27 court refund stays bound to the selected official fee and source case", () => {
  assert.match(source, /openCourtRefund/);
  assert.match(source, /fee_record_id: courtRefundFee\.id/);
  assert.match(source, /case_no: viewingCounselCase\.serial_no/);
  assert.match(source, /法院退费：\$\{courtRefundFee/);
  assert.match(source, /原案：\$\{viewingCounselCase/);
  assert.match(source, /key === "refund" \? \(selectedFirmFee/);
  assert.doesNotMatch(source, /label="退款账户名"/);
  assert.doesNotMatch(source, /label="退款银行"/);
  assert.doesNotMatch(source, /label="退款账号"/);
  assert.doesNotMatch(source, /expected_date/);
});
