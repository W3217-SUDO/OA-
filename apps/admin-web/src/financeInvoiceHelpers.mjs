const text = (value) => String(value ?? "").trim();
const unique = (values) => [...new Set(values.filter((value) => value != null && value !== ""))];
const cents = (value) => Math.round((Number(value) + Number.EPSILON) * 100);

export function validateInvoiceAmounts(values) {
  const amount = Number(values.amount);
  if (!Number.isFinite(amount) || cents(amount) <= 0) return "开票金额必须大于0";
  if (values.extra_amount != null && (!Number.isFinite(Number(values.extra_amount)) || Number(values.extra_amount) < 0)) return "高开金额必须为非负有限数";
  const services = Array.isArray(values.service_items) ? values.service_items : [];
  for (const [index, row] of services.entries()) {
    if (!text(row.service_name)) return `第${index + 1}项服务名称不能为空`;
    const qty = Number(row.quantity), price = Number(row.unit_price), lineAmount = Number(row.amount);
    if (!Number.isFinite(qty) || qty <= 0 || !Number.isFinite(price) || price < 0 || !Number.isFinite(lineAmount) || lineAmount < 0) return "服务数量、单价和金额无效";
    if (cents(qty * price) !== cents(lineAmount)) return "服务金额必须等于数量乘单价";
    const rate = Number(row.tax_rate ?? 0), tax = Number(row.tax_amount ?? 0);
    if (!Number.isFinite(rate) || rate < 0 || rate > 100 || !Number.isFinite(tax) || tax < 0) return "税率须在0至100之间，税额须为非负有限数";
  }
  if (services.length && services.reduce((sum, row) => sum + cents(row.amount), 0) !== cents(amount)) return "服务项金额合计必须等于开票金额";
  const allocations = Array.isArray(values.case_fee_allocations) ? values.case_fee_allocations : [];
  if (allocations.length) {
    const ids = allocations.map((row) => Number(row.fee_id));
    if (ids.some((id) => !Number.isInteger(id) || id <= 0) || unique(ids).length !== ids.length) return "费用分配ID必须是唯一正整数";
    const selected = unique((values.case_fee_ids || []).map(Number));
    if (ids.length !== selected.length || ids.some((id) => !selected.includes(id))) return "费用分配必须与所选费用逐项一致";
    if (allocations.some((row) => row.amount == null || !Number.isFinite(Number(row.amount)) || cents(row.amount) <= 0)) return "本次开票金额必须为正数";
    if (allocations.reduce((sum, row) => sum + cents(row.amount), 0) !== cents(amount)) return "费用分配金额合计必须等于开票金额";
  }
  return "";
}

export const buildInvoiceApplicationPayload = ({ values = {}, cases = [], contracts = [], caseFees = [], requireSource = false }) => {
  const requested = Array.isArray(values.case_fee_ids) ? values.case_fee_ids : values.case_fee_ids ? [values.case_fee_ids] : [];
  const feeIds = unique(requested.map(Number));
  if (feeIds.some((id) => !Number.isInteger(id) || id <= 0)) return { ok: false, error: "关联费用编号无效" };
  if (requireSource && !feeIds.length) return { ok: false, error: "新建发票申请至少关联一笔案件费用" };
  const linked = feeIds.map((id) => caseFees.find((row) => Number(row.id) === id));
  if (linked.some((row) => !row)) return { ok: false, error: "关联费用不存在或无权访问，请重新加载明细" };
  if (linked.some((row) => row.data?.missing_or_forbidden || row.data?.contract_missing_or_forbidden)) return { ok: false, error: "来源费用或合同不存在或无权访问" };
  const source = linked.map((row) => {
    const data = row.data || row;
    const contractId = data.contract_record_id ?? data.contract_id;
    const contract = contracts.find((item) => Number(item.id) === Number(contractId) || (text(data.contract_no) && text(item.serial_no) === text(data.contract_no)));
    const caseRecord = cases.find((item) => text(item.serial_no) === text(data.case_no));
    return { customer: text(row.customer || data.customer || contract?.customer || caseRecord?.customer),
      customerId: data.customer_record_id ?? data.customer_id ?? contract?.data?.customer_id,
      customerNo: text(data.customer_no || contract?.data?.customer_no),
      caseNo: text(data.case_no), caseId: data.case_record_id ?? data.case_id ?? caseRecord?.id,
      contractId: contractId ?? contract?.id, contractNo: text(data.contract_no || contract?.serial_no),
      externalNo: text(data.external_contract_no || contract?.data?.external_contract_no),
    };
  });
  const customerNames = unique(source.map((row) => row.customer));
  if (customerNames.length > 1 || unique(source.map((row) => row.customerId)).length > 1 || unique(source.map((row) => row.customerNo)).length > 1) return { ok: false, error: "一次申请开票只能选择同一客户下的费用" };
  if (source.length && source.some((row) => !row.customer)) return { ok: false, error: "来源费用缺少客户信息，请重新加载明细" };
  if (customerNames.length && text(values.customer) && customerNames[0] !== text(values.customer)) return { ok: false, error: "开票客户与来源费用不一致" };
  const error = validateInvoiceAmounts(values);
  if (error) return { ok: false, error };
  const payload = { ...values, customer: customerNames[0] || text(values.customer), amount: cents(values.amount) / 100, case_fee_ids: feeIds };
  if (source.length) {
    // Summary fields are meaningful only for one source. Per-fee links stay in allocations.
    const caseNos = unique(source.map((row) => row.caseNo));
    const contractNos = unique(source.map((row) => row.contractNo));
    const contractIds = unique(source.map((row) => row.contractId));
    const oneCase = caseNos.length === 1 && source.every((row) => row.caseNo === caseNos[0]);
    const oneContract = contractIds.length <= 1 && contractNos.length <= 1 && source.every((row) => row.contractId || row.contractNo);
    Object.assign(payload, { case_no: oneCase ? caseNos[0] : "", case_record_id: oneCase ? source[0].caseId ?? null : null,
      contract_record_id: oneContract ? source[0].contractId ?? null : null, contract_no: oneContract ? source[0].contractNo : "",
      external_contract_no: oneContract ? source[0].externalNo : "" });
  } else {
    const caseNo = text(values.case_no);
    const caseRecord = cases.find((row) => text(row.serial_no) === caseNo);
    if (caseNo && !caseRecord) return { ok: false, error: "关联案件不存在或无权访问" };
    const contractId = values.contract_record_id == null || values.contract_record_id === "" ? null : Number(values.contract_record_id);
    if (contractId != null && (!Number.isInteger(contractId) || contractId <= 0)) return { ok: false, error: "关联合同编号无效" };
    if (contractId != null && !contracts.some((row) => Number(row.id) === contractId)) return { ok: false, error: "关联合同不存在或无权访问" };
    Object.assign(payload, { case_no: caseNo, case_record_id: caseRecord?.id ?? null, contract_record_id: contractId });
  }
  return { ok: true, payload };
};
