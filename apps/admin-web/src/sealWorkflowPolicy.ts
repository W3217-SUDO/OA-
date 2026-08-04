export type SealAction = "approve" | "reject" | "stamp" | "archive";
export type SealActionRow = { status: string };
export type SealSelectionKey = string | number;
export type SealHistoryEvent = {
  id: number;
  action?: string;
  from_status?: string;
  to_status?: string;
  operator?: string;
  comment?: string;
  created_at?: string;
  audit_status?: string;
  audit_date?: string;
  audit_content?: string;
  audit_round?: number;
  current_step?: string;
  step?: string;
};
export type SealAuditRow = {
  id: number;
  auditor: string;
  audit_status: string;
  audit_date: string;
  audit_content: string;
  audit_round: number;
  current_step: string;
};

function isAuditEvent(event: SealHistoryEvent): boolean {
  if (event.audit_status || event.audit_date || event.audit_content || event.audit_round !== undefined) return true;
  const action = String(event.action || "");
  if (/拒绝|驳回|退回|reject(?:ed)?/i.test(action)) return true;
  return /(?:审批|审核)(?:通过|拒绝|驳回)$|驳回$/.test(String(event.action || ""));
}

function legacySealAuditStatusName(value: unknown): string {
  const status = String(value || "").trim();
  if (!status) return "";
  const normalized = status.toLowerCase();
  if (["a", "approved", "approve", "pass", "passed"].includes(normalized)) return "审批通过";
  if (["r", "rejected", "reject", "refused", "refuse"].includes(normalized)) return "审批拒绝";
  if (["p", "pending"].includes(normalized)) return "待审批";
  return status;
}

export function toSealAuditRows(events: readonly SealHistoryEvent[]): SealAuditRow[] {
  return events.filter(isAuditEvent).map((event, index) => ({
    id: event.id,
    auditor: String(event.operator || ""),
    audit_status: legacySealAuditStatusName(event.audit_status || event.to_status || ""),
    audit_date: String(event.audit_date || event.created_at || ""),
    audit_content: String(event.audit_content || event.comment || ""),
    audit_round: Number(event.audit_round ?? index + 1),
    current_step: String(event.current_step || event.step || event.to_status || ""),
  }));
}

export function sealResponseIsFailure(data: unknown): boolean {
  if (!data || typeof data !== "object") return false;
  const payload = data as Record<string, unknown>;
  return payload.IsSuccess === false || payload.isSuccess === false || payload.is_success === false;
}

export function sealErrorMessage(error: unknown, fallback: string): string {
  const value = (error && typeof error === "object" ? error : {}) as Record<string, any>;
  const responseData = value.response?.data;
  const payload = responseData && typeof responseData === "object" ? responseData : value;
  for (const candidate of [payload.detail, payload.Message, payload.message, value.message]) {
    if (typeof candidate === "string" && candidate.trim()) return candidate;
  }
  return fallback;
}

export function canSealAction(action: SealAction, row: SealActionRow): boolean {
  if (action === "approve" || action === "reject") return row.status === "待审批";
  if (action === "stamp") return row.status === "待用印";
  return row.status === "已用印";
}

export function canSealWithdraw(row: SealActionRow & { owner?: string }): boolean {
  return row.status === "待审批" || row.status === "待用印";
}

export const sealFilePagination = {
  defaultPageSize: 15,
  showSizeChanger: true,
  pageSizeOptions: [10, 15, 20, 50, 100, 200],
  showQuickJumper: { goButton: "GO" },
  showTotal: (total: number) => `共 ${total} 个文件`,
};

export type SealAssetAuditRow = {
  id: number;
  asset_id: number;
  asset_code: string;
  asset_name: string;
  action: string;
  operator: string;
  comment: string;
  created_at: string;
};

export const sealAssetAuditPagination = {
  defaultPageSize: 15,
  showSizeChanger: true,
  pageSizeOptions: [10, 15, 20, 50, 100, 200],
  showQuickJumper: { goButton: "GO" },
  showTotal: (total: number) => `共 ${total} 条审计记录`,
};

export function canViewSealAssetAudit(role: unknown): boolean {
  return role === "admin" || role === "manager";
}

