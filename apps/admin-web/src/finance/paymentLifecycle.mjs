export const isContractPayment = (row) =>
  row?.module === "contract_payment" || row?.data?._source_module === "contract_payment";

export const paymentActionPath = (row, action) =>
  `${isContractPayment(row) ? "/contract-payment-applications" : "/finance/fees"}/${row.id}/${action}`;

export const canEditContractPayment = (row) => isContractPayment(row) &&
  ["草稿", "已驳回", "已退回"].includes(row.status) &&
  row.data?.writeoff_status !== "已核销" && Number(row.data?.paid_amount || 0) === 0;

export const paymentLifecycleStatus = (row) => {
  if (String(row?.data?.writeoff_status || "").trim() === "待核销") return "待核销";
  const canonical = {
    待审批: "待审批",
    已审批: "待付款",
    部分付款: "待付款",
    已付款: "已付款",
    已退回: "已驳回",
    已驳回: "已驳回",
    已拒绝: "已驳回",
    已作废: "已作废",
  }[row?.status];
  if (canonical) return canonical;
  return String(row?.data?.payment_status || (row?.status === "草稿" ? "创建待提交" : row?.status) || "").trim();
};

export const unifiedPaymentQueryParams = (params) => {
  const { module, ...query } = params;
  return { ...query, page: Math.max(1, Number(query.page) || 1), page_size: Math.min(500, Math.max(1, Number(query.page_size) || 15)) };
};

export const paymentLineKey = (row) => row?.case_fee_id ? `fee:${row.case_fee_id}` : `object:${row?.contract_object_id}`;

export function contractPaymentEditPayload(values, selectedKeys, candidates, amounts, remarks = {}) {
  if (!selectedKeys.length) throw new Error("请至少选择一笔案件费用");
  if (new Set(selectedKeys).size !== selectedKeys.length || selectedKeys.length > 100) throw new Error("付款费用数量或标识无效");
  const lines = selectedKeys.map((key) => {
    const row = candidates.find((item) => paymentLineKey(item) === key);
    if (!row) throw new Error("原单关联费用不可用，请重新加载后核对");
    const value = Number(amounts[key]);
    const amount = Math.round((value + Number.EPSILON) * 100) / 100;
    const remaining = Number(row.remaining_amount);
    if (!Number.isFinite(amount) || amount <= 0 || amount > 999999999 || row.remaining_amount == null || !Number.isFinite(remaining) || amount > remaining + 0.0001) throw new Error("本次支付金额必须大于0且不能超过待付余额");
    const feeId = row.case_fee_id == null ? null : Number(row.case_fee_id);
    const objectId = row.contract_object_id == null ? null : Number(row.contract_object_id);
    if (Boolean(feeId) === Boolean(objectId) || [feeId, objectId].some((id) => id != null && (!Number.isInteger(id) || id <= 0))) throw new Error("付款费用来源标识无效");
    return { case_fee_id: feeId, contract_object_id: objectId, amount, remark: String(remarks[key] || "").trim() };
  });
  const unitId = Number(values.payment_type_id);
  if (!Number.isInteger(unitId) || unitId <= 0) throw new Error("请选择收款单位");
  return { payment_type_id: unitId, payer_name: String(values.payer_name || "").trim(),
    application_date: values.application_date, remark: String(values.remark || "").trim(), lines };
}
