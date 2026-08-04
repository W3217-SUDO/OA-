const text = (value) => String(value ?? "").trim();

const findById = (rows, id) =>
  rows.find((row) => Number(row?.id) === Number(id));

const caseFeeBelongsToCase = (row, caseNo) => {
  const data = row?.data || {};
  return text(data.case_no || row?.case_no) === caseNo;
};

export const buildInvoiceApplicationPayload = ({
  values = {},
  cases = [],
  contracts = [],
  caseFees = [],
}) => {
  const caseNo = text(values.case_no);
  const caseRecord = caseNo
    ? cases.find((row) => text(row?.serial_no) === caseNo)
    : null;
  if (caseNo && !caseRecord) {
    return { ok: false, error: "关联案件不存在或无权访问" };
  }

  const contractId =
    values.contract_record_id == null || values.contract_record_id === ""
      ? null
      : Number(values.contract_record_id);
  const contractRecord =
    contractId == null ? null : findById(contracts, contractId);
  if (contractId != null && !Number.isFinite(contractId)) {
    return { ok: false, error: "关联合同编号无效" };
  }
  if (contractId != null && !contractRecord) {
    return { ok: false, error: "关联合同不存在或无权访问" };
  }

  const requestedFeeIds = Array.isArray(values.case_fee_ids)
    ? values.case_fee_ids
    : values.case_fee_ids == null || values.case_fee_ids === ""
      ? []
      : [values.case_fee_ids];
  const feeIds = [...new Set(requestedFeeIds.map(Number))];
  if (feeIds.some((id) => !Number.isInteger(id) || id <= 0)) {
    return { ok: false, error: "关联费用编号无效" };
  }
  const linkedFees = feeIds.map((id) => findById(caseFees, id));
  if (
    linkedFees.some(
      (row) => !row || (caseNo && !caseFeeBelongsToCase(row, caseNo)),
    )
  ) {
    return { ok: false, error: "关联费用不存在、无权访问或不属于当前案件" };
  }

  const amount = Number(values.amount);
  if (!Number.isFinite(amount) || amount <= 0) {
    return { ok: false, error: "开票金额必须大于0" };
  }

  return {
    ok: true,
    payload: {
      ...values,
      customer: text(
        values.customer || caseRecord?.customer || contractRecord?.customer,
      ),
      case_no: caseNo,
      amount,
      contract_record_id: contractId,
      case_record_id: caseRecord?.id ?? null,
      case_fee_ids: feeIds,
    },
  };
};
