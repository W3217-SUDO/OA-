import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("payment approval page-size changer updates its controlled value", () => {
  assert.match(
    source,
    /const \[paymentAuditPageSize, setPaymentAuditPageSize\] = useState\(15\);/,
  );

  const pagination = source.match(
    /pagination=\{\{[\s\S]*?\.\.\.\(isFeeQueryRoute/,
  );
  assert.ok(pagination, "payment approval pagination should exist");
  assert.match(pagination[0], /showSizeChanger:\s*true/);
  assert.match(
    pagination[0],
    /initialView\s*===\s*"finance-payment-audit"\s*\?\s*paymentAuditPageSize/,
  );
  assert.match(
    pagination[0],
    /initialView\s*===\s*"finance-payment-audit"[\s\S]*?onShowSizeChange:[\s\S]*?setPaymentAuditPageSize\(pageSize\)/,
  );
});

test("payment approval number opens the legacy single-record review view", () => {
  const columns = source.match(
    /const paymentAuditOriginalColumns = \[[\s\S]*?\n  \];/,
  );

  assert.ok(columns, "payment approval columns should exist");
  assert.match(
    columns[0],
    /title:\s*"请款单号"[\s\S]*?dataIndex:\s*"serial_no"[\s\S]*?<Button[\s\S]*?setFeeReviewTargets\(\[row\]\)[\s\S]*?\{value\}[\s\S]*?<\/Button>/,
  );
});

test("payment approval empty selection keeps the legacy failure prompt", () => {
  const batchReview = source.match(
    /const openBatchFeeReview = \(\) => \{[\s\S]*?\n  \};/,
  );

  assert.ok(batchReview, "payment approval batch handler should exist");
  assert.match(
    batchReview[0],
    /initialView\s*===\s*"finance-payment-audit"[\s\S]*?Modal\.info\(\{[\s\S]*?title:\s*"提示"[\s\S]*?content:\s*"请选择审批项\."[\s\S]*?okText:\s*"确定"/,
  );
});

test("ordinary payment rows expose dedicated cancel and rollback contracts", () => {
  assert.match(source, /finance\/fees\/\$\{paymentCancelTarget\.id\}\/cancel/);
  assert.match(source, /finance\/fees\/\$\{paymentRollbackTarget\.id\}\/rollback/);
  assert.match(source, /api\.post\([\s\S]*?paymentCancelTarget[\s\S]*?reason/);
  assert.match(source, /api\.post\([\s\S]*?paymentRollbackTarget[\s\S]*?comment/);
  assert.match(source, /const reason = paymentCancelReason\.trim\(\)/);
  assert.match(source, /if \(!reason\)[\s\S]*?请输入撤回原因/);
  assert.match(source, /comment: paymentRollbackComment\.trim\(\)/);
  assert.match(source, /error\?\.response\?\.data\?\.detail/);
  assert.match(source, /撤销请款|付款撤销/);
  assert.match(source, /回滚请款|付款回滚/);
  assert.match(source, /撤销成功！/);
  assert.match(source, /撤销失败！/);
  assert.match(source, /回滚成功！/);
  assert.match(source, /回滚失败！/);
  assert.match(source, /open=\{Boolean\(paymentCancelTarget\)\}/);
  assert.match(source, /open=\{Boolean\(paymentRollbackTarget\)\}/);
});
