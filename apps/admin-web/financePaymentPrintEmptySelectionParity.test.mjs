import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const loadEmptySelectionMessage = () => {
  const start = source.indexOf("const paymentPackageEmptySelectionMessage");
  const end = source.indexOf("\n\nexport default function FinanceCenterPage", start);
  assert.notEqual(start, -1, "payment print empty-selection policy should exist");
  assert.notEqual(end, -1, "payment print empty-selection policy should be extractable");
  const javascript = ts.transpileModule(source.slice(start, end), {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.None,
    },
  }).outputText;
  const context = vm.createContext({});
  vm.runInContext(
    `${javascript}\nglobalThis.__message = paymentPackageEmptySelectionMessage;`,
    context,
  );
  return context.__message;
};

test("payment print chooses the legacy export prompt without changing the shared internal flow", () => {
  const messageFor = loadEmptySelectionMessage();
  assert.equal(
    messageFor("finance-payment-print"),
    "请选择需要导出的请款单.",
  );
  assert.equal(messageFor("finance-internal-payment"), "请选择提成.");
});
