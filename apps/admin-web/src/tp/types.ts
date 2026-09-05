import type { Dayjs } from "dayjs";
import type { UploadFile } from "antd";

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
  creation_mode?: string;
  reminder_due: boolean;
  reminder_text: string;
  initiator: string;
  initiator_display_name?: string;
  collaborators: string[];
  collaborator_display_names?: string[];
  case_no: string;
  case_nos?: string[];
  start_at?: string;
  end_at?: string;
  plaintiff: string;
  defendant: string;
  case_stage: string;
  department: string;
  created_at: string;
  updated_at: string;
  verified_at: string;
  rejected_reason: string;
  handoff_recipient: string;
  handoff_auto_complete_at: string;
  completion_auto_confirm_at: string;
  auto_completed: boolean;
  performance_impact?: { overdue?: boolean; overdue_days?: number; penalty_points?: number };
  exception_request?: { action?: string; status?: string; reason?: string };
  latest_unread_message: string;
  latest_unread_sender: string;
  latest_unread_sender_display_name?: string;
  latest_unread_at: string;
  unread_count: number;
  latest_unread_notification_id?: number;
  data?: Record<string, unknown>;
};

export type Summary = {
  total: number;
  pending: number;
  processing: number;
  awaiting_confirmation: number;
  due_soon: number;
  overdue: number;
  reminders: number;
};

export type HistoryItem = {
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

export type TaskFeedbackAttachment = {
  id: number;
  original_name: string;
  category: string;
  uploader: string;
  uploader_display_name?: string;
  created_at: string;
  size: number;
  remark?: string;
};

export type TaskSort = {
  field: "created_at" | "deadline" | "days_remaining" | "updated_at";
  order: "ascend" | "descend";
} | null;

export type CaseRecord = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  owner: string;
  owner_display_name?: string;
};

export type PeopleOption = { username: string; label: string };

export type CaseContextTaskPageState = { items: TaskRow[]; total: number; page: number; pageSize: number; pages: number };

export type DialogAction = "reject" | "resend";

export type FeeAction = "lawFee" | "platformFee" | "internalFee";

export type FeeSubtype = "官费" | "第三方费用" | "代理费" | "其他费用" | "内部费用";

export type CaseBatchAction = "hearing_lawyer" | "handling_lawyers" | "assistant" | "case_stage";

export type TaskBatchLifecycleAction = "accept" | "complete" | "confirm" | "handoff" | "withdraw";

export type TaskQuery = {
  priority?: string;
  serial_no?: string;
  title?: string;
  description?: string;
  initiator?: string;
  case_no?: string;
  source?: string;
  owner?: string;
  plaintiff?: string;
  defendant?: string;
  created_range?: [Dayjs, Dayjs];
  deadline_range?: [Dayjs, Dayjs];
};

export type StatusTab = { key: string; label: string; statuses: string[] };

export type DirectoryUser = {
  username: string;
  display_name: string;
  department: string;
  is_active: boolean;
};
