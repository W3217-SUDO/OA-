const formatValue = (value, pattern) => {
  if (value && typeof value === "object" && typeof value.format === "function") return String(value.format(pattern));
  return String(value ?? "").trim();
};

export const buildCaseHearingPayload = (values) => ({
  ...values,
  hearing_date: formatValue(values?.hearing_date, "YYYY-MM-DD"),
  hearing_time: formatValue(values?.hearing_time, "HH:mm"),
});

export const getCaseHearingValidationError = (values) => {
  if (!values?.case_record_id) return "\u8bf7\u9009\u62e9\u5173\u8054\u6848\u4ef6";
  if (!formatValue(values.hearing_date, "YYYY-MM-DD")) return "\u8bf7\u9009\u62e9\u5f00\u5ead\u65e5\u671f";
  if (!formatValue(values.hearing_time, "HH:mm")) return "\u8bf7\u9009\u62e9\u5f00\u5ead\u65f6\u95f4";
  if (!String(values.court ?? "").trim()) return "\u8bf7\u8f93\u5165\u5f00\u5ead\u6cd5\u9662";
  return "";
};

export const getCaseHearingDeleteValidationError = (role) =>
  role === "admin" ? "" : "\u4ec5\u7ba1\u7406\u5458\u53ef\u4ee5\u5220\u9664\u6392\u671f";

export const getCaseArchiveReviewValidationError = ({ role, status } = {}) => {
  if (!new Set(["admin", "manager"]).has(role)) return "\u53ea\u6709\u7ba1\u7406\u5458\u6216\u90e8\u95e8\u8d1f\u8d23\u4eba\u53ef\u4ee5\u5ba1\u6838\u5f52\u6863";
  if (status !== "\u5f85\u5f52\u6863\u5ba1\u6838") return "\u53ea\u6709\u5f85\u5f52\u6863\u5ba1\u6838\u6848\u4ef6\u53ef\u4ee5\u5ba1\u6838";
  return "";
};

export const getCaseUnarchiveReviewValidationError = ({
  role,
  status,
  requestStatus,
  requestedBy,
  currentUsername,
  approved,
  comment,
} = {}) => {
  if (!new Set(["admin", "manager"]).has(role)) return "\u53ea\u6709\u7ba1\u7406\u5458\u6216\u90e8\u95e8\u8d1f\u8d23\u4eba\u53ef\u4ee5\u5ba1\u6279\u89e3\u6863";
  if (status !== "\u5df2\u5f52\u6863" || requestStatus !== "\u5f85\u5ba1\u6279") return "\u8be5\u6848\u4ef6\u6ca1\u6709\u5f85\u5ba1\u6279\u7684\u89e3\u6863\u7533\u8bf7";
  if (requestedBy && requestedBy === currentUsername && role !== "admin") return "\u89e3\u6863\u7533\u8bf7\u4eba\u4e0d\u80fd\u5ba1\u6279\u81ea\u5df1\u7684\u7533\u8bf7";
  if (!approved && String(comment ?? "").trim().length < 2) return "\u9a73\u56de\u65f6\u5fc5\u987b\u586b\u5199\u81f3\u5c112\u4e2a\u5b57\u7684\u539f\u56e0";
  return "";
};

export const buildCaseUnarchiveReviewPayload = ({ approved, comment } = {}) => ({
  approved: Boolean(approved),
  comment: String(comment ?? "").trim(),
});
