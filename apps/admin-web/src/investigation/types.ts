export type Row = {
  id: number;
  module: string;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  owner: string;
  owner_display_name?: string;
  description?: string;
  data: Record<string, any>;
  updated_at: string;
};

export type Attachment = {
  id: number;
  category: string;
  original_name: string;
  size: number;
  uploader: string;
  uploader_display_name?: string;
  created_at: string;
};

export type ClueEvidenceRow = Row & {
  files: Attachment[];
  can_edit: boolean;
  can_delete: boolean;
};

export type ClueWorkspace = {
  clue: Row;
  clue_files: Attachment[];
  evidence: ClueEvidenceRow[];
};

export type Contract = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
};

export type ResolvedClueContract = {
  clue_id: number;
  clue_no?: string;
  clue_title?: string;
  customer?: string;
  contract?: Contract | null;
  error?: string;
};

export type TaskRow = {
  id: number;
  serial_no: string;
  title: string;
  status: string;
  owner: string;
  owner_display_name?: string;
  owner_display_name_missing?: boolean;
  deadline: string;
  priority: string;
  parent_task_id?: number;
  parent_task_no?: string;
  investigation_no?: string;
  data?: Record<string, unknown>;
};

export type Profile = {
  username: string;
  display_name: string;
  role: string;
  role_ids?: string[];
  department?: string;
};

export type PersonOption = {
  value: string;
  label: string;
  username?: string;
  search_text?: string;
};

export type InvestigationActions = {
  review_clue: boolean;
  review_customer_clue: boolean;
  review_notary: boolean;
  register_notary_certificate: boolean;
};

export type InvestigationBootstrapData = {
  profile: Profile;
  assignmentSupervisor: string;
  notaryOfficeOptions: { value: string }[];
  casePeopleOptions: PersonOption[];
  warehouseCatalog: WarehouseCatalogItem[];
};

export type WarehouseStorageLocation = { id: number; name: string; is_active: boolean };
export type WarehouseCatalogItem = { id: number; name: string; is_active: boolean; locations: WarehouseStorageLocation[] };

export type InvestigationRegionGroup = {
  province: string;
  cities: string[];
};

export type AdministrativeRegionOption = {
  text: string;
  value: string;
  children?: AdministrativeRegionOption[];
};

export type SubtaskLifecycleAction = "accept" | "complete";

export type ModuleKey = "investigation" | "clue" | "notary" | "evidence";
