export const OLD_CUSTOMER_EMAIL_PATTERN: RegExp;
export const normalizeCustomerRecipients: (value?: unknown) => string[];
export const buildCustomerShareRequest: (customerId?: unknown, recipients?: unknown, comment?: unknown) => {
  method: "post"; url: string; data: { recipients: string[]; comment: string };
} | null;
export const normalizeCustomerManager: (value?: unknown) => string;
export const matchesDirectoryOption: (inputValue?: unknown, option?: { value?: unknown; label?: unknown }) => boolean;
export const buildCustomerManagerRequest: (customerId?: unknown, manager?: unknown) => {
  method: "put"; url: string; data: { managers: string[] };
} | null;
export const validateCustomerUploadFile: (file?: unknown) => { ok: boolean; code?: "empty" | "size" | "type" };
export const validateCustomerPhotoFile: (file?: unknown) => { ok: boolean; code?: "empty" | "size" | "type" };
export const buildCustomerContactStatusRequest: (customerId?: unknown, contactId?: unknown, action?: unknown) => {
  method: "patch"; url: string; data: Record<string, boolean>;
} | null;
export const getCustomerPermissionMessage: (error?: unknown) => string;
export const getCustomerMutationErrorMessage: (error?: unknown, fallback?: string) => string;
