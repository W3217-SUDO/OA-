import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const loadControlledPageSize = () => {
  const start = source.indexOf("const paymentQueryControlledPageSize");
  const end = source.indexOf("\n\nconst paymentQueryFeeTypeControl", start);
  assert.notEqual(
    start,
    -1,
    "payment query should keep the selected legacy page size",
  );
  assert.notEqual(end, -1, "payment query page-size policy should be extractable");
  const javascript = ts.transpileModule(source.slice(start, end), {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.None,
    },
  }).outputText;
  const context = vm.createContext({});
  vm.runInContext(
    `${javascript}\nglobalThis.__controlledPageSize = paymentQueryControlledPageSize;`,
    context,
  );
  return context.__controlledPageSize;
};

test("payment query keeps each selected legacy page size without affecting other routes", () => {
  const controlledPageSize = loadControlledPageSize();

  for (const pageSize of [10, 15, 20, 50, 100, 200]) {
    assert.equal(controlledPageSize("finance-payment-query", pageSize), pageSize);
  }
  assert.equal(controlledPageSize("finance-payment-mine", 20), undefined);
  assert.equal(controlledPageSize("finance-payment-print", 20), undefined);
});

test("payment query pagination stores a changed page size and reuses it for GO", () => {
  assert.match(
    source,
    /const \[paymentQueryPageSize, setPaymentQueryPageSize\] = useState\([\s\S]*?paymentQueryDefaultPageSize\(initialView\)/,
    "payment query needs route-scoped page-size state",
  );
  assert.match(
    source,
    /pageSize:[\s\S]*?paymentQueryControlledPageSize\(\s*initialView,\s*paymentQueryPageSize,?\s*\)/,
    "table pagination should render the selected page size",
  );
  assert.match(
    source,
    /initialView === "finance-payment-query"[\s\S]*?onShowSizeChange:[\s\S]*?setPaymentQueryPageSize\(pageSize\)/,
    "page-size changes should update only the payment query route",
  );
  assert.match(
    source,
    /const submitPaymentQueryQuickPage = \(\) => \{[\s\S]*?paymentQueryControlledPageSize\(\s*initialView,\s*paymentQueryPageSize,?\s*\)/,
    "GO range validation should use the currently selected page size",
  );
});
