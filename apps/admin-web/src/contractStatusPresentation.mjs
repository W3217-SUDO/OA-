const PRESENTED_APPROVED_STATUS = "\u5ba1\u6279\u901a\u8fc7";
const LEGACY_APPROVED_STATUSES = new Set(["\u5df2\u901a\u8fc7", "\u5c65\u884c\u4e2d"]);

export const displayContractStatus = (status) => (
  LEGACY_APPROVED_STATUSES.has(String(status ?? "")) ? PRESENTED_APPROVED_STATUS : status
);
