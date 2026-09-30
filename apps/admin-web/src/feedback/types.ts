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
};

export type FeedbackDetails = FeedbackRecord & {
  events: FeedbackEvent[];
  can_assign: boolean;
  available_actions: string[];
};

export type FeedbackPage = {
  items: FeedbackRecord[];
  total: number;
  page: number;
  page_size: number;
};
