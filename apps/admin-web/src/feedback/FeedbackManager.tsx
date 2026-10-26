import { useEffect, useState } from "react";
import { Alert, Button, DatePicker, Input, message, Popconfirm, Segmented, Select, Space, Tag } from "antd";
import type { Dayjs } from "dayjs";
import Table from "../components/ResizableTable";
import type { TableColumnsType } from "antd";
import dayjs from "dayjs";
import { api } from "../api";
import FeedbackDetail from "./FeedbackDetail";
import FeedbackForm from "./FeedbackForm";
import { consumeFeedbackTarget, type FeedbackPageOption } from "./navigation";
import type { FeedbackPage, FeedbackRecord, FeedbackStatusCounts } from "./types";

type Props = {
  sourceRoute: string;
  pageControls: Record<string, string[]>;
  openPages: FeedbackPageOption[];
  menuPages: FeedbackPageOption[];
  onNavigate: (route: string) => void;
  /** 问题处理中心：只看和处理，不在这里提交；状态改成带数量的页签，多一列“涉及按钮”。 */
  center?: boolean;
  /** 问题反馈页头部的“提交反馈 / 我的反馈”切换：由页面控制，列表只看自己提交或指派给自己的。 */
  view?: "create" | "mine";
  onViewChange?: (view: "create" | "mine") => void;
  /** 头部切换按钮每点一次加一，用来从详情回到对应视图。 */
  navKey?: number;
  onChanged?: () => void;
};
// 处理流程：待处理 →（处理人处理完）待验证 →（提交人验证通过）已解决；没解决可重新打开回到待处理。
const statuses = ["待处理", "待验证", "已解决"];
const statusColors: Record<string, string> = {
  待处理: "warning", 待验证: "processing", 已解决: "success",
};

