import { useEffect, useState } from "react";
import { Alert, Button, Input, Space, Table } from "antd";
import type { TableColumnsType } from "antd";
import dayjs from "dayjs";
import { api } from "../api";
import FeedbackDetail from "./FeedbackDetail";
import FeedbackForm from "./FeedbackForm";
import type { FeedbackPage, FeedbackRecord } from "./types";

type Props = { sourcePage: string };

export default function FeedbackManager({ sourcePage }: Props) {
  const [rows, setRows] = useState<FeedbackRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [keyword, setKeyword] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [reload, setReload] = useState(0);
  const [viewing, setViewing] = useState<FeedbackRecord | null>(null);
  const [creating, setCreating] = useState(false);
  const listVisible = !viewing && !creating;

  useEffect(() => {
    if (!listVisible) return;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    void api.get<FeedbackPage>("/feedback", {
      params: { keyword: query, page, page_size: pageSize }, signal: controller.signal,
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
  }, [listVisible, page, pageSize, query, reload]);

  const columns: TableColumnsType<FeedbackRecord> = [
    { title: "提交人", width: 140, ellipsis: true,
      render: (_, row) => row.owner_display_name || row.owner },
    { title: "提交时间", width: 165, render: (_, row) => dayjs(row.created_at).format("YYYY-MM-DD HH:mm:ss") },
    { title: "问题描述", dataIndex: "description", ellipsis: true },
    { title: "提交页面", dataIndex: "page", width: 220, ellipsis: true },
    { title: "截图", width: 65, render: (_, row) => row.has_screenshot ? "有" : "无" },
    { title: "操作", width: 80, render: (_, row) => <Button type="link" size="small" onClick={() => setViewing(row)}>查看</Button> },
  ];

  if (viewing) return <FeedbackDetail feedback={viewing} onBack={() => setViewing(null)} />;
  if (creating) return <FeedbackForm sourcePage={sourcePage} onCancel={() => setCreating(false)}
    onSubmitted={() => { setCreating(false); setReload((current) => current + 1); }} />;

  return <section aria-label="问题反馈列表">
      <Space wrap style={{ marginBottom: 16 }}>
        <Input.Search value={keyword} allowClear maxLength={200} placeholder="搜索问题、提交人或页面"
          aria-label="搜索问题反馈" style={{ width: 320 }} enterButton="查询"
          onChange={(event) => setKeyword(event.target.value)}
          onSearch={(value) => { setQuery(value.trim()); setPage(1); setReload((current) => current + 1); }} />
        <Button onClick={() => setReload((current) => current + 1)} loading={loading}>刷新</Button>
        <Button type="primary" onClick={() => setCreating(true)}>提交反馈</Button>
      </Space>
      {error ? <Alert type="error" showIcon title={error} /> : <Table<FeedbackRecord>
        rowKey="id" size="small" tableLayout="fixed" columns={columns} dataSource={rows}
        loading={loading} scroll={{ x: 950 }} pagination={{
          current: page, pageSize, total, showSizeChanger: true, pageSizeOptions: [10, 20, 50, 100],
          showTotal: (count) => `共 ${count} 条`,
          onChange: (nextPage, nextSize) => { setPage(nextPage); setPageSize(nextSize); },
        }} />}
  </section>;
}
