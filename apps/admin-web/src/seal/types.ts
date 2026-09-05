export type SealAsset = {
  id: number;
  code: string;
  name: string;
  seal_type: string;
  custodian: string;
  location: string;
  status: string;
  usage_count: number;
  last_used_at?: string;
  remark: string;
  action_keys?: string[];
  capabilities?: { manage_assets?: boolean };
};

export type SealRow = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  owner: string;
  owner_display_name?: string;
  description: string;
  data: Record<string, any>;
  seal_asset?: SealAsset;
  created_at: string;
  updated_at: string;
  file_count?: number;
  application_file_count?: number;
  stamped_file_count?: number;
  application_file_names?: string[];
  stamped_file_names?: string[];
  action_keys?: string[];
  capabilities?: Partial<Record<"approve" | "reject" | "stamp" | "archive", boolean>>;
};

export type Summary = {
  total: number;
  pending: number;
  waiting_stamp: number;
  completed: number;
};

export type EventRow = {
  id: number;
  action: string;
  from_status: string;
  to_status: string;
  operator: string;
  operator_display_name?: string;
  comment: string;
  created_at: string;
  audit_status?: string;
  audit_date?: string;
  audit_content?: string;
  audit_round?: number;
};

export type AttachmentRow = {
  id: number;
  original_name: string;
  category: string;
  size: number;
  uploader: string;
  uploader_display_name?: string;
  created_at: string;
};

export type RelationRow = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  data: Record<string, any>;
};

export type SealPreviewMode = "binary" | "text" | "unsupported";

export type SealActionType = "approve" | "reject" | "stamp" | "archive";

export type SealActionState = {
  type: SealActionType;
  row: SealRow;
};

export type AssetAuditFilters = {
  action: string;
  operator: string;
  keyword: string;
  date_from: string;
  date_to: string;
};
