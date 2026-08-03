export type IncomingPaymentPresentation = {
  sequenceNo: string; receivedDate: string; bankReference: string; amount: number;
  officialAmount: number; agencyAmount: number; otherAmount: number; paymentMethod: string; claimant: string;
};
export type InvoicePresentation = {
  applicationNo: string; invoiceNo: string; invoiceDate: string; amount: number;
  officialAmount: number; agencyAmount: number; otherAmount: number; status: string; remark: string; lineThrough: boolean;
};
export type PaidPresentation = {
  applicationNo: string; applicant: string; pendingAmount: number; paymentDate: string; packageNo: string;
  paidAmount: number; paymentType: string; officialAmount: number; otherAmount: number; lineThrough: boolean;
};
export declare const normalizeIncomingPayment: (row?: unknown) => IncomingPaymentPresentation;
export declare const normalizeInvoiceObject: (row?: unknown) => InvoicePresentation;
export declare const normalizePaidObject: (row?: unknown) => PaidPresentation;
export declare const contractObjectActionPolicy: (status?: string) => { canEdit: boolean; canDelete: boolean; canLog: boolean };
