import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const loadPaymentQueryPageSizeOptions = () => {
  const start = source.indexOf("const paymentQueryPageSizeOptions");
  const end = source.indexOf("\n\nconst paymentQueryDefaultPageSize", start);
  assert.notEqual(start, -1, "payment query page-size options should exist");
  assert.notEqual(end, -1, "payment query page-size options should be extractable");
  const javascript = ts.transpileModule(source.slice(start, end), {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.None,
    },
  }).outputText;
  const context = vm.createContext({});
  vm.runInContext(
    `${javascript}\nglobalThis.__pageSizeOptionsFor = paymentQueryPageSizeOptions;`,
    context,
  );
  return context.__pageSizeOptionsFor;
};

test("payment query pagination offers all six legacy page-size options", () => {
  const optionsFor = loadPaymentQueryPageSizeOptions();

  assert.deepEqual(
    JSON.parse(JSON.stringify(optionsFor("finance-payment-query"))),
    [10, 15, 20, 50, 100, 200],
  );
  assert.equal(optionsFor("finance-payment-mine"), undefined);
  assert.equal(optionsFor("finance-payment-print"), undefined);

  const pagination = source.match(
    /pagination=\{\{[\s\S]*?showSizeChanger:\s*true/,
  );
  assert.ok(pagination, "payment pagination should exist");
  assert.match(
    pagination[0],
    /pageSizeOptions:[\s\S]*?paymentQueryPageSizeOptions\(initialView\)/,
  );
});
