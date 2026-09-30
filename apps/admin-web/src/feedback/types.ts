export type FeedbackRecord = {
  id: number;
  serial_no: string;
  description: string;
  owner: string;
  owner_display_name: string;
  page: string;
  created_at: string;
  has_screenshot: boolean;
};

export type FeedbackPage = {
  items: FeedbackRecord[];
  total: number;
  page: number;
  page_size: number;
};
