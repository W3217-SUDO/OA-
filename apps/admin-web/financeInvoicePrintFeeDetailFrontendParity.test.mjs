import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const sliceBetween = (startNeedle, endNeedle, label = startNeedle) => {
  const start = source.indexOf(startNeedle);
  assert.notEqual(start, -1, label + " should exist");
  const end = source.indexOf(endNeedle, start);
  assert.ok(end > start, label + " should be extractable");
  return source.slice(start, end);
};

const evaluatePageHelper = (
  name,
  endNeedle = "\n\nexport default function FinanceCenterPage",
) => {
  const start = source.indexOf("const " + name);
  assert.notEqual(start, -1, name + " should exist");
  const end = source.indexOf(endNeedle, start);
  assert.ok(end > start, name + " should be extractable");
  const javascript = ts.transpileModule(source.slice(start, end), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.None },
  }).outputText;
  const context = vm.createContext({
    money: (value) => "¥ " + Number(value || 0).toFixed(2),
  });
  vm.runInContext(javascript + "\nglobalThis.__helper = " + name + ";", context);
  return context.__helper;
};

test("invoice list detail opens the invoice record and scanned-file context", () => {
  const invoiceColumns = sliceBetween(
    "const invoiceColumns = [",
    "\n  const refundColumns",
    "invoiceColumns",
  );
  const actionStart = invoiceColumns.lastIndexOf('title: "操作"');
  assert.notEqual(actionStart, -1, "invoice action column should exist");
  const actionColumn = invoiceColumns.slice(actionStart);
  assert.match(invoiceColumns, /openRecordFiles\(r, "发票扫描件"\)/);
  assert.match(actionColumn, /setInvoiceDetail\(r\)|openInvoiceDetail\(r\)/);
  assert.doesNotMatch(
    actionColumn,
    /openRefundDetail\(r\)/,
    "invoice detail must not use the refund detail loader or module guard",
  );
});

test("payment print preview keeps legacy package and voucher fields together", () => {
  const createPaymentPrintPreview = evaluatePageHelper("createPaymentPrintPreview");
  const preview = createPaymentPrintPreview(
    {
      id: 77,
      serial_no: "PAY-REQ-77",
      title: "诉讼费",
      customer: "客户A",
      owner: "申请人A",
      data: {
        payment_package_no: "PKG-77",
        fee_type: "诉讼费",
        case_no: "CASE-77",
        contract_no: "CON-77",
        contract_title: "合同77",
        applicant: "申请人A",
        payer_name: "付款方A",
        payee: "收款方A",
      },
    },
    [
      {
        finance_record_id: 77,
        transaction_type: "付款",
        transaction_date: "2026-08-04",
        amount: 1234.56,
        counterparty: "收款方A",
        voucher_no: "VOUCHER-77",
        operator: "出纳A",
        remark: "同号打印",
      },
    ],
    "制单人A",
    "2026-08-04 12:00",
  );
  assert.equal(preview.serialNo, "PAY-REQ-77");
  assert.equal(preview.packageNo, "PKG-77");
  assert.equal(preview.voucherNo, "VOUCHER-77");
  assert.equal(preview.payee, "收款方A");
});

