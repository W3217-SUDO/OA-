import dayjs from "dayjs";
import { readContractListQuery } from "../contractListQuery";
import { normalizeContractDetailReturnView } from "../contractWorkflowPolicy.mjs";
import type { Profile } from "./types";

export const archiveCheckLabels: Record<string,string> = { case_closed:"案件完结", fees_settled:"费用结清", documents_complete:"材料齐全", finance_complete:"财务完结" };

export const colors: Record<string, string> = {
  草稿: "default",
  审批中: "orange",
  审批通过: "green",
  已完成: "green",
  已拒绝: "red",
};

export const CONTRACT_TYPE_OPTIONS = ["法律顾问合同", "争议解决合同", "框架合作合同", "非诉项目合同", "其他"].map((value) => ({ value, label: value }));

export const CONTRACT_FEE_MODE_OPTIONS = ["固定收费", "固定+后期", "免费代理", "法律援助", "计时收费", "全风险代理"].map((value) => ({ value, label: value }));

export const CONTRACT_CREATE_STEP_TITLES = ["合同基本信息", "提交审批", "合同审批", "合同用印"];

export const CONTRACT_SEAL_READY_STATUSES = ["审批中", "审批通过", "已完成", "履行中", "已通过"];

export const WIZARD_STORAGE_KEY = "sunhold-contract-wizard-id";

export const CONTRACT_DETAIL_RETURN_VIEW_STORAGE_KEY = "sunhold:contract-detail-return-view";

export const CONTRACT_DETAIL_TAB_STORAGE_KEY = "sunhold:contract-detail-active-tab";

export const normalizeContractDetailTabKey = (tab?: string | null) =>
  ["objects", "events", "workflow", "attachments", "legacy-attachments", "approvals", "archive"].includes(String(tab || ""))
    ? String(tab)
    : "objects";

export const consumeContractDetailTabKey = () => {
  try {
    const tab = sessionStorage.getItem(CONTRACT_DETAIL_TAB_STORAGE_KEY);
    sessionStorage.removeItem(CONTRACT_DETAIL_TAB_STORAGE_KEY);
    return tab ? normalizeContractDetailTabKey(tab) : null;
  } catch {
    // Detail pages should still open when session storage is unavailable.
  }
  return null;
};

export const consumeContractDetailReturnView = () => {
  try {
    const view = String(sessionStorage.getItem(CONTRACT_DETAIL_RETURN_VIEW_STORAGE_KEY) || "");
    sessionStorage.removeItem(CONTRACT_DETAIL_RETURN_VIEW_STORAGE_KEY);
    return normalizeContractDetailReturnView(view);
  } catch {
    // Detail pages can still close safely when session storage is unavailable.
  }
  return "contract-mine";
};

export const readContractQuery = (view: string): Record<string, any> => {
  const parsed = readContractListQuery(sessionStorage, view) as Record<string, any>;
  if (Array.isArray(parsed.signed_at)) parsed.signed_at = parsed.signed_at.map((value: string) => dayjs(value));
  if (Array.isArray(parsed.archive_date)) parsed.archive_date = parsed.archive_date.map((value: string) => dayjs(value));
  return parsed;
};

export const initialProfile = (): Profile => {
  try {
    const stored = JSON.parse(localStorage.getItem("user") || "{}");
    return {
      username: stored.username || "",
      display_name: stored.display_name || "",
      department: stored.department || "",
      role: stored.role || "",
      menu_keys: Array.isArray(stored.menu_keys) ? stored.menu_keys : undefined,
      action_keys: Array.isArray(stored.action_keys) ? stored.action_keys : undefined,
      menuKeys: Array.isArray(stored.menuKeys) ? stored.menuKeys : undefined,
      actionKeys: Array.isArray(stored.actionKeys) ? stored.actionKeys : undefined,
    };
  } catch {
    return { username: "", display_name: "", department: "", role: "" };
  }
};

export const amount = (value?: number) => Number(value || 0).toFixed(2);

export const moneyKeys = [
  "official_paid",
  "official_received",
  "official_unreceived",
  "official_loss",
  "agency_total",
  "agency_received",
  "agency_due",
  "other_total",
  "other_paid",
  "other_due",
  "invoice_opened",
  "invoice_should",
  "invoice_excess",
] as const;
