import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Input, Popconfirm, Select, Space, Tag, message } from "antd";
import { api } from "../api";
import Table from "../components/ResizableTable";

type RecycleTable = { table: string; label: string; count: number };
type RecycleRow = {
  id: number; title: string; serial_no: string | null; module: string | null; status: string | null;
  deleted_at: string; deleted_by: string | null;
};
type RecycleList = { items: RecycleRow[]; total: number; page: number; page_size: number; label: string };

const PAGE_SIZE_OPTIONS = ["20", "50", "100"];
const when = (value: string) => new Date(value).toLocaleString("zh-CN", { hour12: false });

/** 管理员回收站：已删除的数据只做逻辑删除，这里可以按类型查看是谁何时删的并恢复；系统不提供物理清除。 */
export function SystemRecycleBin() {
  const [tables, setTables] = useState<RecycleTable[]>([]);
  const [table, setTable] = useState<string>("");
  const [keyword, setKeyword] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [data, setData] = useState<RecycleList | null>(null);
  const [selected, setSelected] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadTables = useCallback(async () => {
    try {
      const { data: result } = await api.get<{ items: RecycleTable[] }>("/system/recycle-bin/tables");
      setTables(result.items);
      setTable((current) => (current && result.items.some((item) => item.table === current) ? current : result.items[0]?.table || ""));
    } catch (failure: any) {
      setError(failure?.response?.data?.detail || "回收站读取失败");
    }
  }, []);

  const loadRows = useCallback(async () => {
    if (!table) { setData(null); return; }
    setLoading(true);
    try {
      const { data: result } = await api.get<RecycleList>("/system/recycle-bin", { params: { table, keyword, page, page_size: pageSize } });
      setData(result);
      setError("");
    } catch (failure: any) {
      setError(failure?.response?.data?.detail || "回收站读取失败");
    } finally {
      setLoading(false);
    }
  }, [table, keyword, page, pageSize]);

  useEffect(() => { void loadTables(); }, [loadTables]);
  useEffect(() => { void loadRows(); }, [loadRows]);

  const restore = async (ids: number[]) => {
    try {
      const { data: result } = await api.post<{ restored: number }>("/system/recycle-bin/restore", { table, ids });
      message.success(`已恢复 ${result.restored} 条`);
      setSelected([]);
      await Promise.all([loadTables(), loadRows()]);
    } catch (failure: any) {
      message.error(failure?.response?.data?.detail || "恢复失败");
    }
  };

  return (
    <div>
      <Alert type="info" showIcon style={{ marginBottom: 12 }}
        title="系统里的删除都是逻辑删除：数据只是被隐藏，仍保存在库里，附件文件也保留。这里可以查看是谁、何时删的，并恢复。" />
      {error && <Alert type="error" showIcon style={{ marginBottom: 12 }} title={error} />}
      <Space wrap style={{ marginBottom: 12 }}>
        <Select
          style={{ width: 280 }} value={table || undefined} placeholder={tables.length ? "选择数据类型" : "回收站是空的"}
          options={tables.map((item) => ({ value: item.table, label: `${item.label}（${item.count}）` }))}
          onChange={(value) => { setTable(value); setPage(1); setSelected([]); }}
        />
        <Input.Search
          allowClear style={{ width: 260 }} placeholder="按名称、编号搜索" disabled={!table}
          onSearch={(value) => { setKeyword(value); setPage(1); }}
        />
        <Popconfirm title={`恢复选中的 ${selected.length} 条数据？`} disabled={!selected.length} onConfirm={() => void restore(selected)}>
          <Button type="primary" disabled={!selected.length}>恢复选中</Button>
        </Popconfirm>
      </Space>
      <Table<RecycleRow>
        rowKey="id" loading={loading} dataSource={data?.items ?? []} locale={{ emptyText: "没有已删除的数据" }}
        rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys as number[]) }}
        pagination={{
          current: page, pageSize, total: data?.total ?? 0, showSizeChanger: true, pageSizeOptions: PAGE_SIZE_OPTIONS,
          showTotal: (count) => `共 ${count} 条`,
          onChange: (nextPage, nextSize) => { setPage(nextPage); setPageSize(nextSize); },
        }}
        columns={[
          { title: "名称", dataIndex: "title", ellipsis: true },
          { title: "编号", dataIndex: "serial_no", render: (value: string | null) => value || "—" },
          { title: "类别", dataIndex: "module", render: (value: string | null) => (value ? <Tag>{value}</Tag> : "—") },
          { title: "状态", dataIndex: "status", render: (value: string | null) => value || "—" },
          { title: "删除人", dataIndex: "deleted_by", render: (value: string | null) => value || "—" },
          { title: "删除时间", dataIndex: "deleted_at", render: when },
          { title: "操作", key: "action", render: (_: unknown, row: RecycleRow) => (
            <Popconfirm title="恢复这条数据？" onConfirm={() => void restore([row.id])}><Button size="small" type="link">恢复</Button></Popconfirm>
          ) },
        ]}
      />
    </div>
  );
}
