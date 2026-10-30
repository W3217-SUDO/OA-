import { useCallback, useEffect, useState } from "react";
import dayjs, { type Dayjs } from "dayjs";
import { Button, Card, DatePicker, Empty, Form, Input, Modal, Popconfirm, Space, Tag, message } from "antd";
import Table from "./components/ResizableTable";
import { api } from "./api";

// BUG20261030004：知识产权中心“专利年费”，照老系统中间一栏 年费清单 / 年费监控，每项带数量，点一项右边出案件。
type SummaryItem = { key: string; group: string; label: string; count: number };
type FeeRow = {
  case_id: number;
  serial_no: string;
  case_name: string;
  case_type: string;
  customer: string;
  applicant: string;
  application_no: string;
  application_date: string;
  procurator: string;
  fee_year: number;
  year_no: number;
  fee_name: string;
  standard_amount: number;
  due_date: string;
  late_deadline: string;
  status: string;
  paid_date: string | null;
};

const VIEW_PARAM = "fee_view";
const errorDetail = (error: any, fallback: string) => error?.response?.data?.detail || fallback;

const initialView = () => new URLSearchParams(window.location.search).get(VIEW_PARAM) || "";

export default function IprAnnualFeePage() {
  const [summary, setSummary] = useState<SummaryItem[]>([]);
  const [view, setView] = useState(initialView);
  const [rows, setRows] = useState<FeeRow[]>([]);
  const [keyword, setKeyword] = useState("");
  const [loading, setLoading] = useState(false);
  const [paying, setPaying] = useState<FeeRow | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm<{ paid_date: Dayjs; notes: string }>();

  const loadSummary = useCallback(async () => {
    try {
      const { data } = await api.get<{ items: SummaryItem[] }>("/ipr/annual-fee-monitor/summary");
      setSummary(data.items);
      setView((current) => (current && data.items.some((item) => item.key === current) ? current : data.items[0]?.key || ""));
    } catch (error) {
      message.error(errorDetail(error, "专利年费数量加载失败"));
    }
  }, []);

  const loadRows = useCallback(async (key: string, word: string) => {
    if (!key) return;
    setLoading(true);
    try {
      const { data } = await api.get<{ items: FeeRow[] }>("/ipr/annual-fee-monitor/items", { params: { view: key, keyword: word.trim() || undefined } });
      setRows(data.items);
    } catch (error) {
      message.error(errorDetail(error, "专利年费列表加载失败"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadSummary(); }, [loadSummary]);
  useEffect(() => {
    if (!view) return;
    const params = new URLSearchParams(window.location.search);
    if (params.get(VIEW_PARAM) !== view) {
      params.set(VIEW_PARAM, view);
      window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}${window.location.hash}`);
    }
    void loadRows(view, keyword);
    // 关键字只在点“查询”时生效。
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, loadRows]);

  const refresh = async () => {
    await Promise.all([loadSummary(), loadRows(view, keyword)]);
  };

  const openCase = (row: FeeRow) => {
    const params = new URLSearchParams(window.location.search);
    params.set("page", "ipr-patent");
    params.delete(VIEW_PARAM);
    params.set("record_id", String(row.case_id));
    window.location.search = params.toString();
  };

  const startPay = (row: FeeRow) => {
    setPaying(row);
    form.setFieldsValue({ paid_date: dayjs(), notes: "" });
  };

  const submitPaid = async () => {
    if (!paying) return;
    const values = await form.validateFields();
    setSaving(true);
    try {
      await api.post("/ipr/annual-fee-monitor/paid", {
        case_id: paying.case_id, fee_year: paying.fee_year,
        paid_date: values.paid_date.format("YYYY-MM-DD"), notes: values.notes || "",
      });
      message.success(`${paying.serial_no} ${paying.fee_name}已登记缴纳`);
      setPaying(null);
      await refresh();
    } catch (error) {
      message.error(errorDetail(error, "登记已缴失败"));
    } finally {
      setSaving(false);
    }
  };

  const undoPaid = async (row: FeeRow) => {
    try {
      await api.post("/ipr/annual-fee-monitor/unpaid", { case_id: row.case_id, fee_year: row.fee_year });
      message.success(`${row.serial_no} ${row.fee_name}已改回待缴`);
      await refresh();
    } catch (error) {
      message.error(errorDetail(error, "撤销已缴失败"));
    }
  };

  const groups = ["年费清单", "年费监控"].map((name) => ({ name, items: summary.filter((item) => item.group === name) }));
  const current = summary.find((item) => item.key === view);

  return (
    <div className="page-shell ipr-annual-fee-page" style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "flex-start" }}>
      <Card size="small" title="专利年费" style={{ width: 200, flex: "0 0 200px" }} styles={{ body: { padding: "4px 0" } }}>
        {groups.map((group) => (
          <div key={group.name} style={{ marginBottom: 8 }}>
            <div style={{ padding: "6px 12px", fontWeight: 600 }}>{group.name}</div>
            {group.items.map((item) => (
              <div
                key={item.key}
                role="button"
                tabIndex={0}
                onClick={() => setView(item.key)}
                onKeyDown={(event) => { if (event.key === "Enter") setView(item.key); }}
                style={{
                  padding: "5px 12px 5px 24px", cursor: "pointer",
                  background: item.key === view ? "#e6f4ff" : undefined,
                  color: item.key === view ? "#1677ff" : undefined,
                }}
              >
                {item.label}({item.count})
              </div>
            ))}
          </div>
        ))}
      </Card>
      <Card
        size="small"
        style={{ flex: "1 1 600px", minWidth: 0 }}
        title={current ? `${current.group} · ${current.label}` : "专利年费"}
        extra={(
          <Space>
            <Input
              placeholder="案号/案件名称/客户/申请号"
              value={keyword}
              allowClear
              onChange={(event) => setKeyword(event.target.value)}
              onPressEnter={() => void loadRows(view, keyword)}
              style={{ width: 220 }}
            />
            <Button type="primary" onClick={() => void loadRows(view, keyword)}>查询</Button>
          </Space>
        )}
      >
        <Table<FeeRow>
          rowKey={(row) => `${row.case_id}-${row.fee_year}`}
          size="small"
          loading={loading}
          dataSource={rows}
          scroll={{ x: 1300 }}
          pagination={{ defaultPageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
          locale={{ emptyText: <Empty description="没有需要缴纳的年费" /> }}
          columns={[
            { title: "案号", dataIndex: "serial_no", width: 130, fixed: "left", render: (value: string, row) => <Button type="link" size="small" style={{ padding: 0 }} onClick={() => openCase(row)}>{value}</Button> },
            { title: "案件名称", dataIndex: "case_name", width: 200, ellipsis: true },
            { title: "专利类型", dataIndex: "case_type", width: 130 },
            { title: "申请号", dataIndex: "application_no", width: 150 },
            { title: "申请日", dataIndex: "application_date", width: 100 },
            { title: "客户", dataIndex: "customer", width: 180, ellipsis: true },
            { title: "年度", dataIndex: "fee_name", width: 110 },
            { title: "应缴日", dataIndex: "due_date", width: 100 },
            { title: "滞纳截止", dataIndex: "late_deadline", width: 100 },
            { title: "标准年费", dataIndex: "standard_amount", width: 90, align: "right" },
            { title: "代理人", dataIndex: "procurator", width: 90 },
            {
              title: "状态", dataIndex: "status", width: 120,
              render: (value: string, row) => value === "已缴"
                ? <Tag color="green">已缴 {row.paid_date || ""}</Tag>
                : dayjs(row.due_date).isBefore(dayjs(), "day") ? <Tag color="red">逾期未缴</Tag> : <Tag color="orange">待缴</Tag>,
            },
            {
              title: "操作", key: "op", width: 110, fixed: "right",
              render: (_: unknown, row) => row.status === "已缴"
                ? <Popconfirm title="改回待缴？" onConfirm={() => void undoPaid(row)}><Button type="link" size="small">撤销已缴</Button></Popconfirm>
                : <Button type="link" size="small" onClick={() => startPay(row)}>登记已缴</Button>,
            },
          ]}
        />
      </Card>
      <Modal
        open={!!paying}
        title={paying ? `登记已缴：${paying.serial_no} ${paying.fee_name}` : "登记已缴"}
        onCancel={() => setPaying(null)}
        onOk={() => void submitPaid()}
        confirmLoading={saving}
        okText="登记"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="paid_date" label="缴费日期" rules={[{ required: true, message: "请选择缴费日期" }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} maxLength={500} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
