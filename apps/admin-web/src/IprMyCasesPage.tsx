import { useCallback, useEffect, useState } from "react";
import { Button, Card, DatePicker, Empty, Form, Input, message } from "antd";
import Table from "./components/ResizableTable";
import { api } from "./api";
import { iprCaseDetailRoute } from "./ipr/iprCaseTabs";
import { FILTERS, IPR_MY_CASE_GROUPS, dateText, myCaseQueryParams, remainingDays, text, type FilterValues, type GroupKey } from "./ipr/myCases";

// 501613（范文玲 11-05）：知识产权中心“我的案件”，照老系统 案件中心 › 我的案件：
// 左侧按我在案件里的角色分组（带数量），右侧筛选和案件列表。前五组不含失效案件，失效的在“失效案件”里看。
type CaseRow = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  data?: Record<string, unknown> | null;
};
type Counts = Partial<Record<GroupKey, number>>;
const errorDetail = (error: any, fallback: string) => error?.response?.data?.detail || fallback;

export default function IprMyCasesPage({ onNavigate }: { onNavigate?: (route: string) => void }) {
  const [form] = Form.useForm<FilterValues>();
  const [group, setGroup] = useState<GroupKey>("mine");
  const [counts, setCounts] = useState<Counts>({});
  const [rows, setRows] = useState<CaseRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [filters, setFilters] = useState<FilterValues>({});
  const [loading, setLoading] = useState(false);
  const [people, setPeople] = useState<Record<string, string>>({});
  const roleView = IPR_MY_CASE_GROUPS.find((item) => item.key === group)?.roleView || "my:mine";

  useEffect(() => {
    api.get<Counts>("/ipr/cases/my-counts").then(({ data }) => setCounts(data)).catch(() => undefined);
    // 案件管理人迁移时存的是账号，列表里显示成姓名。
    api.get<{ items: { username: string; display_name: string }[] }>("/users/directory")
      .then(({ data }) => setPeople(Object.fromEntries(data.items.map((item) => [item.username, item.display_name]))))
      .catch(() => undefined);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<{ items: CaseRow[]; total: number }>("/ipr/cases", {
        params: { ...myCaseQueryParams(roleView, filters), page, page_size: pageSize },
      });
      setRows(data.items || []);
      setTotal(data.total || 0);
    } catch (error) {
      setRows([]);
      setTotal(0);
      message.error(errorDetail(error, "案件列表加载失败"));
    } finally {
      setLoading(false);
    }
  }, [roleView, filters, page, pageSize]);

  useEffect(() => { void load(); }, [load]);

  const exportExcel = async () => {
    try {
      const response = await api.get("/ipr/cases/export/excel", { params: myCaseQueryParams(roleView, filters), responseType: "blob" });
      const url = URL.createObjectURL(response.data as Blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `我的案件-${IPR_MY_CASE_GROUPS.find((item) => item.key === group)?.label || ""}.xls`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      message.error(errorDetail(error, "导出失败"));
    }
  };

  const person = (value: unknown) => {
    const raw = text(value);
    return people[raw] || raw;
  };
  const field = (row: CaseRow, ...keys: string[]) => {
    for (const key of keys) {
      const value = text(row.data?.[key]);
      if (value) return value;
    }
    return "";
  };

  return (
    <div className="page-shell ipr-my-cases-page" style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "flex-start" }}>
      <Card size="small" title="我的案件" style={{ width: 200, flex: "0 0 200px" }} styles={{ body: { padding: "4px 0" } }}>
        {IPR_MY_CASE_GROUPS.map((item) => (
          <div
            key={item.key}
            role="button"
            tabIndex={0}
            onClick={() => { setGroup(item.key); setPage(1); }}
            onKeyDown={(event) => { if (event.key === "Enter") { setGroup(item.key); setPage(1); } }}
            style={{
              padding: "6px 16px", cursor: "pointer",
              background: item.key === group ? "#e6f4ff" : undefined,
              color: item.key === group ? "#1677ff" : undefined,
            }}
          >
            {item.label}{counts[item.key] !== undefined ? `(${counts[item.key]})` : ""}
          </div>
        ))}
      </Card>
      <Card size="small" style={{ flex: "1 1 600px", minWidth: 0 }} title="案件列表">
        <Form form={form} layout="inline" style={{ rowGap: 8, marginBottom: 12 }}
          onFinish={(values) => { setFilters(values); setPage(1); }}>
          {FILTERS.map((item) => (
            <Form.Item key={item.name} name={item.name} label={item.label} style={{ width: 240 }}>
              <Input placeholder={item.placeholder || item.label} allowClear />
            </Form.Item>
          ))}
          <Form.Item name="application_dates" label="申请日">
            <DatePicker.RangePicker style={{ width: 240 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">查询</Button>
            <Button style={{ marginLeft: 8 }} onClick={() => { form.resetFields(); setFilters({}); setPage(1); }}>重置</Button>
            <Button style={{ marginLeft: 8 }} onClick={() => void exportExcel()}>导出Excel</Button>
          </Form.Item>
        </Form>
        <Table<CaseRow>
          rowKey="id"
          size="small"
          loading={loading}
          dataSource={rows}
          scroll={{ x: 1500 }}
          pagination={{
            current: page, pageSize, total, showSizeChanger: true, showTotal: (value) => `共 ${value} 条`,
            onChange: (next, size) => { setPage(size !== pageSize ? 1 : next); setPageSize(size); },
          }}
          locale={{ emptyText: <Empty description="暂无案件" /> }}
          columns={[
            {
              title: "案件编号", dataIndex: "serial_no", width: 140,
              render: (value: string, row) => (
                <Button type="link" size="small" style={{ padding: 0 }}
                  onClick={() => onNavigate?.(iprCaseDetailRoute({ id: row.id, serial_no: row.serial_no, data: { case_kind: field(row, "case_kind") } }))}>
                  {value}
                </Button>
              ),
            },
            { title: "申请人", key: "applicant", width: 180, ellipsis: true, render: (_: unknown, row) => field(row, "applicant", "applicant_name") },
            { title: "案件类型", key: "case_type", width: 120, render: (_: unknown, row) => field(row, "case_type") },
            { title: "案件阶段", key: "case_phase", width: 110, render: (_: unknown, row) => field(row, "case_phase") || row.status },
            { title: "申请号", key: "application_no", width: 140, render: (_: unknown, row) => field(row, "application_no") },
            { title: "申请日", key: "application_date", width: 100, render: (_: unknown, row) => dateText(field(row, "application_date", "case_request_date")) },
            { title: "案件/商标名称", dataIndex: "title", width: 200, ellipsis: true },
            { title: "商标类别", key: "trademark_class", width: 90, render: (_: unknown, row) => field(row, "trademark_ids") },
            { title: "案源人", key: "source_person", width: 90, render: (_: unknown, row) => field(row, "case_origin_people_name", "case_source") },
            { title: "案件管理人", key: "business_owner", width: 100, render: (_: unknown, row) => person(field(row, "business_owner_name", "business_owner")) },
            { title: "截止日", key: "deadline", width: 100, render: (_: unknown, row) => dateText(field(row, "deadline")) },
            { title: "剩余天数", key: "remaining", width: 90, align: "right", render: (_: unknown, row) => remainingDays(field(row, "deadline")) },
          ]}
        />
      </Card>
    </div>
  );
}
