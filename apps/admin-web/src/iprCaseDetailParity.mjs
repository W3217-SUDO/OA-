const uniquePositiveNumbers = (values) => [...new Set((Array.isArray(values) ? values : []).map(Number).filter((value) => Number.isInteger(value) && value > 0))];
const uniqueTrimmedStrings = (values) => [...new Set((Array.isArray(values) ? values : []).map((value) => String(value ?? "").trim()).filter(Boolean))];

export const getIprCaseCustomerValidationError = ({ customerIds, primaryCustomerId } = {}) => {
  const selected = uniquePositiveNumbers(customerIds);
  if (!selected.length || !Number(primaryCustomerId)) return "请至少选择一个客户并指定主客户";
  if (!selected.includes(Number(primaryCustomerId))) return "请从已选客户中指定一个主客户";
  return "";
};

export const buildIprCaseCustomerPayload = ({ customerIds, primaryCustomerId } = {}) => ({
  customer_ids: uniquePositiveNumbers(customerIds),
  primary_customer_id: Number(primaryCustomerId),
});

export const buildIprCaseContactPayload = ({ customerId, documentContactIds, technologyContactIds } = {}) => ({
  customer_id: Number(customerId),
  document_contact_ids: uniqueTrimmedStrings(documentContactIds),
  technology_contact_ids: uniqueTrimmedStrings(technologyContactIds),
});

export const buildIprCaseLawFirmPayload = ({ lawFirmIds } = {}) => ({
  law_firm_ids: uniquePositiveNumbers(lawFirmIds),
});

export const getIprCaseDeletionConfirmation = (kind, label = "") => {
  const labels = {
    log: "业务日志",
    file: "案件文档",
    reminder: "案件提醒",
    "assisted-fee": "资助费用",
  };
  const target = labels[kind] || "案件记录";
  return {
    title: `确认删除${target}？`,
    content: `${label ? `${label}将被删除，` : ""}删除后不可恢复。`,
    okText: "确认删除",
    cancelText: "取消",
  };
};
