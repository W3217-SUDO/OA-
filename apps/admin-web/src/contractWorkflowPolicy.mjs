export const CONTRACT_ATTACHMENT_ACCEPT = ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.png,.jpg,.jpeg,.zip,.rar";
export const CONTRACT_ATTACHMENT_MAX_BYTES = 20 * 1024 * 1024;
export const CONTRACT_ATTACHMENT_LOCKED_STATUSES = ["审批中", "已归档"];
export const CONTRACT_DRAFT_EDITABLE_STATUSES = ["草稿", "已拒绝"];

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
