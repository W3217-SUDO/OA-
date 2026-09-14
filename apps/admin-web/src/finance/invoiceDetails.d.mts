import type { Fee } from "./types";
export type InvoiceServiceRow = Record<string, any> & { key: string; service_name?: string; quantity?: number; unit_price?: number | null; amount?: number | null; tax_rate?: number; tax_amount?: number | null };
export type InvoiceObjectRow = Record<string, any> & { key: string; fee_id: number; fee_amount: number | null; received_amount: number | null; issued_amount: number | null; allocation_amount: number | null };
export function invoiceServiceRows(record: any): InvoiceServiceRow[];
export function invoiceObjectRows(record: any): InvoiceObjectRow[];
export function invoiceObjectFees(record: any): Fee[];
export function invoiceEditValues(record: any): Record<string, any> & { case_fee_ids: number[]; case_fee_allocations: Array<{ fee_id: number; amount: number | null }> };
export function fetchInvoiceRecord(client: { get: (url: string) => Promise<{ data: any }> }, id: number): Promise<Fee>;
