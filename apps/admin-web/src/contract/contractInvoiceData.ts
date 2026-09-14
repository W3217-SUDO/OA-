import { api } from "../api";
import type { Contract } from "./types";
import { customerInvoiceDefaults, validateInvoiceContracts } from "./contractInvoiceApplication";
import type { InvoiceApplicationSubject } from "./contractInvoiceApplication";

async function loadInvoiceCustomer(contract: Contract) {
  const id = Number(contract.data.customer_id || 0);
  const no = String(contract.data.customer_no || "").trim();
  if (id) {
    const { data } = await api.get(`/records/${id}`);
    if (data.module !== "customer" || (no && data.serial_no !== no) || data.title !== contract.customer) throw new Error("客户关联不一致，请核对合同客户资料");
    return data;
  }
  const matches: any[] = [];
  let page = 1;
  while (true) {
    const { data } = await api.get("/records", { params: { module: "customer", keyword: no || contract.customer, page, page_size: 100 } });
    const rows = data.items || [];
    matches.push(...rows.filter((row: any) => row.module === "customer" && (no ? row.serial_no === no : row.title === contract.customer)));
    if (rows.length < 100 || page * 100 >= Number(data.total)) break;
    page += 1;
  }
  if (matches.length !== 1) throw new Error(matches.length ? "客户名称对应多份档案，请先明确合同客户关联" : "客户资料不存在或无权访问");
  return (await api.get(`/records/${matches[0].id}`)).data;
}

export async function loadContractInvoiceData(contracts: Contract[]) {
  validateInvoiceContracts(contracts);
  const subjects = new Map<number, InvoiceApplicationSubject>();
  // Each call retains the server's per-contract visibility and lifecycle checks.
  for (const contract of contracts) {
    const { data } = await api.get(`/contracts/${contract.id}/invoice-candidates`);
    for (const row of data.items || []) {
      const previous = subjects.get(Number(row.fee_id));
      if (previous && previous.contract_record_id !== contract.id) throw new Error("同一费用存在冲突的合同归属");
      subjects.set(Number(row.fee_id), { ...row, fee_id: Number(row.fee_id), contract_record_id: contract.id,
        contract_no: contract.serial_no, external_contract_no: row.external_contract_no ?? contract.data.external_contract_no ?? "" });
    }
  }
  const customer = await loadInvoiceCustomer(contracts[0]);
  return { subjects: [...subjects.values()], defaults: customerInvoiceDefaults(customer, contracts[0].customer) };
}
