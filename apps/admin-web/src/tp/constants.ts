import dayjs from "dayjs";
import type { UploadFile } from "antd";
import type {
  TaskRow,
  Summary,
  StatusTab,
  CaseContextTaskPageState,
  TaskSort,
} from "./types";

// ─── Constants ───────────────────────────────────────────────────────────

export const CASE_CONTEXT_TASK_DEFAULT_PAGE = 1;
export const CASE_CONTEXT_TASK_DEFAULT_PAGE_SIZE = 15;

export const PERSON_NAME_PLACEHOLDER = "姓名待维护";

export const EMPTY_SUMMARY: Summary = {
  total: 0,
  pending: 0,
  processing: 0,
  awaiting_confirmation: 0,
  due_soon: 0,
  overdue: 0,
  reminders: 0,
};

export const statusColors: Record<string, string> = {
  进行中: "blue",
  待接收: "orange",
  待处理: "orange",
  处理中: "blue",
  待确认: "purple",
  已完成: "green",
  已验收: "green",
  已逾期: "red",
  已拒绝: "red",
  已停止: "default",
  已撤回: "default",
};

export const createdTabs: StatusTab[] = [
  {
    key: "active",
    label: "进行中",
    statuses: ["待接收", "待处理", "处理中", "进行中", "已逾期"],
  },
  { key: "finished", label: "进行中-已完成", statuses: ["已完成", "待确认"] },
  { key: "rejected", label: "进行中-拒绝", statuses: ["已拒绝"] },
  { key: "stopped", label: "进行中-已停止", statuses: ["已停止"] },
  { key: "withdrawn", label: "进行中-已撤回", statuses: ["已撤回"] },
  { key: "accepted", label: "已验收", statuses: ["已验收"] },
];

export const receivedTabs: StatusTab[] = [
  { key: "pending", label: "待处理", statuses: ["待接收", "待处理"] },
  {
    key: "processing",
    label: "进行中",
    statuses: ["处理中", "进行中", "已逾期"],
  },
  { key: "finished", label: "完成", statuses: ["已完成", "待确认", "已验收"] },
  { key: "stopped", label: "停止", statuses: ["已停止", "已撤回", "已拒绝"] },
];

export const collaboratingTabs: StatusTab[] = [
  { key: "active", label: "进行中", statuses: ["待接收", "待处理", "处理中", "进行中", "已逾期"] },
  { key: "finished", label: "完成", statuses: ["已完成", "待确认", "已验收"] },
];

// ─── Utility functions ───────────────────────────────────────────────────

export const visiblePersonName = (displayName?: string | null) =>
  String(displayName || "").trim() || PERSON_NAME_PLACEHOLDER;

export const visibleOptionalPersonName = (reference?: string | null, displayName?: string | null) =>
  String(reference || "").trim() ? visiblePersonName(displayName) : "—";

export const visibleCollaboratorNames = (row?: TaskRow | null) => {
  if (!row?.collaborators?.length) return "—";
  const names = (row.collaborator_display_names || []).map((name) => String(name || "").trim()).filter(Boolean);
  return names.length === row.collaborators.length ? names.join("、") : PERSON_NAME_PLACEHOLDER;
};

export const appendSelectedUploadFiles = (body: FormData, files: UploadFile[]) => {
  let appended = 0;
  for (const file of files) {
    const source = file.originFileObj || (file as unknown as File);
    if (source && typeof (source as Blob).arrayBuffer === "function") {
      body.append("files", source);
      appended += 1;
    }
  }
  return appended;
};

export const normalizeCaseContextTaskPageState = (
  payload: any,
  fallbackPage = CASE_CONTEXT_TASK_DEFAULT_PAGE,
  fallbackPageSize = CASE_CONTEXT_TASK_DEFAULT_PAGE_SIZE,
): CaseContextTaskPageState => {
  const items = Array.isArray(payload?.items) ? payload.items : [];
  const total = Number.isFinite(Number(payload?.total)) ? Number(payload.total) : items.length;
  const pageSize = Number.isFinite(Number(payload?.page_size)) ? Number(payload.page_size) : fallbackPageSize;
  const page = Number.isFinite(Number(payload?.page)) ? Number(payload.page) : fallbackPage;
  const pages = Number.isFinite(Number(payload?.pages))
    ? Number(payload.pages)
    : total > 0
      ? Math.ceil(total / Math.max(pageSize, 1))
      : 0;
  return { items, total, page, pageSize, pages };
};

export const formatTaskDate = (value?: string) =>
  value ? dayjs(value).format("YYYY-M-D") : "";

export const formatTaskDateTime = (value?: string) =>
  value ? dayjs(value).format("YYYY-M-D H:m:s") : "";

export const formatTaskScheduleTime = (value?: string) =>
  value && /[T\s]\d{1,2}:\d{2}/.test(value)
    ? dayjs(value).format("YYYY-M-D HH:mm")
    : formatTaskDate(value);

export const taskDataValues = (value: unknown) => {
  const values = Array.isArray(value) ? value : [value];
  return values
    .flatMap((item) => String(item || "").split(/[,，;；\n]/))
    .map((item) => item.trim())
    .filter(Boolean);
};

export const taskCaseNos = (row: TaskRow) => Array.from(new Set([
  ...taskDataValues(row.case_no),
  ...taskDataValues(row.case_nos),
  ...taskDataValues(row.data?.case_nos),
  ...taskDataValues(row.data?.caseNos),
  ...taskDataValues(row.data?.CaseNos),
]));

export const taskTemporalValue = (row: TaskRow, keys: string[], fallback = "") => {
  for (const key of keys) {
    const value = String(row.data?.[key] || "").trim();
    if (value) return value;
  }
  return fallback;
};

export const taskStartedAt = (row: TaskRow) =>
  row.start_at || taskTemporalValue(row, ["started_at", "start_at", "task_begin_time", "TaskBeginTime"]);

export const taskEndedAt = (row: TaskRow) =>
  row.end_at || taskTemporalValue(row, ["deadline_at", "end_at", "task_end_time", "TaskEndTime"], row.deadline);

export const taskCreationMode = (row: TaskRow) =>
  row.creation_mode === "自动" ? "自动" : "人工";

export const contains = (value: unknown, query?: string) =>
  !query?.trim() ||
  String(value || "")
    .toLowerCase()
    .includes(query.trim().toLowerCase());
