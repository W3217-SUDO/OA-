import { filterContractLinkedRows } from "./contractWorkflowPolicy.mjs";

const numeric = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
};

const normalizeLine = (line = {}) => ({
  contract_object_id: Number(line.contract_object_id || 0),
  case_record_id: Number(line.case_record_id || line.case_id || 0),
  case_no: String(line.case_no || "").trim(),
  fee_type: String(line.fee_type || "").trim(),
  requested_amount: numeric(line.requested_amount ?? line.amount),
});

const lineSummary = (lines) => lines
  .map((line) => `${line.case_no || "—"}｜${line.fee_type || "—"}｜${line.requested_amount.toFixed(2)}`)
  .join("；");

export const normalizeContractPaymentApplications = (payload = {}, contract = {}) => {
  const rows = Array.isArray(payload?.items) ? payload.items : [];
  return filterContractLinkedRows(rows, contract).map((row) => {
    const lines = Array.isArray(row?.lines) ? row.lines.map(normalizeLine) : [];
    const summary = lineSummary(lines);
    const sourceData = row?.data && typeof row.data === "object" ? row.data : {};
    const data = {
      ...sourceData,
      amount: numeric(sourceData.amount),
      signed_at: String(sourceData.signed_at || ""),
      type: String(sourceData.type || ""),
      lines,
      line_summary: summary,
    };
    return {
      ...row,
      id: Number(row?.id || 0),
      serial_no: String(row?.serial_no || ""),
      title: String(row?.title || ""),
      customer: String(row?.customer || ""),
      status: String(row?.status || ""),
      owner: String(row?.owner || ""),
      department: String(row?.department || ""),
      description: String(row?.description || ""),
      data,
      lines,
      line_summary: summary,
    };
  });
};
