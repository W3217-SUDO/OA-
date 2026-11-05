import { useCallback, useEffect, useRef, useState } from "react";
import dayjs, { type Dayjs } from "dayjs";
import { Button, Card, DatePicker, Empty, Form, Input, Modal, Popconfirm, Select, Space, message } from "antd";
import Table from "./components/ResizableTable";
import { api } from "./api";
import { iprCaseDetailRoute } from "./ipr/iprCaseTabs";

// 280146 / 501616：知识产权中心“专利转文”“商标转文”，照老系统中间一栏次级菜单（带未转数量），右边官文列表；
// 勾选后 生成转文（老系统转达函模板，同一客户）、上传转文（勾选的官文标已转）、标记已转。
type Kind = "patent" | "trademark";
type SummaryItem = { key: string; label: string; count: number };
type Row = {
  attachment_id: number; case_id: number; serial_no: string; status: string; file_type: string; file_name: string;
  received_date: string; application_no: string; application_date: string; customer: string; case_name: string; trademark_class: string;
};
type Filters = { case_no?: string; customer?: string; status?: string };

const TITLES: Record<Kind, string> = { patent: "专利转文", trademark: "商标转文" };
const errorDetail = (error: any, fallback: string) => error?.response?.data?.detail || fallback;
const blobErrorDetail = async (error: any, fallback: string) => {
  const data = error?.response?.data;
  if (data instanceof Blob) {
    try { return JSON.parse(await data.text())?.detail || fallback; } catch { return fallback; }
  }
  return errorDetail(error, fallback);
};

