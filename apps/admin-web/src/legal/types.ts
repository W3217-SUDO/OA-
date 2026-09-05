import type { AgentSkill } from "../agentSkillRouting";
import type { getCompanyScheduleCourtLevels } from "./constants";

export type CaseRow = {
  id: number;
  module?: string;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  owner: string;
  owner_display_name?: string;
  department: string;
  description: string;
  created_at?: string;
  data: Record<string, any>;
};

export type CaseFeeIncomingPaymentLink = {
  id: number;
  receipt_no: string;
  received_date: string;
  allocated_amount: number;
  amount: number;
  payer_name: string;
  bank_reference: string;
  status: string;
  contract_no: string;
  customer_name: string;
  payment_method: string;
  assigned_official_fee: number;
  assigned_agency_fee: number;
};

export type CasePaymentTypeOption = {
  id: number;
  code: string;
  name: string;
  nature: string;
  payee: string;
  account_bank: string;
  account: string;
};

export type PaymentTypeCreateTarget = { feeId: number; draftIndex?: number };

export type CaseCommissionPreviewRow = {
  preview_key: string;
  client_key: string;
  case_no: string;
  commission_role: string;
  commission_type: string;
  expense_subtype: string;
  employee_username: string;
  employee_display_name: string;
  base_amount: number;
  reference_commission: number;
  actual_amount: number;
  remark: string;
};

export type CaseCommissionPreview = {
  case: { id: number; serial_no: string; title: string };
  source_fee: {
    id: number;
    serial_no: string;
    amount: number;
    fee_type: string;
    refund_amount: number;
    invoice_over_amount: number;
    cost_over_amount: number;
  };
  personnel: Array<{ role: string; username: string; display_name: string }>;
  items: Omit<CaseCommissionPreviewRow, "client_key">[];
  missing_messages: string[];
};

export type CaseCommissionResult = {
  application_no: string;
  application_date: string;
  payment_items: Array<{
    record_id: number;
    application_no: string;
    payee: string;
    commission_type: string;
    amount: number;
    case_no: string;
    application_date: string;
  }>;
};

export type CaseLitigantPartyField = "plaintiffs" | "defendants" | "third_parties";

export type CaseLitigantCandidate = {
  id: number;
  serial_no: string;
  title: string;
  customer_type?: string;
};

export type CaseLitigantAgent = {
  name: string;
  law_firm: string;
  position: string;
  phone: string;
  authority: string;
};

export type CaseLitigantAgentField = "plaintiff_agents" | "defendant_agents" | "third_party_agents";

export type CaseAgentAttachment = { id: number; name: string; mime_type?: string; preview_url?: string };

export type CaseAgentDocument = { id: number; original_name: string; category?: string; source_module?: string; size?: number };

export type CaseAgentDocumentTreeNode = { key: string; title: string; selectable?: boolean; disabled?: boolean; children?: CaseAgentDocumentTreeNode[] };

export type CaseAgentMessage = {
  id?: string;
  role: "user" | "assistant";
  content: string;
  operator?: string;
  created_at?: string;
  attachments?: CaseAgentAttachment[];
};

export type CaseAgentAction = {
  id: string;
  type: string;
  summary: string;
  status: "pending" | "approved" | "rejected";
  requested_by?: string;
  requested_at?: string;
  decided_by?: string;
  decided_at?: string;
  decision_comment?: string;
};

export type CaseAgentState = {
  thread_id: string;
  messages: CaseAgentMessage[];
  pending_actions: CaseAgentAction[];
  last_response: string;
  updated_at?: string;
  active_skill?: string;
};

export type CaseAgentStatus = {
  enabled: boolean;
  ready: boolean;
  checkpoint_backend: string;
  model: string;
  model_configured: boolean;
  write_requires_approval: boolean;
  skills?: AgentSkill[];
  error?: string | null;
};

export type CasePhaseOption = { id: number; code: string; name: string; canonical_name: string; case_type?: string; parent_code?: string; sort_order?: number };

export type ParameterRelation = {
  sources: Array<{ id: number; code?: string; name?: string }>;
  targets: Array<{ id: number; code?: string; name?: string }>;
  relations: Record<string, number[]>;
};

export type CaseRelationCatalog = {
  caseTypeFileTypes: ParameterRelation;
  fileTypeFeeTypes: ParameterRelation;
  caseTypePhases: ParameterRelation;
};

export type CasePhaseListItem = { label: string; value: string; count: number };

export type CasePhaseTreeItem = CasePhaseListItem & { children: CasePhaseListItem[] };

export type CompanyScheduleCourtLevel = ReturnType<typeof getCompanyScheduleCourtLevels>[number][0];

export type ContractRow = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  owner: string;
  owner_display_name?: string;
  department: string;
  data: Record<string, any>;
};

export type Profile = {
  username: string;
  display_name: string;
  department: string;
  role?: string;
};

export type Hearing = {
  id: number;
  case_record_id: number;
  case_no: string;
  case_title: string;
  customer: string;
  weekday: string;
  hearing_date: string;
  hearing_time: string;
  court: string;
  courtroom: string;
  hearing_type: string;
  hearing_lawyer: string;
  status: string;
};

