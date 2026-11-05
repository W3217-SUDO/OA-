import dayjs from "dayjs";
import type { UploadFile } from "antd";
import type {
  TaskRow,
  Summary,
  StatusTab,
  CaseContextTaskPageState,
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

// 501629（tgn 11-05 选 A）：接受、协作的任务按老系统页签名称；发起的任务保持老系统 6 个状态。
export const receivedTabs: StatusTab[] = [
  { key: "pending", label: "待处理", statuses: ["待接收", "待处理"] },
  {
    key: "processing",
    label: "处理中",
    statuses: ["处理中", "进行中", "已逾期"],
  },
  { key: "finished", label: "已完成", statuses: ["已完成", "待确认", "已验收"] },
  { key: "stopped", label: "已停止", statuses: ["已停止", "已撤回", "已拒绝"] },
];

export const collaboratingTabs: StatusTab[] = [
  { key: "active", label: "处理中", statuses: ["待接收", "待处理", "处理中", "进行中", "已逾期"] },
  { key: "finished", label: "已完成", statuses: ["已完成", "待确认", "已验收"] },
];

// ─── Utility functions ───────────────────────────────────────────────────

// 501629（tgn 11-05）：已完成的任务，剩余天数按完成那天固定（后端 _task_schedule_state）。
// 逾期完成显示“逾期完成 X 天”（灰色），按期完成显示“按期完成”；未完成的仍显示“X/天”，逾期标红、3 天内标橙。
const FINISHED_TASK_STATUSES = new Set(["已完成", "已验收", "待确认"]);
export const taskDaysDisplay = (status: string | null | undefined, value: number | null | undefined) => {
  if (value == null) return { text: "", className: "" };
  if (FINISHED_TASK_STATUSES.has(String(status || ""))) {
    return value < 0
      ? { text: `逾期完成 ${Math.abs(value)} 天`, className: "task-days-finished" }
      : { text: "按期完成", className: "task-days-finished" };
  }
  return { text: `${value}/天`, className: value < 0 ? "task-days-overdue" : value <= 3 ? "task-days-soon" : "" };
};

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
