import type { Contract } from "./types";

export type InvoiceApplicationSubject = {
  fee_id: number; fee_no?: string; case_record_id?: number; case_no: string; case_title?: string;
  contract_record_id?: number; contract_no?: string; external_contract_no?: string;
  case_stage?: string; fee_type?: string; expense_scope?: string; amount: number | null;
  invoiceable_amount: number | null; received_amount?: number | null; invoiced_amount?: number | null;
  court_name?: string; court_lawyer?: string; investigator?: string; case_assistant?: string;
  payer_name?: string; payment_mode?: string; received_date?: string;
};
export type InvoiceAllocation = { fee_id: number; amount: number };
export const invoiceMoney = (value: unknown) => Math.round((Number(value) + Number.EPSILON) * 100) / 100;
export const invoiceTotal = (rows: Array<{ amount?: unknown }>) => invoiceMoney(rows.reduce((sum, row) => sum + invoiceMoney(row.amount || 0), 0));

export function validateInvoiceContracts(contracts: Contract[]) {
  if (!contracts.length) throw new Error("请选择合同");
  if (contracts.length > 100) throw new Error("单次最多选择100份合同");
  const names = new Set(contracts.map(row => row.customer.trim()));
  const ids = new Set(contracts.map(row => row.data.customer_id).filter(Boolean));
  const nos = new Set(contracts.map(row => row.data.customer_no?.trim()).filter(Boolean));
  if (names.size !== 1 || names.has("") || ids.size > 1 || nos.size > 1) throw new Error("请选择同一客户下的合同");
  if (new Set(contracts.map(row => row.data.contract_body?.trim() || "律所")).size > 1) throw new Error("平台合同与律所合同不能合并开票");
}

export function buildContractInvoiceRoute(contracts: Contract[]) {
  validateInvoiceContracts(contracts);
  const first = contracts[0];
  // Keep the established route prefix; the encoded list also survives refresh and a copied URL.
  const value = contracts.length === 1 ? first.serial_no : JSON.stringify(contracts.map(({ id, serial_no }) => ({ id, serial_no })));
  return `contract-invoice-apply-${first.id}-${encodeURIComponent(value)}`;
}

export function readContractInvoiceRoute(id: number, encoded: string): Array<{ id: number; serial_no: string }> {
  const value = decodeURIComponent(encoded);
  const rows = value.startsWith("[") ? JSON.parse(value) : [{ id, serial_no: value }];
  if (!Array.isArray(rows) || !rows.length || rows.length > 100 || rows[0].id !== id ||
    rows.some(row => !Number.isSafeInteger(row.id) || row.id <= 0 || typeof row.serial_no !== "string" || !row.serial_no.trim()) ||
    new Set(rows.map(row => row.id)).size !== rows.length) throw new Error("开票合同参数无效，请从合同列表重新进入");
  return rows;
}

export function customerInvoiceDefaults(customer: { title?: string; data?: Record<string, any> }, fallbackName = "") {
  const data = customer.data || {};
  const first = (...values: unknown[]) => values.map(value => String(value ?? "").trim()).find(Boolean) || "";
  return {
    invoice_title: first(data.invoice_title, customer.title, fallbackName),
    taxpayer_id: first(data.taxpayer_id, data.credit_code),
    invoice_address: first(data.invoice_address, data.contact_address, data.address, data.registered_address),
    invoice_phone: first(data.invoice_phone, data.phone),
    bank_name: first(data.bank_name), bank_account: first(data.bank_account),
    email: first(data.email), recipient: first(data.contact), recipient_phone: first(data.phone),
    delivery_address: first(data.contact_address, data.address, data.invoice_address, data.registered_address),
  };
}

