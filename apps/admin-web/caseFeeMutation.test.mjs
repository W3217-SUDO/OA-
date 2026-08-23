import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("draft case fees have guarded edit and delete operations", () => {
  assert.match(source, /const editCaseFee = \(row: CaseRow\) => \{\s*if \(row\.status !== "草稿"\)/);
  assert.match(source, /api\.put\(`\/finance\/fees\/\$\{editingFeeRow\.id\}`/);
  assert.match(source, /const deleteCaseFee = \(row: CaseRow\) => \{\s*if \(row\.status !== "草稿"\)/);
  assert.match(source, /api\.delete\(`\/finance\/fees\/\$\{row\.id\}`/);
  assert.match(source, /Modal\.confirm\(\{ title: `删除费用/);
});

test("the fee editor is isolated from the create drawer and clears its target", () => {
  assert.match(source, /open=\{Boolean\(editingFeeRow\)\}/);
  assert.match(source, /okText="保存费用草稿"/);
  assert.match(source, /onCancel=\{\(\) => \{ setEditingFeeRow\(null\); feeForm\.resetFields\(\); \}\}/);
  assert.match(source, /open=\{Boolean\(feeCase\)\}/);
});

test("law-firm and internal fees retain their distinct payment flows", () => {
  assert.match(source, /if\(key==="payment"\)return openPaymentRequest\(selectedFirmFee!\)/);
  assert.match(source, /if\(key==="payment"\)return void previewInternalPayment\(selectedInternalFee!\)/);
});
