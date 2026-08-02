import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("legacy PaymentView is represented by a finance record detail fetch", () => {
  assert.match(source, /const openPaymentDetail = async \(row: Fee\)/);
  assert.match(source, /api\.get\(`\/records\/\$\{row\.id\}`\)/);
});

test("payment detail accepts both finance and contract-payment records", () => {
  assert.match(source, /\["finance", "contract_payment"\]\.includes\(data\.module\)/);
});

test("invalid detail records fail explicitly instead of opening a misleading modal", () => {
  assert.match(source, /throw new Error\("请款单详情记录无效"\)/);
  assert.match(source, /error\?\.message \|\|\s*"请款单详情加载失败"/);
});

test("payment query and mine rows use the canonical detail loader", () => {
  const helperUses = source.match(/void openPaymentDetail\(row\)/g) || [];
  assert.ok(helperUses.length >= 2);
  assert.match(
    source,
    /\[\s*"finance-payment-mine",\s*"finance-payment-query",\s*"finance-internal-mine",\s*\]/,
  );
});

test("detail loading is bounded to one record and does not introduce page scans", () => {
  const helper = source.slice(
    source.indexOf("const openPaymentDetail"),
    source.indexOf("\n  useEffect", source.indexOf("const openPaymentDetail")),
  );
  assert.doesNotMatch(helper, /page_size|while|for \(/);
});

test("legacy detail dependencies remain rendered by the existing detail panel", () => {
  assert.match(source, /title="请款单详情"/);
  assert.match(source, /linkedCaseForFee\(feeDetail\)/);
  assert.match(source, /feeDetail\.data\.contract_no/);
});

