import { normalizeSharedObjectValues } from "./customerParity.mjs"

const isObject = (value) => Boolean(value && typeof value === "object" && !Array.isArray(value))

const firstDefined = (value, keys) => {
  for (const key of keys) {
    if (value?.[key] !== undefined && value?.[key] !== null) return value[key]
  }
  return undefined
}

const envelopeFailureValue = (value) => {
  if (!isObject(value)) return undefined
  if (value.IsSuccess === false || value.isSuccess === false || value.ok === false) return value
  return undefined
}

export const getCustomerResponseMessage = (error, fallback = "客户数据加载失败") => {
  const sources = [error?.response?.data, error]
  for (const source of sources) {
    const message = firstDefined(source, ["Message", "message", "detail", "error"])
    if (typeof message === "string" && message.trim()) return message.trim()
  }
  return String(fallback)
}

export class CustomerCollectionResponseError extends Error {
  constructor(message) {
    super(message)
    this.name = "CustomerCollectionResponseError"
    this.code = "CUSTOMER_COLLECTION_FAILURE"
  }
}

export const assertCustomerCollectionSuccess = (payload) => {
  let value = payload
  for (let depth = 0; depth < 3; depth += 1) {
    if (Array.isArray(value) || !isObject(value)) return payload
    const failure = envelopeFailureValue(value)
    if (failure) {
      throw new CustomerCollectionResponseError(getCustomerResponseMessage(failure, "客户数据加载失败"))
    }
    const nested = firstDefined(value, ["data", "Data"])
    if (nested === undefined) return payload
    value = nested
  }
  return payload
}

export const normalizeCustomerCollectionItems = (payload) => {
  assertCustomerCollectionSuccess(payload)
  let value = payload
  for (let depth = 0; depth < 3; depth += 1) {
    if (Array.isArray(value)) return value
    if (!isObject(value)) return []
    const nested = firstDefined(value, ["data", "Data", "items", "Items"])
    if (nested === undefined) return []
    value = nested
  }
  return Array.isArray(value) ? value : []
}

const withAliases = (item, aliases) => {
  if (!isObject(item)) return null
  const normalized = { ...item }
  for (const [canonical, keys] of Object.entries(aliases)) {
    const value = firstDefined(item, keys)
    if (value !== undefined) normalized[canonical] = value
  }
  return normalized
}

export const normalizeCustomerEventItems = (payload) =>
  normalizeCustomerCollectionItems(payload)
    .map((item) => withAliases(item, {
      id: ["id", "Id", "event_id", "EventId"],
      content: ["content", "Content", "comment", "Comment"],
      operator: ["operator", "Operator", "operate_user", "OperateUser"],
      created_at: ["created_at", "CreatedAt", "operate_time", "OperateTime"],
      action: ["action", "Action"],
    }))
    .filter(Boolean)

export const normalizeCustomerAttachmentItems = (payload) =>
  normalizeCustomerCollectionItems(payload)
    .map((item) => withAliases(item, {
      id: ["id", "Id", "attachment_id", "AttachmentId", "customer_file_id", "CustomerFileId"],
      original_name: ["original_name", "OriginalName", "file_name", "FileName"],
      document_date: ["document_date", "DocumentDate", "file_date", "FileDate"],
      created_at: ["created_at", "CreatedAt", "create_time", "CreateTime"],
      uploader: ["uploader", "Uploader", "file_uploader", "FileUploader"],
      category: ["category", "Category"],
      is_license: ["is_license", "IsLicense", "isLicense"],
      size: ["size", "Size", "file_size", "FileSize"],
      remark: ["remark", "Remark"],
    }))
    .filter(Boolean)

export const normalizeCustomerSharedObjectItems = (payload) =>
  normalizeSharedObjectValues(normalizeCustomerCollectionItems(payload))

export const normalizeCustomerHistoryItems = (payload) =>
  normalizeCustomerCollectionItems(payload)
    .map((item) => withAliases(item, {
      id: ["id", "Id", "record_id", "RecordId"],
      action: ["action", "Action"],
      operator: ["operator", "Operator"],
      comment: ["comment", "Comment"],
      created_at: ["created_at", "CreatedAt", "operate_time", "OperateTime"],
    }))
    .filter(Boolean)
