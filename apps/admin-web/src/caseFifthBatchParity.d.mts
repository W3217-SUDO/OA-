export const CASE_TASK_PAGE_SIZE_OPTIONS: number[];

export function getCaseReminderDateValidationError(
  reminderDate: unknown,
  deadline: unknown,
): string;

export type CaseTaskPagination = {
  defaultPageSize: number;
  pageSizeOptions: number[];
  showSizeChanger: boolean;
  showTotal: (total: number) => string;
};

export function getCaseTaskPagination(): CaseTaskPagination;
export function getCaseArchivePagination(view: unknown): CaseTaskPagination;
export function getCaseUnarchiveRequestValidationError(reason: unknown): string;

export type CaseFileTypeOption = {
  value: string;
  label: string;
  code?: string;
  parent_code?: string;
  options?: CaseFileTypeOption[];
};

export function buildCaseFileTypeTreeOptions(items: unknown): CaseFileTypeOption[];
export function resolveCaseFileTypeSelection(value: unknown, options: CaseFileTypeOption[]): string;
