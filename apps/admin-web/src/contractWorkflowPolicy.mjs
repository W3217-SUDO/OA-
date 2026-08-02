export const CONTRACT_ATTACHMENT_ACCEPT = ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.png,.jpg,.jpeg,.zip,.rar";
export const CONTRACT_ATTACHMENT_MAX_BYTES = 20 * 1024 * 1024;
export const CONTRACT_ATTACHMENT_LOCKED_STATUSES = ["审批中", "已归档"];
export const CONTRACT_DRAFT_EDITABLE_STATUSES = ["草稿", "已拒绝"];
export const CONTRACT_LIST_PAGE_SIZES = [10, 15, 20, 50, 100, 200];
export const CONTRACT_QUERY_FIELDS = ["title", "serial_no", "type", "customer", "case_no", "fee_type", "signed_at", "source_person", "contract_body"];
const CONTRACT_LIST_ROUTES = new Set(["contract-mine", "contract-dept", "contract-company", "contract-audit", "contract-audit-pending", "contract-audit-refused", "contract-audit-approved"]);
export const contractMenuEntries = () => [
  { key: "contract-mine", label: "我的合同", scope: "mine", legacyPath: "FCM/Contract/ContractList" },
  { key: "contract-dept", label: "部门合同", scope: "department", legacyPath: "CMS/Contract/ContractList" },
  { key: "contract-company", label: "公司合同", scope: "company", legacyPath: "CMS/Contract/GeneralLedgerList" },
  { key: "contract-audit-pending", label: "待审批合同", scope: "audit", legacyPath: "CMS/Contract/ContractList/2" },
  { key: "contract-audit-refused", label: "已驳回合同", scope: "audit", legacyPath: "CMS/Contract/ContractList/4" },
  { key: "contract-audit-approved", label: "已审批合同", scope: "audit", legacyPath: "CMS/Contract/ContractList/3" },
];
export const contractListViewConfig = (view) => {
  const entry = contractMenuEntries().find((item) => item.key === view);
  const audit = view.startsWith("contract-audit");
  const statuses = contractAuditViewConfig(view).statuses;
  return { scope: entry?.scope || "all", defaultPageSize: audit || view === "contract-dept" || view === "contract-company" ? 20 : 15, statuses, queryFields: CONTRACT_QUERY_FIELDS };
};
export const normalizeContractQuery = (values = {}) => {
  const normalized = {};
  for (const field of CONTRACT_QUERY_FIELDS) {
    const value = values[field];
    if (Array.isArray(value)) normalized[field] = value.length ? value : undefined;
    else if (typeof value === "string") normalized[field] = value.trim() || undefined;
    else if (value !== undefined && value !== null) normalized[field] = value;
  }
  return normalized;
};
export const buildContractListRequestParams = (view, pagination, query = {}) => {
  const config = contractListViewConfig(view);
  const normalized = normalizeContractQuery(query);
  const current = Number(pagination?.current);
  const selectedPageSize = Number(pagination?.pageSize);
  const params = { module: "contract", scope: config.scope, page: Number.isInteger(current) && current > 0 ? current : 1, page_size: CONTRACT_LIST_PAGE_SIZES.includes(selectedPageSize) ? selectedPageSize : config.defaultPageSize };
  for (const field of CONTRACT_QUERY_FIELDS) {
    const value = normalized[field];
    if (field === "signed_at" && Array.isArray(value) && value.length === 2) {
      if (typeof value[0]?.format === "function") params.signed_at_start = value[0].format("YYYY-MM-DD");
      if (typeof value[1]?.format === "function") params.signed_at_end = value[1].format("YYYY-MM-DD");
    } else if (value !== undefined) params[field] = value;
  }
  if (config.statuses.length) params.statuses = config.statuses.join(",");
  return params;
};
export const canAccessContractView = (view, profile = {}) => CONTRACT_LIST_ROUTES.has(view) && profile.role !== "guest";
export const validateContractApprovalSubmission = (status, approvers, attachmentCount) => {
  const errors = [];
  if (!CONTRACT_DRAFT_EDITABLE_STATUSES.includes(status)) errors.push("status");
  if (!String(approvers || "").trim()) errors.push("approver");
  if (Number(attachmentCount) < 1) errors.push("attachment");
  return errors;
};
export const contractAttachmentActionPolicy = (status) => {
  const mutable = canMutateContractAttachments(status);
  return { canUpload: mutable, canDelete: mutable, canDownload: true, canPreview: true };
};
export const extractContractErrorMessage = (error, fallback) => {
  const detail = error?.response?.data?.detail || error?.response?.data?.message || error?.message;
  return typeof detail === "string" && detail.trim() ? detail.trim() : fallback;
};
export const contractAuditActionPolicy = (view) => {
  const canReview = view === "contract-audit" || view === "contract-audit-pending";
  return { canReview, canReviewChange: canReview, canExport: true };
};
export const contractAuditViewConfig = (view) => {
  if (view === "contract-audit-pending") return { statuses: ["审批中"] };
  if (view === "contract-audit-refused") return { statuses: ["已拒绝", "已驳回"] };
  if (view === "contract-audit-approved") return { statuses: ["已通过", "履行中", "已完成", "已归档"] };
  return { statuses: [] };
};
export const normalizeContractDetailReturnView = (view) => {
  const allowed = new Set([
    "contract-mine",
    "contract-dept",
    "contract-company",
    "contract-audit",
    "contract-audit-pending",
    "contract-audit-refused",
    "contract-audit-approved",
  ]);
  return allowed.has(view) ? view : "contract-mine";
};

