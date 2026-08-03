export const CONTRACT_OBJECT_DEFAULT_PAGE_SIZE = 10;
export const CONTRACT_OBJECT_PAGE_SIZES = [10, 15, 20, 50, 100, 200];

const numeric = (value, fallback = 0) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const compareDescending = (left, right) => numeric(right) - numeric(left);

// Legacy ContractObjects orders by CaseId then CaseOfficeFeeId, both descending.
// The local projection may expose only case_record_id/id, so id is the safe tie-breaker.
export const sortContractObjectRows = (rows = []) => [...rows].sort((left, right) => {
  const byCase = compareDescending(left?.case_record_id ?? left?.case_id, right?.case_record_id ?? right?.case_id);
  if (byCase) return byCase;
  const byOfficeFee = compareDescending(left?.case_office_fee_id ?? left?.caseOfficeFeeId, right?.case_office_fee_id ?? right?.caseOfficeFeeId);
  if (byOfficeFee) return byOfficeFee;
  return compareDescending(left?.id, right?.id);
});

// Legacy ContractObjectList orders received/invoiced/paid collections by their
// payment/invoice identity ascending before rendering the three tables.
export const sortContractRecordRows = (rows = []) => [...rows].sort((left, right) => (
  numeric(left?.id ?? left?.payment_id ?? left?.invoice_id) - numeric(right?.id ?? right?.payment_id ?? right?.invoice_id)
));

export const paginateContractObjectRows = (rows = [], current = 1, pageSize = CONTRACT_OBJECT_DEFAULT_PAGE_SIZE) => {
  const total = rows.length;
  const safePageSize = CONTRACT_OBJECT_PAGE_SIZES.includes(Number(pageSize)) ? Number(pageSize) : CONTRACT_OBJECT_DEFAULT_PAGE_SIZE;
  const pageCount = Math.max(1, Math.ceil(total / safePageSize));
  const safeCurrent = Math.min(Math.max(1, Number(current) || 1), pageCount);
  return {
    items: rows.slice((safeCurrent - 1) * safePageSize, safeCurrent * safePageSize),
    current: safeCurrent,
    pageSize: safePageSize,
    total,
  };
};
