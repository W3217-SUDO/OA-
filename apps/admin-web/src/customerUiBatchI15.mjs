export const CUSTOMER_CONTACT_FORM_DEFAULTS = {
  contact_status: "正常联系",
  is_valid: true,
  is_primary: false,
  remark: "",
}

export const CUSTOMER_DOCUMENT_FORM_DEFAULTS = {
  category: "客户资料",
  remark: "",
}

export const getCustomerAttachmentDate = (attachment = {}) =>
  String(attachment?.document_date ?? attachment?.created_at ?? "").trim()

export const canDeleteCustomerAttachment = (canManageCurrentCustomer) => Boolean(canManageCurrentCustomer)
