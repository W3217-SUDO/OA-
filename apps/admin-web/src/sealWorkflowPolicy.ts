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
};
export type SealAuditRow = {
  id: number;
  auditor: string;
  audit_status: string;
  audit_date: string;
  audit_content: string;
  audit_round: number;
};

function isAuditEvent(event: SealHistoryEvent): boolean {
  if (event.audit_status || event.audit_date || event.audit_content || event.audit_round !== undefined) return true;
  return /(?:审批|审核)(?:通过|拒绝|驳回)$|驳回$/.test(String(event.action || ""));
}

export function toSealAuditRows(events: readonly SealHistoryEvent[]): SealAuditRow[] {
  return events.filter(isAuditEvent).map((event, index) => ({
    id: event.id,
    auditor: String(event.operator || ""),
    audit_status: String(event.audit_status || event.to_status || ""),
    audit_date: String(event.audit_date || event.created_at || ""),
    audit_content: String(event.audit_content || event.comment || ""),
    audit_round: Number(event.audit_round ?? index + 1),
  }));
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
