import { useState } from "react";
import { Button, message } from "antd";
import { api } from "../api";
import { notifyConflictReviewUpdated } from "./events";

export function ConflictReviewCheckButton({ recordId, refreshRecordId, onChecked }: {
  recordId: number;
  refreshRecordId?: number;
  onChecked?: () => Promise<void>;
}) {
  const [checking, setChecking] = useState(false);
  const check = async () => {
    setChecking(true);
    try {
      await api.post(`/conflict-reviews/record/${recordId}/check`);
      notifyConflictReviewUpdated(refreshRecordId ?? recordId);
      await onChecked?.();
    } catch (error: any) { message.error(error?.response?.data?.detail || "利益冲突审查启动失败"); }
    finally { setChecking(false); }
  };
  return <Button size="small" loading={checking} onClick={() => void check()}>启动/重新审查</Button>;
}
