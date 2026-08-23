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

export type CaseContractContext = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  customer_id: number;
  customer_no: string;
  at: number;
};

type CaseContractContextSource = CaseContractOptionSource & {
  data?: CaseContractOptionSource["data"] & {
    customer_id?: unknown;
    customer_no?: unknown;
  };
};

type CaseContractStorage = Pick<Storage, "setItem">;

export const CASE_CONTRACT_CONTEXT_KEY = "sunhold:case-contract-context";

// Browser context improves the workflow but never replaces server-side checks.
export function buildCaseContractContext(contract: CaseContractContextSource, now: () => number = Date.now): CaseContractContext | null {
  const id = Number(contract.id || 0);
  const serialNo = String(contract.serial_no || "").trim();
  const customer = String(contract.customer || "").trim();
  if (!id || !serialNo || !customer) return null;
  return {
    id,
    serial_no: serialNo,
    title: String(contract.title || "").trim(),
    customer,
    customer_id: Number(contract.data?.customer_id || 0),
    customer_no: String(contract.data?.customer_no || "").trim(),
    at: now(),
  };
}

export function rememberCaseContractContext(storage: CaseContractStorage, context: CaseContractContext): void {
  storage.setItem(CASE_CONTRACT_CONTEXT_KEY, JSON.stringify(context));
}

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
