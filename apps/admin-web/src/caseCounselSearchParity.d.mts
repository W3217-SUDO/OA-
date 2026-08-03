export type CaseCounselSearchScope = 'mine' | 'department' | 'company';

export type CaseCounselSearchValues = {
  customer?: unknown;
  serial_no?: unknown;
  keyword?: unknown;
  counsel_range?: unknown;
  counsel_start?: unknown;
  counsel_end?: unknown;
  counsel_type?: unknown;
  status?: unknown;
  case_status?: unknown;
  handling_lawyer?: unknown;
  assistant?: unknown;
  document_name?: unknown;
  sort_order?: unknown;
};

export type CaseCounselSearchPayload = {
  scope: CaseCounselSearchScope;
  customer: string;
  serial_no: string;
  keyword: string;
  counsel_start: string | null;
  counsel_end: string | null;
  counsel_type: string;
  case_status: string;
  handling_lawyer: string;
  assistant: string;
  document_name: string;
  sort_order: 'updated_desc' | 'case_no_asc' | 'case_no_desc';
  page: number;
  page_size: number;
  [key: string]: unknown;
};

export function buildCaseCounselSearchPayload(
  values?: CaseCounselSearchValues,
  scope?: unknown,
  page?: unknown,
  pageSize?: unknown,
  extra?: Record<string, unknown>,
): CaseCounselSearchPayload;
