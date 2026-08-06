export type CaseContractOptionSource = {
  id: number;
  serial_no: string;
  customer: string;
  title: string;
  owner?: string;
  owner_display_name?: string;
  data?: {
    source_person?: string;
    source_person_display_name?: string;
  };
};

export function resolveCaseSourcePerson(contract: CaseContractOptionSource | null | undefined): string {
  if (!contract) return "";
  return String(
    contract.data?.source_person_display_name
      || contract.owner_display_name
      || contract.data?.source_person
      || contract.owner
      || "",
  ).trim();
}

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
