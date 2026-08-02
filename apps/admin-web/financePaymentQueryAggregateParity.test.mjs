import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const loadPaymentQueryPageTotal = () => {
  const start = source.indexOf("const paymentQueryPageTotal");
  const end = source.indexOf("\n\nconst paymentQueryFeeTypeControl", start);
  assert.notEqual(start, -1, "payment query should expose a page total policy");
  assert.notEqual(end, -1, "payment query total policy should be extractable");
  const javascript = ts.transpileModule(source.slice(start, end), {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.None,
    },
  }).outputText;
  const context = vm.createContext({});
  vm.runInContext(
    `${javascript}\nglobalThis.__pageTotal = paymentQueryPageTotal;`,
    context,
  );
  return context.__pageTotal;
};

test("payment query renders the current page amount total from fee amounts", () => {
  const pageTotal = loadPaymentQueryPageTotal();

  assert.equal(
    pageTotal([
      { data: { amount: 1500 } },
      { data: { amount: "300.5" } },
      { data: {} },
    ]),
    "1800.50",
  );
});

test("payment query places its amount total row around the current page rows", () => {
  assert.match(
    source,
    /initialView === "finance-payment-query" && configuredRows\.length[\s\S]*?finance-payment-query-page-total[\s\S]*?paymentQueryPageTotal\(configuredRows\)/,
    "payment query should render a legacy total row before its data",
  );
  assert.match(
    source,
    /summary=\{[\s\S]*?initialView === "finance-payment-query"[\s\S]*?finance-payment-query-page-total-bottom[\s\S]*?paymentQueryPageTotal\(pageData\)/,
    "payment query should render the total again after its data",
  );
});
