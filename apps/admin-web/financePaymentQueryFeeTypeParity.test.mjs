import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const loadPaymentQueryFeeTypeControl = () => {
  const start = source.indexOf("const paymentQueryFeeTypeControl");
  const end = source.indexOf("\n\ntype PaymentPrintDocumentData", start);
  assert.notEqual(start, -1, "payment query fee-type policy should exist");
  assert.notEqual(end, -1, "payment query fee-type policy should be extractable");
  const javascript = ts.transpileModule(source.slice(start, end), {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.None,
    },
  }).outputText;
  const context = vm.createContext({});
  vm.runInContext(
    `${javascript}\nglobalThis.__feeTypeControl = paymentQueryFeeTypeControl;`,
    context,
  );
  return context.__feeTypeControl;
};

test("payment query alone uses the legacy free-text fee-type filter", () => {
  const feeTypeControlFor = loadPaymentQueryFeeTypeControl();
  assert.equal(feeTypeControlFor("finance-payment-query"), undefined);
  assert.equal(feeTypeControlFor("finance-payment-mine"), "feeType");
  assert.equal(feeTypeControlFor("finance-payment-print"), "feeType");
  assert.equal(feeTypeControlFor("finance-payment-writeoff"), "feeType");
  assert.match(
    source,
    /queryField\(\s*"费用类型",\s*"feeType",\s*paymentQueryFeeTypeControl\(initialView\),?\s*\)/,
  );
});
