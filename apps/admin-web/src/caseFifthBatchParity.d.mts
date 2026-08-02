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
