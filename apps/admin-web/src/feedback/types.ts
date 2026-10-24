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
  available_actions: string[];
};

export type FeedbackPage = {
  items: FeedbackRecord[];
  total: number;
  page: number;
  page_size: number;
};
