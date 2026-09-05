import type { ContractPaymentSourceState,ContractPaymentSourceSuccess,Fee,FinanceFlow,InvoiceCustomerDefaults,InvoiceSourceFields,PaymentPrintDocumentData,Transaction } from "./types";

export const feeTypes = [
  "官方费用",
  "代理费",
  "其他费用",
  "内部费用",
  "结算费用",
  "预损费用",
  "归档费用",
];

export const internalApprovalRoutes = [
  "finance-payment-audit",
  "finance-internal-archive",
  "finance-internal-audit",
  "finance-internal-fee-audit",
  "finance-internal-refund-audit",
];

export const statusColors: Record<string, string> = {
  草稿: "default",
  待审批: "orange",
  已审批: "blue",
  部分付款: "cyan",
  已付款: "green",
  已退回: "red",
  已驳回: "red",
  待开票: "cyan",
  已开票: "green",
  已作废: "default",
  退款办理中: "blue",
  已退款: "green",
};

export const money = (v: number) =>
  `¥ ${Number(v || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2 })}`;

export const voucherCategory: Record<string, string> = {
  付款: "付款凭证",
  开票: "发票扫描件",
  回款: "回款凭证",
  退费: "退费凭证",
};

export const attachmentRecordModule = (row: FinanceFlow, category: string) =>
  row.module ||
  (category === "发票扫描件"
    ? "invoice"
    : category === "退费凭证"
      ? "refund"
      : "finance");

export const initialSessionUser = () => {
  try {
    return JSON.parse(localStorage.getItem("user") || "{}");
  } catch {
    return {};
  }
};

export const CONTRACT_PAYMENT_SOURCE_KEYS = [
  ["payment_no", "请款单号"],
  ["contract_no", "合同号"],
  ["customer", "客户名称"],
  ["amount", "金额"],
  ["source_id", "来源ID"],
  ["source_module", "来源模块"],
  ["return_page", "返回路径"],
] as const;

export const parseContractPaymentSource = (
  initialView: string,
  search: string,
): ContractPaymentSourceState => {
  if (initialView !== "finance-payment-mine") return { active: false };
  const params = new URLSearchParams(search);
  if (!CONTRACT_PAYMENT_SOURCE_KEYS.some(([key]) => params.has(key))) {
    return { active: false };
  }
  const duplicates = CONTRACT_PAYMENT_SOURCE_KEYS.filter(
    ([key]) => params.getAll(key).length > 1,
  ).map(([, label]) => label);
  if (duplicates.length) {
    return {
      active: true,
      ok: false,
      error: `合同付款来源参数重复：${duplicates.join("、")}`,
    };
  }
  const values = Object.fromEntries(
    CONTRACT_PAYMENT_SOURCE_KEYS.map(([key]) => [
      key,
      String(params.get(key) || "").trim(),
    ]),
  );
  const missing = CONTRACT_PAYMENT_SOURCE_KEYS.filter(
    ([key]) => !values[key],
  ).map(([, label]) => label);
  if (missing.length) {
    return {
      active: true,
      ok: false,
      error: `合同付款来源缺少参数：${missing.join("、")}`,
    };
  }
  if (values.source_module !== "contract_payment") {
    return { active: true, ok: false, error: "合同付款来源模块无效" };
  }
  const sourceId = Number(values.source_id);
  if (!Number.isInteger(sourceId) || sourceId <= 0) {
    return { active: true, ok: false, error: "合同付款来源ID无效" };
  }
  const amount = Number(values.amount);
  if (!Number.isFinite(amount) || amount <= 0) {
    return { active: true, ok: false, error: "合同付款来源金额无效" };
  }
  const returnMatch = values.return_page.match(/^contract-detail-(\d+)-(.+)$/);
  let returnContractNo = "";
  try {
    returnContractNo = returnMatch ? decodeURIComponent(returnMatch[2]) : "";
  } catch {
    returnContractNo = "";
  }
  if (
    !returnMatch ||
    Number(returnMatch[1]) <= 0 ||
    returnContractNo !== values.contract_no
  ) {
    return { active: true, ok: false, error: "合同付款返回路径无效" };
  }
  return {
    active: true,
    ok: true,
    paymentNo: values.payment_no,
    contractNo: values.contract_no,
    customer: values.customer,
    amount,
    sourceId,
    sourceModule: "contract_payment",
    returnPage: values.return_page,
  };
};

