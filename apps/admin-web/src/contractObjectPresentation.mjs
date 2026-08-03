const isPresent = (value) => value !== undefined && value !== null && value !== "";

const first = (sources, keys, fallback = "") => {
  for (const source of sources) {
    for (const key of keys) {
      const current = source?.[key];
      if (isPresent(current)) return current;
    }
  }
  return fallback;
};

const numeric = (source, keys) => {
  const current = first([source], keys, null);
  if (current === null) return null;
  const parsed = Number(current);
  return Number.isFinite(parsed) ? parsed : null;
};

const firstNumber = (sources) => {
  for (const current of sources) if (current !== null && current !== undefined) return current;
  return 0;
};

const nested = (row, key) => row?.[key] || row?.[key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())] || {};

const allocationFeeTotals = (allocations) => {
  const totals = { official: 0, agency: 0, other: 0 };
  for (const allocation of Array.isArray(allocations) ? allocations : []) {
    for (const item of Array.isArray(allocation?.settlement_items) ? allocation.settlement_items : []) {
      const feeType = String(item?.fee_type || "").trim();
      const amount = numeric(item, ["settlement_amount"]);
      if (amount === null) continue;
      if (feeType.includes("代理")) totals.agency += amount;
      else if (["官费", "官方", "诉讼", "公证", "保全", "鉴定", "公告"].some((token) => feeType.includes(token))) totals.official += amount;
      else totals.other += amount;
    }
  }
  return totals;
};

export const normalizeIncomingPayment = (row = {}) => {
  const payment = nested(row, "payment_basic");
  const allocations = allocationFeeTotals(row.allocations);
  return {
    sequenceNo: first([row, payment], ["receipt_no", "sequence_no", "SequenceNo"], ""),
    receivedDate: first([row, payment], ["received_date", "cashed_date", "CashedDate"], ""),
    bankReference: first([row, payment], ["bank_reference", "invoice_no", "InvoiceNo"], ""),
    amount: firstNumber([numeric(row, ["amount"]), numeric(payment, ["cashed_amount", "CashedAmount"])]),
    officialAmount: firstNumber([numeric(row, ["official_amount"]), numeric(payment, ["case_office_fee_applied_amount", "CaseOfficeFeeAppliedAmount"]), allocations.official]),
    agencyAmount: firstNumber([numeric(row, ["agency_amount"]), numeric(payment, ["case_non_office_fee_applied_amount", "CaseNonOfficeFeeAppliedAmount"]), allocations.agency]),
    otherAmount: firstNumber([numeric(row, ["other_amount"]), numeric(payment, ["case_commission_fee_applied_amount", "CaseCommissionFeeAppliedAmount"]), allocations.other]),
    paymentMethod: first([row, payment], ["payment_method", "payment_mode_name", "PaymentModeName"], ""),
    claimant: first([row, payment], ["claimant", "applied_operator_name", "AppliedOperatorName"], ""),
  };
};

export const normalizeInvoiceObject = (row = {}) => {
  const invoice = nested(row, "invoice_basic");
  const data = row?.data || {};
  const status = String(first([row, data, invoice], ["status", "invoice_status_name", "InvoiceStatusName"], "") || "");
  return {
    applicationNo: first([row, data, invoice], ["serial_no", "application_no", "invoice_application_no", "InvoiceApplicationNo"], ""),
    invoiceNo: first([data, row, invoice], ["invoice_no", "InvoiceNo"], ""),
    invoiceDate: first([data, row, invoice], ["invoice_date", "InvoiceDate"], ""),
    amount: firstNumber([numeric(data, ["amount"]), numeric(row, ["amount"]), numeric(invoice, ["invoice_amount", "InvoiceAmount"])]),
    officialAmount: firstNumber([numeric(data, ["official_amount"]), numeric(row, ["official_amount"]), numeric(invoice, ["case_office_fee_amount", "CaseOfficeFeeAmount"])]),
    agencyAmount: firstNumber([numeric(data, ["agency_amount"]), numeric(row, ["agency_amount"]), numeric(invoice, ["case_non_office_fee_amount", "CaseNonOfficeFeeAmount"])]),
    otherAmount: firstNumber([numeric(data, ["other_amount"]), numeric(row, ["other_amount"]), numeric(invoice, ["case_commission_fee_amount", "CaseCommissionFeeAmount"])]),
    status,
    remark: first([data, row, invoice], ["remark", "description", "Remark"], ""),
    lineThrough: ["已取消", "申请已取消", "已撤回", "已作废"].includes(status),
  };
};

const paidStatus = (row) => String(first([row, nested(row, "payment_basic"), row?.data], ["status", "payment_status", "PaymentStatus"], "") || "");
const isSettled = (status) => ["装订中", "已付款", "Packing", "Paid"].includes(status);

export const normalizePaidObject = (row = {}) => {
  const payment = nested(row, "payment_basic");
  const paymentTypeObject = nested(row, "payment_type");
  const data = row?.data || {};
  const flatPaymentType = typeof row?.payment_type === "string" ? row.payment_type : "";
  const status = paidStatus(row);
  const rawPaidAmount = firstNumber([numeric(data, ["amount"]), numeric(row, ["amount"]), numeric(payment, ["paid_amount", "PaidAmount"])]);
  const paymentType = first([data, { payment_type: flatPaymentType }, payment, paymentTypeObject], ["payment_type", "PaymentTypeName"], "");
  const official = firstNumber([numeric(data, ["official_amount"]), numeric(row, ["official_amount"]), numeric(payment, ["official_amount"]), paymentType === "官费" ? rawPaidAmount : null]);
  const other = firstNumber([numeric(data, ["other_amount"]), numeric(row, ["other_amount"]), numeric(payment, ["other_amount"]), paymentType === "其他费用" || paymentType === "代理费" ? rawPaidAmount : null]);
  return {
    applicationNo: first([row, data, payment], ["serial_no", "application_no", "ApplicationNo"], ""),
    applicant: first([data, row, payment], ["applicant", "owner", "applicant_name", "ApplicantName"], ""),
    pendingAmount: isSettled(status) ? 0 : rawPaidAmount,
    paymentDate: first([data, row, payment], ["paid_date", "payment_date", "PaymentDate"], ""),
    packageNo: first([data, row, payment], ["voucher_no", "payment_reference", "package_no", "PackageNo"], ""),
    paidAmount: isSettled(status) ? rawPaidAmount : 0,
    paymentType,
    officialAmount: official,
    otherAmount: other,
    lineThrough: ["申请已取消", "已取消", "已撤回", "已作废", "ApplicationCanceled"].includes(status),
  };
};

export const contractObjectActionPolicy = (status) => {
  const mutable = !["审批中", "已归档"].includes(String(status || ""));
  return { canEdit: mutable, canDelete: mutable, canLog: true };
};