export default function IprTransferPage({ kind, onNavigate }: { kind: Kind; onNavigate?: (route: string) => void }) {
  const [summary, setSummary] = useState<SummaryItem[]>([]);
  const [view, setView] = useState("");
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<number[]>([]);
  const [form] = Form.useForm<Filters>();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploadForm] = Form.useForm<{ document_date: Dayjs; remark?: string }>();

  const loadSummary = useCallback(async () => {
    try {
      const { data } = await api.get<{ items: SummaryItem[] }>(`/ipr/transfer-center/${kind}/summary`);
      setSummary(data.items);
      setView((current) => (current && data.items.some((item) => item.key === current) ? current : data.items[0]?.key || ""));
    } catch (error) {
      message.error(errorDetail(error, `${TITLES[kind]}数量加载失败`));
    }
  }, [kind]);

  const loadRows = useCallback(async (key: string, values: Filters) => {
    if (!key) return;
    setLoading(true);
    try {
      const { data } = await api.get<{ items: Row[] }>(`/ipr/transfer-center/${kind}/items`, {
        params: { item: key, case_no: values.case_no || undefined, customer: values.customer || undefined, status: values.status || "未转" },
      });
      setRows(data.items);
      setSelected([]);
    } catch (error) {
      message.error(errorDetail(error, "官文列表加载失败"));
    } finally {
      setLoading(false);
    }
  }, [kind]);

  useEffect(() => { void loadSummary(); }, [loadSummary]);
  useEffect(() => { if (view) void loadRows(view, form.getFieldsValue()); }, [view, loadRows, form]);

  const refresh = async () => {
    await loadSummary();
    await loadRows(view, form.getFieldsValue());
  };

  const openFile = async (row: Row) => {
    try {
      const response = await api.get(`/attachments/${row.attachment_id}/download`, { params: { case_id: row.case_id }, responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      window.open(url, "_blank", "noopener");
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (error) {
      message.error(await blobErrorDetail(error, "官文打开失败"));
    }
  };

  const generate = async () => {
    if (!selected.length) {
      message.warning("请先勾选要转达的官文（须同一客户）");
      return;
    }
    try {
      const response = await api.get(`/ipr/transfer-center/${kind}/generate`, {
        params: { item: view, attachment_ids: selected.join(",") }, responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${current?.label || TITLES[kind]}.docx`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      message.error(await blobErrorDetail(error, "生成转文失败"));
    }
  };

  const openUpload = () => {
    if (!selected.length) {
      message.warning("请先勾选已经转达的官文");
      return;
    }
    uploadForm.setFieldsValue({ document_date: dayjs(), remark: "" });
    setUploadFile(null);
    if (fileRef.current) fileRef.current.value = "";
    setUploadOpen(true);
  };

  const submitUpload = async () => {
    const values = await uploadForm.validateFields();
    if (!uploadFile) {
      message.warning("请选择转达函文件");
      return;
    }
    const body = new FormData();
    body.append("file", uploadFile);
    body.append("attachment_ids", JSON.stringify(selected));
    body.append("document_date", values.document_date.format("YYYY-MM-DD"));
    body.append("remark", values.remark || "");
    setUploading(true);
    try {
      const { data } = await api.post<{ cases: number; transmitted: number }>("/ipr/transfer-center/upload", body);
      message.success(`已上传到 ${data.cases} 个案件，${data.transmitted} 份官文标为已转`);
      setUploadOpen(false);
      await refresh();
    } catch (error) {
      message.error(errorDetail(error, "上传转文失败"));
    } finally {
      setUploading(false);
    }
  };

  const markTransmitted = async () => {
    try {
      const { data } = await api.post<{ updated: number }>("/ipr/transfer-center/mark-transmitted", { attachment_ids: selected });
      message.success(`已标记 ${data.updated} 份官文为已转`);
      await refresh();
    } catch (error) {
      message.error(errorDetail(error, "标记已转失败"));
    }
  };

  const current = summary.find((item) => item.key === view);
  const isTrademark = kind === "trademark";

  return (
    <div className="page-shell ipr-transfer-page" style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "flex-start" }}>
      <Card size="small" title={TITLES[kind]} style={{ width: 280, flex: "0 0 280px" }} styles={{ body: { padding: "4px 0" } }}>
        {summary.map((item) => (
          <div
            key={item.key}
            role="button"
            tabIndex={0}
            onClick={() => setView(item.key)}
            onKeyDown={(event) => { if (event.key === "Enter") setView(item.key); }}
            style={{
              padding: "5px 12px", cursor: "pointer",
              background: item.key === view ? "#e6f4ff" : undefined, color: item.key === view ? "#1677ff" : undefined,
            }}
          >
            {item.label}({item.count})
          </div>
        ))}
      </Card>
      <Card size="small" style={{ flex: "1 1 600px", minWidth: 0 }} title={current ? `${TITLES[kind]} · ${current.label}` : "官文列表"}>
        <Form form={form} layout="inline" style={{ rowGap: 8, marginBottom: 12 }} initialValues={{ status: "未转" }}
          onFinish={(values) => void loadRows(view, values)}>
          <Form.Item name="case_no" label="案件编号或申请号" style={{ width: 300 }}><Input allowClear placeholder="案件编号或申请号" /></Form.Item>
          <Form.Item name="customer" label="客户/申请人" style={{ width: 260 }}><Input allowClear placeholder="客户/申请人" /></Form.Item>
          <Form.Item name="status" label="状态">
            <Select style={{ width: 100 }} options={["未转", "已转", "全部"].map((value) => ({ value, label: value }))} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">查询</Button>
            <Button style={{ marginLeft: 8 }} onClick={() => { form.resetFields(); void loadRows(view, { status: "未转" }); }}>重置</Button>
          </Form.Item>
        </Form>
        <Table<Row>
          rowKey="attachment_id"
          rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys.map(Number)) }}
          size="small"
          loading={loading}
          dataSource={rows}
          scroll={{ x: 1300 }}
          pagination={{ defaultPageSize: 15, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
          locale={{ emptyText: <Empty description="没有待转的官文" /> }}
          columns={[
            { title: "状态", dataIndex: "status", width: 70 },
            { title: "文件类型", dataIndex: "file_type", width: 180, ellipsis: true },
            { title: "文件名称", dataIndex: "file_name", width: 220, ellipsis: true,
              render: (value: string, row) => <Button type="link" size="small" style={{ padding: 0 }} onClick={() => void openFile(row)}>{value}</Button> },
            { title: "收文日期", dataIndex: "received_date", width: 100 },
            { title: "案号", dataIndex: "serial_no", width: 130,
              render: (value: string, row) => (
                <Button type="link" size="small" style={{ padding: 0 }}
                  onClick={() => onNavigate?.(iprCaseDetailRoute({ id: row.case_id, serial_no: row.serial_no, data: { case_kind: isTrademark ? "商标" : "专利" } }))}>{value}</Button>
              ) },
            { title: "申请号", dataIndex: "application_no", width: 150 },
            { title: "申请日", dataIndex: "application_date", width: 100 },
            { title: "客户", dataIndex: "customer", width: 200, ellipsis: true },
            { title: isTrademark ? "商标名称" : "发明名称", dataIndex: "case_name", width: 200, ellipsis: true },
          ]}
        />
        <Space wrap style={{ marginTop: 8 }}>
          <Button onClick={() => void generate()}>生成转文</Button>
          <Button onClick={openUpload}>上传转文</Button>
          <Popconfirm title={`把勾选的 ${selected.length} 份官文标记为已转？`} okText="标记" cancelText="取消" disabled={!selected.length}
            onConfirm={() => void markTransmitted()}>
            <Button disabled={!selected.length}>标记已转</Button>
          </Popconfirm>
        </Space>
        <Modal open={uploadOpen} title={`上传转文（已勾选 ${selected.length} 份官文）`} onCancel={() => setUploadOpen(false)}
          onOk={() => void submitUpload()} confirmLoading={uploading} okText="上传">
          <Form form={uploadForm} layout="vertical">
            <Form.Item label="转达函文件" required>
              <input ref={fileRef} type="file" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.zip,.rar" onChange={(event) => setUploadFile(event.target.files?.[0] || null)} />
            </Form.Item>
            <Form.Item name="document_date" label="转达日期" rules={[{ required: true, message: "请选择转达日期" }]}>
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="remark" label="说明"><Input.TextArea rows={2} maxLength={500} /></Form.Item>
          </Form>
        </Modal>
      </Card>
    </div>
  );
}
