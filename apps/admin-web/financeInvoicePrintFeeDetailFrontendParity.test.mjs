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
