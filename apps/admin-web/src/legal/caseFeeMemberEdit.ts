import type { CaseDetailCapabilities, CaseRow } from "./types";

// 501384（fwl 11-04）：费用新建后还没产生任何数据时，本案人员都能修改、删除；有了审批、付款、退费、回款、开票、结算后
// 只有分配了修改/删除案件费用权限的角色能改删。和后端 app/core/case_fee_member_edit.py 同一规则，后端改删时还会再核对一次。
const UNTOUCHED_STATUSES = new Set(["草稿", "已记录"]);
const ACTIVITY_AMOUNTS = ["payment_requested_amount", "applied_amount", "paid_amount", "cashed_amount", "received_amount", "invoice_amount", "invoiced_amount",
  "refund_requested_amount", "refunded_amount", "refund_amount", "settled_amount", "settlement_amount", "writeoff_amount"];
const ACTIVITY_MARKS = ["payment_application_no", "invoice_no", "invoice_record_id", "receipt_attachment_id", "bill_no", "settlement_no", "settlement_id",
  "settled_at", "writeoff_at", "written_off_at", "submitted_for_approval_at"];

export function caseFeeUntouched(row?: CaseRow | null): boolean {
  if (!row || !UNTOUCHED_STATUSES.has(String(row.status || ""))) return false;
  const data = (row.data || {}) as Record<string, unknown>;
  if (ACTIVITY_AMOUNTS.some((key) => Math.abs(Number(data[key] || 0)) > 0)) return false;
  if (ACTIVITY_MARKS.some((key) => !["", "0", "/", "—"].includes(String(data[key] ?? "").trim()))) return false;
  return !["receipt_files", "bill_files", "invoices"].some((key) => Array.isArray(data[key]) ? (data[key] as unknown[]).length > 0 : Boolean(data[key]));
}

/** 律所/平台费用能不能改（action=edit）或删（action=delete）：有角色权限，或本案人员且这笔费用还没产生数据。没选费用时按“可能可以”显示菜单。 */
export function canChangeCaseFee(capabilities: CaseDetailCapabilities, action: "edit" | "delete", row?: CaseRow | null): boolean {
  if (action === "edit" ? capabilities.can_edit_finance : capabilities.can_delete_finance) return true;
  return Boolean(capabilities.can_change_untouched_finance) && (!row || caseFeeUntouched(row));
}
