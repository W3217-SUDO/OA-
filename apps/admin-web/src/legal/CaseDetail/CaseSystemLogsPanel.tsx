import { useEffect, useState } from "react";
import { Alert, Button, Descriptions, Empty, Modal, Pagination, Spin } from "antd";
import Table from "../../components/ResizableTable";
import { api } from "../../api";
import "./case-system-logs.css";

export interface CaseSystemLog {
  id: string;
  source: "current" | "legacy";
  source_id: number;
  source_case_no: string;
  action: string;
  comment: string;
  operator: string;
  operator_display_name: string;
  created_at: string | null;
}

interface LogPage {
  items: CaseSystemLog[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface CaseSystemLogsPanelProps {
  caseId: number;
  refreshKey?: number;
  casePersonDisplayName: (source: unknown, displayName?: unknown) => string;
}

const logTime = (value: string | null) => value ? value.replace("T", " ").slice(0, 19) : "—";

const CaseSystemLogsContent = ({ caseId, refreshKey, casePersonDisplayName }: CaseSystemLogsPanelProps) => {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [reload, setReload] = useState(0);
  const [result, setResult] = useState<LogPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<CaseSystemLog | null>(null);
  const [detail, setDetail] = useState<CaseSystemLog | null>(null);
  const [detailError, setDetailError] = useState("");

  const openDetail = (item: CaseSystemLog) => {
    setDetail(null);
    setDetailError("");
    setSelected(item);
  };

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setResult(null);
    setError("");
    void api.get<LogPage>(`/cases/${caseId}/system-logs`, {
      params: { page, page_size: pageSize }, signal: controller.signal,
    }).then(({ data }) => {
      if (!controller.signal.aborted) setResult(data);
    }).catch((cause) => {
      if (!controller.signal.aborted) setError(cause?.response?.data?.detail || "系统日志加载失败");
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [caseId, page, pageSize, refreshKey, reload]);

  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    setDetail(null);
    setDetailError("");
    void api.get<CaseSystemLog>(`/cases/${caseId}/system-logs/${selected.source}/${selected.source_id}`, {
      signal: controller.signal,
    }).then(({ data }) => {
      if (!controller.signal.aborted) setDetail(data);
    }).catch((cause) => {
      if (!controller.signal.aborted) setDetailError(cause?.response?.data?.detail || "系统日志详情加载失败");
    });
    return () => controller.abort();
  }, [caseId, selected]);

  return <section className="case-system-logs" aria-label="案件系统日志">
    {error ? <Alert type="error" showIcon title={error} action={<Button onClick={() => setReload(value => value + 1)}>重试</Button>} /> : <Spin spinning={loading}>
      <div className="case-system-logs-table">
        <Table rowKey="id" size="small" pagination={false} dataSource={result?.items || []} columns={[
          { title: "时间", dataIndex: "created_at", width: 170, render: logTime },
          { title: "操作", dataIndex: "action", width: 160 },
          { title: "操作人", width: 110, render: (_: unknown, row: CaseSystemLog) => casePersonDisplayName(row.operator, row.operator_display_name) },
          { title: "说明", dataIndex: "comment", render: (value: string) => <span className="case-system-log-content">{value}</span> },
          { title: "操作", width: 70, render: (_: unknown, row: CaseSystemLog) => <Button type="link" onClick={() => openDetail(row)}>查看</Button> },
        ]} />
      </div>
      <div className="case-system-logs-cards">
        {result?.items.map(item => <article key={item.id} className="case-system-log-card">
          <div className="case-system-log-meta"><time>{logTime(item.created_at)}</time><span>{casePersonDisplayName(item.operator, item.operator_display_name)}</span></div>
          <strong>{item.action}</strong><p className="case-system-log-content">{item.comment}</p>
          <Button type="link" onClick={() => openDetail(item)}>查看</Button>
        </article>)}
        {result?.total === 0 && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无系统日志" />}
      </div>
      {result && <Pagination current={result.page} pageSize={result.page_size} total={result.total} showSizeChanger pageSizeOptions={[15, 30, 50, 100]} showTotal={total => `共 ${total} 条`} onChange={(nextPage, nextSize) => { setPage(nextSize === pageSize ? nextPage : 1); setPageSize(nextSize); }} />}
    </Spin>}
    <Modal className="case-system-log-modal" open={Boolean(selected)} title="系统日志详情" footer={null} onCancel={() => setSelected(null)} destroyOnHidden width="min(720px, 96vw)">
      {detailError ? <Alert type="error" showIcon title={detailError} /> : !detail ? <Spin /> : <Descriptions column={1} size="small" className="case-system-log-detail" items={[
        { key: "time", label: "操作时间", children: logTime(detail.created_at) },
        { key: "operator", label: "操作人", children: casePersonDisplayName(detail.operator, detail.operator_display_name) },
        { key: "case", label: "来源案件", children: detail.source_case_no },
        { key: "action", label: "操作", children: detail.action },
        { key: "comment", label: "说明", children: <span className="case-system-log-content">{detail.comment}</span> },
      ]} />}
    </Modal>
  </section>;
};

export const CaseSystemLogsPanel = (props: CaseSystemLogsPanelProps) => <CaseSystemLogsContent key={props.caseId} {...props} />;
