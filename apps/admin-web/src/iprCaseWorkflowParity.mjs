const REVIEW_ROLES = new Set(["admin", "manager"]);
const SUBMIT_STATUSES = new Set(["草稿", "已驳回"]);

export const getIprCaseActionValidationError = ({
  action,
  role,
  status,
  applicationNo,
  approved,
  comment,
} = {}) => {
  if (action === "submit") {
    if (!SUBMIT_STATUSES.has(status)) return "当前状态不能提交知识产权立案审核";
    if (!String(applicationNo ?? "").trim()) return "提交立案审核前必须填写申请号或注册号";
  }
  if (action === "review") {
    if (!REVIEW_ROLES.has(role)) return "仅管理员或管理人员可以审核知识产权立案";
    if (status !== "待立案审核") return "该知识产权案件不在待立案审核状态";
    if (!approved && !String(comment ?? "").trim()) return "驳回必须填写原因";
  }
  if (action === "close" && status !== "在办") return "仅在办知识产权案件可以结案";
  if (action === "reopen") {
    if (!REVIEW_ROLES.has(role)) return "仅管理员或管理人员可以重新开启知识产权案件";
    if (status !== "已结案") return "仅已结案知识产权案件可以重新开启";
  }
  return "";
};

export const buildIprCaseActionPayload = ({ action, approved, comment } = {}) => (
  action === "review"
    ? { approved: Boolean(approved), comment: String(comment ?? "").trim() }
    : { comment: String(comment ?? "").trim() }
);

export const normalizeIprCaseActionResponse = (response, fallback) => {
  const payload = response?.data ?? response ?? {};
  const explicit = payload.is_success ?? payload.IsSuccess ?? payload.success;
  const ok = explicit === undefined ? true : Boolean(explicit);
  const message = String(payload.message ?? payload.Message ?? fallback);
  return { ok, message: message.trim() || fallback };
};

export const getIprCaseActionErrorMessage = (error, fallback) => {
  const payload = error?.response?.data ?? error?.data ?? error ?? {};
  const message = payload.detail ?? payload.message ?? payload.Message ?? error?.message ?? fallback;
  return String(message || "").trim() || fallback;
};
