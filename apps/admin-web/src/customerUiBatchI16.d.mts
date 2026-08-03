export function normalizeCustomerCollectionItems(payload: unknown): unknown[]
export function normalizeCustomerEventItems(payload: unknown): Array<Record<string, unknown>>
export function normalizeCustomerAttachmentItems(payload: unknown): Array<Record<string, unknown>>
export function normalizeCustomerSharedObjectItems(payload: unknown): string[]
export function normalizeCustomerHistoryItems(payload: unknown): Array<Record<string, unknown>>
export function assertCustomerCollectionSuccess(payload: unknown): unknown
export function getCustomerResponseMessage(error: unknown, fallback?: string): string
export class CustomerCollectionResponseError extends Error {
  code: string
}