export const buildContractDraftDefaults = ({ serialNo, profile, customer }) => ({
  serial_no: serialNo,
  status: "草稿",
  owner: profile.username || "admin",
  department: profile.department || "上海分所",
  type: "法律顾问合同",
  contract_body: "律所",
  fee_type: "固定收费",
  amount: 0,
  signed_at: new Date(),
  customer_id: customer?.id,
  title: customer?.title ? `${customer.title}合同` : undefined,
});

export const validateContractDraftValues = (values) => {
  const errors = [];
  if (!Number(values.customer_id)) errors.push("customer_id");
  if (!String(values.title || "").trim()) errors.push("title");
  return errors;
};

export const resolveContractCustomerSelection = (customerId, customers, linkedCustomer, profile) => {
  if (!customerId || Number.isNaN(customerId)) return null;
  const exact = customers.find((item) => item.id === customerId);
  if (exact) return exact;
  if (linkedCustomer?.id === customerId) {
    return {
      id: linkedCustomer.id,
      serial_no: linkedCustomer.serial_no || `C-${linkedCustomer.id}`,
      title: linkedCustomer.name,
      owner: profile.username || "",
      data: { customer_managers: profile.username ? [profile.username] : [] },
    };
  }
  return null;
};

export const filterContractCaseOptions = (cases, customer) => {
  const expected = String(customer || "").trim();
  if (!expected) return cases;
  return cases.filter((item) => !String(item.customer || "").trim() || item.customer === expected);
};

export const filterContractLinkedRows = (rows = [], contract = {}) => {
  const contractId = Number(contract?.id || 0);
  const contractNo = String(contract?.serial_no || "").trim();
  return rows.filter((item) => {
    const data = item?.data || {};
    const linkedId = Number(item?.contract_record_id || data.contract_record_id || data.contract_id || 0);
    const linkedNo = String(item?.contract_no || data.contract_no || "").trim();
    return (contractId > 0 && linkedId === contractId) || (Boolean(contractNo) && linkedNo === contractNo);
  });
};

export const canActOnContractApproval = (status, approver, username, role) =>
  status === "审批中" && Boolean(approver) && (approver === username || role === "admin");

export const buildContractApprovalPayload = (approved, comment) => ({
  approved,
  comment: String(comment || "").trim(),
});

export const canMutateContractAttachments = (status) => !CONTRACT_ATTACHMENT_LOCKED_STATUSES.includes(status);

export const validateContractAttachment = (file) => {
  if (!file) return "请选择合同附件";
  if (!Number(file.size)) return "文件没有任何内容";
  if (Number(file.size) > CONTRACT_ATTACHMENT_MAX_BYTES) return "单个文件不能超过 20MB";
  return null;
};
