const contractBody = (contract) => String(contract?.data?.contract_body || "律所").trim();

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
