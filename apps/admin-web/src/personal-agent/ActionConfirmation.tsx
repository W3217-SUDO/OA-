import { useEffect, useRef, useState } from "react";
import { Alert, Button, Modal, Space, Spin, Tag, message } from "antd";
import { CheckOutlined, CloseOutlined, ReloadOutlined } from "@ant-design/icons";
import { isAxiosError } from "axios";
import { api } from "../api";
import { AgentOperationPreview, agentOperationError, agentOperationMessage, hasAgentOperationPreview } from "../AgentOperationPreview";
import type { ToolRequest } from "../AgentToolRequests";
import type { DecisionFailure, PendingAction } from "./types";
import "./confirmation-history.css";

const STATUS_NAMES: Record<PendingAction["status"], string> = {
  pending: "待确认", executing: "执行中", succeeded: "已执行", failed: "执行失败", rejected: "已取消",
  approved: "已批准",
};

export function ActionConfirmation({ action, deciding, decisionFailure, onDecide, onClose }: {
  action: PendingAction | null;
  deciding: boolean;
  decisionFailure?: DecisionFailure;
  onDecide: (action: PendingAction, decision: "approved" | "rejected") => Promise<boolean>;
  onClose: () => void;
}) {
  const [request, setRequest] = useState<ToolRequest | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const activeId = useRef(action?.id);
  activeId.current = action?.id;
  const requestId = action?.type === "mcp.call" ? action.payload?.request_id : undefined;

  useEffect(() => {
    setRequest(null); setError(""); setLoading(false);
    if (!action || action.type !== "mcp.call") return;
    if (typeof requestId !== "string" || !requestId) { setError("工具请求缺少有效编号，不能确认执行"); return; }
    const controller = new AbortController();
    setLoading(true);
    void api.get<ToolRequest>(`/agent-tools/requests/${encodeURIComponent(requestId)}`, { signal: controller.signal })
      .then(({ data }) => {
        if (controller.signal.aborted) return;
        setRequest(data);
        if (data.error !== undefined && data.error !== null) setError(agentOperationMessage(data.error));
      })
      .catch((failure: unknown) => {
        if (!controller.signal.aborted) setError(agentOperationError(failure, "操作状态读取失败"));
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [action?.id, action?.status, requestId, refresh]);

  const currentStatus = action?.type === "mcp.call" ? request?.status : action?.status;
  const pendingFailure = decisionFailure?.actionId === action?.id ? decisionFailure : undefined;
  const visibleError = error || pendingFailure?.message || (action?.type !== "mcp.call" && action?.error != null ? agentOperationMessage(action.error) : "");
  const canDecide = action?.status === "pending" && (action.type !== "mcp.call" || currentStatus === "pending");
  const previewAction = action && request ? { ...action, summary: request.summary, preview: request.preview } : action;
  const personalMcpPreviewMissing = action?.type === "personal_mcp.call" && !(action.preview?.operation_name && action.preview.method && action.preview.path && action.preview.params && action.preview.requires_confirmation === true);
  const decide = async (decision: "approved" | "rejected") => {
    if (!action || !canDecide || deciding || loading || (decision === "approved" && (error || personalMcpPreviewMissing))) return;
    try {
      if (await onDecide(action, decision)) onClose();
    } catch (failure: unknown) {
      const text = agentOperationError(failure, "操作未完成，请查看真实执行状态");
      setError(text); message.error(text);
      if (isAxiosError(failure)) {
        const outcome = failure.response?.data?.detail;
        if (request && outcome && typeof outcome === "object" && typeof outcome.status === "string" && Object.hasOwn(STATUS_NAMES, outcome.status)) {
          setRequest({ ...request, status: outcome.status as ToolRequest["status"], error: outcome.error });
        }
      }
      if (action.type === "mcp.call" && typeof requestId === "string" && requestId) {
        setLoading(true);
        try {
          const { data } = await api.get<ToolRequest>(`/agent-tools/requests/${encodeURIComponent(requestId)}`);
          if (activeId.current === action.id) setRequest(data);
        } catch (readError) {
          if (activeId.current === action.id) setError(`${text}；${agentOperationError(readError, "真实执行状态读取失败")}，禁止重复提交`);
        } finally { if (activeId.current === action.id) setLoading(false); }
      }
    }
  };

  return <Modal className="personal-action-confirmation" open={!!action} title="智能体操作确认" width={760} maskClosable={!deciding} closable={!deciding} keyboard={!deciding}
    onCancel={() => { if (!deciding) onClose(); }}
    footer={<Space wrap>
      {action?.type === "mcp.call" && <Button icon={<ReloadOutlined />} loading={loading} disabled={deciding} onClick={() => setRefresh((value) => value + 1)}>刷新状态</Button>}
      <Button disabled={deciding} onClick={onClose}>关闭</Button>
      {canDecide && <>
        <Button icon={<CloseOutlined />} disabled={deciding || loading || !!pendingFailure} onClick={() => void decide("rejected")}>取消操作</Button>
        <Button type="primary" icon={<CheckOutlined />} loading={deciding} disabled={deciding || loading || !!visibleError || personalMcpPreviewMissing || !previewAction || !hasAgentOperationPreview(previewAction)} onClick={() => void decide("approved")}>确认并执行</Button>
      </>}
    </Space>}>
    {currentStatus && <Tag color={currentStatus === "failed" ? "error" : currentStatus === "succeeded" ? "success" : "processing"} style={{ marginBottom: 12 }}>{STATUS_NAMES[currentStatus]}</Tag>}
    {visibleError && <Alert type="error" showIcon title={currentStatus === "failed" ? "操作执行失败" : "操作未完成"} description={visibleError} style={{ marginBottom: 12, overflowWrap: "anywhere", whiteSpace: "pre-wrap" }} />}
    {personalMcpPreviewMissing && <Alert type="error" showIcon title="外部工具调用预览不完整，不能确认执行" />}
    {pendingFailure && <Alert type={pendingFailure.state === "unknown" ? "warning" : "info"} showIcon title={pendingFailure.state === "syncing" ? "正在只读核对真实执行状态" : pendingFailure.state === "unknown" ? "执行状态未能核实，禁止重复提交" : "已读取最新对话状态，可在历史记录查看详情"} style={{ marginBottom: 12 }} />}
    {currentStatus && currentStatus !== "pending" && <Alert type={currentStatus === "succeeded" ? "success" : "warning"} showIcon title={currentStatus === "failed" ? "该确认请求已失败，不能重复执行" : `该请求${STATUS_NAMES[currentStatus]}，不能重复确认`} style={{ marginBottom: 12 }} />}
    <Spin spinning={loading}><div style={{ maxHeight: "60dvh", overflowY: "auto" }}>{previewAction && <AgentOperationPreview action={previewAction} />}</div></Spin>
  </Modal>;
}
