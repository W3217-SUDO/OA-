import { useCallback, useEffect, useRef, useState } from "react";
import dayjs, { type Dayjs } from "dayjs";
import { Button, Card, DatePicker, Empty, Form, Input, Modal, Select, Space, message } from "antd";
import Table from "./components/ResizableTable";
import { api } from "./api";
import { iprCaseDetailRoute } from "./ipr/iprCaseTabs";

// BUG20261030004：知识产权中心“专利年费”，照老系统中间一栏 年费清单 / 年费监控，每项带数量，点一项右边出案件。
// 高勤兰 10-30：不手动登记已缴，按年费官费是否上传缴费凭证判断；列和筛选照老系统。
type SummaryItem = { key: string; group: string; label: string; count: number };
type FeeRow = {
  case_id: number;
  serial_no: string;
  case_name: string;
  case_type: string;
  applicant: string;
  application_no: string;
  application_date: string;
  case_source: string;
  fee_year: number;
  year_no: number;
  due_date: string;
  period_start: string;
  period_end: string;
  informed: boolean;
  annual_fee: number;
  term_expired?: boolean;
  relief_rate: number;
  inform_amount: number;
  gained_amount: number;
  bill_amount: number;
};
type FilterValues = {
  applicant?: string; customer?: string; case_source?: string; case_type?: string; writer?: string;
  case_no?: string; case_phase?: string; procurator?: string; application_dates?: [Dayjs | null, Dayjs | null] | null;
};

const VIEW_PARAM = "fee_view";
const FILTERS: { name: keyof FilterValues; label: string }[] = [
  { name: "applicant", label: "申请人" }, { name: "case_type", label: "案件类型" }, { name: "case_phase", label: "案件阶段" },
  { name: "customer", label: "客户名称" }, { name: "writer", label: "撰稿人" }, { name: "procurator", label: "代理人" },
  { name: "case_source", label: "案源人" }, { name: "case_no", label: "案号/申请号" },
];
const errorDetail = (error: any, fallback: string) => error?.response?.data?.detail || fallback;
// 下载接口出错时返回的是 Blob，要先读出文字再取 detail。
const blobErrorDetail = async (error: any, fallback: string) => {
  const data = error?.response?.data;
  if (data instanceof Blob) {
    try { return JSON.parse(await data.text())?.detail || fallback; } catch { return fallback; }
  }
  return errorDetail(error, fallback);
};
const initialView = () => new URLSearchParams(window.location.search).get(VIEW_PARAM) || "";
const amountText = (value: number) => String(Math.round(value || 0));
const rowKey = (row: FeeRow) => `${row.case_id}-${row.year_no}`;

const queryParams = (values: FilterValues) => {
  const params: Record<string, string> = {};
  for (const { name } of FILTERS) {
    const value = String(values[name] || "").trim();
    if (value) params[name] = value;
  }
  const [from, to] = values.application_dates || [];
  if (from) params.date_from = from.format("YYYY-MM-DD");
  if (to) params.date_to = to.format("YYYY-MM-DD");
  return params;
};

