import { getCustomerResponseMessage } from "./customerUiBatchI16.mjs"

const isObject = (value) => Boolean(value && typeof value === "object" && !Array.isArray(value))

export class CustomerMutationResponseError extends Error {
  constructor(message) {
    super(message)
    this.name = "CustomerMutationResponseError"
    this.code = "CUSTOMER_MUTATION_FAILURE"
  }
}

export const assertCustomerMutationSuccess = (payload) => {
  let value = payload
  for (let depth = 0; depth < 3; depth += 1) {
    if (!isObject(value)) return payload
    if (value.IsSuccess === false || value.isSuccess === false || value.ok === false) {
      throw new CustomerMutationResponseError(getCustomerResponseMessage(value, "客户操作失败"))
    }
    const nested = value.data ?? value.Data
    if (nested === undefined) return payload
    value = nested
  }
  return payload
}

export const getCustomerMutationErrorMessage = (error, fallback = "客户操作失败") =>
  getCustomerResponseMessage(error, fallback)
