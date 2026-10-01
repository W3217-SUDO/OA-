import { useState } from "react";
import type { RefundCaseFeeLogKind } from "../types";

const logTemplates: Record<RefundCaseFeeLogKind, string> = {
  court: "提交法院时间:\n法院联系人:\n联系电话:\n快递单号:",
  received: "法院打款时间:\n账户:",
  other: "",
};

/** 案件费用退费操作的弹窗状态和日志模板由同一流程管理。 */
export function useRefundCaseFeeActionState() {
  const [refundCaseFeeStatusOpen, setRefundCaseFeeStatusOpen] = useState(false);
  const [refundCaseFeeStatus, setRefundCaseFeeStatus] = useState("R10");
  const [refundCaseFeeLogKind, setRefundCaseFeeLogKind] = useState<RefundCaseFeeLogKind | null>(null);
  const [refundCaseFeeLogContent, setRefundCaseFeeLogContent] = useState("");
  const [refundCaseFeeMutationLoading, setRefundCaseFeeMutationLoading] = useState(false);

  const openRefundCaseFeeStatus = (status: string) => {
    setRefundCaseFeeStatus(status);
    setRefundCaseFeeStatusOpen(true);
  };
  const closeRefundCaseFeeStatus = () => setRefundCaseFeeStatusOpen(false);
  const openRefundCaseFeeLog = (kind: RefundCaseFeeLogKind) => {
    setRefundCaseFeeLogContent(logTemplates[kind]);
    setRefundCaseFeeLogKind(kind);
  };
  const closeRefundCaseFeeLog = () => {
    setRefundCaseFeeLogKind(null);
    setRefundCaseFeeLogContent("");
  };

  return {
    refundCaseFeeStatusOpen,
    setRefundCaseFeeStatusOpen,
    refundCaseFeeStatus,
    setRefundCaseFeeStatus,
    refundCaseFeeLogKind,
    setRefundCaseFeeLogKind,
    refundCaseFeeLogContent,
    setRefundCaseFeeLogContent,
    refundCaseFeeMutationLoading,
    setRefundCaseFeeMutationLoading,
    openRefundCaseFeeStatus,
    closeRefundCaseFeeStatus,
    openRefundCaseFeeLog,
    closeRefundCaseFeeLog,
  };
}
