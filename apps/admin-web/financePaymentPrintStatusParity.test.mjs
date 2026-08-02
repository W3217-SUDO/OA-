import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const loadPaymentPrintStatusField = () => {
  const start = source.indexOf("const paymentPrintStatusField");
  const end = source.indexOf("\n\nexport default function FinanceCenterPage", start);
  assert.notEqual(start, -1, "payment print status policy should exist");
  assert.notEqual(end, -1, "payment print status policy should be extractable");
  const javascript = ts.transpileModule(source.slice(start, end), {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.None,
    },
  }).outputText;
  const context = vm.createContext({});
  vm.runInContext(
    `${javascript}\nglobalThis.__statusField = paymentPrintStatusField;`,
    context,
  );
  return context.__statusField;
};

test("payment print alone uses the legacy bounded status selector", () => {
  const statusFieldFor = loadPaymentPrintStatusField();
  assert.deepEqual(
    JSON.parse(JSON.stringify(statusFieldFor("finance-payment-print"))),
    {
      options: [
        "请选择",
        "创建待提交",
        "待审批",
        "待付款",
        "待核销",
        "已付款",
        "已驳回",
        "已作废",
      ],
      defaultValue: "请选择",
    },
  );
  assert.equal(statusFieldFor("finance-payment-waiting"), undefined);
  assert.match(
    source,
    /"finance-payment-print":\s*\{[\s\S]*?f\("付款状态",\s*paymentPrintStatusField\(initialView\)\)/,
  );
});
