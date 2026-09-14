const rows = (value) => Array.isArray(value) ? value : [];
const numeric = (value) => value == null || value === "" || !Number.isFinite(Number(value)) ? null : Number(value);

export function invoiceServiceRows(record) {
  return rows(record?.data?.service_items).map((item, index) => ({ ...item, key: `service-${index}` }));
}

export function invoiceObjectRows(record) {
  const data = record?.data || {};
  const allocations = rows(data.case_fee_allocations);
  const objects = rows(data.invoice_objects);
  const source = objects.length ? objects : allocations;
  return source.map((item, index) => {
    const feeId = Number(item.fee_id ?? item.case_fee_id);
    const allocation = allocations.find((row) => Number(row.fee_id ?? row.case_fee_id) === feeId);
    return {
      ...item,
      fee_id: feeId,
      key: `${feeId}-${index}`,
      fee_amount: numeric(item.fee_amount ?? item.case_fee_amount),
      received_amount: numeric(item.received_amount ?? item.cashed_amount ?? item.case_fee_cashed_amount),
      issued_amount: numeric(item.issued_amount ?? item.invoiced_amount),
      allocation_amount: numeric(Object.hasOwn(item, "allocation_amount") ? item.allocation_amount : allocation?.amount ?? item.current_invoice_amount ?? item.invoice_applied_amount ?? item.amount),
    };
  });
}

export function invoiceObjectFees(record) {
  return invoiceObjectRows(record).filter((row) => Number.isInteger(row.fee_id) && row.fee_id > 0).map((row) => ({
    id: row.fee_id, module: "finance", serial_no: row.fee_no || "", title: row.case_title || row.case_name || "",
    customer: row.customer || record.customer, owner: "", status: "", data: {
      ...row, amount: row.fee_amount, invoice_amount: row.issued_amount, invoiced_amount: row.issued_amount,
      contract_id: row.contract_record_id ?? row.contract_id,
      case_id: row.case_record_id ?? row.case_id,
    },
  }));
}

export function invoiceEditValues(record) {
  const data = record?.data || {};
  const objects = invoiceObjectRows(record);
  const ids = objects.length ? objects.map((row) => row.fee_id) : rows(data.case_fee_ids).map(Number);
  return { ...data, customer: record.customer || data.customer,
    case_fee_ids: ids,
    service_items: invoiceServiceRows(record).map(({ key, ...row }) => row),
    case_fee_allocations: objects.map((row) => ({ fee_id: row.fee_id, amount: row.allocation_amount })),
  };
}

export async function fetchInvoiceRecord(client, id) {
  const { data } = await client.get(`/finance/invoices/${id}`);
  if (!data || data.module !== "invoice" || String(data.id) !== String(id)) throw new Error("发票详情记录不匹配");
  return data;
}
