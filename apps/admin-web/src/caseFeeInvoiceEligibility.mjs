export const resolveCaseFeeInvoiceEligibility = (feeId, eligibleFees = []) => {
  const normalizedId = Number(feeId);
  const fee = eligibleFees.find((item) => Number(item?.id) === normalizedId);
  if (!fee) {
    return {
      ok: false,
      error: "该费用已经申请开票或当前不可开票，不能重复申请",
    };
  }
  return { ok: true, fee };
};