test("writeoff refresh keeps the currently open payment detail record", () => {
  const writeoffFee = sliceBetween(
    "const writeoffFee = async () =>",
    "\n  const writeoffPaymentPackage",
    "writeoffFee",
  );
  assert.match(writeoffFee, /const target = writeoffTarget/);
  assert.match(writeoffFee, /refreshCurrentFinanceFeeList\(/);
  assert.match(writeoffFee, /feeDetail\?\.id === target\.id/);
  assert.match(writeoffFee, /openPaymentDetail\(target\)/);
});

test("refund detail still has a stale-response guard for same-record status", () => {
  const refundColumns = sliceBetween(
    "const refundColumns = [",
    "\n  const transactionColumns",
    "refundColumns",
  );
  assert.match(
    refundColumns,
    /openRefundDetail\(r\)/,
    "refund rows should still expose the guarded refund detail loader",
  );
  const openRefundDetail = sliceBetween(
    "const openRefundDetail = async (row: FinanceFlow)",
    "\n  useEffect",
    "openRefundDetail",
  );
  assert.match(openRefundDetail, /refundDetailRequestGuard\.begin\(\)/);
  assert.match(openRefundDetail, /refundDetailRequestGuard\.isLatest\(token\)/);
  assert.match(openRefundDetail, /String\(data\.id\) !== String\(row\.id\)/);
});

test("invoice scanned-file detail request is guarded by module, category, and 404 permission failures", () => {
  const openRecordFiles = sliceBetween(
    "const openRecordFiles = async (row: FinanceFlow, category: string)",
    "\n  const uploadRecordFile",
    "openRecordFiles",
  );
  assert.match(openRecordFiles, /params:\s*{[\s\S]*record_id:\s*row\.id[\s\S]*category/);
  assert.match(
    openRecordFiles,
    /params:\s*{[\s\S]*(module|record_module):\s*row\.module/,
    "attachment lookup must carry the business module so same numeric ids from other modules cannot leak files",
  );
  assert.match(
    openRecordFiles,
    /catch \(error: any\)[\s\S]*(response\?\.data\?\.detail|setRecordFileTarget\(null\))/,
    "403/404 attachment failures should not leave a stale scanned-file modal open",
  );
});

test("my invoice draft and rejected rows expose the legacy edit entry", () => {
  const invoiceMineOperation = sliceBetween(
    "const invoiceMineOperation = (_: unknown, row: FinanceFlow)",
    "\n  const openInvoiceProcess",
    "invoiceMineOperation",
  );
  assert.match(
    invoiceMineOperation,
    /\["草稿",\s*"已驳回"\]\.includes\(row\.status\)[\s\S]*openInvoiceEdit\(row\)[\s\S]*>\s*编辑\s*</,
    "my invoice rows in draft/rejected status should keep the old edit jump",
  );
});

test("invoice detail received amount links to existing receipt detail with a disabled fallback", () => {
  const openInvoiceReceivedDetail = sliceBetween(
    "const openInvoiceReceivedDetail = (row: FinanceFlow | null)",
    "\n  const invoiceDisplay",
    "openInvoiceReceivedDetail",
  );
  assert.match(
    openInvoiceReceivedDetail,
    /receiptId[\s\S]*message\.warning\("当前发票未关联到账记录"\)/,
    "received amount link should warn instead of navigating without a receipt id",
  );
  assert.match(openInvoiceReceivedDetail, /onNavigate\?\.\("finance-receipts-query"\)/);
  assert.match(
    openInvoiceReceivedDetail,
    /const nextQuery = \{[\s\S]*routeField[0-9]+:\s*receiptId[\s\S]*\};[\s\S]*setOriginalQueryDraft\(nextQuery\)/,
    "received detail should carry the receipt id through nextQuery before routing",
  );

  const invoiceDetailPage = sliceBetween(
    "const invoiceDetailPage = invoiceDisplay ? (",
    "\n  const paymentPrintPreviewPage",
    "invoiceDetailPage",
  );
  assert.match(
    invoiceDetailPage,
    /<Button\s+type="link"\s+onClick=\{\(\) => openInvoiceReceivedDetail\(invoiceDisplay\)\}/,
    "received amount cell should be clickable from invoice details",
  );
});

test("payment print package lookup rejects cross-module package matches and handles 404 without stale fields", () => {
  const openPaymentDetail = sliceBetween(
    "const openPaymentDetail = async (row: Fee)",
    "\n  const openRefundDetail",
    "openPaymentDetail",
  );
  assert.match(openPaymentDetail, /params:\s*{\s*module:\s*"finance_package"/);
  assert.match(
    openPaymentDetail,
    /paymentPackage[\s\S]*\.module\s*===\s*"finance_package"/,
    "same package number from a non-finance_package module must not populate print/detail package fields",
  );
  const printPayment = sliceBetween(
    "const printPayment = async (row: Fee) =>",
    "\n  const loadInvoiceReferenceData",
    "printPayment",
  );
  assert.match(
    printPayment,
    /(payment_package_context|finance_package)[\s\S]*(catch|message\.warning)/,
    "printing should guard package context 403/404 instead of using stale cross-module package fields",
  );
});
