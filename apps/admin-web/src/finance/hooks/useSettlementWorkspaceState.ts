import { Form } from "antd";
import { useState } from "react";
import type { SettlementBatchFormValues } from "../formTypes";
import type { SettlementContext, SettlementContextRow, SettlementTaskForm } from "../types";

/** 结算任务、日志与案件批改共用同一次操作生命周期。 */
export function useSettlementWorkspaceState() {
  const [settlementBatchOpen, setSettlementBatchOpen] = useState(false);
  const [settlementBatchForm] = Form.useForm<SettlementBatchFormValues>();
  const [settlementContext, setSettlementContext] = useState<SettlementContext | null>(null);
  const [settlementLogContent, setSettlementLogContent] = useState("");
  const [settlementTaskForm, setSettlementTaskForm] = useState<SettlementTaskForm>({
    title: "", owner: "", deadline: null, priority: "普通",
  });
  const [settlementContextRows, setSettlementContextRows] = useState<SettlementContextRow[]>([]);
  const [settlementActionLoading, setSettlementActionLoading] = useState(false);

  const closeSettlementBatch = () => setSettlementBatchOpen(false);
  const openSettlementBatch = () => {
    settlementBatchForm.resetFields();
    setSettlementBatchOpen(true);
  };
  return {
    settlementBatchOpen, setSettlementBatchOpen, settlementBatchForm, openSettlementBatch, closeSettlementBatch,
    settlementContext, setSettlementContext, settlementLogContent, setSettlementLogContent,
    settlementTaskForm, setSettlementTaskForm, settlementContextRows, setSettlementContextRows,
    settlementActionLoading, setSettlementActionLoading,
  };
}
