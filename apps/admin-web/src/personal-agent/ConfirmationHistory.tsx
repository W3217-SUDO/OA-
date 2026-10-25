import { POPUP_WIDTH } from "../components/common/popupSize";
import { useEffect, useState } from "react";
import { Alert, Button, Drawer, Empty, Pagination, Select, Spin, Tag, Tooltip } from "antd";
import { AuditOutlined, EyeOutlined, ReloadOutlined } from "@ant-design/icons";
import { api } from "../api";
import { agentOperationMessage } from "../AgentOperationPreview";
import { ConfirmationHistoryDetails } from "./ConfirmationHistoryDetails";
import { errorText, type ConfirmationDetail, type ConfirmationHistoryPage, type ConfirmationRecord, type ConfirmationStatus } from "./types";
import "./confirmation-history.css";

const STATUS_LABELS: Record<ConfirmationStatus, string> = {
  pending: "待确认",
  executing: "执行中", succeeded: "已执行", failed: "执行失败", rejected: "已取消",
};
const STATUS_COLORS: Record<ConfirmationStatus, string> = {
  pending: "warning",
  executing: "processing", succeeded: "success", failed: "error", rejected: "default",
};
const PAGE_SIZE = 20;
const displayTime = (value: string | null) => {
  if (!value) return "未记录";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false });
};

export function ConfirmationHistory({ onReopen, busy = false }: { onReopen?: (detail: ConfirmationDetail) => Promise<void>; busy?: boolean }) {
  const [open, setOpen] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<ConfirmationRecord | null>(null);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<ConfirmationStatus | "">("");
  const [refresh, setRefresh] = useState(0);
  const [data, setData] = useState<ConfirmationHistoryPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    setData(null); setError(""); setLoading(true);
    void api.get<ConfirmationHistoryPage>("/personal-agent/confirmation-history", {
      params: { page, page_size: PAGE_SIZE, ...(status ? { status } : {}) }, signal: controller.signal,
    }).then(({ data: result }) => {
      if (!controller.signal.aborted) setData(result);
    }).catch((failure: unknown) => {
      if (!controller.signal.aborted) setError(errorText(failure, "历史确认记录加载失败"));
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [open, page, status, refresh]);

  return <>
    <Tooltip title="历史确认记录">
      <Button className="confirmation-history-trigger" type="text" icon={<AuditOutlined />} aria-label="历史确认记录" onClick={() => { setPage(1); setStatus(""); setOpen(true); }}>
        <span className="confirmation-history-label">历史确认记录</span>
      </Button>
    </Tooltip>
    <Drawer rootClassName="confirmation-history-drawer" title="历史确认记录" size={POPUP_WIDTH.sm} open={open} onClose={() => setOpen(false)}>
      <div className="confirmation-history-toolbar">
        <Select aria-label="确认记录状态" value={status} onChange={(value) => { setStatus(value); setPage(1); }} options={[
          { value: "", label: "全部确认记录" },
          ...Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label })),
        ]} />
        <Tooltip title="刷新确认记录"><Button icon={<ReloadOutlined />} aria-label="刷新确认记录" loading={loading} onClick={() => setRefresh((value) => value + 1)} /></Tooltip>
      </div>
      {error && <Alert type="error" showIcon title="历史确认记录加载失败" description={error} action={<Button onClick={() => setRefresh((value) => value + 1)}>重试</Button>} />}
      <div className="confirmation-history-content" aria-busy={loading}>
        {loading ? <div className="confirmation-history-loading" role="status"><Spin /><span>正在加载确认记录</span></div> : data && <>
          {!data.items.length ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={status ? "此状态下暂无确认记录" : "暂无历史确认记录"} /> : <ol className="confirmation-history-list">
            {data.items.map((item) => <li key={`${item.source}:${item.id}`}>
              <div className="confirmation-history-record-heading"><Tag color={STATUS_COLORS[item.status]}>{STATUS_LABELS[item.status]}</Tag><strong>{item.summary}</strong></div>
              <dl className="confirmation-history-metadata">
                <div><dt>请求时间</dt><dd>{displayTime(item.requested_at)}</dd></div>
                <div><dt>决定时间</dt><dd>{displayTime(item.decided_at)}</dd></div>
                {item.finished_at && <div><dt>结束时间</dt><dd>{displayTime(item.finished_at)}</dd></div>}
                <div><dt>操作人</dt><dd>{item.operator || "未记录"}</dd></div>
                {item.conversation_title && <div><dt>所属对话</dt><dd>{item.conversation_title}</dd></div>}
              </dl>
              {item.comment && <p className="confirmation-history-comment">决定备注：{item.comment}</p>}
              {item.error !== null && item.error !== undefined && <Alert type="error" showIcon title="执行错误" description={agentOperationMessage(item.error)} />}
              {item.result !== null && item.result !== undefined && <details className="confirmation-history-result">
                <summary>执行结果</summary>
                <pre>{typeof item.result === "string" ? item.result : JSON.stringify(item.result, null, 2)}</pre>
              </details>}
              <Button className="confirmation-history-detail-button" icon={<EyeOutlined />} disabled={busy} onClick={() => setSelectedRecord(item)}>查看详情</Button>
            </li>)}
          </ol>}
        </>}
      </div>
      {data && data.total > 0 && <div className="confirmation-history-pagination"><span>共 {data.total} 条</span><Pagination simple current={data.page} pageSize={data.page_size} total={data.total} showSizeChanger={false} onChange={setPage} /></div>}
    </Drawer>
    <ConfirmationHistoryDetails record={selectedRecord} onClose={() => setSelectedRecord(null)} onReopen={onReopen} busy={busy} onReopened={() => { setSelectedRecord(null); setOpen(false); }} />
  </>;
}
