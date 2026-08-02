const dateText = (value) => {
  if (value && typeof value === "object" && "format" in value && typeof value.format === "function") {
    return String(value.format("YYYY-MM-DD"));
  }
  return String(value ?? "").trim();
};

export const getCaseReminderDateValidationError = (reminderDate, deadline) => {
  const reminder = dateText(reminderDate);
  const due = dateText(deadline);
  return reminder && due && reminder > due ? "提醒日期不能晚于截止日期" : "";
};

export const CASE_TASK_PAGE_SIZE_OPTIONS = [10, 15, 20, 50, 100];

export const getCaseTaskPagination = () => ({
  defaultPageSize: 15,
  pageSizeOptions: [...CASE_TASK_PAGE_SIZE_OPTIONS],
  showSizeChanger: true,
  showTotal: (total) => `共 ${total} 项`,
});
