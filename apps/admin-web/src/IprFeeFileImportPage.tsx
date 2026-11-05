import { useState } from "react";
import dayjs, { type Dayjs } from "dayjs";
import { Alert, Button, Card, DatePicker, Empty, Input, Space, Tag, Upload, message } from "antd";
import type { UploadFile } from "antd";
import Table from "./components/ResizableTable";
import { api } from "./api";
import { IPR_FEE_FILE_PAGES, type IprFeeFilePage } from "./ipr/feeFilePages";

// 501618（高勤兰 11-05）：知识产权中心 › 案件文件，按旧系统补齐收据、发票的导入和上传。
// 老案件费用迁移前，收据、发票先挂成案件文档（案件页“发票文件”页签里能看到）。
type PreviewRow = Record<string, unknown> & { file_name: string; status: string; errors: string[] };
type CaseRow = { id: number; serial_no: string; title: string; customer: string; status: string; data?: Record<string, unknown> | null };

const errorDetail = (error: any, fallback: string) => error?.response?.data?.detail || fallback;
const text = (value: unknown) => String(value ?? "").trim();

function ImportPanel({ page }: { page: IprFeeFilePage }) {
  const [file, setFile] = useState<File | null>(null);
  const [rows, setRows] = useState<PreviewRow[]>([]);
  const [importable, setImportable] = useState(0);
  const [loading, setLoading] = useState(false);
  const isReceipt = page.kind === "receipt-import";

  const send = async (confirm: boolean) => {
    if (!file) return message.warning("请先选择文件");
    const body = new FormData();
    body.append("file", file);
    body.append("confirm", confirm ? "true" : "false");
    if (!isReceipt) body.append("scope", page.kind === "invoice-import-contract" ? "contract" : "case");
    setLoading(true);
    try {
      const { data } = await api.post<{ items: PreviewRow[]; importable?: number; created?: number }>(
        isReceipt ? "/ipr/fee-file-import/receipts" : "/ipr/fee-file-import/invoices", body,
      );
      setRows(data.items || []);
      if (confirm) {
        message.success(`已导入 ${data.created ?? 0} 个文件`);
        setImportable(0);
      } else {
        setImportable(data.importable ?? 0);
      }
    } catch (error) {
      message.error(errorDetail(error, confirm ? "导入失败" : "识别失败"));
    } finally {
      setLoading(false);
    }
  };

  const columns = isReceipt ? [
    { title: "文件名", dataIndex: "file_name", width: 200 },
    { title: "状态", dataIndex: "status", width: 200, render: (value: string) => value === "可导入" ? <Tag color="green">可导入</Tag> : <span style={{ color: "#cf1322" }}>{value}</span> },
    { title: "案件编号", dataIndex: "serial_no", width: 130 },
    { title: "案件类型", key: "case_type", width: 110, render: (_: unknown, row: PreviewRow) => text(row.case_type) || text(row.case_kind) },
    { title: "申请号", dataIndex: "application_no", width: 140 },
    { title: "费用号", dataIndex: "fee_code", width: 90 },
    { title: "费用类型", dataIndex: "fee_type", width: 160 },
  ] : [
    { title: "文件名", dataIndex: "file_name", width: 180 },
    { title: "状态", dataIndex: "status", width: 200, render: (value: string) => value === "可导入" ? <Tag color="green">可导入</Tag> : <span style={{ color: "#cf1322" }}>{value}</span> },
    { title: "发票编号", dataIndex: "invoice_no", width: 150 },
    { title: "请票单号", dataIndex: "invoice_serial_no", width: 130 },
    ...(page.kind === "invoice-import-contract"
      ? [{ title: "合同编号", dataIndex: "contract_no", width: 130 }]
      : [{ title: "案件编号", key: "cases", width: 160, render: (_: unknown, row: PreviewRow) => ((row.cases as { serial_no: string }[]) || []).map((item) => item.serial_no).join("、") }]),
    { title: "客户名称", dataIndex: "customer", width: 160 },
    { title: "开票金额", dataIndex: "amount", width: 100, align: "right" as const },
    { title: "开票日期", dataIndex: "invoice_date", width: 100 },
    { title: "领票人", dataIndex: "applicant", width: 90 },
    { title: "票据状态", dataIndex: "status_text", width: 90 },
    { title: "备注", dataIndex: "remark", width: 160, ellipsis: true },
  ];

  return <>
    <Alert type="info" showIcon style={{ marginBottom: 12 }} title={page.rule} />
    <Space wrap style={{ marginBottom: 12 }}>
      <Upload maxCount={1} beforeUpload={(item) => { setFile(item); setRows([]); setImportable(0); return false; }}
        onRemove={() => { setFile(null); setRows([]); setImportable(0); }}
        fileList={file ? [{ uid: "1", name: file.name, status: "done" } as UploadFile] : []}
        accept=".zip,.pdf,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.gif,.ofd">
        <Button>选择文件</Button>
      </Upload>
      <Button loading={loading} onClick={() => void send(false)}>上传文件</Button>
      <Button type="primary" loading={loading} disabled={!importable} onClick={() => void send(true)}>开始导入{importable ? `（${importable}）` : ""}</Button>
    </Space>
    <Table<PreviewRow> rowKey="file_name" size="small" dataSource={rows} columns={columns} scroll={{ x: 1100 }} pagination={false}
      locale={{ emptyText: <Empty description="选择文件后点“上传文件”识别" /> }} />
  </>;
}

