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

export const getCaseArchivePagination = (view) => ({
  pageSize: String(view ?? "").includes("done") || String(view ?? "").includes("refused") ? 10 : 15,
  pageSizeOptions: [10, 15, 20, 50, 100],
  showSizeChanger: true,
  showTotal: (total) => `共有${total}条`,
});

export const getCaseUnarchiveRequestValidationError = (reason) =>
  String(reason ?? "").trim().length < 2 ? "请输入至少2个字的解档原因" : "";

const normalizeCaseFileType = (item) => ({
  ...item,
  value: String(item?.value ?? item?.code ?? "").trim(),
  label: String(item?.label ?? item?.value ?? item?.code ?? "").trim(),
  code: String(item?.code ?? item?.value ?? "").trim(),
  parent_code: String(item?.parent_code ?? "").trim(),
});

export const buildCaseFileTypeTreeOptions = (items) => {
  const normalized = (Array.isArray(items) ? items : [])
    .map(normalizeCaseFileType)
    .filter((item) => item.value && item.label);
  const codes = new Set(normalized.map((item) => item.code));
  const childrenByParent = new Map();
  for (const item of normalized) {
    if (!item.parent_code || !codes.has(item.parent_code)) continue;
    const children = childrenByParent.get(item.parent_code) || [];
    children.push(item);
    childrenByParent.set(item.parent_code, children);
  }
  return normalized
    .filter((item) => !item.parent_code || !codes.has(item.parent_code))
    .map((item) => {
      const children = childrenByParent.get(item.code) || [];
      return children.length ? { ...item, options: children } : item;
    });
};

export const resolveCaseFileTypeSelection = (value, options) => {
  const requested = String(value ?? "").trim();
  const flatten = (items) => (Array.isArray(items) ? items.flatMap((item) => [item, ...flatten(item.options)]) : []);
  const available = flatten(options);
  return available.find((item) => item.value === requested)?.value || available[0]?.value || "";
};
