// Customer batch 8 UI policies derived from CRM.Customer.js and the existing
// customer upload/status contracts. These functions are deliberately pure so
// the page and runtime tests exercise the same behavior.
export const OLD_CUSTOMER_EMAIL_PATTERN = /^\w+(([-\w])|(\.\w+))*\@[A-Za-z0-9]+((\.|-)[A-Za-z0-9]+)*\.[A-Za-z0-9]+$/

const CUSTOMER_DOCUMENT_TYPES = new Set([".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".png", ".jpg", ".jpeg", ".zip", ".rar"])
const CUSTOMER_PHOTO_TYPES = new Set([".jpg", ".jpeg", ".png", ".gif", ".webp"])
const CUSTOMER_DOCUMENT_MAX_BYTES = 20 * 1024 * 1024
const CUSTOMER_PHOTO_MAX_BYTES = 10 * 1024 * 1024

const fileSuffix = (file) => {
  const name = String(file?.name ?? "")
  const index = name.lastIndexOf(".")
  return index >= 0 ? name.slice(index).toLowerCase() : ""
}

const validateFile = (file, allowed, maxBytes) => {
  if (!file) return { ok: false, code: "empty" }
  if (Number(file.size) <= 0) return { ok: false, code: "empty" }
  if (Number(file.size) > maxBytes) return { ok: false, code: "size" }
  if (!allowed.has(fileSuffix(file))) return { ok: false, code: "type" }
  return { ok: true }
}

export const normalizeCustomerRecipients = (value) => {
  const values = Array.isArray(value) ? value : [value]
  return [...new Set(values.flatMap((item) => String(item ?? "").split(/[,，]/).map((part) => part.trim()).filter(Boolean)))]
}

export const buildCustomerShareRequest = (customerId, recipients, comment = "") => {
  const id = String(customerId ?? "").trim()
  const normalized = normalizeCustomerRecipients(recipients)
  if (!id || !normalized.length) return null
  return {
    method: "post",
    url: `/customers/${encodeURIComponent(id)}/share`,
    data: { recipients: normalized, comment: String(comment ?? "").trim() },
  }
}

export const normalizeCustomerManager = (value) => String(value ?? "").trim()

export const matchesDirectoryOption = (inputValue, option = {}) => {
  const needle = String(inputValue ?? "").trim().toLowerCase()
  if (!needle) return true
  const text = `${option.value ?? ""} ${option.label ?? ""}`.toLowerCase()
  return text.includes(needle)
}

export const buildCustomerManagerRequest = (customerId, manager) => {
  const id = String(customerId ?? "").trim()
  const normalized = normalizeCustomerManager(manager)
  if (!id || !normalized) return null
  return {
    method: "put",
    url: `/customers/${encodeURIComponent(id)}/managers`,
    data: { managers: [normalized] },
  }
}

export const validateCustomerUploadFile = (file) => validateFile(file, CUSTOMER_DOCUMENT_TYPES, CUSTOMER_DOCUMENT_MAX_BYTES)
export const validateCustomerPhotoFile = (file) => validateFile(file, CUSTOMER_PHOTO_TYPES, CUSTOMER_PHOTO_MAX_BYTES)

export const buildCustomerContactStatusRequest = (customerId, contactId, action) => {
  const customer = String(customerId ?? "").trim()
  const contact = String(contactId ?? "").trim()
  const patch = action === "primary"
    ? { is_primary: true }
    : action === "active"
      ? { is_valid: true }
      : action === "inactive"
        ? { is_valid: false }
        : null
  if (!customer || !contact || !patch) return null
  return {
    method: "patch",
    url: `/customers/${encodeURIComponent(customer)}/contacts/${encodeURIComponent(contact)}/status`,
    data: patch,
  }
}

export const getCustomerPermissionMessage = (error = {}) =>
  Number(error?.response?.status) === 403 ? "无权限执行该客户操作" : ""

export const getCustomerMutationErrorMessage = (error = {}, fallback = "操作失败") =>
  error?.response?.data?.detail || getCustomerPermissionMessage(error) || fallback
