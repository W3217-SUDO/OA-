import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const loadPaymentQueryQuickJumper = () => {
  const start = source.indexOf("const paymentQueryQuickJumper");
  const end = source.indexOf("\n\nconst paymentQueryPageSizeOptions", start);
  assert.notEqual(start, -1, "payment query quick-jumper policy should exist");
  assert.notEqual(end, -1, "payment query quick-jumper policy should be extractable");
  const javascript = ts.transpileModule(source.slice(start, end), {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.None,
    },
  }).outputText;
  const context = vm.createContext({});
  vm.runInContext(
    `${javascript}\nglobalThis.__quickJumperFor = paymentQueryQuickJumper;`,
    context,
  );
  return context.__quickJumperFor;
};

const loadPaymentQuerySinglePageGo = () => {
  const start = source.indexOf("const paymentQueryShowsSinglePageGo");
  const end = source.indexOf("\n\nconst paymentQueryPageSizeOptions", start);
  assert.notEqual(start, -1, "payment query single-page GO policy should exist");
  assert.notEqual(end, -1, "payment query single-page GO policy should be extractable");
  const javascript = ts.transpileModule(source.slice(start, end), {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.None,
    },
  }).outputText;
  const context = vm.createContext({});
  vm.runInContext(
    `${javascript}\nglobalThis.__showsSinglePageGo = paymentQueryShowsSinglePageGo;`,
    context,
  );
  return context.__showsSinglePageGo;
};

test("payment query keeps the legacy GO control visible for a single page", () => {
  const quickJumperFor = loadPaymentQueryQuickJumper();
  const showsSinglePageGo = loadPaymentQuerySinglePageGo();

  assert.deepEqual(
    JSON.parse(JSON.stringify(quickJumperFor("finance-payment-query"))),
    { goButton: "GO" },
  );
  assert.equal(quickJumperFor("finance-payment-mine"), undefined);
  assert.equal(quickJumperFor("finance-payment-print"), undefined);
  assert.equal(showsSinglePageGo("finance-payment-query", 1, 15), true);
  assert.equal(showsSinglePageGo("finance-payment-query", 15, 15), true);
  assert.equal(showsSinglePageGo("finance-payment-query", 16, 15), false);
  assert.equal(showsSinglePageGo("finance-payment-query", 0, 15), false);
  assert.equal(showsSinglePageGo("finance-payment-mine", 1, 15), false);

  const pagination = source.match(
    /pagination=\{\{[\s\S]*?showSizeChanger:\s*true/,
  );
  assert.ok(pagination, "payment pagination should exist");
  assert.match(
    pagination[0],
    /showQuickJumper:\s*paymentQueryQuickJumper\(initialView\)/,
  );
  assert.match(
    source,
    /paymentQueryShowsSinglePageGo\([\s\S]*?configuredRows\.length[\s\S]*?aria-label="跳转页码"[\s\S]*?>\s*GO\s*<\/Button>/,
  );
});