export type TaskRow = {
  id: number;
  serial_no: string;
  title: string;
  status: string;
  owner: string;
  owner_display_name?: string;
  initiator: string;
  initiator_display_name?: string;
  deadline: string;
  priority: string;
  source: string;
  creation_mode?: string;
  task_type?: string;
  case_no: string;
  days_remaining?: number | null;
  collaborators?: string[];
  collaborator_display_names?: string[];
  workflow_status?: string;
  start_at?: string;
  end_at?: string;
  created_at?: string;
  description?: string;
  department?: string;
  is_vip?: boolean;
};

export type CaseTaskHistoryItem = {
  id: number;
  action: string;
  operator: string;
  operator_display_name?: string;
  comment: string;
  from_status: string;
  to_status: string;
  created_at: string;
};

export type CaseTaskAttachment = {
  id: number;
  original_name: string;
  category: string;
  uploader: string;
  uploader_display_name?: string;
  created_at: string;
};

export type CaseTaskPageState = { items: TaskRow[]; total: number; page: number; pageSize: number; pages: number };

export type AttachmentRow = {id:number;record_id:number|null;original_name:string;category:string;uploader:string;uploader_display_name?:string;created_at:string;size:number;remark?:string;content_editable?:boolean;is_locked?:boolean};

export type CaseAssistedFee = {
  id: number;
  case_record_id: number;
  assisted_type: string;
  amount?: number | null;
  status: "待办理" | "已办理";
  request_date: string;
  request_user: string;
  confirmed_date?: string | null;
  confirmed_user?: string | null;
  remark?: string;
  created_at?: string;
  updated_at?: string;
};

export type CaseClueEvidenceRow = CaseRow & {
  files: AttachmentRow[];
  can_edit: boolean;
  can_delete: boolean;
};

export type CaseClueWorkspace = {
  clue: CaseRow;
  clue_files: AttachmentRow[];
  evidence: CaseClueEvidenceRow[];
};

export type CaseFileTypeOption = {value:string;label:string;code?:string;parent_code?:string;disabled?:boolean;options?:CaseFileTypeOption[]};

export type WarehouseStorageLocationOption = { id: number; name: string; is_active: boolean };

export type WarehouseCatalogOption = { id: number; name: string; is_active: boolean; locations: WarehouseStorageLocationOption[] };

export type AttachmentPreview = {
  name: string;
  kind: "image" | "pdf" | "text" | "docx";
  url?: string;
  text?: string;
  attachmentId?: number;
  page?: number;
  pageCount?: number;
};

export type CaseReminderRow = {id:number;description:string;owner:string;data:{reminder_date:string;deadline:string;case_id:number}};

export type CaseEventRow = {
  id: number;
  case_id: number;
  event_type: string;
  content: string;
  event_time: string;
  deadline?: string | null;
  remind_at?: string | null;
  reminder_enabled: boolean;
  status: "待处理" | "已完成" | "已逾期";
  creator: string;
  creator_display_name?: string;
  created_at?: string;
  updated_at?: string;
  can_edit?: boolean;
  can_delete?: boolean;
};

export type CaseEventCapabilities = { can_create: boolean; can_edit: boolean; can_delete: boolean };

export type CaseLogRow = {id:number;content:string;operator:string;operator_display_name?:string;created_at:string};

export type CaseLogKind = "case" | "refund";

export type CaseTaskKind = "案件任务" | "客户任务";

export type CaseDocumentFolderEditor = { mode: "create" | "rename"; originalName?: string };

export type CaseAiDraftEditor = { mode: "create" | "edit"; item?: AttachmentRow };

export type CaseWordEditorBlock = { id: string; text: string; editable: boolean; readOnlyReason?: string };

export type CaseWordEditor = {
  caseId: number;
  item: AttachmentRow;
  lockToken: string;
  blocks: CaseWordEditorBlock[];
  savedBlocks: CaseWordEditorBlock[];
  version: string;
  expiresAt?: string;
};

export type CaseDetailCapabilities = {
  can_write: boolean;
  can_generate_document: boolean;
  can_upload_attachment: boolean;
  can_delete_attachment: boolean;
  can_create_reminder: boolean;
  can_delete_reminder: boolean;
  can_create_log: boolean;
  can_update_progress: boolean;
  can_change_phase: boolean;
  can_manage_hearing: boolean;
  can_create_case_task: boolean;
  can_delete_case: boolean;
  can_duplicate_case: boolean;
  can_merge_case: boolean;
  can_assign_team: boolean;
  can_edit_hearing_lawyer: boolean;
  can_edit_basic: boolean;
  can_edit_court_info: boolean;
  can_close_case: boolean;
  can_archive: boolean;
  can_create_finance: boolean;
  can_manage_assisted_fees: boolean;
  team_role: "manager" | "handling_lawyer" | "assistant" | "none";
  reason: string;
};

export type CaseFeeColumnContext = {
  scope: "律所" | "平台" | "内部";
  rows: CaseRow[];
  selectedKeys: import("react").Key[];
  setSelectedKeys: (keys: import("react").Key[]) => void;
};