export const matchesContractPaymentSource = (
  item: Fee,
  source: ContractPaymentSourceSuccess,
) =>
  item.data?._source_module === source.sourceModule &&
  Number(item.id) === source.sourceId &&
  String(item.serial_no || "").trim() === source.paymentNo &&
  String(item.data?.contract_no || "").trim() === source.contractNo &&
  String(item.customer || "").trim() === source.customer &&
  Number(item.data?.amount) === source.amount;

export const paymentPackageEmptySelectionMessage = (initialView: string) =>
  initialView === "finance-payment-print"
    ? "请选择需要导出的请款单."
    : "请选择提成.";

export const paymentPrintStatusField = (initialView: string) =>
  initialView === "finance-payment-print"
    ? {
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
      }
    : undefined;

export const paymentWriteoffClearQuery = (initialView: string) =>
  initialView === "finance-payment-writeoff" ? { status: "待核销" } : {};

export const paymentPackagePageSizeOptions = [10, 15, 20, 50, 100, 200];

export const paymentPackageRequestParams = (
  initialView: string,
  query: Record<string, any>,
  page: number,
  pageSize: number,
) => {
  if (initialView === "finance-payment-package-manage") {
    const paymentRange = query.routeField3 || [];
    return {
      page,
      page_size: pageSize,
      ...(String(query.routeField0 || "").trim() ? { package_no: String(query.routeField0).trim() } : {}),
      ...(String(query.routeField1 || "").trim() ? { status: String(query.routeField1).trim() } : {}),
      ...(String(query.routeField2 || "").trim() ? { payee: String(query.routeField2).trim() } : {}),
      ...(paymentRange?.[0] ? { payment_date_from: paymentRange[0].format("YYYY-MM-DD") } : {}),
      ...(paymentRange?.[1] ? { payment_date_to: paymentRange[1].format("YYYY-MM-DD") } : {}),
    };
  }
  const pageId = initialView === "finance-internal-writeoff" ? "5001003006" : "";
  const status = String(
    initialView === "finance-internal-writeoff"
      ? "待核销"
      : query.status || query.routeField3 || "",
  ).trim();
  return {
    page,
    page_size: pageSize,
    ...(pageId ? { page_id: pageId } : {}),
    ...(status ? { status } : {}),
  };
};

export const normalizePaymentPackageResponse = (
  data: Record<string, any> | undefined,
  fallbackPage = 1,
  fallbackPageSize = 15,
) => ({
  items: Array.isArray(data?.items) ? data.items : [],
  total: Number(data?.total || 0),
  page: Number(data?.page || fallbackPage),
  pageSize: Number(data?.page_size || fallbackPageSize),
});

export const paymentPackageWordExportPath = (packageNo: string) =>
  "/finance/payment-packages/{package_no}/print-word".replace(
    "{package_no}",
    encodeURIComponent(packageNo),
  );

export const paymentPackageWriteoffPayload = (
  values: Record<string, any>,
  formatDate: (value: any) => any = (value) => value,
) => ({
  amount: values.amount,
  paid_date: formatDate(values.paid_date),
  payment_method: values.payment_method,
  invoice_no: values.invoice_no,
  remark: values.remark || "",
});

export const paymentQueryQuickJumper = (initialView: string) =>
  [
    "finance-payment-query",
    "finance-payment-mine",
    "finance-internal-mine",
  ].includes(initialView)
    ? { goButton: "GO" }
    : undefined;

// Legacy AP/PaymentList accepts the complete payment status vocabulary and
// treats an omitted status as "all statuses". Keep this matrix explicit so
// query requests do not silently collapse to the local workflow subset.
export const paymentQueryLegacyStatusMatrix = [
  "创建待提交",
  "待审批",
  "待付款",
  "待核销",
  "已付款",
  "已驳回",
  "已作废",
];

export const paymentQueryLegacyErrorMessage = "查询出错.";

export const paymentQueryRequestParams = (
  query: Record<string, any>,
  page: number,
  pageSize: number,
) => ({
  module: "finance",
  page,
  page_size: pageSize,
  keyword: String(query.paymentNo || "").trim(),
  record_status: String(query.status || "").trim(),
});

export const contractPaymentQueryRequestParams = (
  query: Record<string, any>,
  page: number,
  pageSize: number,
) => ({
  module: "contract_payment",
  page,
  page_size: pageSize,
  keyword: String(query.paymentNo || "").trim(),
  record_status: String(query.status || "").trim(),
});

export const paymentQueryShowsSinglePageGo = (
  initialView: string,
  total: number,
  pageSize: number,
) =>
  initialView === "finance-payment-query" &&
  total > 0 &&
  total <= pageSize;

