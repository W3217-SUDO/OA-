import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const evaluateHelper = (name) => {
  const start = source.indexOf(`const ${name}`);
  const end = source.indexOf("\n\n", start);
  assert.notEqual(start, -1, `${name} should exist`);
  assert.notEqual(end, -1, `${name} should be extractable`);
  const javascript = ts.transpileModule(source.slice(start, end), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.None },
  }).outputText;
  const context = vm.createContext({});
  vm.runInContext(`${javascript}\nglobalThis.__value = ${name};`, context);
  return context.__value;
};

test("payment package requests use bounded page coordinates and route status", () => {
  const paramsFor = evaluateHelper("paymentPackageRequestParams");
  assert.deepEqual(
    JSON.parse(JSON.stringify(paramsFor("finance-internal-writeoff", {}, 2, 15))),
    { page: 2, page_size: 15, status: "待核销" },
  );
  assert.deepEqual(
    JSON.parse(JSON.stringify(paramsFor("finance-internal-done", { routeField3: "已付款" }, 1, 20))),
    { page: 1, page_size: 20, status: "已付款" },
  );
});

test("payment package response normalization keeps bounded runtime metadata", () => {
  const normalize = evaluateHelper("normalizePaymentPackageResponse");
  assert.deepEqual(
    JSON.parse(JSON.stringify(normalize({ items: [{ id: 7 }], total: 31, page: 3, page_size: 10 }, 1, 15))),
    { items: [{ id: 7 }], total: 31, page: 3, pageSize: 10 },
  );
  assert.deepEqual(
    JSON.parse(JSON.stringify(normalize(undefined, 2, 20))),
    { items: [], total: 0, page: 2, pageSize: 20 },
  );
});

test("payment package writeoff payload preserves the server contract fields", () => {
  const payload = evaluateHelper("paymentPackageWriteoffPayload");
  assert.deepEqual(
    JSON.parse(JSON.stringify(payload({
      amount: 125.5,
      paid_date: "2026-08-03",
      payment_method: "bank",
      invoice_no: "INV-001",
      remark: "writeoff",
    }))),
    {
      amount: 125.5,
      paid_date: "2026-08-03",
      payment_method: "bank",
      invoice_no: "INV-001",
      remark: "writeoff",
    },
  );
});

test("payment package list exposes server total/current pagination and six legacy sizes", () => {
  const pageSizes = evaluateHelper("paymentPackagePageSizeOptions");
  assert.deepEqual(Array.from(pageSizes), [10, 15, 20, 50, 100, 200]);
  assert.match(source, /paymentPackageMeta/);
  assert.match(source, /current: paymentPackageMeta\.page/);
  assert.match(source, /total: paymentPackageMeta\.total/);
});

test("payment package writeoff keeps the confirmed amount read-only", () => {
  assert.match(source, /name="amount"[\s\S]*?readOnly/);
});

test("payment package writeoff does not fake atomic voucher attachment", () => {
  const start = source.indexOf("const writeoffPaymentPackage");
  const end = source.indexOf("const printPayment", start);
  assert.notEqual(start, -1, "writeoff handler should exist");
  assert.notEqual(end, -1, "writeoff handler boundary should exist");
  const writeoff = source.slice(start, end);
  assert.doesNotMatch(writeoff, /paymentPackageVoucherFile|FormData|\/attachments/);
});

test("payment package writeoff resets its form on cancel and success", () => {
  assert.match(source, /paymentPackageWriteoffForm\.resetFields\(\)/);
});
