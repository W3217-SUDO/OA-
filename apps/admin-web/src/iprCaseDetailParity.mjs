import dayjs from "dayjs";

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

const STATUS_ERROR_MESSAGES = {
  401: "登录状态已失效，请重新登录",
  403: "当前账号无权执行此操作",
  404: "案件记录不存在或已被删除",
  409: "当前案件状态不允许此操作",
  422: "请求数据校验失败",
};

const SECTION_ERROR_MESSAGES = {
  files: "案件文档加载失败",
  logs: "案件日志加载失败",
  reminders: "案件提醒加载失败",
  assistedFees: "资助费用加载失败",
};

export const getIprApiErrorMessage = (error, fallback = "操作失败") => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => item?.msg || item?.message).filter(Boolean);
    if (messages.length) return messages.join("；");
  }
  return STATUS_ERROR_MESSAGES[error?.response?.status] || fallback;
};

export const getIprSectionLoadError = (section, error) =>
  getIprApiErrorMessage(error, SECTION_ERROR_MESSAGES[section] || "案件详情加载失败");

export const getIprCompatibleFileCategory = ({ category, caseKinds, fileTypes } = {}) => {
  if (!String(category ?? "").trim()) return undefined;
  const kinds = Array.isArray(caseKinds) ? caseKinds.map((value) => String(value)) : [];
  const match = (Array.isArray(fileTypes) ? fileTypes : []).find((item) => {
    if (item?.name !== category) return false;
    const applicableKinds = Array.isArray(item.case_kinds) ? item.case_kinds : [];
    return !applicableKinds.length || kinds.every((kind) => applicableKinds.includes(kind));
  });
  return match ? category : undefined;
};

export const buildIprDeadlineFromOffset = ({ baseDate, years = 0, months = 0, days = 0 } = {}) => {
  if (!baseDate) return "";
  const result = (typeof baseDate === "string" ? dayjs(baseDate) : baseDate)
    .add(Number(years) || 0, "year")
    .add(Number(months) || 0, "month")
    .add(Number(days) || 0, "day");
  return result.format("YYYY-MM-DD");
};