export const paymentQueryQuickPageResult = (value: string, totalPages: number) => {
  if (value === "") {
    return { ok: false, page: null, message: "请输入页码数" };
  }
  if (!/^[0-9]*[1-9][0-9]*$/.test(value)) {
    return { ok: false, page: null, message: "请输入正确的页码!" };
  }
  const page = Number(value);
  if (page > totalPages) {
    return { ok: false, page: null, message: "请输入有效范围的页码!" };
  }
  return { ok: true, page, message: "" };
};

export const paymentQueryPageSizeOptions = (initialView: string) =>
  initialView === "finance-payment-query"
    ? [10, 15, 20, 50, 100, 200]
    : undefined;

export const paymentQueryDefaultPageSize = (initialView: string) =>
  initialView === "finance-payment-query" ? 15 : undefined;

// Legacy FAS/FAM invoice controllers initialize every invoice list with
// PageSize=20 (audit/process/application lists alike).
export const invoiceLegacyDefaultPageSize = (initialView: string) =>
  initialView.startsWith("finance-invoice") ? 20 : 15;

export const invoiceLegacyErrorMessage = "查询出错.";
export const settlementLegacyErrorMessage = "查询出错.";

export const paymentQueryControlledPageSize = (
  initialView: string,
  selectedPageSize: number,
) =>
  initialView === "finance-payment-query" ? selectedPageSize : undefined;

export const paymentQueryServerPagePlan = (page: number, pageSize: number) => {
  const safePage = Math.max(1, page);
  const safePageSize = Math.max(1, pageSize);
  if (safePageSize <= 100) {
    return [{ page: safePage, pageSize: safePageSize }];
  }
  const apiPageCount = Math.ceil(safePageSize / 100);
  const firstApiPage = (safePage - 1) * apiPageCount + 1;
  return Array.from({ length: apiPageCount }, (_value, index) => ({
    page: firstApiPage + index,
    pageSize: 100,
  }));
};

export const paymentQueryPageTotal = (
  rows: ReadonlyArray<{
    data?: Record<string, any>;
    amount?: number | string;
  }>,
) =>
  rows
    .reduce(
      (sum, row) => sum + Number(row.data?.amount ?? row.amount ?? 0),
      0,
    )
    .toFixed(2);

export const paymentQueryFeeTypeControl = (initialView: string): "feeType" | undefined =>
  initialView === "finance-payment-query" ? undefined : "feeType";

export const settlementContextPageSize = 100;

export const settlementContextTasksRequest = (caseId: number, page: number) => ({
  url: "/cases/" + caseId + "/tasks",
  params: { page, page_size: settlementContextPageSize },
});

export const normalizeSettlementContextRows = (data: any) =>
  Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : [];

export const effectivePaymentQuery = (
  initialView: string,
  query: Record<string, any>,
  knownFeeTypes: string[],
) => {
  const feeType = String(query.feeType || "").trim();
  if (
    initialView !== "finance-payment-query" ||
    !feeType ||
    knownFeeTypes.includes(feeType)
  ) {
    return query;
  }
  const next = { ...query };
  delete next.feeType;
  return next;
};

export const invoiceText = (value: unknown) => String(value ?? "").trim();

export const legacyInvoiceUpdateFailureMessage = (response: { data?: unknown }) => {
  const payload = response?.data;
  if (!payload || typeof payload !== "object") return "";
  const result = payload as Record<string, unknown>;
  if (result.IsSuccess !== false && result.success !== false) return "";
  return invoiceText(result.message || result.Message || result.detail) || "发票申请更新失败";
};

export const findInvoiceContract = (fee: Fee, contracts: Fee[]) => {
  const data = fee.data || {};
  const contractId = Number(data.contract_id ?? data.contract_record_id);
  const contractNo = invoiceText(data.contract_no);
  return contracts.find((contract) =>
    (Number.isFinite(contractId) && contractId > 0 && contract.id === contractId) ||
    (contractNo && contract.serial_no === contractNo),
  );
};

export const findInvoiceCustomer = (
  customerRows: Fee[],
  customerName: unknown,
  customerNo: unknown,
  customerId: unknown,
) => {
  const name = invoiceText(customerName);
  const serialNo = invoiceText(customerNo);
  const id = Number(customerId);
  return customerRows.find((customer) =>
    (Number.isFinite(id) && id > 0 && customer.id === id) ||
    (serialNo && customer.serial_no === serialNo) ||
    (name && (customer.title === name || customer.customer === name)),
  );
};

