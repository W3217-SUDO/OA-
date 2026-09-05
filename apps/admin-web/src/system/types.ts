export type ParameterRow = {
  id: number;
  category: string;
  code: string;
  name: string;
  extra: Record<string, any>;
  sort_order: number;
  is_active: boolean;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
  children?: ParameterRow[];
};

export type ParameterRelationKind =
  | "case-type-file-types"
  | "file-type-fee-types"
  | "case-type-case-phases";

export type ParameterRelationEditor = {
  kind: ParameterRelationKind;
  title: string;
  source: ParameterRow;
  targetCategory: string;
  targetLabel: string;
};

export type SystemConfig = {
  key: string;
  label: string;
  group: string;
  value: Record<string, any>;
  description: string;
  updated_by: string;
  updated_at: string;
};

export type CacheRow = {
  key: string;
  name: string;
  description: string;
  storage: string;
  clearable: boolean;
  entry_count: number;
  bucket_count: number;
  last_cleared_at: string | null;
  last_cleared_by: string;
};

export type CacheSummary = {
  cache_entries: number;
  cache_buckets: number;
  clearable_caches: number;
  scope: string;
};

export type MenuRow = {
  id: number;
  key: string;
  parent_key: string;
  label: string;
  description: string;
  icon: string;
  sort_order: number;
  is_visible: boolean;
  is_active: boolean;
  is_system: boolean;
  updated_by: string;
  updated_at: string;
};

export type SystemUser = {
  id: number;
  username: string;
  display_name: string;
  person_display_name?: string;
  display_name_missing?: boolean;
  department: string;
  role: string;
  role_ids?: string[];
  is_active: boolean;
  must_change_password?: boolean;
  contract_approval_enabled?: boolean;
  dingtalk_user_id?: string;
  dingtalk_bound?: boolean;
  profile?: Record<string, any>;
  email: string;
  mobile: string;
  office_phone: string;
  failed_login_attempts: number;
  locked_until: string | null;
  last_login_at: string | null;
  created_at: string;
};

export type RolePermission = {
  role: string;
  display_name: string;
  data_scope: string;
  menu_keys: string[];
  field_keys: string[];
  updated_at: string;
};

export type SecurityPolicy = {
  min_password_length: number;
  max_failed_attempts: number;
  lock_minutes: number;
  token_minutes: number;
  updated_by: string;
  updated_at: string;
};
