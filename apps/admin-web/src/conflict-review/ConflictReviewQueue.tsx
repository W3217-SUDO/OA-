import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Select, Table, Tabs, Tag } from "antd";
import { api } from "../api";
import { CONFLICT_REVIEW_UPDATED_EVENT, openConflictReview } from "./events";
import { conflictKindLabel, conflictStatusLabel } from "./types";
import type { ConflictKind, ConflictReview, ConflictReviewList } from "./types";
import "./conflict-review.css";

export function ConflictReviewQueue({ view, onPermission }: { view: "my" | "queue"; onPermission?: (allowed: boolean) => void }) {
  const [rows, setRows] = useState<ConflictReview[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [status, setStatus] = useState(view === "queue" ? "pending" : "");
  const [kind, setKind] = useState<ConflictKind>("absolute");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const reload = useCallback(() => setRevision((value) => value + 1), []);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    api.get<ConflictReviewList>("/conflict-reviews", { params: { view, status: status || undefined, kind: view === "queue" ? kind : undefined, page, page_size: pageSize }, signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted) { setRows(data.items); setTotal(data.total); onPermission?.(data.can_review); } })
      .catch((cause: any) => { if (!controller.signal.aborted && cause?.code !== "ERR_CANCELED") { setRows([]); setTotal(0); setError(cause?.response?.data?.detail || "利益冲突审查列表加载失败"); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [view, status, kind, page, pageSize, revision, onPermission]);
  useEffect(() => {
    window.addEventListener(CONFLICT_REVIEW_UPDATED_EVENT, reload);
    return () => window.removeEventListener(CONFLICT_REVIEW_UPDATED_EVENT, reload);
  }, [reload]);
  return <div>
    <div className="conflict-review-toolbar"><Select aria-label="按审查状态筛选" style={{ width: 190 }} value={status} onChange={(value) => { setStatus(value); setPage(1); }} options={[
      { value: "", label: "全部状态" }, { value: "pending", label: "待核查" }, { value: "approved_false_positive", label: "误判核查通过" }, { value: "approved_waiver", label: "书面豁免通过" }, { value: "rejected", label: "审核不通过" }, { value: "stopped", label: "已停止代理" },
    ]} /><Button onClick={reload}>刷新列表</Button></div>
    {view === "queue" && <Tabs activeKey={kind} onChange={(key) => { setKind(key as ConflictKind); setPage(1); }} items={[
      { key: "absolute", label: "绝对禁止" }, { key: "relative", label: "相对禁止" }, { key: "special", label: "专项待核实" },
    ]} />}
    {error && <Alert type="error" showIcon title={error} />}
    <Table<ConflictReview> rowKey="id" size="small" loading={loading} dataSource={rows} scroll={{ x: 850 }} pagination={{ current: page, pageSize, total, showSizeChanger: true, showTotal: (value) => `共 ${value} 条`, onChange: (next, size) => { setPage(next); setPageSize(size); } }} columns={[
      { title: "业务编号", dataIndex: "source_no", width: 160 }, { title: "业务名称", dataIndex: "source_title" },
      { title: "冲突类型", dataIndex: "kind", width: 130, render: (value: ConflictKind) => <Tag color={value === "absolute" ? "red" : "gold"}>{conflictKindLabel(value)}</Tag> },
      { title: "审查状态", dataIndex: "status", width: 145, render: conflictStatusLabel }, { title: "提交人", dataIndex: "submitter", width: 120 },
      { title: "操作", key: "action", width: 130, render: (_, row) => <Button type="link" onClick={() => openConflictReview(row.id, row.source_record_id)}>{view === "queue" ? "核查与审核" : "查看与反馈"}</Button> },
    ]} />
  </div>;
}