export const buildInvoiceCustomerDefaults = (
  customerRows: Fee[],
  customerName: unknown,
  customerNo: unknown,
  customerId: unknown,
): InvoiceCustomerDefaults => {
  const customer = findInvoiceCustomer(customerRows, customerName, customerNo, customerId);
  const data = customer?.data || {};
  const name = invoiceText(customer?.title || customer?.customer || customerName);
  return {
    customer: name,
    customer_no: invoiceText(customer?.serial_no || customerNo),
    invoice_title: invoiceText(data.invoice_title || name),
    taxpayer_id: invoiceText(
      data.taxpayer_id || data.credit_code || data.unified_social_credit_code,
    ),
    invoice_phone: invoiceText(data.invoice_phone || data.phone || data.office_phone),
    bank_account: invoiceText(data.bank_account),
    bank_name: invoiceText(data.bank_name),
    invoice_address: invoiceText(data.invoice_address || data.registered_address),
  };
};

export const invoiceFeeAvailableAmount = (fee: Fee) =>
  Number(fee.data?.remaining_invoice_amount ?? fee.data?.amount ?? 0);

export const refundStatusOptions = ["全部", "草稿", "待审批", "退款办理中", "已退款", "已驳回"];

export const invoiceFeeIssuedAmount = (fee: Fee) => {
  const data = fee.data || {};
  if (data.invoiced_amount != null) return Number(data.invoiced_amount || 0);
  return Math.max(0, Number(data.amount || 0) - invoiceFeeAvailableAmount(fee));
};

export const buildInvoiceSourceFields = (
  selectedFees: Fee[],
  contracts: Fee[],
  customerRows: Fee[],
): InvoiceSourceFields => {
  const first = selectedFees[0];
  if (!first) return {};
  const data = first.data || {};
  const contract = findInvoiceContract(first, contracts);
  const contractData = contract?.data || {};
  const customerDefaults = buildInvoiceCustomerDefaults(
    customerRows,
    first.customer || data.customer || contract?.customer,
    data.customer_no || contractData.customer_no,
    data.customer_id || data.customer_record_id || contractData.customer_id,
  );
  return {
    case_no: invoiceText(data.case_no),
    case_record_id: data.case_id || data.case_record_id || undefined,
    contract_record_id:
      data.contract_id || data.contract_record_id || contract?.id || undefined,
    contract_no: invoiceText(data.contract_no || contract?.serial_no),
    external_contract_no: invoiceText(
      data.external_contract_no || contractData.external_contract_no,
    ),
    ...customerDefaults,
    amount: Number(
      selectedFees.reduce((total, fee) => total + invoiceFeeAvailableAmount(fee), 0).toFixed(2),
    ),
  };
};

export const createPaymentPrintPreview = (
  row: Fee,
  transactions: Transaction[],
  creator: string,
  printTime: string,
): PaymentPrintDocumentData | null => {
  const payment = transactions
    .filter(
      (item) =>
        item.finance_record_id === row.id && item.transaction_type === "付款",
    )
    .sort((a, b) =>
      String(b.transaction_date).localeCompare(String(a.transaction_date)),
    )[0];
  if (!payment) return null;
  return {
    documentTitle: `${row.serial_no}付款单`,
    packageNo:
      row.data.payment_package_no || row.data.package_no || "",
    serialNo: row.serial_no,
    paymentDate: payment.transaction_date,
    feeTitle: row.title,
    attribute:
      row.data.attribute || row.data.property || row.data.expense_subtype || "",
    feeType:
      row.data.fee_type_name ||
      row.data.commission_type ||
      row.data.fee_type ||
      row.title,
    customer: row.customer,
    caseNo: row.data.case_no,
    contractNo: row.data.contract_no,
    contractTitle: row.data.contract_title || "",
    applicant: row.data.applicant || row.owner || "",
    applicantDisplayName:
      row.data.applicant_display_name || row.data.owner_display_name || "",
    payer: row.data.payer || row.data.payer_name || row.customer || "",
    payerDisplayName:
      row.data.payer_display_name || row.data.payer_name_display_name || "",
    payee: payment.counterparty || row.data.payee,
    amount: money(payment.amount || 0),
    voucherNo: payment.voucher_no,
    operator: payment.operator,
    operatorDisplayName: (payment as any).operator_display_name || "",
    remark: payment.remark || row.data.description || row.data.remark,
    creator,
    printTime,
  };
};
