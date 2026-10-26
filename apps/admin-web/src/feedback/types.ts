export type FeedbackRecord = {
  id: number;
  serial_no: string;
  description: string;
  status: string;
  owner: string;
  owner_display_name: string;
  assignee: string;
  assignee_display_name: string;
  page: string;
  route: string;
  controls: string[];
  /** 改成日期编号前的旧编号（只有 2026-10-26 前提交的问题有）。 */
  legacy_serial_no?: string;
  created_at: string;
  updated_at: string;
  has_screenshot: boolean;
};

export type FeedbackEvent = {
  id: number;
  action: string;
  from_status: string;
  to_status: string;
  operator: string;
  operator_display_name: string;
  comment: string;
  created_at: string;
  has_screenshot: boolean;
  attachments?: FeedbackAttachment[];
};

export type FeedbackAttachment = {
  id: number;
  name: string;
  size: number;
  content_type: string;
  is_image: boolean;
};

export type FeedbackDetails = FeedbackRecord & {
  attachments: FeedbackAttachment[];
  events: FeedbackEvent[];
  can_assign: boolean;
  /** 管理员可以删除问题（逻辑删除，可在回收站恢复）。 */
  can_delete?: boolean;
  available_actions: string[];
};

export type FeedbackStatusCounts = {
  total: number;
  counts: Record<string, number>;
};

export type FeedbackPage = {
  items: FeedbackRecord[];
  total: number;
  can_delete?: boolean;
  page: number;
  page_size: number;
};
