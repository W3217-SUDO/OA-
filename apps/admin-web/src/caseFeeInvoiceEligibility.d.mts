export type InvoiceEligibleFee = {
  id: number;
  [key: string]: unknown;
};

export type InvoiceEligibilityResult =
  | { ok: true; fee: InvoiceEligibleFee }
  | { ok: false; error: string };

export function resolveCaseFeeInvoiceEligibility(
  feeId: number,
  eligibleFees?: InvoiceEligibleFee[],
): InvoiceEligibilityResult;
