export const CUSTOMER_CONTACT_FORM_DEFAULTS: {
  readonly contact_status: "正常联系";
  readonly is_valid: true;
  readonly is_primary: false;
  readonly remark: "";
};
export const CUSTOMER_DOCUMENT_FORM_DEFAULTS: {
  readonly category: "客户资料";
  readonly remark: "";
};
export const getCustomerAttachmentDate: (attachment?: unknown) => string;
export const canDeleteCustomerAttachment: (canManageCurrentCustomer?: unknown) => boolean;
