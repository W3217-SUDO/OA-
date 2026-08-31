export const buildCasePaymentTypeSelectOptions = (items = []) =>
  (Array.isArray(items) ? items : [])
    .filter((item) => Number(item?.id) > 0 && String(item?.payee || "").trim())
    .map((item) => ({
      value: Number(item.id),
      label: [item.payee, item.account_bank, item.account]
        .map((value) => String(value || "").trim())
        .filter(Boolean)
        .join("｜"),
    }));

export const buildExternalPaymentRequestPayload = (values = {}, comment = "") => ({
  amount: Number(values.amount),
  payment_type_id: Number(values.payment_type_id),
  payment_remark: String(values.payment_remark || "").trim(),
  comment: String(values.payment_remark || comment || "").trim(),
});
