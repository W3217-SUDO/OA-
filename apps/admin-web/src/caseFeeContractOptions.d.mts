type ContractOptionSource = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
};

type CaseFeeSource = {
  customer?: string;
  data?: Record<string, unknown>;
};

export function buildCaseFeeContractOptions(
  contracts: ContractOptionSource[],
  sourceCase?: CaseFeeSource | null,
  editingFee?: CaseFeeSource | null,
): Array<{ value: number; label: string }>;
