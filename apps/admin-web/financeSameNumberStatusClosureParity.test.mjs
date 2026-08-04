import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";
import { refundStatusForRoute } from "./src/financeRefundHelpers.mjs";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const internalFeeHelperSource = await readFile(
  new URL("./src/financeInternalFeeHelpers.mjs", import.meta.url),
  "utf8",
);

const sliceBetween = (startNeedle, endNeedle, label = startNeedle) => {
  const start = source.indexOf(startNeedle);
  assert.notEqual(start, -1, label + " should exist");
  const end = source.indexOf(endNeedle, start);
  assert.ok(end > start, label + " should be extractable");
  return source.slice(start, end);
};

const evaluatePageHelper = (name, endNeedle = "\n\nexport default function FinanceCenterPage") => {
  const start = source.indexOf("const " + name);
  assert.notEqual(start, -1, name + " should exist");
  const end = source.indexOf(endNeedle, start);
  assert.ok(end > start, name + " should be extractable");
  const javascript = ts.transpileModule(source.slice(start, end), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.None },
  }).outputText;
  const context = vm.createContext({
    money: (value) => "¥" + Number(value || 0).toFixed(2),
  });
  vm.runInContext(javascript + "\nglobalThis.__helper = " + name + ";", context);
  return context.__helper;
};

const evaluatePageHelpers = (names, startNeedle, endNeedle) => {
  const start = source.indexOf(startNeedle);
  assert.notEqual(start, -1, startNeedle + " should exist");
  const end = source.indexOf(endNeedle, start);
  assert.ok(end > start, startNeedle + " block should be extractable");
  const javascript = ts.transpileModule(source.slice(start, end), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.None },
  }).outputText;
  const context = vm.createContext({});
  vm.runInContext(
    javascript + "\nglobalThis.__helpers = {" + names.map((name) => name + ":" + name).join(",") + "};",
    context,
  );
  return context.__helpers;
};

