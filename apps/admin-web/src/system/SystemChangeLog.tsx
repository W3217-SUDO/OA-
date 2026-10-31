import { POPUP_WIDTH } from "../components/common/popupSize";
import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Checkbox, DatePicker, Input, Modal, Popconfirm, Select, Space, Tabs, Tag, message } from "antd";
import type { Dayjs } from "dayjs";
import { api } from "../api";
import Table from "../components/ResizableTable";
import { usePersonNames } from "../personNames";

type Change = { field: string; before: unknown; after: unknown };
type ChangeLog = {
  id: number; table: string; table_label: string; row_id: string; action: string; action_label: string; summary: string;
  changes: Change[]; actor: string; source: string; source_label: string; created_at: string;
  reverted_at: string | null; reverted_by: string | null; revert_of: number | null;
};
type Listing = {
  items: ChangeLog[]; total: number; sources: Record<string, string>; actions: Record<string, string>;
  tables: { table: string; label: string }[];
};

const PAGE_SIZE_OPTIONS = ["20", "50", "100"];
const ACTION_COLOR: Record<string, string> = { insert: "green", update: "blue", delete: "red", restore: "gold" };
const SOURCE_COLOR: Record<string, string> = { web: "default", mcp: "purple", agent: "cyan", system: "default" };
const when = (value: string | null) => (value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "—");
const show = (value: unknown) => (value === "__absent__" ? "（无）" : value === "__unknown__" ? "（未记录）" : value === null || value === undefined || value === "" ? "—"
  : typeof value === "object" ? JSON.stringify(value) : String(value));

type Operation = {
  id: number; username: string; source: string; source_label: string; token_name: string | null; tool_name: string;
  is_write: boolean; ok: boolean; pending: boolean; detail: string; created_at: string;
};

/** 智能体与 MCP 的每一次调用：谁、什么时候、调了什么、参数和结果（查询、写入、失败、待确认都记）。 */
function OperationLog() {
  const showPerson = usePersonNames();
  const [items, setItems] = useState<Operation[]>([]);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState<{ username?: string; source?: string; tool?: string; write_only?: boolean; failed_only?: boolean; range?: [Dayjs, Dayjs] | null }>({});
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { range, ...rest } = filters;
      const params: Record<string, unknown> = { ...rest, page, page_size: pageSize };
      if (range) { params.date_from = range[0].format("YYYY-MM-DD"); params.date_to = range[1].format("YYYY-MM-DD"); }
      const { data } = await api.get<{ items: Operation[]; total: number }>("/system/change-logs/operations", { params });
      setItems(data.items); setTotal(data.total); setError("");
    } catch (failure: any) {
      setError(failure?.response?.data?.detail || "操作日志读取失败");
    } finally {
      setLoading(false);
    }
  }, [filters, page, pageSize]);
  useEffect(() => { void load(); }, [load]);
  const set = (patch: Partial<typeof filters>) => { setFilters((current) => ({ ...current, ...patch })); setPage(1); };
  return (
    <div>
      {error && <Alert type="error" showIcon style={{ marginBottom: 12 }} title={error} />}
      <Space wrap style={{ marginBottom: 12 }}>
        <Select allowClear style={{ width: 130 }} placeholder="来源" value={filters.source} onChange={(value) => set({ source: value })}
          options={[{ value: "agent", label: "站内智能体" }, { value: "mcp", label: "MCP" }]} />
        <Input.Search allowClear style={{ width: 150 }} placeholder="操作人账号" onSearch={(value) => set({ username: value || undefined })} />
        <Input.Search allowClear style={{ width: 200 }} placeholder="接口名" onSearch={(value) => set({ tool: value || undefined })} />
        <Checkbox checked={!!filters.write_only} onChange={(event) => set({ write_only: event.target.checked || undefined })}>只看写入</Checkbox>
        <Checkbox checked={!!filters.failed_only} onChange={(event) => set({ failed_only: event.target.checked || undefined })}>只看失败</Checkbox>
        <DatePicker.RangePicker value={filters.range ?? null} onChange={(value) => set({ range: (value as [Dayjs, Dayjs]) ?? null })} />
      </Space>
      <Table<Operation>
        rowKey="id" loading={loading} dataSource={items} locale={{ emptyText: "没有操作日志" }} scroll={{ x: 1200 }}
        pagination={{ current: page, pageSize, total, showSizeChanger: true, pageSizeOptions: PAGE_SIZE_OPTIONS, showTotal: (count) => `共 ${count} 条`,
          onChange: (nextPage, nextSize) => { setPage(nextPage); setPageSize(nextSize); } }}
        columns={[
          { title: "时间", dataIndex: "created_at", width: 170, render: when },
          { title: "操作人", dataIndex: "username", width: 110, render: (value: string) => showPerson(value) },
          { title: "来源", dataIndex: "source", width: 140, render: (_: string, row: Operation) => <Tag color={SOURCE_COLOR[row.source]}>{row.source_label}{row.token_name ? ` · ${row.token_name}` : ""}</Tag> },
          { title: "接口", dataIndex: "tool_name", width: 260, ellipsis: true, render: (value: string, row: Operation) => <>{row.is_write && <Tag color="volcano">写入</Tag>}{value}</> },
          { title: "结果", key: "result", width: 90, render: (_: unknown, row: Operation) => row.pending ? <Tag color="gold">待确认</Tag> : <Tag color={row.ok ? "success" : "error"}>{row.ok ? "成功" : "失败"}</Tag> },
          { title: "参数与结果", dataIndex: "detail", width: 360, ellipsis: true },
        ]}
      />
    </div>
  );
}