export function selectedInvoiceAllocations(keys: Array<string | number | bigint>, previous: InvoiceAllocation[], subjects: InvoiceApplicationSubject[]) {
  return keys.map(key => {
    const row = subjects.find(item => item.fee_id === Number(key));
    if (!row) throw new Error("所选费用不存在或无权访问，请重新加载");
    if (row.amount == null || row.invoiceable_amount == null || !Number.isFinite(Number(row.amount)) || !Number.isFinite(Number(row.invoiceable_amount))) throw new Error("费用金额或可开票余额缺失，请先核对财务资料");
    const saved = previous.find(item => item.fee_id === row.fee_id);
    return { fee_id: row.fee_id, amount: saved ? saved.amount : invoiceMoney(row.invoiceable_amount) };
  });
}

export function validateInvoiceAmounts(values: Record<string, any>, subjects: InvoiceApplicationSubject[], keys: Array<string | number | bigint>) {
  if (!keys.length) throw new Error("请至少选择一笔案件费用");
  if (keys.length > 100) throw new Error("单张发票最多选择100笔费用");
  const allocations: InvoiceAllocation[] = values.case_fee_allocations || [];
  const keySet = new Set(keys.map(Number));
  if (allocations.length !== keySet.size || new Set(allocations.map(row => row.fee_id)).size !== allocations.length ||
    allocations.some(row => !keySet.has(row.fee_id) || !subjects.some(item => item.fee_id === row.fee_id))) throw new Error("开票分配与所选费用不一致");
  selectedInvoiceAllocations(keys, allocations, subjects);
  if (allocations.some(row => !Number.isFinite(Number(row.amount)) || invoiceMoney(row.amount) <= 0)) throw new Error("每笔本次开票金额必须大于0");
  const total = invoiceTotal(allocations);
  if (!Number.isFinite(total) || total !== invoiceMoney(values.amount)) throw new Error("开票金额必须等于逐费分配合计");
  const services: Array<Record<string, any>> = values.service_items || [];
  if (!services.length || services.length > 100 || services.some(row => !String(row.service_name || "").trim() ||
    !Number.isFinite(Number(row.amount)) || Number(row.amount) < 0 || !Number.isFinite(Number(row.quantity)) || Number(row.quantity) <= 0 ||
    !Number.isFinite(Number(row.unit_price)) || Number(row.unit_price) < 0 ||
    !Number.isFinite(Number(row.tax_rate)) || Number(row.tax_rate) < 0 || Number(row.tax_rate) > 100 ||
    !Number.isFinite(Number(row.tax_amount)) || Number(row.tax_amount) < 0)) throw new Error("请完整填写服务名称、数量、单价、金额、税率和税额");
  if (services.some(row => invoiceMoney(Number(row.quantity) * Number(row.unit_price)) !== invoiceMoney(row.amount))) throw new Error("服务金额必须等于数量乘以单价");
  if (invoiceTotal(services) !== total) throw new Error("服务项金额合计必须等于本次开票合计");
  return allocations.map(row => ({ fee_id: row.fee_id, amount: invoiceMoney(row.amount) }));
}

export const invoiceSubjectQueryFields = [
  ["case_no", "案件编号"], ["contract_no", "合同号"], ["external_contract_no", "合同外部编号"],
  ["case_title", "案件名称"], ["court_name", "法院名称"], ["court_lawyer", "开庭律师"],
  ["investigator", "调查员"], ["payer_name", "回款单位"], ["fee_type", "费用类型"],
  ["case_assistant", "律师助理"], ["payment_mode", "回款方式"],
] as const;

export function filterInvoiceSubjects(subjects: InvoiceApplicationSubject[], query: Record<string, any>) {
  return subjects.filter(row => invoiceSubjectQueryFields.every(([key]) => !query[key] || String(row[key] || "").toLocaleLowerCase().includes(String(query[key]).trim().toLocaleLowerCase())) &&
    (!query.received_from || Boolean(row.received_date && row.received_date.slice(0, 10) >= query.received_from)) &&
    (!query.received_to || Boolean(row.received_date && row.received_date.slice(0, 10) <= query.received_to)));
}
