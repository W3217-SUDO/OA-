export const caseFeeRefundLabel = (data = {}) => {
  const requested = Number(data.refund_amount ?? data.refund_requested_amount ?? 0);
  const refunded = Number(data.refunded_amount ?? 0);
  if (requested <= 0) return "0";
  return `${requested} ${refunded >= requested ? "(已退)" : "(未退)"}`;
};
