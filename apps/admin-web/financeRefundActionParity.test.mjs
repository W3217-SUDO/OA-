import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("./src/FinanceCenterPage.tsx", import.meta.url), "utf8");

test("refund fee creation uses the legacy multi-case slide panel", () => {
  assert.match(source, /openRefundBatchFee\(feeTypeByKey\[key\]\)/);
  assert.match(source, /open=\{refundBatchFeeOpen\}/);
  assert.match(source, /title="新增费用"/);
  assert.match(source, /items=\{\[\{ title: "新增费用" \}, \{ title: "申请付款" \}\]\}/);
  assert.match(source, /同步首行到全部/);
  for (const label of ["案号", "合同号", "费用类型", "金额", "备注", "截止日期", "操作"]) {
    assert.match(source, new RegExp(`>${label}<`));
  }
});

test("refund batch fee creation is sent as one transactional request", () => {
  assert.match(source, /api\.post\("\/finance\/case-fees\/batch"/);
  assert.match(source, /contract_record_id: item\.contract_record_id \|\| null/);
  assert.match(source, /deadline: formatRequiredDate\(item\.deadline, "截止日期"\)/);
});

test("refund documents tasks and logs use the whole selected case set", () => {
  assert.match(source, /const linked = selectedSettlementCases\(\);[\s\S]*for \(const caseRecord of linked\)/);
  assert.match(source, /caseRecords: linked/);
  assert.match(source, /source_case_no: item\.serial_no/);
});

