import { POPUP_WIDTH } from "../components/common/popupSize";
import { useEffect, useState } from "react";
import { Alert, Button, Modal, Space, Spin, Tag } from "antd";
import { ArrowRightOutlined, ReloadOutlined } from "@ant-design/icons";
import { api } from "../api";
import { AgentOperationPreview, agentOperationMessage } from "../AgentOperationPreview";
import { errorText, type ConfirmationDetail, type ConfirmationRecord } from "./types";

type Props = {
  record: ConfirmationRecord | null;
  onClose: () => void;
  onReopen?: (detail: ConfirmationDetail) => Promise<void>;
  onReopened: () => void;
  busy: boolean;
};

export function ConfirmationHistoryDetails({ record, onClose, onReopen, onReopened, busy }: Props) {
  const [detail, setDetail] = useState<ConfirmationDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [reopening, setReopening] = useState(false);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    setDetail(null); setError("");
    if (!record) return;
    const controller = new AbortController();
    setLoading(true);
    void api.get<ConfirmationDetail>(`/personal-agent/confirmation-history/${record.source}/${encodeURIComponent(record.id)}`, { signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted) setDetail(data); })
      .catch((failure: unknown) => { if (!controller.signal.aborted) setError(errorText(failure, "操作详情读取失败")); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [record?.source, record?.id, refresh]);

  const reopen = async () => {
    if (!detail || !onReopen || !detail.can_decide || detail.item.status !== "pending" || reopening || busy) return;
    setReopening(true); setError("");
    try { await onReopen(detail); onReopened(); }
    catch (failure) { setError(errorText(failure, "待确认操作恢复失败")); }
    finally { setReopening(false); }
  };

  return <Modal className="confirmation-history-detail" open={!!record} title="操作详情" width={POPUP_WIDTH.md}
    closable={!reopening} maskClosable={!reopening} keyboard={!reopening} onCancel={onClose}
    footer={<Space wrap>
      <Button icon={<ReloadOutlined />} loading={loading} disabled={reopening} onClick={() => setRefresh((value) => value + 1)}>刷新详情</Button>
      <Button disabled={reopening} onClick={onClose}>关闭</Button>
      {onReopen && detail?.can_decide && detail.item.status === "pending" && <Button type="primary" icon={<ArrowRightOutlined />} loading={reopening} disabled={busy || loading || !!error} onClick={() => void reopen()}>回到对话查看并确认</Button>}
    </Space>}>
    {error && <Alert type="error" showIcon title="操作未完成" description={error} />}
    <Spin spinning={loading}><div className="confirmation-history-detail-content">
      {detail && <>
        <strong>{detail.item.summary}</strong>
        {detail.item.status === "pending" && <Tag color="warning">待确认</Tag>}
        {detail.item.status === "pending" && !detail.can_decide && <Alert type="warning" showIcon title="无法重开原确认" description="原会话或有效操作关联不可用，此记录只能只读查看" />}
        {detail.item.error != null && <Alert type="error" showIcon title="执行错误" description={agentOperationMessage(detail.item.error)} />}
        {detail.action && <AgentOperationPreview action={detail.action} />}
        {!detail.action && detail.item.source === "mcp" && detail.request_preview && <AgentOperationPreview action={{ id: detail.item.id, type: "mcp.call", summary: detail.item.summary, payload: { request_id: detail.item.id }, preview: detail.request_preview }} />}
        {detail.item.result != null && <pre>{typeof detail.item.result === "string" ? detail.item.result : JSON.stringify(detail.item.result, null, 2)}</pre>}
      </>}
    </div></Spin>
  </Modal>;
}
