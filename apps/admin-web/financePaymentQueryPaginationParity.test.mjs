import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const loadPaymentQueryDefaultPageSize = () => {
  const start = source.indexOf("const paymentQueryDefaultPageSize");
  const end = source.indexOf("\n\nconst paymentQueryFeeTypeControl", start);
  assert.notEqual(start, -1, "payment query page-size policy should exist");
  assert.notEqual(end, -1, "payment query page-size policy should be extractable");
  const javascript = ts.transpileModule(source.slice(start, end), {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.None,
    },
  }).outputText;
  const context = vm.createContext({});
  vm.runInContext(
    `${javascript}\nglobalThis.__pageSizeFor = paymentQueryDefaultPageSize;`,
    context,
  );
  return context.__pageSizeFor;
};

test("payment query pagination keeps the legacy fifteen-row default", () => {
  const pageSizeFor = loadPaymentQueryDefaultPageSize();

  assert.equal(pageSizeFor("finance-payment-query"), 15);
  assert.equal(pageSizeFor("finance-payment-mine"), undefined);
  assert.equal(pageSizeFor("finance-payment-print"), undefined);

  const pagination = source.match(
    /pagination=\{\{[\s\S]*?showSizeChanger:\s*true/,
  );
  assert.ok(pagination, "payment pagination should exist");
  assert.match(
    pagination[0],
    /pageSize:[\s\S]*?paymentQueryDefaultPageSize\(initialView\)/,
  );
});
