import { useRef, useState } from "react";
import { Alert, Button, List, message, Modal, Pagination, Select, Space, Spin, Tag } from "antd";
import { ArrowLeftOutlined, CheckOutlined, CloseOutlined, ReloadOutlined } from "@ant-design/icons";
import { api } from "./api";
import { AgentOperationPreview, agentOperationError, hasAgentOperationPreview, type AgentActionPreview } from "./AgentOperationPreview";
import { AgentToolResult } from "./AgentToolResult";

type ToolRequest = {
  request_id: string;
  status: "pending" | "executing" | "succeeded" | "failed" | "rejected";
  summary: string;
  preview: AgentActionPreview;
  created_at: string;
  error?: unknown;
  result?: unknown;
};
type RequestPage = { items: ToolRequest[]; total: number; page: number; page_size: number };
const STATUS_NAMES: Record<ToolRequest["status"], string> = {
  pending: "待确认", executing: "执行中", succeeded: "已执行", failed: "执行失败", rejected: "已取消",
};
const requestAction = (request: ToolRequest) => ({
  id: request.request_id, type: "mcp.call", summary: request.summary,
  payload: { request_id: request.request_id }, preview: request.preview,
});

export function AgentToolRequests({ buttonLabel = "MCP 待确认", titlePrefix = "MCP" }: { buttonLabel?: string; titlePrefix?: string } = {}) {
  const [open, setOpen] = useState(false);
  const [requests, setRequests] = useState<RequestPage | null>(null);
  const [active, setActive] = useState<ToolRequest | null>(null);
  const [loading, setLoading] = useState(false);
  const [deciding, setDeciding] = useState(false);
  const [error, setError] = useState("");
  const [requestStatus, setRequestStatus] = useState("pending");
  const decidingRef = useRef(false);
  const generationRef = useRef(0);

  const loadRequests = async (page = 1, status = requestStatus) => {
    const generation = ++generationRef.current;
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get<RequestPage>("/agent-tools/requests", { params: { status, page, page_size: 20 } });
      if (generation === generationRef.current) setRequests(data);
    } catch (failure: unknown) {
      if (generation === generationRef.current) setError(agentOperationError(failure, "待确认请求读取失败"));
    } finally {
      if (generation === generationRef.current) setLoading(false);
    }
  };
  const viewRequest = async (requestId: string) => {
    const generation = ++generationRef.current;
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get<ToolRequest>(`/agent-tools/requests/${encodeURIComponent(requestId)}`);
      if (generation === generationRef.current) setActive(data);
    } catch (failure: unknown) {
      if (generation === generationRef.current) setError(agentOperationError(failure, "操作参数读取失败"));
    } finally {
      if (generation === generationRef.current) setLoading(false);
    }
  };
  const decide = async (decision: "approved" | "rejected") => {
    if (!active || active.status !== "pending" || decidingRef.current) return;
    decidingRef.current = true;
    setDeciding(true);
    setError("");
    try {
      const { data } = await api.post<ToolRequest>(`/agent-tools/requests/${encodeURIComponent(active.request_id)}/decision`, { decision, comment: "智能体中心人工确认" }, { headers: { "X-OA-Agent-Confirmation": "frontend" } });
      setActive(data);
      if (data.status === "succeeded") message.success("操作已执行");
      else if (data.status === "rejected") message.success("操作已取消");
      else if (data.status === "failed") setError(typeof data.error === "string" ? data.error : JSON.stringify(data.error));
    } catch (failure: unknown) {
      setError(agentOperationError(failure, "操作未完成，请刷新查看执行状态"));
    } finally {
      decidingRef.current = false;
      setDeciding(false);
    }
  };
  const close = () => {
    if (decidingRef.current) return;
    generationRef.current++;
    setOpen(false);
    setActive(null);
    setLoading(false);
  };

  return <>
    <Button size="small" icon={<CheckOutlined />} onClick={() => { setOpen(true); setActive(null); void loadRequests(); }}>{buttonLabel}</Button>
    <Modal open={open} title={active ? `${titlePrefix}操作确认` : titlePrefix === "MCP" ? "MCP 待确认操作" : `${titlePrefix}操作记录`} width={760} onCancel={close} maskClosable={!deciding}
      footer={active ? <Space wrap>
        <Button icon={<ArrowLeftOutlined />} disabled={deciding} onClick={() => { setActive(null); void loadRequests(); }}>返回列表</Button>
        {active.status === "pending" && <>
          <Button icon={<CloseOutlined />} disabled={deciding || loading || Boolean(error)} onClick={() => void decide("rejected")}>取消操作</Button>
          <Button type="primary" icon={<CheckOutlined />} loading={deciding} disabled={loading || Boolean(error) || !hasAgentOperationPreview(requestAction(active))} onClick={() => void decide("approved")}>确认并执行</Button>
        </>}
      </Space> : null}
    >
      <Space style={{ marginBottom: 12 }} wrap>
        {!active && <Select value={requestStatus} disabled={loading} style={{ width: 140 }} options={[{ value: "pending", label: "待确认请求" }, { value: "", label: "全部请求" }]}
          onChange={(value) => { setRequestStatus(value); void loadRequests(1, value); }} />}
        {active && <Tag color={active.status === "failed" ? "error" : active.status === "succeeded" ? "success" : "processing"}>{STATUS_NAMES[active.status]}</Tag>}
        <Button size="small" icon={<ReloadOutlined />} disabled={deciding} loading={loading} onClick={() => active ? void viewRequest(active.request_id) : void loadRequests(requests?.page)}>刷新</Button>
      </Space>
      {error && <Alert type="error" showIcon title={error} style={{ marginBottom: 12 }} />}
      <Spin spinning={loading}>
        <div style={{ maxHeight: "60dvh", overflowY: "auto", overflowWrap: "anywhere" }}>
          {active ? <>
            <AgentOperationPreview action={requestAction(active)} />
            {active.error !== undefined && active.error !== null && <Alert type="error" showIcon title={typeof active.error === "string" ? active.error : JSON.stringify(active.error)} style={{ marginTop: 12 }} />}
            <AgentToolResult result={active.result} showDetails />
          </> : requests && !error && <List size="small" dataSource={requests.items} locale={{ emptyText: "暂无待确认操作" }} renderItem={(item) => <List.Item
            actions={[<Button key="view" size="small" disabled={loading} onClick={() => void viewRequest(item.request_id)}>查看并确认</Button>]}
          ><List.Item.Meta title={<><Tag>{STATUS_NAMES[item.status]}</Tag>{item.preview.operation_name}</>} description={<><div>{item.summary}</div><small>{item.request_id} · {item.created_at}</small></>} /></List.Item>} />}
        </div>
      </Spin>
      {!active && requests && !error && <Pagination size="small" current={requests.page} pageSize={requests.page_size} total={requests.total} showSizeChanger={false} disabled={loading} onChange={(page) => void loadRequests(page)} style={{ marginTop: 12 }} />}
    </Modal>
  </>;
}
