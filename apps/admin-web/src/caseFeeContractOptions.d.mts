type ContractOptionSource = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  data?: Record<string, unknown>;
};

type CaseFeeSource = {
  customer?: string;
  data?: Record<string, unknown>;
};

export function buildCaseFeeContractOptions(
  contracts: ContractOptionSource[],
  sourceCase?: CaseFeeSource | null,
  editingFee?: CaseFeeSource | null,
  expenseScope?: string,
): Array<{ value: number; label: string }>;
