import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const loadPaymentWriteoffClearQuery = () => {
  const start = source.indexOf("const paymentWriteoffClearQuery");
  const end = source.indexOf("\n\ntype PaymentPrintDocumentData", start);
  assert.notEqual(start, -1, "payment writeoff clear policy should exist");
  assert.notEqual(end, -1, "payment writeoff clear policy should be extractable");
  const javascript = ts.transpileModule(source.slice(start, end), {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.None,
    },
  }).outputText;
  const context = vm.createContext({});
  vm.runInContext(
    `${javascript}\nglobalThis.__clearQuery = paymentWriteoffClearQuery;`,
    context,
  );
  return context.__clearQuery;
};

test("clearing payment writeoff keeps the legacy locked pending-writeoff status", () => {
  const clearQueryFor = loadPaymentWriteoffClearQuery();
  assert.deepEqual(
    JSON.parse(JSON.stringify(clearQueryFor("finance-payment-writeoff"))),
    { status: "待核销" },
  );
  assert.deepEqual(
    JSON.parse(JSON.stringify(clearQueryFor("finance-payment-print"))),
    {},
  );
  assert.deepEqual(
    JSON.parse(JSON.stringify(clearQueryFor("finance-payment-waiting"))),
    {},
  );
  assert.match(
    source,
    /const next = paymentWriteoffClearQuery\(initialView\);\s*setOriginalQueryDraft\(next\);\s*setOriginalQuery\(next\);/,
  );
});
