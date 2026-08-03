import test from "node:test";
import assert from "node:assert/strict";
import {
  normalizeIncomingPayment,
  normalizeInvoiceObject,
  normalizePaidObject,
  contractObjectActionPolicy,
} from "./src/contractObjectPresentation.mjs";

test("incoming payment presentation maps the legacy sequence and date fields", () => {
  const row = normalizeIncomingPayment({ payment_basic: { SequenceNo: "SK-1", CashedDate: "2026-07-01" } });
  assert.deepEqual({ sequenceNo: row.sequenceNo, receivedDate: row.receivedDate }, { sequenceNo: "SK-1", receivedDate: "2026-07-01" });
});

test("incoming payment presentation maps bank reference and amount", () => {
  const row = normalizeIncomingPayment({ payment_basic: { InvoiceNo: "BANK-1", CashedAmount: 1200 } });
  assert.equal(row.bankReference, "BANK-1");
  assert.equal(row.amount, 1200);
});

test("incoming payment presentation preserves the three legacy fee allocations", () => {
  const row = normalizeIncomingPayment({ payment_basic: { CaseOfficeFeeAppliedAmount: 10, CaseNonOfficeFeeAppliedAmount: 20, CaseCommissionFeeAppliedAmount: 30 } });
  assert.deepEqual([row.officialAmount, row.agencyAmount, row.otherAmount], [10, 20, 30]);
});

test("incoming payment presentation keeps payment mode and claimant", () => {
  const row = normalizeIncomingPayment({ payment_basic: { PaymentModeName: "银行转账", AppliedOperatorName: "alice" } });
  assert.deepEqual([row.paymentMethod, row.claimant], ["银行转账", "alice"]);
});

test("incoming payment presentation reads the local top-level DTO and aggregates proven settlement items", () => {
  const row = normalizeIncomingPayment({
    receipt_no: "RC-LOCAL",
    received_date: "2026-07-04",
    amount: 0,
    bank_reference: "BANK-LOCAL",
    claimant: "alice",
    allocations: [{
      amount: 15,
      settlement_items: [
        { fee_type: "官方费用", settlement_amount: 5 },
        { fee_type: "代理费", settlement_amount: 7 },
        { fee_type: "其他费用", settlement_amount: 3 },
      ],
    }],
  });
  assert.deepEqual([row.sequenceNo, row.receivedDate, row.bankReference, row.amount, row.claimant], ["RC-LOCAL", "2026-07-04", "BANK-LOCAL", 0, "alice"]);
  assert.deepEqual([row.officialAmount, row.agencyAmount, row.otherAmount], [5, 7, 3]);
});

test("incoming payment presentation prioritizes the current top-level DTO and preserves explicit zeroes", () => {
  const row = normalizeIncomingPayment({
    payment_basic: {
      SequenceNo: "OLD-RC",
      CashedDate: "2020-01-01",
      InvoiceNo: "OLD-BANK",
      CashedAmount: 999,
      CaseOfficeFeeAppliedAmount: 999,
    },
    receipt_no: "RC-CURRENT",
    received_date: "2026-08-03",
    bank_reference: "BANK-CURRENT",
    amount: 0,
    official_amount: 0,
  });
  assert.deepEqual(
    [row.sequenceNo, row.receivedDate, row.bankReference, row.amount, row.officialAmount],
    ["RC-CURRENT", "2026-08-03", "BANK-CURRENT", 0, 0],
  );
});

test("invoice presentation maps request number, invoice number and date", () => {
  const row = normalizeInvoiceObject({ invoice_basic: { InvoiceApplicationNo: "FP-REQ", InvoiceNo: "INV-1", InvoiceDate: "2026-07-02" } });
  assert.deepEqual([row.applicationNo, row.invoiceNo, row.invoiceDate], ["FP-REQ", "INV-1", "2026-07-02"]);
});

test("invoice presentation exposes fee totals and status remark", () => {
  const row = normalizeInvoiceObject({ invoice_basic: { InvoiceAmount: 100, CaseOfficeFeeAmount: 10, CaseNonOfficeFeeAmount: 20, CaseCommissionFeeAmount: 30, InvoiceStatusName: "已开票", Remark: "ok" } });
  assert.deepEqual([row.amount, row.officialAmount, row.agencyAmount, row.otherAmount, row.status, row.remark], [100, 10, 20, 30, "已开票", "ok"]);
});

test("invoice presentation strikes canceled applications", () => {
  assert.equal(normalizeInvoiceObject({ status: "申请已取消" }).lineThrough, true);
  assert.equal(normalizeInvoiceObject({ status: "已开票" }).lineThrough, false);
});

test("invoice presentation reads non-empty and zero-valued fields from the local BusinessRecord data", () => {
  const row = normalizeInvoiceObject({ serial_no: "INV-LOCAL-REQ", status: "已开票", data: { invoice_no: "LOCAL-INV", invoice_date: "2026-07-05", amount: 0, official_amount: 0, agency_amount: 12, other_amount: 0, applicant: "alice" } });
  assert.deepEqual([row.applicationNo, row.invoiceNo, row.invoiceDate, row.amount, row.officialAmount, row.agencyAmount, row.otherAmount], ["INV-LOCAL-REQ", "LOCAL-INV", "2026-07-05", 0, 0, 12, 0]);
});

