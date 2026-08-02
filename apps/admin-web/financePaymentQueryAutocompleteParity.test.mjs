import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const loadEffectivePaymentQuery = () => {
  const start = source.indexOf("const effectivePaymentQuery");
  const end = source.indexOf("\n\ntype PaymentPrintDocumentData", start);
  assert.notEqual(start, -1, "payment query normalization should exist");
  assert.notEqual(end, -1, "payment query normalization should be extractable");
  const javascript = ts.transpileModule(source.slice(start, end), {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.None,
    },
  }).outputText;
  const context = vm.createContext({});
  vm.runInContext(
    `${javascript}\nglobalThis.__effectivePaymentQuery = effectivePaymentQuery;`,
    context,
  );
  return context.__effectivePaymentQuery;
};

test("payment query ignores unmatched fee-type text without clearing the visible draft", () => {
  const effectiveQuery = loadEffectivePaymentQuery();
  const draft = {
    feeType: "CODEX-FINANCE-F2-AUTOCOMPLETE-READONLY",
    customer: "上海客户",
  };

  assert.deepEqual(
    JSON.parse(
      JSON.stringify(
        effectiveQuery("finance-payment-query", draft, [
          "官方费用",
          "代理费",
        ]),
      ),
    ),
    { customer: "上海客户" },
  );
  assert.equal(
    effectiveQuery(
      "finance-payment-query",
      { feeType: "官方费用" },
      ["官方费用", "代理费"],
    ).feeType,
    "官方费用",
  );
  assert.equal(
    effectiveQuery("finance-payment-print", draft, ["官方费用"]).feeType,
    "CODEX-FINANCE-F2-AUTOCOMPLETE-READONLY",
  );
  assert.equal(draft.feeType, "CODEX-FINANCE-F2-AUTOCOMPLETE-READONLY");
  assert.match(
    source,
    /const next = effectivePaymentQuery\(\s*initialView,\s*\{ \.\.\.configuredDefaults, \.\.\.originalQueryDraft \},\s*feeTypes,?\s*\);/,
  );
});