function UploadPanel({ page }: { page: IprFeeFilePage }) {
  const [numbers, setNumbers] = useState("");
  const [customer, setCustomer] = useState("");
  const [rows, setRows] = useState<CaseRow[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [documentDate, setDocumentDate] = useState<Dayjs>(dayjs());
  const [loading, setLoading] = useState(false);

  const search = async () => {
    const list = numbers.split(/[,，\s]+/).map((item) => item.trim()).filter(Boolean).slice(0, 50);
    if (!list.length && !customer.trim()) return message.warning("请填写案件编号/申请号或客户");
    setLoading(true);
    try {
      const queries = (list.length ? list : [""]).map((number) => api.get<{ items: CaseRow[] }>("/ipr/cases", {
        params: { case_no: number || undefined, customer: customer.trim() || undefined, case_kind: page.caseKind, page_size: 100 },
      }));
      const merged = new Map<number, CaseRow>();
      for (const { data } of await Promise.all(queries)) for (const row of data.items || []) merged.set(row.id, row);
      setRows(Array.from(merged.values()));
      setSelected([]);
    } catch (error) {
      message.error(errorDetail(error, "查询案件失败"));
    } finally {
      setLoading(false);
    }
  };

  const upload = async () => {
    if (!selected.length) return message.warning("请先勾选案件");
    if (!file) return message.warning("请选择要上传的文件");
    const body = new FormData();
    body.append("file", file);
    body.append("case_ids", JSON.stringify(selected));
    body.append("category", page.category || "");
    body.append("document_date", documentDate.format("YYYY-MM-DD"));
    body.append("remark", page.label);
    setLoading(true);
    try {
      await api.post("/ipr/cases/files/batch-upload", body);
      message.success(`已上传到 ${selected.length} 个案件`);
      setFile(null);
    } catch (error) {
      message.error(errorDetail(error, "上传失败"));
    } finally {
      setLoading(false);
    }
  };

  return <>
    <Alert type="info" showIcon style={{ marginBottom: 12 }} title={page.rule} />
    <Space wrap style={{ marginBottom: 12 }}>
      <span>案号：</span>
      <Input style={{ width: 260 }} value={numbers} onChange={(event) => setNumbers(event.target.value)} placeholder="案件编号或申请号（多个用逗号分隔）" allowClear />
      <span>客户：</span>
      <Input style={{ width: 200 }} value={customer} onChange={(event) => setCustomer(event.target.value)} placeholder="客户名称" allowClear />
      <Button type="primary" loading={loading} onClick={() => void search()}>查询</Button>
    </Space>
    <Space wrap style={{ marginBottom: 12 }}>
      <Upload maxCount={1} beforeUpload={(item) => { setFile(item); return false; }} onRemove={() => setFile(null)}
        fileList={file ? [{ uid: "1", name: file.name, status: "done" } as UploadFile] : []}>
        <Button>选择文件</Button>
      </Upload>
      <span>文档日期：</span>
      <DatePicker value={documentDate} onChange={(value) => value && setDocumentDate(value)} allowClear={false} />
      <Button type="primary" loading={loading} disabled={!selected.length || !file} onClick={() => void upload()}>批量上传{selected.length ? `（${selected.length} 个案件）` : ""}</Button>
    </Space>
    <Table<CaseRow> rowKey="id" size="small" dataSource={rows} scroll={{ x: 1000 }}
      rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys.map(Number)) }}
      pagination={{ defaultPageSize: 20, showTotal: (total) => `共 ${total} 条` }}
      locale={{ emptyText: <Empty description="按案号或客户查询案件" /> }}
      columns={[
        { title: "案件编号", dataIndex: "serial_no", width: 140 },
        { title: "申请号", key: "application_no", width: 150, render: (_: unknown, row) => text(row.data?.application_no) },
        { title: "客户", dataIndex: "customer", width: 180, ellipsis: true },
        { title: "案件名称", dataIndex: "title", width: 220, ellipsis: true },
        { title: "案件类型", key: "case_type", width: 120, render: (_: unknown, row) => text(row.data?.case_type) || text(row.data?.case_kind) },
        { title: "案件阶段", key: "case_phase", width: 110, render: (_: unknown, row) => text(row.data?.case_phase) || row.status },
      ]} />
  </>;
}

export default function IprFeeFileImportPage({ route }: { route: string }) {
  const page = IPR_FEE_FILE_PAGES[route];
  if (!page) return <Empty description="页面不存在" />;
  return <Card size="small" className="page-shell" title={page.label}>
    {page.kind === "case-upload" ? <UploadPanel page={page} /> : <ImportPanel page={page} />}
  </Card>;
}
