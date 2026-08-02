import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const loadQuickPageResult = () => {
  const start = source.indexOf("const paymentQueryQuickPageResult");
  const end = source.indexOf("\n\nconst paymentQueryPageSizeOptions", start);
  assert.notEqual(start, -1, "payment query GO validation policy should exist");
  assert.notEqual(end, -1, "payment query GO validation policy should be extractable");
  const javascript = ts.transpileModule(source.slice(start, end), {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.None,
    },
  }).outputText;
  const context = vm.createContext({});
  vm.runInContext(
    `${javascript}\nglobalThis.__quickPageResult = paymentQueryQuickPageResult;`,
    context,
  );
  return context.__quickPageResult;
};

test("payment query GO keeps legacy validation and range semantics", () => {
  const quickPageResult = loadQuickPageResult();
  const result = (value, totalPages) =>
    JSON.parse(JSON.stringify(quickPageResult(value, totalPages)));

  assert.deepEqual(result("1", 1), { ok: true, page: 1, message: "" });
  assert.deepEqual(result("01", 1), { ok: true, page: 1, message: "" });
  assert.deepEqual(result("", 1), {
    ok: false,
    page: null,
    message: "请输入页码数",
  });
  for (const invalid of ["abc", "0", "-1", "1.5", " "]) {
    assert.deepEqual(result(invalid, 1), {
      ok: false,
      page: null,
      message: "请输入正确的页码!",
    });
  }
  assert.deepEqual(result("2", 1), {
    ok: false,
    page: null,
    message: "请输入有效范围的页码!",
  });
});

test("single-page GO preserves raw input, validates only on click, and keeps Enter passive", () => {
  const start = source.indexOf('className="finance-payment-query-single-page-go"');
  const end = source.indexOf("</div>", start);
  assert.notEqual(start, -1, "single-page payment query GO should exist");
  assert.notEqual(end, -1, "single-page payment query GO should be extractable");
  const block = source.slice(start, end);

  assert.match(
    block,
    /setPaymentQueryQuickPage\(event\.target\.value\)/,
    "legacy pager keeps invalid text visible until GO validation",
  );
  assert.doesNotMatch(
    block,
    /onPressEnter=/,
    "legacy pager does not bind Enter to GO",
  );
  assert.match(
    block,
    /onClick=\{submitPaymentQueryQuickPage\}/,
    "GO should invoke the scoped validation handler",
  );
  assert.match(
    source,
    /const submitPaymentQueryQuickPage = \(\) => \{[\s\S]*?paymentQueryQuickPageResult\([\s\S]*?message\.warning\(result\.message\)[\s\S]*?setPaymentQueryQuickPage\(String\(result\.page\)\)/,
    "failed GO should warn without changing the input; valid GO canonicalizes the page",
  );
});