export default function IprAnnualFeePage({ onNavigate }: { onNavigate?: (route: string) => void }) {
  const [summary, setSummary] = useState<SummaryItem[]>([]);
  const [view, setView] = useState(initialView);
  const [rows, setRows] = useState<FeeRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [form] = Form.useForm<FilterValues>();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [fileTypes, setFileTypes] = useState<{ value: string; label: string }[]>([]);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploadForm] = Form.useForm<{ category: string; document_date: Dayjs; remark?: string }>();

  const loadSummary = useCallback(async () => {
    try {
      const { data } = await api.get<{ items: SummaryItem[] }>("/ipr/annual-fee-monitor/summary");
      setSummary(data.items);
      setView((current) => (current && data.items.some((item) => item.key === current) ? current : data.items[0]?.key || ""));
    } catch (error) {
      message.error(errorDetail(error, "专利年费数量加载失败"));
    }
  }, []);

  const loadRows = useCallback(async (key: string, values: FilterValues) => {
    if (!key) return;
    setLoading(true);
    try {
      const { data } = await api.get<{ items: FeeRow[] }>("/ipr/annual-fee-monitor/items", { params: { view: key, ...queryParams(values) } });
      setRows(data.items);
      setSelectedKeys([]);
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
    // 筛选条件只在点“过滤”时生效，切换左侧项目沿用当前条件。
    void loadRows(view, form.getFieldsValue());
  }, [view, loadRows, form]);

  // 在单独的案件标签里打开，不重新加载网页，年费页和其他标签都保持原样（BUG20261102003/002）。
  const openCase = (row: FeeRow) => {
    onNavigate?.(iprCaseDetailRoute({ id: row.case_id, serial_no: row.serial_no, data: { case_kind: "专利" } }));
  };

  // 生成年费清单：勾选了导出勾选的，没勾导出当前列表全部（带上当前筛选）。
  const exportList = async (kind: "excel" | "word") => {
    if (kind === "word" && !selectedKeys.length) {
      message.warning("请先勾选要生成年费清单的案件（须同一客户、已授权）");
      return;
    }
    const label = current?.label || "专利年费";
    try {
      const response = await api.get(`/ipr/annual-fee-monitor/export/${kind}`, {
        params: { view, ...queryParams(form.getFieldsValue()), keys: selectedKeys.join(",") || undefined },
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `年费清单-${label}.${kind === "excel" ? "xls" : "docx"}`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      message.error(await blobErrorDetail(error, "生成年费清单失败"));
    }
  };

  // 上传文件：照老系统，勾选案件、选文件类型，同一个文件挂到每个勾选的案件。
  const openUpload = async () => {
    if (!selectedKeys.length) {
      message.warning("请先勾选要上传文件的案件");
      return;
    }
    uploadForm.setFieldsValue({ category: undefined, document_date: dayjs(), remark: "" });
    setUploadFile(null);
    if (fileRef.current) fileRef.current.value = "";
    setUploadOpen(true);
    if (!fileTypes.length) {
      try {
        const { data } = await api.get<{ items: { name: string }[] }>("/ipr/case-file-types", { params: { case_kind: "专利" } });
        setFileTypes(data.items.map((item) => ({ value: item.name, label: item.name })));
      } catch (error) {
        message.error(errorDetail(error, "文件类型加载失败"));
      }
    }
  };

  const submitUpload = async () => {
    const values = await uploadForm.validateFields();
    if (!uploadFile) {
      message.warning("请选择要上传的文件");
      return;
    }
    const caseIds = Array.from(new Set(selectedKeys.map((key) => Number(key.split("-")[0]))));
    const body = new FormData();
    body.append("file", uploadFile);
    body.append("case_ids", JSON.stringify(caseIds));
    body.append("category", values.category);
    body.append("document_date", values.document_date.format("YYYY-MM-DD"));
    body.append("remark", values.remark || "");
    setUploading(true);
    try {
      const { data } = await api.post<{ created: number }>("/ipr/annual-fee-monitor/upload", body);
      message.success(`已上传到 ${data.created} 个案件`);
      setUploadOpen(false);
    } catch (error) {
      message.error(errorDetail(error, "上传文件失败"));
    } finally {
      setUploading(false);
    }
  };

  const reset = () => {
    form.resetFields();
    void loadRows(view, {});
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
      <Card size="small" style={{ flex: "1 1 600px", minWidth: 0 }} title={current ? `${current.group} · ${current.label}` : "案件列表"}>
        <Form form={form} layout="inline" style={{ rowGap: 8, marginBottom: 12 }} onFinish={(values) => void loadRows(view, values)}>
          {FILTERS.map((item) => (
            <Form.Item key={item.name} name={item.name} label={item.label} style={{ width: 240 }}>
              <Input placeholder={item.label} allowClear />
            </Form.Item>
          ))}
          <Form.Item name="application_dates" label="申请日">
            <DatePicker.RangePicker style={{ width: 240 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">过滤</Button>
            <Button style={{ marginLeft: 8 }} onClick={reset}>重置</Button>
          </Form.Item>
        </Form>
        <Table<FeeRow>
          rowKey={rowKey}
          rowSelection={{ selectedRowKeys: selectedKeys, onChange: (keys) => setSelectedKeys(keys.map(String)) }}
          size="small"
          loading={loading}
          dataSource={rows}
          scroll={{ x: 1400 }}
          pagination={{ defaultPageSize: 15, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
          locale={{ emptyText: <Empty description="没有需要缴纳的年费" /> }}
          columns={[
            { title: "申请人", dataIndex: "applicant", width: 180, ellipsis: true },
            { title: "专利名称", dataIndex: "case_name", width: 200, ellipsis: true },
            { title: "案件类型", dataIndex: "case_type", width: 130 },
            { title: "案件编号", dataIndex: "serial_no", width: 130, render: (value: string, row) => <Button type="link" size="small" style={{ padding: 0 }} onClick={() => openCase(row)}>{value}</Button> },
            { title: "申请号", dataIndex: "application_no", width: 150 },
            { title: "申请日", dataIndex: "application_date", width: 100 },
            { title: "年度", key: "year", width: 200, render: (_: unknown, row) => row.term_expired ? "0" : <>第{row.year_no}年度：<br />{row.period_start}至{row.period_end}</> },
            { title: "年费", dataIndex: "annual_fee", width: 80, align: "right" },
            { title: "费减", dataIndex: "relief_rate", width: 70, align: "right", render: (value: number) => `${value}%` },
            { title: "案源人", dataIndex: "case_source", width: 90 },
            { title: "本案通/回/付", key: "amounts", width: 130, render: (_: unknown, row) => row.term_expired ? "专利权到期" : row.informed ? `${amountText(row.inform_amount)}/${amountText(row.gained_amount)}/${amountText(row.bill_amount)}` : "未通知" },
          ]}
        />
        <Space wrap style={{ marginTop: 8 }}>
          <Button onClick={() => void exportList("excel")}>生成年费清单(Excel)</Button>
          <Button onClick={() => void exportList("word")}>生成年费清单(Word)</Button>
          <Button onClick={() => void openUpload()}>上传文件</Button>
        </Space>
        <Modal
          open={uploadOpen}
          title={`上传文件（已勾选 ${selectedKeys.length} 项）`}
          onCancel={() => setUploadOpen(false)}
          onOk={() => void submitUpload()}
          confirmLoading={uploading}
          okText="上传"
        >
          <Form form={uploadForm} layout="vertical">
            <Form.Item name="category" label="文件类型" rules={[{ required: true, message: "请选择文件类型" }]}>
              <Select showSearch optionFilterProp="label" options={fileTypes} />
            </Form.Item>
            <Form.Item name="document_date" label="文档日期" rules={[{ required: true, message: "请选择文档日期" }]}>
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item label="文件" required>
              <input ref={fileRef} type="file" onChange={(event) => setUploadFile(event.target.files?.[0] || null)} />
            </Form.Item>
            <Form.Item name="remark" label="说明">
              <Input.TextArea rows={2} maxLength={1000} />
            </Form.Item>
          </Form>
        </Modal>
      </Card>
    </div>
  );
}