export default function FeedbackManager({ sourceRoute, pageControls, openPages, menuPages, onNavigate, center = false, view, onViewChange, navKey = 0, onChanged }: Props) {
  const [rows, setRows] = useState<FeedbackRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [keyword, setKeyword] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  // 按提交日期筛选（含结束当天），后端按北京时间整天算。
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);
  const dateParams = {
    date_from: dateRange?.[0]?.format("YYYY-MM-DD") || undefined,
    date_to: dateRange?.[1]?.format("YYYY-MM-DD") || undefined,
  };
  const dateKey = `${dateParams.date_from || ""}~${dateParams.date_to || ""}`;
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [reload, setReload] = useState(0);
  const [viewingId, setViewingId] = useState<number | null>(null);
  // 从侧栏“问题反馈”进来时直接进入填写；从通知打开指定反馈时由 openTarget 切回详情。
  const [creatingState, setCreatingState] = useState(!center && Boolean(sourceRoute));
  const creating = view ? view === "create" : creatingState;
  const setCreating = (next: boolean) => {
    if (onViewChange) onViewChange(next ? "create" : "mine");
    else setCreatingState(next);
  };
  const mine = Boolean(view);
  const [statusCounts, setStatusCounts] = useState<FeedbackStatusCounts | null>(null);
  // 管理员在问题处理中心可以删除问题（逻辑删除，回收站可恢复）。
  const [canDelete, setCanDelete] = useState(false);
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

  useEffect(() => { if (navKey) setViewingId(null); }, [navKey]);

  useEffect(() => {
    if (!listVisible) return;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    void api.get<FeedbackPage>("/feedback", {
      params: { keyword: query, status, page, page_size: pageSize, mine: mine || undefined, ...dateParams }, signal: controller.signal,
    }).then(({ data }) => {
      if (controller.signal.aborted) return;
      setRows(data.items);
      setTotal(data.total);
      setCanDelete(Boolean(data.can_delete));
    }).catch((failure: any) => {
      if (controller.signal.aborted) return;
      setError(failure?.response?.data?.detail || "反馈列表加载失败");
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [listVisible, page, pageSize, query, status, reload, mine, dateKey]);

  // 状态页签上的数量随列表一起刷新（处理完回到列表也会更新）。
  useEffect(() => {
    if (!center || !listVisible) return;
    let cancelled = false;
    void api.get<FeedbackStatusCounts>("/feedback/status-counts", { params: dateParams }).then(({ data }) => {
      if (!cancelled) setStatusCounts(data);
    }).catch(() => undefined);
    return () => { cancelled = true; };
  }, [center, listVisible, reload, dateKey]);

  const removeFeedback = async (row: FeedbackRecord) => {
    try {
      await api.delete(`/feedback/${row.id}`);
      message.success(`已删除问题 ${row.serial_no}`);
      setReload((current) => current + 1);
      onChanged?.();
    } catch (failure: any) {
      message.error(failure?.response?.data?.detail || "删除失败");
    }
  };
  const showDelete = center && canDelete;

  const columns: TableColumnsType<FeedbackRecord> = [
    { title: "编号", dataIndex: "serial_no", width: 215, ellipsis: true,
      render: (value, row) => <Button type="link" size="small" onClick={() => setViewingId(row.id)}>{value}</Button> },
    { title: "问题描述", dataIndex: "description", width: 280, ellipsis: true },
    { title: "状态", dataIndex: "status", width: 100,
      render: (value: string) => <Tag color={statusColors[value] || "default"}>{value}</Tag> },
    { title: "提交人", width: 105, ellipsis: true, render: (_, row) => row.owner_display_name || row.owner },
    { title: "最近更新", width: 160, render: (_, row) => dayjs(row.updated_at || row.created_at).format("YYYY-MM-DD HH:mm") },
    { title: "提交页面", dataIndex: "page", width: 180, ellipsis: true },
    ...(center ? [{ title: "涉及按钮", key: "controls", width: 160, ellipsis: true,
      render: (_: unknown, row: FeedbackRecord) => row.controls?.length ? row.controls.join("、") : "—" }] : []),
    { title: "截图/附件", width: 85, render: (_, row) => row.has_screenshot ? "有" : "无" },
    ...(showDelete ? [{ title: "操作", key: "actions", width: 80,
      render: (_: unknown, row: FeedbackRecord) => <Popconfirm title={`删除问题 ${row.serial_no}？`}
        description="删除后可由管理员在“系统管理 → 回收站”恢复。" okText="删除" cancelText="取消"
        okButtonProps={{ danger: true }} onConfirm={() => removeFeedback(row)}>
        <Button type="link" size="small" danger>删除</Button>
      </Popconfirm> }] : []),
  ];

  if (viewingId) return <FeedbackDetail feedbackId={viewingId} onNavigate={onNavigate} onBack={() => { setViewingId(null); setReload((current) => current + 1); onChanged?.(); }} />;
  if (creating) return <FeedbackForm sourceRoute={sourceRoute} pageControls={pageControls} openPages={openPages} menuPages={menuPages} onCancel={() => setCreating(false)}
    onSubmitted={(id) => { setCreating(false); setViewingId(id); onChanged?.(); }} />;

  return <section aria-label="问题反馈列表">
      <Space wrap style={{ marginBottom: 16 }}>
        <Input.Search value={keyword} allowClear maxLength={200} placeholder="搜索问题、提交人或页面"
          aria-label="搜索问题反馈" style={{ width: 320 }} enterButton="查询"
          onChange={(event) => setKeyword(event.target.value)}
          onSearch={(value) => { setQuery(value.trim()); setPage(1); setReload((current) => current + 1); }} />
        {!center && <Select aria-label="筛选反馈状态" value={status} style={{ width: 130 }} options={[
          { value: "", label: "全部状态" }, ...statuses.map((value) => ({ value, label: value })),
        ]} onChange={(value) => { setStatus(value); setPage(1); }} />}
        <DatePicker.RangePicker aria-label="按提交日期筛选" value={dateRange} allowEmpty={[true, true]}
          placeholder={["提交开始日期", "提交结束日期"]} style={{ width: 280 }}
          onChange={(value) => { setDateRange(value as [Dayjs | null, Dayjs | null] | null); setPage(1); }} />
        <Button onClick={() => setReload((current) => current + 1)} loading={loading}>刷新</Button>
        {!center && !view && <Button type="primary" onClick={() => setCreating(true)}>提交反馈</Button>}
      </Space>
      {center && <Segmented aria-label="按状态筛选反馈" style={{ marginBottom: 12 }} value={status}
        onChange={(value) => { setStatus(String(value)); setPage(1); }}
        options={[{ value: "", label: `全部 ${statusCounts?.total ?? ""}` },
          ...statuses.map((value) => ({ value, label: `${value} ${statusCounts?.counts[value] ?? ""}` }))]} />}
      {error ? <Alert type="error" showIcon title={error} /> : <Table<FeedbackRecord>
        rowKey="id" size="small" tableLayout="fixed" columns={columns} dataSource={rows}
        loading={loading} scroll={{ x: (center ? 1285 : 1125) + (showDelete ? 80 : 0) }} pagination={{
          current: page, pageSize, total, showSizeChanger: true, pageSizeOptions: [10, 20, 50, 100],
          showTotal: (count) => `共 ${count} 条`,
          onChange: (nextPage, nextSize) => { setPage(nextPage); setPageSize(nextSize); },
        }} />}
  </section>;
}
