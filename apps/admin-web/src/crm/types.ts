export type Contact = {
  id: string;
  name: string;
  project_role: string;
  phone: string;
  office_phone: string;
  im_account: string;
  email: string;
  position: string;
  contact_status: string;
  portal_account?: string;
  portal_enabled?: boolean;
  is_valid: boolean;
  is_primary: boolean;
  remark: string;
  photo_attachment_id?: number;
  photo_original_name?: string;
};

export type Note = {
  id: string;
  type: string;
  content: string;
  operator: string;
  created_at: string;
};

export type Attachment = {
  id: number;
  category: string;
  original_name: string;
  size: number;
  uploader: string;
  remark: string;
  created_at: string;
  document_date?: string | null;
  is_license?: boolean | string | null;
  IsLicense?: boolean | string | null;
  isLicense?: boolean | string | null;
};

export type CustomerEvent = {
  id: number;
  action: string;
  operator: string;
  comment: string;
  created_at: string;
};

export type CustomerNotice = {
  id: number;
  action: string;
  comment: string;
  operator: string;
  created_at: string;
};

export type LegacyCustomerHistory = {
  coordinators: any[];
  contacts: any[];
  events: any[];
  files: any[];
  zero_baselines: { source_table: string; source_row_count: number; audit_status: string }[];
  counts: { coordinators: number; contacts: number; events: number; files: number };
};

export const EMPTY_LEGACY_CUSTOMER_HISTORY: LegacyCustomerHistory = {
  coordinators: [], contacts: [], events: [], files: [], zero_baselines: [],
  counts: { coordinators: 0, contacts: 0, events: 0, files: 0 },
};

export type Customer = {
  id: number;
  customer_guid?: string;
  serial_no: string;
  title: string;
  status: string;
  owner: string;
  department: string;
  description: string;
  created_at: string;
  updated_at: string;
  data: {
    customer_guid?: string;
    contact?: string | string[];
    contact_accounts?: string[];
    contact_account_display_names?: string[];
    contact_account_display_name?: string;
    phone?: string;
    level?: string;
    shared_with?: string[];
    contacts?: Contact[];
    notes?: Note[];
    customer_managers?: string[];
    source_person?: string;
    file_date?: string;
    last_contact_at?: string;
    last_modified_date?: string;
    contact_count?: number;
    contract_count?: number;
    civil_case_count?: number;
    ipr_case_count?: number;
    agency_fee_due?: number;
    official_fee_unreceived?: number;
    credit_code?: string;
    legal_representative?: string;
    registered_address?: string;
    invoice_title?: string;
    taxpayer_id?: string;
    invoice_address?: string;
    invoice_phone?: string;
    bank_name?: string;
    bank_account?: string;
    customer_type?: string;
    short_name?: string;
    fax?: string;
    legal_agent_id_no?: string;
    legal_agent_title?: string;
    customer_source?: string;
    customer_source_display_name?: string;
    is_shared?: string;
    is_assisted?: string;
    province?: string;
    postal_code?: string;
    patent_customer_type?: string;
    fee_reduction?: string;
    industry?: string;
    output_value?: string;
    cooperation_status?: string;
    gb_classification?: string;
    website?: string;
    organization_nature?: string;
    organization_code?: string;
    registration_region?: string;
    registration_postal_code?: string;
    registered_capital?: string;
    registration_year?: string;
    level_change?: {
      status?: string;
      from_level?: string;
      to_level?: string;
      requested_by?: string;
      review_comment?: string;
    };
    key_change?: { status?: string; before?: Record<string, string>; after?: Record<string, string> };
    portal_access?: {
      account?: string;
      enabled?: boolean;
    };
  };
};

export type Profile = {
  username: string;
  display_name: string;
  department: string;
  role?: string;
};

export type DirectoryUser = {
  username: string;
  display_name: string;
  department: string;
  account_type?: string;
  eligible_customer_person?: boolean;
};
