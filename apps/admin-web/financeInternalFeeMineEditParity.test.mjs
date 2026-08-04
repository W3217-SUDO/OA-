import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("my internal-fee draft row reuses the guarded finance-fee edit flow", () => {
  const operation = source.match(
    /const internalMineOperation = \([\s\S]*?\n  const feeQueryFields/,
  );

  assert.ok(operation, "internal-fee row operation should exist");
  assert.match(
    operation[0],
    /const mayEdit =[\s\S]*?row\.module === "finance"[\s\S]*?row\.data\.fee_type === "内部费用"[\s\S]*?row\.status === "草稿"[\s\S]*?\(canManage \|\| row\.owner === currentUser\.username\)/,
  );
  assert.match(
    operation[0],
    /mayEdit && \([\s\S]*?openFeeEdit\(row\)[\s\S]*?编辑/,
  );
  assert.match(
    source,
    /const openFeeEdit = \(row: Fee\) => \{[\s\S]*?expense_scope:[\s\S]*?expense_subtype:[\s\S]*?case_record_id:[\s\S]*?contract_record_id:/,
  );
});
