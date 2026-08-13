export type CustomerListSummary = {
  agency_fee_due: number;
  official_fee_unreceived: number;
  total_paid_case_office_fee_amount: number;
  total_cashed_case_office_fee_amount: number;
  total_un_cashed_case_office_fee_amount: number;
  total_deficit_case_office_fee_amount: number;
  total_case_non_office_fee_amount: number;
  total_cashed_case_non_office_fee_amount: number;
  total_un_cashed_case_non_office_fee_amount: number;
  total_case_commission_fee_amount: number;
  total_cashed_case_commission_fee_amount: number;
  total_paid_case_commission_fee_amount: number;
  total_un_paid_case_commission_fee_amount: number;
  total_invoiced_amount: number;
  total_invoice_over_amount: number;
  total_un_invoiced_amount: number;
};

export const CUSTOMER_LIST_PAGE_SIZES: readonly number[];
export const CUSTOMER_EVENT_MAX_LENGTH: number;

export const CUSTOMER_SUMMARY_FIELDS: readonly string[];
export const normalizeCustomerSummary: (
  summary?: Record<string, unknown>,
) => CustomerListSummary;
export const CUSTOMER_PATCH_SERVER_FIELDS: ReadonlySet<string>;
export const filterCustomerPatchData: (
  data?: Record<string, unknown>,
) => Record<string, unknown>;
export const synchronizeCustomerSource: (
  data?: Record<string, unknown>,
  customerSource?: unknown,
) => Record<string, unknown>;
export const normalizeSharedObjectValues: (
  values?: unknown,
) => string[];
export const buildContactStatusPatch: (
  contact?: unknown,
  action?: string,
) => Record<string, boolean>;
export const buildContactStatusRequest: (
  customerId?: unknown,
  contactId?: unknown,
  contact?: unknown,
  action?: string,
) => { method: "patch"; url: string; data: Record<string, boolean> } | null;
export const runContactStatusUpdate: (
  request: { method: "patch"; url: string; data: Record<string, boolean> } | null,
  patch: (url: string, data: Record<string, boolean>) => Promise<unknown>,
  refreshDetail: () => Promise<unknown>,
  reloadList: () => Promise<unknown>,
) => Promise<boolean>;
export const getCustomerGuid: (customer?: unknown) => string;
export const buildCustomerEventListPath: (customerGuid?: unknown) => string | null;
export const buildCustomerEventRequest: (
  customerGuid?: unknown,
  content?: unknown,
) => { method: "post"; url: string; data: { action: string; comment: string } } | null;
export const buildCustomerActionRequest: (
  customerId?: unknown,
  action?: string,
  comment?: unknown,
) => { method: "post"; url: string; data: { comment: string } } | null;
export const buildCustomerActionConfirmation: (
  action?: string,
  title?: unknown,
) => { action: string; title: string; danger: boolean; requiresConfirm: boolean } | null;
export const getCustomerActionMessage: (action?: string, success?: boolean) => string;
export const buildCustomerListParams: (options?: {
  scope?: unknown; keyword?: unknown; customerType?: unknown; manager?: unknown; page?: unknown; pageSize?: unknown;
}) => Record<string, unknown>;
export const normalizeCustomerListPagination: (
  total?: unknown, page?: unknown, pageSize?: unknown,
) => { page: number; pageSize: number; lastPage: number };
export const buildCustomerContactListRequest: (
  customerId?: unknown, page?: unknown, pageSize?: unknown,
) => { method: "get"; url: string; params: { page: number; page_size: number } } | null;
export const normalizeCustomerContactPage: (payload?: unknown) => {
  items: any[]; total: number; page: number; pageSize: number;
};
export const buildCustomerDocumentUploadFields: (options?: {
  customerId?: unknown; customerGuid?: unknown; category?: unknown; remark?: unknown; isLicense?: boolean;
}) => Record<string, string>;
export const getCustomerDocumentUploadError: (error?: unknown) => string;
export const isCustomerDetailManageable: (customer?: unknown, profile?: unknown) => boolean;
export const buildCustomerDetailReturnState: (options?: {
  scope?: unknown; page?: unknown; pageSize?: unknown; keyword?: unknown; managerKeyword?: unknown;
}) => { scope: string; page: number; pageSize: number; keyword: string; managerKeyword: string };
export const buildCustomerFileListPath: (customerGuid?: unknown) => string | null;
export const buildCustomerFileDownloadPath: (
  customerGuid?: unknown,
  attachmentId?: unknown,
) => string | null;
export const isCustomerRegistrationAddressSafe: (value?: unknown) => boolean;
export const isCustomerPostalCodeSafe: (value?: unknown) => boolean;