test("invoice presentation prioritizes current BusinessRecord data over a stale legacy projection", () => {
  const row = normalizeInvoiceObject({
    serial_no: "INV-CURRENT-REQ",
    status: "已开票",
    description: "current remark",
    invoice_basic: {
      InvoiceApplicationNo: "INV-OLD-REQ",
      InvoiceNo: "INV-OLD",
      InvoiceDate: "2020-01-01",
      InvoiceAmount: 900,
      CaseOfficeFeeAmount: 900,
      InvoiceStatusName: "待开票",
      Remark: "old remark",
    },
    data: {
      invoice_no: "INV-CURRENT",
      invoice_date: "2026-08-03",
      amount: 0,
      official_amount: 0,
      agency_amount: 12,
      other_amount: 0,
    },
  });
  assert.deepEqual(
    [row.applicationNo, row.invoiceNo, row.invoiceDate, row.amount, row.officialAmount, row.agencyAmount, row.otherAmount, row.status, row.remark],
    ["INV-CURRENT-REQ", "INV-CURRENT", "2026-08-03", 0, 0, 12, 0, "已开票", "current remark"],
  );
});

test("paid presentation maps application number and applicant", () => {
  const row = normalizePaidObject({ payment_basic: { ApplicationNo: "PAY-1", ApplicantName: "bob" } });
  assert.deepEqual([row.applicationNo, row.applicant], ["PAY-1", "bob"]);
});

test("paid presentation computes pending and paid amounts from status", () => {
  const pending = normalizePaidObject({ payment_basic: { PaymentStatus: "审批中", PaidAmount: 80 } });
  const paid = normalizePaidObject({ payment_basic: { PaymentStatus: "已付款", PaidAmount: 80 } });
  assert.deepEqual([pending.pendingAmount, pending.paidAmount, paid.pendingAmount, paid.paidAmount], [80, 0, 0, 80]);
});

test("paid presentation exposes payment fields and cancellation styling", () => {
  const row = normalizePaidObject({ payment_basic: { PaymentStatus: "申请已取消", PaymentDate: "2026-07-03", PackageNo: "PK-1" }, payment_type: "官费", data: { official_amount: 80, other_amount: 0 } });
  assert.deepEqual([row.paymentDate, row.packageNo, row.paymentType, row.lineThrough], ["2026-07-03", "PK-1", "官费", true]);
  assert.equal(contractObjectActionPolicy("审批中").canEdit, false);
  assert.equal(contractObjectActionPolicy("草稿").canDelete, true);
});

test("paid presentation reads local contract-payment data without replacing zero values", () => {
  const row = normalizePaidObject({ serial_no: "CP-LOCAL", status: "待审批", data: { applicant: "alice", amount: 0, application_date: "2026-07-06", payment_type: "官费", official_amount: 0, other_amount: 0 } });
  assert.deepEqual([row.applicationNo, row.applicant, row.paymentDate, row.paidAmount, row.pendingAmount, row.officialAmount, row.otherAmount], ["CP-LOCAL", "alice", "", 0, 0, 0, 0]);
});

test("paid presentation reads the legacy PaymentType object", () => {
  const row = normalizePaidObject({
    payment_basic: { ApplicationNo: "PAY-OLD", PaymentStatus: "Paid", PaidAmount: 80 },
    payment_type: { PaymentTypeName: "官费" },
  });
  assert.deepEqual([row.paymentType, row.officialAmount, row.otherAmount], ["官费", 80, 0]);
});

test("paid presentation prioritizes current BusinessRecord data and preserves explicit zeroes", () => {
  const row = normalizePaidObject({
    serial_no: "CP-CURRENT",
    status: "待审批",
    owner: "current-owner",
    payment_basic: {
      ApplicationNo: "CP-OLD",
      ApplicantName: "old-owner",
      PaymentStatus: "Paid",
      PaymentDate: "2020-01-01",
      PackageNo: "OLD-VOUCHER",
      PaidAmount: 500,
    },
    payment_type: { PaymentTypeName: "代理费" },
    data: {
      applicant: "current-applicant",
      amount: 0,
      paid_date: "2026-08-03",
      voucher_no: "CURRENT-VOUCHER",
      payment_type: "官费",
      official_amount: 0,
      other_amount: 0,
    },
  });
  assert.deepEqual(
    [row.applicationNo, row.applicant, row.pendingAmount, row.paidAmount, row.paymentDate, row.packageNo, row.paymentType, row.officialAmount, row.otherAmount],
    ["CP-CURRENT", "current-applicant", 0, 0, "2026-08-03", "CURRENT-VOUCHER", "官费", 0, 0],
  );
});