test("payment query must not drop same-number contract payment requests", () => {
  const queryParams = evaluatePageHelper("paymentQueryRequestParams", "\n});");
  const contractQueryParams = evaluatePageHelper("contractPaymentQueryRequestParams", "\n});");
  const params = queryParams({ paymentNo: " FK-20260804-001 ", status: "待付款" }, 2, 50);
  const contractParams = contractQueryParams({ paymentNo: " FK-20260804-001 ", status: "待付款" }, 2, 50);
  assert.equal(params.keyword, "FK-20260804-001");
  assert.equal(params.record_status, "待付款");
  assert.equal(params.module, "finance");
  assert.equal(contractParams.module, "contract_payment");
  assert.equal(contractParams.keyword, "FK-20260804-001");
  assert.equal(contractParams.record_status, "待付款");
  assert.match(source, /contractPaymentQueryRequestParams\(/);
});

test("payment detail must load package context for the same package number shown in lists and prints", () => {
  const openPaymentDetail = sliceBetween(
    "const openPaymentDetail = async (row: Fee)",
    "\n  const openRefundDetail",
    "openPaymentDetail",
  );
  assert.match(openPaymentDetail, /api\.get[\s\S]*\/records\//);
  assert.match(
    openPaymentDetail,
    /payment_package_no|package_no|finance_package|payment-packages/,
    "detail view should keep PackageNo/payment package context alongside the request record",
  );
});

test("single payment print keeps request number and package number from the same row", () => {
  const createPreview = evaluatePageHelper("createPaymentPrintPreview");
  const preview = createPreview(
    {
      id: 41,
      serial_no: "REQ-20260804-001",
      title: "官方费用",
      customer: "测试客户",
      owner: "Admin",
      data: {
        payment_package_no: "PKG-20260804-001",
        case_no: "CASE-001",
        contract_no: "CON-001",
        fee_type: "官方费用",
        applicant: "申请人",
        payee: "收款方",
      },
    },
    [
      {
        finance_record_id: 41,
        transaction_type: "付款",
        transaction_date: "2026-08-04",
        amount: 300,
        counterparty: "收款方",
        voucher_no: "PAY-001",
        operator: "出纳",
      },
    ],
    "制单人",
    "2026-08-04 10:00",
  );
  assert.equal(preview.serialNo, "REQ-20260804-001");
  assert.equal(preview.packageNo, "PKG-20260804-001");
  assert.equal(preview.documentTitle, "REQ-20260804-001付款单");
});

test("ordinary writeoff must refresh the same request id/status instead of broad reloading only", () => {
  const writeoffFee = sliceBetween(
    "const writeoffFee = async () =>",
    "\n  const writeoffPaymentPackage",
    "writeoffFee",
  );
  assert.match(writeoffFee, /\/finance\/fees\/[\s\S]*\/writeoff/);
  assert.match(
    writeoffFee,
    /refreshCurrentFinanceFeeList\(|loadPaymentQueryPage\(|openPaymentDetail\(writeoffTarget\)|setFeeDetail\(/,
    "ordinary writeoff should prove the same request id is reloaded with its updated status",
  );
});

test("internal fee package writeoff preserves PackageNo, invoice_no and PaidDate in the frontend contract", () => {
  const packageOperation = sliceBetween(
    "const paymentPackageOperation = (_: unknown, row: Fee)",
    "\n  const originalColumns",
    "paymentPackageOperation",
  );
  const writeoffModal = sliceBetween(
    "className=\"finance-payment-package-writeoff-modal\"",
    "\n      <Modal\n        width={760}",
    "payment package writeoff modal",
  );
  assert.match(packageOperation, /package_no:\s*row\.serial_no/);
  assert.match(packageOperation, /invoice_no:\s*""/);
  assert.match(writeoffModal, /name="paid_date"/);
  assert.match(writeoffModal, /name="invoice_no"/);
  assert.match(internalFeeHelperSource, /payment_status/);
});

test("not-required refund route keeps R100 for query and clear flows", () => {
  assert.equal(refundStatusForRoute("finance-refund-not-required", ""), "R100");
  assert.equal(refundStatusForRoute("finance-refund-not-required", "已退款"), "R100");
  assert.match(source, /refundStatusForRoute\(initialView, ""\)/);
});

test("refund detail must ignore stale responses so the same refund number/status stay stable", () => {
  const openRefundDetail = sliceBetween(
    "const openRefundDetail = async (row: FinanceFlow)",
    "\n  useEffect",
    "openRefundDetail",
  );
  assert.match(openRefundDetail, /api\.get[\s\S]*\/records\//);
  assert.match(
    openRefundDetail,
    /refundDetailRequestGuard|isLatestRefundDetail|row\.id\s*===\s*data\.id|data\.id\s*===\s*row\.id/,
    "refund detail should guard against stale responses before setting detail state",
  );
});

test("invoice number links remain tied to invoice detail and scanned files", () => {
  assert.match(source, /发票号码:\s*data\.invoice_no/);
  assert.match(source, /row\.data\?\.invoice_no/);
  assert.match(source, /invoice_record_id/);
  assert.match(source, /openRecordFiles\(invoice, "发票扫描件"\)/);
});

test("settlement context tasks consume every paged case-task result", () => {
  const { settlementContextTasksRequest: requestFor } = evaluatePageHelpers(
    ["settlementContextPageSize", "settlementContextTasksRequest"],
    "const settlementContextPageSize",
    "\n\nconst normalizeSettlementContextRows",
  );
  assert.deepEqual(JSON.parse(JSON.stringify(requestFor(41, 3))), {
    url: "/cases/41/tasks",
    params: { page: 3, page_size: 100 },
  });
  assert.match(source, /const loadSettlementContextTasks = async \(caseId: number\)/);
  assert.match(source, /Math\.ceil\(total \/ settlementContextPageSize\)/);
  assert.match(source, /Array\.from\(\{ length: totalPages - 1 \}/);
  assert.doesNotMatch(
    sliceBetween("const openSettlementContext", "\n  const generateSettlementDocument"),
    /api\.get\(\s*`\/cases\/\$\{linked\.id\}\/tasks`/,
  );
});
