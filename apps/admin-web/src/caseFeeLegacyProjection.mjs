export const caseFeeRefundLabel = (data = {}) => {
  if (String(data.refund_status || "").toUpperCase() === "R100" || data.refund_not_required) {
    return "不再办理退费";
  }
  const requested = Number(data.refund_amount ?? data.refund_requested_amount ?? 0);
  const refunded = Number(data.refunded_amount ?? 0);
  if (requested <= 0) return "0";
  return `${requested} ${refunded >= requested ? "(已退)" : "(未退)"}`;
};
