const contractBody = (contract) => String(contract?.data?.contract_body || "律所").trim();

export const defaultCaseFeeContractId = (contracts, sourceCase, expenseScope) => {
  if (!["律所", "平台"].includes(expenseScope)) return undefined;
  const data = sourceCase?.data || {};
  const candidates = contracts.filter((contract) => contract.customer === sourceCase?.customer
    && contractBody(contract) === expenseScope);
  const linkedId = Number(data.contract_record_id || data.contract_id || 0);
  // 已有明确 ID 时只认该记录，不能改选同客户的其他合同。
  if (linkedId) return candidates.some((contract) => contract.id === linkedId) ? linkedId : undefined;
  const number = String(data.contract_no || "").trim();
  const matches = number ? candidates.filter((contract) => contract.serial_no === number) : [];
  return matches.length === 1 ? matches[0].id : undefined;
};

export const buildCaseFeeContractOptions = (contracts, sourceCase, editingFee, expenseScope = "") => {
  const customer = String(editingFee?.customer || sourceCase?.customer || "").trim();
  const scopedBody = ["律所", "平台"].includes(String(expenseScope).trim())
    ? String(expenseScope).trim()
    : "";
  const options = contracts
    .filter((contract) => (!customer || contract.customer === customer) && (!scopedBody || contractBody(contract) === scopedBody))
    .map((contract) => ({ value: contract.id, label: `${contract.serial_no}｜${contract.title}` }));

  const linkedId = Number(
    editingFee?.data?.contract_record_id
      || editingFee?.data?.contract_id
      || sourceCase?.data?.contract_record_id
      || sourceCase?.data?.contract_id,
  );
  if (!linkedId || options.some((option) => option.value === linkedId)) return options;

  const linkedContract = contracts.find((contract) => contract.id === linkedId);
  if (scopedBody && contractBody(linkedContract) !== scopedBody) return options;
  const contractNo = String(
    editingFee?.data?.contract_no
      || sourceCase?.data?.contract_no
      || linkedContract?.serial_no
      || "",
  ).trim();
  const contractTitle = String(
    editingFee?.data?.contract_title
      || sourceCase?.data?.contract_title
      || linkedContract?.title
      || "",
  ).trim();
  const label = [contractNo, contractTitle].filter(Boolean).join("｜") || `合同 ${linkedId}`;
  return [{ value: linkedId, label }, ...options];
};
