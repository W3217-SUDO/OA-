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
  "claimed_at",
  "released_at",
  "recycled_at",
  "restored_at",
  "contract_count",
  "civil_case_count",
  "contact_count",
  "customer_guid",
  "event_history",
])

export const filterCustomerPatchData = (data = {}) =>
  Object.fromEntries(Object.entries(data).filter(([key]) => !CUSTOMER_PATCH_SERVER_FIELDS.has(key)))
