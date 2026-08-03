export class CustomerMutationResponseError extends Error {
  code: string
}
export function assertCustomerMutationSuccess<T>(payload: T): T
export function getCustomerMutationErrorMessage(error: unknown, fallback?: string): string
