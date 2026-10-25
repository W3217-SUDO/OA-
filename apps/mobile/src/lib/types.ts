// 字段与网页端 apps/admin-web/src 中的同名类型保持一致，只保留移动端用到的部分。

export type SessionUser = {
  username: string;
  display_name: string;
  department: string;
  role: string;
  must_change_password?: boolean;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  must_change_password: boolean;
  user: SessionUser;
};

export type Paged<T> = { items: T[]; total: number; page: number; page_size: number };

// tp/types.ts TaskRow
export type TaskRow = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  workflow_status: string;
  owner: string;
  owner_display_name?: string;
  description: string;
  deadline: string;
  days_remaining: number | null;
  priority: string;
  source: string;
  initiator: string;
  initiator_display_name?: string;
  collaborators: string[];
  collaborator_display_names?: string[];
  case_no: string;
  plaintiff: string;
  defendant: string;
  case_stage: string;
  created_at: string;
  updated_at: string;
  rejected_reason: string;
  auto_completed: boolean;
  phase_completion_required?: boolean;
  latest_unread_message: string;
  latest_unread_sender_display_name?: string;
  latest_unread_at: string;
  unread_count: number;
};

export type TaskListResponse = Paged<TaskRow> & { status_counts?: Record<string, number> };

// tp/types.ts HistoryItem
export type TaskHistoryItem = {
  id: number;
  action: string;
  operator: string;
  operator_display_name?: string;
  comment: string;
  from_status: string;
  to_status: string;
  created_at: string;
  unread?: boolean;
};

// legal/types.ts CaseRow
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
  updated_at?: string;
  data: Record<string, any>;
};

export type CaseLog = {
  id: string | number;
  content: string;
  operator: string;
  operator_display_name?: string;
  created_at: string;
};

// personal-agent/types.ts
export type WorkspaceMessage = {
  role: "user" | "assistant";
  content: string;
  created_at?: string;
  skill_name?: string;
  failed?: boolean;
};

export type PendingAction = {
  id: string;
  type: string;
  summary: string;
  status: "pending" | "approved" | "rejected" | "executing" | "succeeded" | "failed";
  error?: unknown;
};

export type WorkspaceState = {
  conversation_id?: string | null;
  conversation_title?: string;
  messages: WorkspaceMessage[];
  pending_actions: PendingAction[];
  dismissed_action_ids: string[];
};

export type WorkspaceConversation = { id: string; title: string; message_count: number; updated_at: string };

export type ConversationSnapshot = {
  items: WorkspaceConversation[];
  active_id: string | null;
  state: WorkspaceState;
  active_unavailable_reason?: string;
};
