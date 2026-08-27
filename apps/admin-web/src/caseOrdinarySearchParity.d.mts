export type CaseOrdinarySearchScope = "mine" | "department" | "company";

export type CaseOrdinarySearchValues = Record<string, unknown> & {
  case_queue?: unknown;
  customer?: unknown;
  serial_no?: unknown;
  keyword?: unknown;
  status?: unknown;
  case_status?: unknown;
  case_statuses?: unknown;
  counsel_range?: unknown;
  counsel_start?: unknown;
  counsel_end?: unknown;
  plaintiff?: unknown;
  prosecutor?: unknown;
  defendant?: unknown;
  evidence_org?: unknown;
  notary_no?: unknown;
  hearing_lawyer?: unknown;
  investigator?: unknown;
  court?: unknown;
  source_range?: unknown;
  source_from?: unknown;
  source_to?: unknown;
  channel?: unknown;
  warehouse?: unknown;
  hearing_range?: unknown;
  hearing_from?: unknown;
  hearing_to?: unknown;
  area?: unknown;
  location?: unknown;
  log_content?: unknown;
  sort_order?: unknown;
};

export type CaseOrdinarySearchPayload = {
  scope: CaseOrdinarySearchScope;
  case_queue: string;
  case_types: string[];
  customer: string;
  serial_no: string;
  keyword: string;
  counsel_start: string | null;
  counsel_end: string | null;
  counsel_type: string;
  case_status: string;
  case_statuses: string[];
  handling_lawyer: string;
  assistant: string;
  document_name: string;
  plaintiff: string;
  prosecutor: string;
  defendant: string;
  evidence_org: string;
  notary_no: string;
  hearing_lawyer: string;
  investigator: string;
  court: string;
  source_from: string | null;
  source_to: string | null;
  channel: string;
  warehouse: string;
  hearing_from: string | null;
  hearing_to: string | null;
  area: string;
  location: string;
  log_content: string;
  sort_order: "updated_desc" | "case_no_asc" | "case_no_desc";
  page: number;
  page_size: number;
  [key: string]: unknown;
};

export type LatestRequestGuard = {
  begin(): number;
  isLatest(requestId: number): boolean;
};

export type OrdinarySearchResult = {
  items: unknown[];
  total: number;
  page: number;
  pageSize: number;
  phaseCounts: Record<string, number>;
};

export type CasePhaseListItem = { label: string; value: string; count: number };
export type CasePhaseOption = {
  name?: string;
  canonical_name?: string;
  sort_order?: number;
};
export type CasePhaseTreeItem = CasePhaseListItem & { children: CasePhaseListItem[] };

export const LEGACY_CASE_PHASE_GROUPS: string[];
export const LEGACY_PHASE_CHILDREN: Record<string, string[]>;
export function legacyCasePhaseFilterValues(phase?: unknown): string[];
export function dashboardCaseQueryForView(view?: unknown): CaseOrdinarySearchValues;

export function buildLegacyCasePhaseTree(
  items?: CasePhaseListItem[],
  catalog?: CasePhaseOption[],
  phaseCounts?: Record<string, number>,
): CasePhaseTreeItem[];

export function createLatestRequestGuard(): LatestRequestGuard;

export function normalizePhaseCounts(value?: unknown): Record<string, number>;

export function parseOrdinarySearchResult(
  data?: Record<string, unknown>,
  fallbackPage?: number,
  fallbackPageSize?: number,
): OrdinarySearchResult;

export function buildCaseOrdinarySearchPayload(
  values?: CaseOrdinarySearchValues,
  scope?: unknown,
  caseTypes?: unknown,
  page?: unknown,
  pageSize?: unknown,
): CaseOrdinarySearchPayload;

export function ordinaryCaseTypesForView(view?: unknown): string[];
export function ordinaryCaseQueueForView(view?: unknown): string;
export function ordinaryCustomerIdForView(view?: unknown): number;
