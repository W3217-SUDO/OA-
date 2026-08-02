import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const loadRequestParams = () => {
  const start = source.indexOf("const paymentQueryRequestParams");
  const end = source.indexOf("\n\nconst paymentQueryShowsSinglePageGo", start);
  assert.notEqual(start, -1);
  assert.notEqual(end, -1);
  const javascript = ts.transpileModule(source.slice(start, end), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.None },
  }).outputText;
  const context = vm.createContext({});
  vm.runInContext(`${javascript}\nglobalThis.__params = paymentQueryRequestParams;`, context);
  return context.__params;
};

test("legacy query status matrix keeps all seven AP statuses", () => {
  for (const status of [
    "创建待提交",
    "待审批",
    "待付款",
    "待核销",
    "已付款",
    "已驳回",
    "已作废",
  ]) {
    assert.match(source, new RegExp(`\\"${status}\\"`));
  }
  assert.match(source, /const paymentStatuses = paymentQueryLegacyStatusMatrix/);
});

test("omitted status preserves the legacy all-status query", () => {
  const params = loadRequestParams()({ paymentNo: "" }, 1, 15);
  assert.equal(params.record_status, "");
  assert.equal(params.keyword, "");
});

test("payment number is trimmed before it becomes the bounded keyword", () => {
  const params = loadRequestParams()({ paymentNo: "  CODEX-PAY  ", status: " 已付款 " }, 3, 50);
  assert.equal(params.keyword, "CODEX-PAY");
  assert.equal(params.record_status, "已付款");
});

test("legacy request keeps finance module and selected page coordinates", () => {
  const params = loadRequestParams()({}, 7, 100);
  assert.deepEqual(JSON.parse(JSON.stringify(params)), {
    module: "finance",
    page: 7,
    page_size: 100,
    keyword: "",
    record_status: "",
  });
});

test("query failures surface the old controller message", () => {
  assert.match(source, /const paymentQueryLegacyErrorMessage = "查询出错\."/);
  assert.match(source, /message\.error\(paymentQueryLegacyErrorMessage\)/);
});

test("query requests remain bounded and do not regress to fetch-all", () => {
  assert.doesNotMatch(source, /paymentQueryRecordPagePlan|loadPaymentQueryRecords/);
  assert.match(source, /paymentQueryServerPagePlan\(page, pageSize\)/);
  assert.match(source, /params: paymentQueryRequestParams\(query, request\.page, request\.pageSize\)/);
});

test("query-only request helper is not reused by other finance views", () => {
  assert.match(source, /initialView === "finance-payment-query"[\s\S]*?loadPaymentQueryPage\(\{\}, 1, paymentQueryPageSize\)/);
  assert.match(source, /initialView === "finance-payment-query"[\s\S]*?loadPaymentQueryPage\(next, 1, paymentQueryPageSize\)/);
});

