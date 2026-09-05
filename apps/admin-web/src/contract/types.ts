export type Contract = {
  id: number;
  contract_guid?: string;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  owner: string;
  department: string;
  archive_status?: "归档中" | "已归档";
  archive_date?: string;
  description: string;
  data: {
    amount: number;
    signed_at: string;
    type: string;
    fee_type?: string;
    case_no?: string;
    contract_no?: string;
    source_person?: string;
    contract_body?: string;
    official_paid?: number;
    official_received?: number;
    official_unreceived?: number;
    official_loss?: number;
    agency_total?: number;
    agency_received?: number;
    agency_due?: number;
    other_total?: number;
    other_paid?: number;
    other_due?: number;
    invoice_opened?: number;
    invoice_should?: number;
    invoice_excess?: number;
    external_contract_no?: string;
    external_contract_numbers?: string[];
    pending_change?: { status?: string; reason?: string; changes?: Change["changes"] };
    end_date?: string;
    approval_count?: number;
    customer_manager?: string;
    customer_id?: number;
    customer_no?: string;
    customer_name?: string;
    submitted_at?: string;
    submitted_by?: string;
    submit_comment?: string;
    seal_application_id?: number;
    seal_application_no?: string;
    current_approver?: string;
    approval_capabilities?: {
      can_approve_current?: boolean;
      current_approver?: string;
    };
    sync_seal?: boolean;
    sync_seal_submitted_at?: string;
    /** 合同审批通过时，是否仍需在用印中心补传真实用印文件。 */
    sync_seal_file_required?: boolean;
    contract_guid?: string;
    contractGuid?: string;
  };
};

export type Step = {
  id: number;
  step_order: number;
  approver: string;
  approver_display_name?: string;
  status: string;
  comment: string;
  acted_at: string | null;
};

export type Change = {
  id: number;
  change_type: string;
  reason: string;
  operator: string;
  created_at: string;
  changes: { field: string; label: string; before: any; after: any }[];
};

export type Profile = {
  username: string;
  display_name: string;
  department: string;
  role: string;
  menu_keys?: string[];
  action_keys?: string[];
  menuKeys?: string[];
  actionKeys?: string[];
};

export type ContractWorkflowCapabilities = {
  canCreate: boolean;
  canEdit: boolean;
  canSubmit: boolean;
  canChange: boolean;
  canReviewChange: boolean;
  canPayment: boolean;
  canInvoice: boolean;
  canArchive: boolean;
  canOpenApproval: boolean;
  canApprove: boolean;
};

export type DirectoryUser = { username: string; display_name: string; department: string; is_active: boolean; role?: string; position?: string; staff_role?: string; job_permissions?: string[]; can_approve_contract?: boolean };

export type ApproverSetting = { username: string; display_name: string; display_name_valid?: boolean; department: string; position: string; selected: boolean };

export type Attachment = { id: number; original_name: string; category: string; size: number; created_at: string; uploader?: string; uploader_display_name?: string };

export type LegacyHistoricalAttachment = {
  id: number; legacy_file_id: number; legacy_file_guid: string; legacy_parent_no: string;
  file_name: string; legacy_declared_size_bytes: number | null; legacy_file_path: string;
  legacy_is_active: boolean; physical_exists: boolean; recovery_status: string; quarantine_reasons: string[];
  download_available: false; preview_available: false; download_reason: string;
};

export type AttachmentPreview = { name: string; kind: "image" | "pdf" | "text" | "docx"; url?: string; text?: string };

export type HistoryEvent = { id: number; action: string; from_status: string; to_status: string; operator: string; comment: string; created_at: string };

export type ContractEvent = { id: number; contract_record_id: number; content: string; operator: string; created_at: string; contract_guid?: string };

export type SealAsset = { id: number; code: string; name: string; seal_type: string; status: string };

export type CustomerRef = { id: number; serial_no: string; title: string; owner: string; data: { customer_managers?: string[] } };

export type ContractPaymentCandidate = { contract_object_id:number; case_record_id:number; case_no:string; case_title:string; fee_type:string; contract_amount:number; reserved_amount:number; remaining_amount:number; remark:string };

export type PaymentTypeOption = { value:number; label:string; id:number; code:string; name:string; nature:string; payee:string; account_bank:string; account:string };

export type ContractArchiveSubject = { contract_object_id:number; case_record_id:number; case_no:string; case_title:string; case_fee_ids:number[]; fee_type:string; contract_amount:number; paid_amount:number; invoiced_amount:number; fee_archived:boolean; materials_ready:boolean; archive_checks:Record<string,boolean> };

export type ContractArchiveSummary = { id:number; serial_no:string; title:string; customer:string; status:string };

export type ContractObjectRow = {
  id: number;
  case_record_id: number;
  case_no: string;
  case_title: string;
  case_type: string;
  case_phase: string;
  fee_type: string;
  amount: number;
  customer_manager: string;
  remark: string;
  logs: Array<{ id: number; action: string; before: Record<string, unknown>; after: Record<string, unknown>; operator: string; created_at: string }>;
};

export type ContractObjectLog = ContractObjectRow["logs"][number];
