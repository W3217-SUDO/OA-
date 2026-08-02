import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const loadPagePlan = () => {
  const start = source.indexOf("const paymentQueryServerPagePlan");
  const end = source.indexOf("\n\nconst paymentQueryPageTotal", start);
  assert.notEqual(start, -1, "payment query should expose a bounded server page plan");
  assert.notEqual(end, -1, "payment query page plan should be extractable");
  const javascript = ts.transpileModule(source.slice(start, end), {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.None,
    },
  }).outputText;
  const context = vm.createContext({});
  vm.runInContext(
    `${javascript}\nglobalThis.__pagePlan = paymentQueryServerPagePlan;`,
    context,
  );
  return context.__pagePlan;
};

test("payment query plans only the selected page and bounded API pages", () => {
  const pagePlan = loadPagePlan();

  assert.deepEqual(JSON.parse(JSON.stringify(pagePlan(1, 15))), [
    { page: 1, pageSize: 15 },
  ]);
  assert.deepEqual(JSON.parse(JSON.stringify(pagePlan(2, 15))), [
    { page: 2, pageSize: 15 },
  ]);
  assert.deepEqual(JSON.parse(JSON.stringify(pagePlan(1, 100))), [
    { page: 1, pageSize: 100 },
  ]);
  assert.deepEqual(JSON.parse(JSON.stringify(pagePlan(1, 200))), [
    { page: 1, pageSize: 100 },
    { page: 2, pageSize: 100 },
  ]);
  assert.deepEqual(JSON.parse(JSON.stringify(pagePlan(67, 200))), [
    { page: 133, pageSize: 100 },
    { page: 134, pageSize: 100 },
  ]);
});

test("payment query keeps request count independent of total rows", () => {
  assert.doesNotMatch(
    source,
    /paymentQueryRecordPagePlan|loadPaymentQueryRecords/,
    "payment query must not fetch every page implied by total",
  );
  assert.match(
    source,
    /const loadPaymentQueryPage = async \([\s\S]*?paymentQueryServerPagePlan\(page, pageSize\)[\s\S]*?Promise\.all\(/,
    "payment query should request only the selected page through the bounded plan",
  );
  assert.match(
    source,
    /paymentQueryRequestParams\(query, request\.page, request\.pageSize\)/,
    "server requests should carry bounded page and page size parameters",
  );
  assert.match(
    source,
    /paymentQueryMeta\.total\s*\/\s*pageSize/,
    "GO range validation should use the server-reported total",
  );
});
