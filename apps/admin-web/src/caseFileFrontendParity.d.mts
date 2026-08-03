export type CaseFilePagination = {
  defaultPageSize: number;
  pageSizeOptions: number[];
  showSizeChanger: boolean;
  showTotal: (total: number) => string;
};

export function getCaseFilePagination(): CaseFilePagination;
export function getCaseAttachmentUploadValidationError(file: unknown): string;
export function getCaseFileRenameValidationError(nextName: unknown, currentName: unknown): string;
export function getCaseAttachmentSelectionValidationError(keys: unknown, action: unknown): string;
export function hasCaseFileTypeOption(value: unknown, options: unknown): boolean;
