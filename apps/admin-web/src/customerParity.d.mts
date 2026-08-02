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

export const CUSTOMER_SUMMARY_FIELDS: readonly string[];
export const normalizeCustomerSummary: (
  summary?: Record<string, unknown>,
) => CustomerListSummary;
export const CUSTOMER_PATCH_SERVER_FIELDS: ReadonlySet<string>;
export const filterCustomerPatchData: (
  data?: Record<string, unknown>,
) => Record<string, unknown>;
