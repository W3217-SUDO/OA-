import { useEffect, useState } from "react";
import { Alert, Button, Input, Select, Space, Table, Tag } from "antd";
import type { TableColumnsType } from "antd";
import dayjs from "dayjs";
import { api } from "../api";
import FeedbackDetail from "./FeedbackDetail";
import FeedbackForm from "./FeedbackForm";
import { consumeFeedbackTarget } from "./navigation";
import type { FeedbackPage, FeedbackRecord } from "./types";

type Props = { sourcePage: string };
const statuses = ["待处理", "处理中", "待补充", "待验证", "已解决"];
const statusColors: Record<string, string> = {
  待处理: "default", 处理中: "processing", 待补充: "warning", 待验证: "cyan", 已解决: "success",
};

export default function FeedbackManager({ sourcePage }: Props) {
  const [rows, setRows] = useState<FeedbackRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [keyword, setKeyword] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [reload, setReload] = useState(0);
  const [viewingId, setViewingId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const listVisible = !viewingId && !creating;

  useEffect(() => {
    const openTarget = () => {
      const target = consumeFeedbackTarget();
      if (target) { setCreating(false); setViewingId(target); }
    };
    openTarget();
    window.addEventListener("sunhold:feedback-target", openTarget);
    return () => window.removeEventListener("sunhold:feedback-target", openTarget);
  }, []);

  useEffect(() => {
    if (!listVisible) return;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    void api.get<FeedbackPage>("/feedback", {
      params: { keyword: query, status, page, page_size: pageSize }, signal: controller.signal,
    }).then(({ data }) => {
      if (controller.signal.aborted) return;
      setRows(data.items);
      setTotal(data.total);
    }).catch((failure: any) => {
      if (controller.signal.aborted) return;
      setError(failure?.response?.data?.detail || "反馈列表加载失败");
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [listVisible, page, pageSize, query, status, reload]);

  const columns: TableColumnsType<FeedbackRecord> = [
    { title: "编号", dataIndex: "serial_no", width: 215, ellipsis: true,
      render: (value, row) => <Button type="link" size="small" onClick={() => setViewingId(row.id)}>{value}</Button> },
    { title: "问题描述", dataIndex: "description", width: 280, ellipsis: true },
    { title: "状态", dataIndex: "status", width: 100,
      render: (value: string) => <Tag color={statusColors[value] || "default"}>{value}</Tag> },
    { title: "提交人", width: 105, ellipsis: true, render: (_, row) => row.owner_display_name || row.owner },
    { title: "处理人", width: 105, ellipsis: true, render: (_, row) => row.assignee_display_name || row.assignee || "未指派" },
    { title: "最近更新", width: 160, render: (_, row) => dayjs(row.updated_at || row.created_at).format("YYYY-MM-DD HH:mm") },
    { title: "提交页面", dataIndex: "page", width: 180, ellipsis: true },
    { title: "截图", width: 65, render: (_, row) => row.has_screenshot ? "有" : "无" },
  ];

  if (viewingId) return <FeedbackDetail feedbackId={viewingId} onBack={() => { setViewingId(null); setReload((current) => current + 1); }} />;
  if (creating) return <FeedbackForm sourcePage={sourcePage} onCancel={() => setCreating(false)}
    onSubmitted={(id) => { setCreating(false); setViewingId(id); }} />;

  return <section aria-label="问题反馈列表">
      <Space wrap style={{ marginBottom: 16 }}>
        <Input.Search value={keyword} allowClear maxLength={200} placeholder="搜索问题、提交人或页面"
          aria-label="搜索问题反馈" style={{ width: 320 }} enterButton="查询"
          onChange={(event) => setKeyword(event.target.value)}
          onSearch={(value) => { setQuery(value.trim()); setPage(1); setReload((current) => current + 1); }} />
        <Select aria-label="筛选反馈状态" value={status} style={{ width: 130 }} options={[
          { value: "", label: "全部状态" }, ...statuses.map((value) => ({ value, label: value })),
        ]} onChange={(value) => { setStatus(value); setPage(1); }} />
        <Button onClick={() => setReload((current) => current + 1)} loading={loading}>刷新</Button>
        <Button type="primary" onClick={() => setCreating(true)}>提交反馈</Button>
      </Space>
      {error ? <Alert type="error" showIcon title={error} /> : <Table<FeedbackRecord>
        rowKey="id" size="small" tableLayout="fixed" columns={columns} dataSource={rows}
        loading={loading} scroll={{ x: 1210 }} pagination={{
          current: page, pageSize, total, showSizeChanger: true, pageSizeOptions: [10, 20, 50, 100],
          showTotal: (count) => `共 ${count} 条`,
          onChange: (nextPage, nextSize) => { setPage(nextPage); setPageSize(nextSize); },
        }} />}
  </section>;
}