export function SystemChangeLog() {
  return <Tabs items={[
    { key: "changes", label: "数据变更（可还原）", children: <DataChangeLog /> },
    { key: "operations", label: "智能体 / MCP 操作日志", children: <OperationLog /> },
  ]} />;
}

/** 管理员变更记录：每次新增、修改、删除、恢复的前后内容、操作人和来源；可一键还原。 */
function DataChangeLog() {
  const showPerson = usePersonNames();
  const [data, setData] = useState<Listing | null>(null);
  const [filters, setFilters] = useState<{ table?: string; source?: string; action?: string; actor?: string; keyword?: string; range?: [Dayjs, Dayjs] | null }>({});
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [detail, setDetail] = useState<ChangeLog | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { range, ...rest } = filters;
      const params: Record<string, unknown> = { ...rest, page, page_size: pageSize };
      if (range) { params.date_from = range[0].format("YYYY-MM-DD"); params.date_to = range[1].format("YYYY-MM-DD"); }
      const { data: result } = await api.get<Listing>("/system/change-logs", { params });
      setData(result);
      setError("");
    } catch (failure: any) {
      setError(failure?.response?.data?.detail || "变更记录读取失败");
    } finally {
      setLoading(false);
    }
  }, [filters, page, pageSize]);
  useEffect(() => { void load(); }, [load]);

  const openDetail = async (id: number) => {
    try { setDetail((await api.get<ChangeLog>(`/system/change-logs/${id}`)).data); } catch { message.error("读取详情失败"); }
  };
  const revert = async (row: ChangeLog, force = false) => {
    try {
      await api.post(`/system/change-logs/${row.id}/revert`, { force });
      message.success("已还原");
      setDetail(null);
      await load();
    } catch (failure: any) {
      const detailInfo = failure?.response?.data?.detail;
      if (failure?.response?.status === 409 && detailInfo?.conflicts) {
        Modal.confirm({
          title: "这条数据在这次变更之后又被修改过",
          content: `直接还原会覆盖后来的修改（${detailInfo.conflicts.join("、")}）。仍要还原吗？`,
          okText: "仍然还原", okButtonProps: { danger: true }, cancelText: "取消",
          onOk: () => revert(row, true),
        });
        return;
      }
      message.error(typeof detailInfo === "string" ? detailInfo : detailInfo?.detail || "还原失败");
    }
  };
  const set = (patch: Partial<typeof filters>) => { setFilters((current) => ({ ...current, ...patch })); setPage(1); };
  const canRevert = (row: ChangeLog) => !row.reverted_at && row.row_id !== "0" && row.row_id !== "" && ["insert", "update", "delete", "restore"].includes(row.action);
  const revertTitle = (row: ChangeLog) => ({ insert: "还原这次新增（逻辑删除该数据）？", update: "把这条数据改回修改前的值？",
    delete: "恢复这条被删除的数据？", restore: "撤销这次恢复（重新删除）？" } as Record<string, string>)[row.action];

  return (
    <div>
      <Alert type="info" showIcon style={{ marginBottom: 12 }}
        title="系统、MCP 和智能体的每一次新增、修改、删除、恢复都会记录在这里：改了什么、改之前是什么、谁改的、从哪里改的。可以一键还原；还原本身也会留下记录。" />
      {error && <Alert type="error" showIcon style={{ marginBottom: 12 }} title={error} />}
      <Space wrap style={{ marginBottom: 12 }}>
        <Select allowClear style={{ width: 220 }} placeholder="数据类型" value={filters.table} onChange={(value) => set({ table: value })}
          options={(data?.tables ?? []).map((item) => ({ value: item.table, label: item.label }))} showSearch optionFilterProp="label" />
        <Select allowClear style={{ width: 120 }} placeholder="来源" value={filters.source} onChange={(value) => set({ source: value })}
          options={Object.entries(data?.sources ?? {}).map(([value, label]) => ({ value, label }))} />
        <Select allowClear style={{ width: 110 }} placeholder="操作" value={filters.action} onChange={(value) => set({ action: value })}
          options={Object.entries(data?.actions ?? {}).map(([value, label]) => ({ value, label }))} />
        <Input.Search allowClear style={{ width: 150 }} placeholder="操作人账号" onSearch={(value) => set({ actor: value || undefined })} />
        <Input.Search allowClear style={{ width: 200 }} placeholder="按名称、编号搜索" onSearch={(value) => set({ keyword: value || undefined })} />
        <DatePicker.RangePicker value={filters.range ?? null} onChange={(value) => set({ range: (value as [Dayjs, Dayjs]) ?? null })} />
      </Space>
      <Table<ChangeLog>
        rowKey="id" loading={loading} dataSource={data?.items ?? []} locale={{ emptyText: "没有变更记录" }} scroll={{ x: 1300 }}
        pagination={{
          current: page, pageSize, total: data?.total ?? 0, showSizeChanger: true, pageSizeOptions: PAGE_SIZE_OPTIONS,
          showTotal: (count) => `共 ${count} 条`, onChange: (nextPage, nextSize) => { setPage(nextPage); setPageSize(nextSize); },
        }}
        columns={[
          { title: "时间", dataIndex: "created_at", width: 170, render: when },
          { title: "操作", dataIndex: "action", width: 80, render: (_: string, row: ChangeLog) => <Tag color={ACTION_COLOR[row.action]}>{row.action_label}</Tag> },
          { title: "数据", key: "data", width: 240, ellipsis: true, render: (_: unknown, row: ChangeLog) => <span>{row.table_label} · {row.summary || `#${row.row_id}`}</span> },
          { title: "改动", dataIndex: "changes", width: 320, ellipsis: true, render: (changes: Change[]) => changes.length
            ? changes.slice(0, 3).map((item) => `${item.field}: ${show(item.before)} → ${show(item.after)}`).join("；") + (changes.length > 3 ? ` 等 ${changes.length} 项` : "") : "—" },
          { title: "操作人", dataIndex: "actor", width: 110, render: (value: string) => showPerson(value) },
          { title: "来源", dataIndex: "source", width: 80, render: (_: string, row: ChangeLog) => <Tag color={SOURCE_COLOR[row.source]}>{row.source_label}</Tag> },
          { title: "状态", key: "state", width: 100, render: (_: unknown, row: ChangeLog) => row.reverted_at ? <Tag>已还原</Tag> : row.revert_of ? <Tag color="gold">还原操作</Tag> : "—" },
          { title: "", key: "op", width: 130, render: (_: unknown, row: ChangeLog) => (
            <Space size={4}>
              <Button size="small" type="link" onClick={() => void openDetail(row.id)}>详情</Button>
              {canRevert(row) && <Popconfirm title={revertTitle(row)} onConfirm={() => void revert(row)}><Button size="small" type="link">还原</Button></Popconfirm>}
            </Space>
          ) },
        ]}
      />
      <Modal open={!!detail} width={POPUP_WIDTH.md} title={detail ? `${detail.table_label} · ${detail.summary || `#${detail.row_id}`}（${detail.action_label}）` : ""}
        onCancel={() => setDetail(null)} footer={detail && canRevert(detail)
          ? <Popconfirm title={revertTitle(detail)} onConfirm={() => void revert(detail)}><Button type="primary">还原</Button></Popconfirm> : null}>
        {detail && <>
          <p>{when(detail.created_at)} · {showPerson(detail.actor)} · 来源：{detail.source_label}{detail.reverted_at ? ` · 已由 ${showPerson(detail.reverted_by)} 于 ${when(detail.reverted_at)} 还原` : ""}</p>
          <Table<Change> size="small" rowKey="field" pagination={false} dataSource={detail.changes} locale={{ emptyText: "（新增、删除、恢复不记录字段明细）" }}
            columns={[
              { title: "字段", dataIndex: "field", width: 200 },
              { title: "修改前", dataIndex: "before", render: (value: unknown) => <span style={{ wordBreak: "break-all" }}>{show(value)}</span> },
              { title: "修改后", dataIndex: "after", render: (value: unknown) => <span style={{ wordBreak: "break-all" }}>{show(value)}</span> },
            ]} />
        </>}
      </Modal>
    </div>
  );
}
