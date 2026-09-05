export type RecordRow = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  owner: string;
  owner_display_name?: string;
  description?: string;
  data: Record<string, any>;
};

export type Attachment = {
  id: number;
  record_id: number | null;
  record_no: string;
  record_title: string;
  category: string;
  original_name: string;
  content_type: string;
  size: number;
  uploader: string;
  uploader_display_name?: string;
  remark: string;
  created_at: string;
};

export type LegacyHistoricalAttachment = {
  id: number;
  source_system: string;
  legacy_entity_type: string;
  legacy_file_id: number;
  legacy_file_guid: string;
  legacy_parent_no: string;
  file_name: string;
  legacy_declared_size_bytes: number | null;
  legacy_file_path: string;
  legacy_is_active: boolean;
  physical_exists: boolean;
  recovery_status: string;
  quarantine_reasons: string[];
  download_available: false;
  preview_available: false;
  download_reason: string;
};

export type SealAsset = { id: number; name: string; seal_type: string; status: string };

export type Template = {
  id: number;
  name: string;
  category: string;
  version: string;
  description: string;
  fields: string[];
  is_active: boolean;
};

export type HistoryEvent = {
  id: number;
  action: string;
  from_status: string;
  to_status: string;
  operator: string;
  operator_display_name?: string;
  comment: string;
  created_at: string;
};

export type ReceiptRow = RecordRow & {
  data: Record<string, any> & {
    case_no?: string;
    plaintiff?: string;
    defendant?: string;
    court_no?: string;
    court_name?: string;
    document_date?: string;
    uploaded_at?: string;
    import_status?: string;
    business_process_status?: string;
    uploader?: string;
    uploader_display_name?: string;
    hearing_lawyer?: string;
    hearing_lawyer_display_name?: string;
    assistant?: string;
    assistant_display_name?: string;
    brand_manager?: string;
    brand_manager_display_name?: string;
    case_manager?: string;
    case_manager_display_name?: string;
    handling_lawyer?: string;
    handling_lawyer_display_name?: string;
    signer_display_name?: string;
  };
};

export type DocumentSummary = {
  documents: number;
  pending_receipt: number;
  received: number;
  attachments: number;
  archive_materials: number;
  templates: number;
};
