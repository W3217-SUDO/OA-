const toLowerCamel = (key) => key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())

const toPascal = (key) => {
  const lowerCamel = toLowerCamel(key)
  return lowerCamel.charAt(0).toUpperCase() + lowerCamel.slice(1)
}

export const CUSTOMER_SUMMARY_FIELDS = [
  "agency_fee_due",
  "official_fee_unreceived",
  "total_paid_case_office_fee_amount",
  "total_cashed_case_office_fee_amount",
  "total_un_cashed_case_office_fee_amount",
  "total_deficit_case_office_fee_amount",
  "total_case_non_office_fee_amount",
  "total_cashed_case_non_office_fee_amount",
  "total_un_cashed_case_non_office_fee_amount",
  "total_case_commission_fee_amount",
  "total_cashed_case_commission_fee_amount",
  "total_paid_case_commission_fee_amount",
  "total_un_paid_case_commission_fee_amount",
  "total_invoiced_amount",
  "total_invoice_over_amount",
  "total_un_invoiced_amount",
]

export const CUSTOMER_LIST_PAGE_SIZES = [10, 15, 20, 50, 100, 200]
export const CUSTOMER_EVENT_MAX_LENGTH = 1000
const CUSTOMER_ACTION_NAMES = new Set(["claim", "release", "recycle", "restore"])
const CUSTOMER_SCOPE_OMIT_MANAGER = new Set(["shared", "recent_contact", "recent_update"])

const summaryAliases = Object.fromEntries(
  CUSTOMER_SUMMARY_FIELDS.map((key) => [key, [key, toLowerCamel(key), toPascal(key)]]),
)

export const normalizeCustomerSummary = (summary = {}) => {
  const normalized = {}
  for (const key of CUSTOMER_SUMMARY_FIELDS) {
    const raw = summaryAliases[key]
      .map((alias) => summary?.[alias])
      .find((value) => value !== undefined && value !== null)
    const value = Number(raw)
    normalized[key] = Number.isFinite(value) ? value : 0
  }
  return normalized
}

export const CUSTOMER_PATCH_SERVER_FIELDS = new Set([
  "contacts",
  "notes",
  "shared_with",
  "shared_at",
  "is_shared",
  "claimed_at",
  "released_at",
  "recycled_at",
  "restored_at",
  "level_change",
  "key_change",
  "status_before_recycle",
  "recycled_by",
  "restored_by",
  "released_by",
  "claimed_by",
  "contract_count",
  "civil_case_count",
  "contact_count",
  "customer_guid",
  "event_history",
])

export const filterCustomerPatchData = (data = {}) =>
  Object.fromEntries(Object.entries(data).filter(([key]) => !CUSTOMER_PATCH_SERVER_FIELDS.has(key)))

// Customer list and detail pages historically read different source fields.
// Keep them in lockstep whenever the editable customer source changes.
export const synchronizeCustomerSource = (data = {}, customerSource = "") => {
  const source = String(customerSource ?? "").trim()
  return { ...data, customer_source: source, source_person: source }
}

export const normalizeSharedObjectValues = (values = []) => {
  if (!Array.isArray(values)) return []
  const normalized = values.map((value) => {
    if (typeof value === "string") return value.trim()
    if (!value || typeof value !== "object") return ""
    return String(
      value.StaffName ?? value.staff_name ?? value.username ?? value.value ?? "",
    ).trim()
  }).filter(Boolean)
  return [...new Set(normalized)]
}

export const buildContactStatusPatch = (contact, action) => {
  if (!contact || typeof contact !== "object") return {}
  if (action === "primary") return { is_primary: true }
  if (action === "active") return { is_valid: true }
  return {}
}

export const buildContactStatusRequest = (customerId, contactId, contact, action) => {
  const patch = buildContactStatusPatch(contact, action)
  if (!customerId || !contactId || !Object.keys(patch).length) return null
  return {
    method: "patch",
    url: `/customers/${customerId}/contacts/${contactId}/status`,
    data: patch,
  }
}

export const runContactStatusUpdate = async (request, patch, refreshDetail, reloadList) => {
  if (!request) return false
  await patch(request.url, request.data)
  await refreshDetail()
  await reloadList()
  return true
}

export const getCustomerGuid = (customer = {}) => {
  const topLevel = String(customer?.customer_guid ?? "").trim()
  return topLevel || String(customer?.data?.customer_guid ?? "").trim()
}

const customerGuidPath = (customerGuid, suffix) => {
  const guid = String(customerGuid ?? "").trim()
  return guid ? `/customers/guid/${encodeURIComponent(guid)}${suffix}` : null
}

export const buildCustomerEventListPath = (customerGuid) =>
  customerGuidPath(customerGuid, "/events")

export const buildCustomerEventRequest = (customerGuid, content) => {
  const path = buildCustomerEventListPath(customerGuid)
  const comment = String(content ?? "").trim()
  if (!path || !comment || comment.length > CUSTOMER_EVENT_MAX_LENGTH) return null
  return {
    method: "post",
    url: path,
    data: { action: "客户注意事项", comment },
  }
}

export const buildCustomerActionRequest = (customerId, action, comment = "") => {
  const id = String(customerId ?? "").trim()
  if (!id || Number(id) <= 0 || !CUSTOMER_ACTION_NAMES.has(action)) return null
  return {
    method: "post",
    url: `/customers/${encodeURIComponent(id)}/${action}`,
    data: { comment: String(comment ?? "").trim() },
  }
}