export function shouldCloseSealAssetAuditAfterDelete(assetId: number, openAssetId: number | null): boolean {
  return openAssetId !== null && assetId === openAssetId;
}

export function createSealAssetAuditRequestTracker() {
  let current = 0;
  return {
    next: () => ++current,
    invalidate: () => ++current,
    isCurrent: (requestId: number) => requestId === current,
  };
}

export function createSealDetailRequestTracker() {
  let current = 0;
  return {
    next: () => ++current,
    invalidate: () => ++current,
    isCurrent: (requestId: number) => requestId === current,
  };
}

function createSealRequestTracker() {
  let current = 0;
  return {
    next: () => ++current,
    invalidate: () => ++current,
    isCurrent: (requestId: number) => requestId === current,
  };
}

export function createSealFileListRequestTracker() {
  return createSealRequestTracker();
}

export function createSealPreviewRequestTracker() {
  return createSealRequestTracker();
}

export function mergeSealAssetSnapshot<T extends { id: SealSelectionKey }>(
  assets: readonly T[],
  latest: T | null | undefined,
): T[] {
  if (!latest) return [...assets];
  let replaced = false;
  const merged = assets.map((asset) => {
    if (asset.id !== latest.id) return asset;
    replaced = true;
    return latest;
  });
  return replaced ? merged : [...assets];
}

export function sealAssetAuditFailureMessage(status?: number): string {
  if (status === 403) return "当前账号无权查看印章资产审计";
  if (status === 404) return "印章不存在";
  if (status === 422) return "审计日期范围无效";
  return "印章资产审计加载失败";
}

export function selectedSealRows<T extends { id: SealSelectionKey }>(
  rows: readonly T[],
  selectedKeys: readonly SealSelectionKey[],
): T[] {
  const selected = new Set(selectedKeys);
  return rows.filter((row) => selected.has(row.id));
}

export function canBatchDeleteSealFiles(
  status: string,
  selectedKeys: readonly SealSelectionKey[],
): boolean {
  return status === "草稿" && selectedKeys.length > 0;
}

export function canBatchStampSealRows(rows: readonly SealActionRow[]): boolean {
  return rows.length > 0 && rows.every((row) => row.status === "待用印");
}

export function canBatchWithdrawSealRows(rows: readonly SealActionRow[]): boolean {
  return rows.length > 0 && rows.every((row) => row.status === "待审批" || row.status === "待用印");
}

export function compareSealDateValues(left: unknown, right: unknown): number {
  const leftValue = String(left || "");
  const rightValue = String(right || "");
  if (!leftValue && !rightValue) return 0;
  if (!leftValue) return -1;
  if (!rightValue) return 1;
  return leftValue.localeCompare(rightValue);
}

export function sealQueryFailureMessage(status?: number): string {
  if (status === 403) return "当前账号无权查询用印记录";
  if (status === 404) return "用印记录不存在或已被移除";
  if (status === 409) return "用印查询条件已失效，请刷新后重试";
  return "用印中心数据加载失败";
}

export function sealAttachmentListFailureMessage(status?: number): string {
  if (status === 403) return "当前账号无权查看用印文件";
  if (status === 404) return "用印申请或文件列表不存在";
  if (status === 409) return "当前状态不允许查看文件列表";
  return "文件列表加载失败";
}

export function formatSealAttachmentSize(value: unknown): string {
  const bytes = Number(value);
  if (!Number.isFinite(bytes) || bytes < 0) return "—";
  if (bytes < 1024) return `${Math.round(bytes)} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1).replace(/\.0$/, "")} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1).replace(/\.0$/, "")} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1).replace(/\.0$/, "")} GB`;
}

export function getSealAttachmentExtension(name: unknown): string {
  const value = String(name || "");
  const index = value.lastIndexOf(".");
  return index > -1 ? value.slice(index + 1).toUpperCase() : "";
}

export function createSealActionGate(): { tryEnter: () => boolean; leave: () => void } {
  let inFlight = false;
  return {
    tryEnter: () => {
      if (inFlight) return false;
      inFlight = true;
      return true;
    },
    leave: () => {
      inFlight = false;
    },
  };
}
