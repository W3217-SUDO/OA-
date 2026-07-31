export type CaseContractOptionSource = {
  id: number;
  serial_no: string;
  customer: string;
  title: string;
};

export function buildCaseContractOptions(
  contracts: CaseContractOptionSource[],
  contractPrefill: CaseContractOptionSource | null,
) {
  const rows = [...contracts];
  if (contractPrefill && !rows.some((row) => row.id === contractPrefill.id)) {
    rows.unshift(contractPrefill);
  }
  return rows.map((row) => ({
    value: row.id,
    label: `${row.serial_no}｜${row.customer}｜${row.title}`,
  }));
}