export const buildCustomerActionConfirmation = (action, title = "") => {
  if (!CUSTOMER_ACTION_NAMES.has(action)) return null
  return {
    action,
    title: String(title ?? ""),
    danger: action === "recycle",
    requiresConfirm: true,
  }
}

const CUSTOMER_ACTION_MESSAGES = {
  claim: ["客户领取成功", "领取失败"],
  release: ["已释放到公海", "释放失败"],
  recycle: ["已移入回收站", "删除失败"],
  restore: ["客户已恢复", "恢复失败"],
}

export const getCustomerActionMessage = (action, success = true) =>
  CUSTOMER_ACTION_MESSAGES[action]?.[success ? 0 : 1] || (success ? "操作成功" : "操作失败")

export const buildCustomerListParams = ({
  scope = "company",
  keyword = "",
  customerType = "客户",
  manager = "",
  page = 1,
  pageSize = 15,
} = {}) => {
  const normalizedPageSize = CUSTOMER_LIST_PAGE_SIZES.includes(Number(pageSize)) ? Number(pageSize) : 15
  const normalizedPage = Number.isInteger(Number(page)) && Number(page) > 0 ? Number(page) : 1
  const normalizedScope = String(scope ?? "").trim()
  const params = {
    scope: normalizedScope,
    customer_name: String(keyword ?? "").trim(),
    customer_type: String(customerType ?? "客户").trim() || "客户",
    page: normalizedPage,
    page_size: normalizedPageSize,
  }
  if (!CUSTOMER_SCOPE_OMIT_MANAGER.has(normalizedScope)) params.manager = String(manager ?? "").trim()
  return params
}

export const normalizeCustomerListPagination = (total = 0, page = 1, pageSize = 15) => {
  const safeTotal = Math.max(0, Number(total) || 0)
  const safePageSize = CUSTOMER_LIST_PAGE_SIZES.includes(Number(pageSize)) ? Number(pageSize) : 15
  const lastPage = Math.max(1, Math.ceil(safeTotal / safePageSize))
  const safePage = Math.min(Math.max(1, Number(page) || 1), lastPage)
  return { page: safePage, pageSize: safePageSize, lastPage }
}

export const buildCustomerContactListRequest = (customerId, page = 1, pageSize = 15) => {
  const id = String(customerId ?? "").trim()
  if (!id || Number(id) <= 0) return null
  const pagination = normalizeCustomerListPagination(Number.MAX_SAFE_INTEGER, page, pageSize)
  return {
    method: "get",
    url: `/customers/${encodeURIComponent(id)}/contacts`,
    params: { page: pagination.page, page_size: pagination.pageSize },
  }
}

export const normalizeCustomerContactPage = (payload = {}) => {
  const items = Array.isArray(payload?.items) ? payload.items : []
  const total = Math.max(items.length, Number(payload?.total) || 0)
  const pageSize = CUSTOMER_LIST_PAGE_SIZES.includes(Number(payload?.page_size)) ? Number(payload.page_size) : 15
  const page = Math.max(1, Number(payload?.page) || 1)
  return { items, total, page, pageSize }
}

export const buildCustomerDocumentUploadFields = ({ customerId, customerGuid, category, remark, isLicense = false } = {}) => ({
  record_id: String(customerId ?? "").trim(),
  customer_guid: String(customerGuid ?? "").trim(),
  category: String(category ?? "客户资料").trim() || "客户资料",
  remark: String(remark ?? "").trim(),
  is_license: String(Boolean(isLicense)),
})

export const getCustomerDocumentUploadError = (error = {}) => {
  const status = Number(error?.response?.status)
  if (status === 413) return "文件不能超过 20MB"
  if (error?.code === "empty") return "文件没有任何内容"
  if (error?.code === "type") return "上传文件类型不正确"
  return error?.response?.data?.detail || "上传失败"
}

export const isCustomerDetailManageable = (customer = {}, profile = {}) => {
  const username = String(profile?.username ?? "")
  if (!username) return false
  if (profile?.role === "admin" || username === "admin") return true
  if (String(customer?.owner ?? "") === username) return true
  if (Array.isArray(customer?.data?.customer_managers) && customer.data.customer_managers.includes(username)) return true
  return profile?.role === "manager" && String(customer?.department ?? "") === String(profile?.department ?? "")
}

export const buildCustomerDetailReturnState = ({ scope, page = 1, pageSize = 15, keyword = "", managerKeyword = "" } = {}) => ({
  scope: String(scope ?? ""),
  page: Math.max(1, Number(page) || 1),
  pageSize: CUSTOMER_LIST_PAGE_SIZES.includes(Number(pageSize)) ? Number(pageSize) : 15,
  keyword: String(keyword ?? ""),
  managerKeyword: String(managerKeyword ?? ""),
})

export const buildCustomerFileListPath = (customerGuid) =>
  customerGuidPath(customerGuid, "/files")

export const buildCustomerFileDownloadPath = (customerGuid, attachmentId) => {
  const path = customerGuidPath(customerGuid, `/files/${attachmentId}/download`)
  return path && attachmentId ? path : null
}

export const isCustomerRegistrationAddressSafe = (value) =>
  !/[\\'"<>|]/.test(String(value ?? ""))

export const isCustomerPostalCodeSafe = (value) =>
  !/[-—\\'"<>|]/.test(String(value ?? ""))
