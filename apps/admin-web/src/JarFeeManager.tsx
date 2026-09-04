import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Button,
  Card,
  DatePicker,
  Drawer,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Upload,
  message,
} from "antd";
import type { TableColumnsType, UploadFile } from "antd";
import {
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  ExportOutlined,
  FileOutlined,
  PlusOutlined,
  ReloadOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "./api";
import { rememberContractDetailTarget } from "./contractDetailNavigation";

type JarFee = {
  id: number;
  serial_no?: string;
  title?: string;
  customer?: string;
  status: string;
  owner?: string;
  created_at?: string;
  data?: Record<string, any>;
  capabilities?: {
    can_update?: boolean;
    can_delete?: boolean;
    can_manage_status?: boolean;
    can_manage_files?: boolean;
    allowed_statuses?: string[];
  };
};

type JarAttachment = {
  id: number;
  original_name: string;
  size?: number;
  category?: string;
  uploader_display_name?: string;
  created_at?: string;
};

const statusColors: Record<string, string> = {
  待确认: "orange",
  已确认: "blue",
  已入账: "green",
  已作废: "default",
};
const statusOptions = ["待确认", "已确认", "已入账", "已作废"];
const amount = (value: unknown) =>
  Number(value || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const errorText = (error: any, fallback: string) => error?.response?.data?.detail || fallback;

export default function JarFeeManager({ onNavigate }: { onNavigate?: (route: string) => void }) {
  const [form] = Form.useForm();
  const [rows, setRows] = useState<JarFee[]>([]);
  const [loading, setLoading] = useState(false);
  const [queryDraft, setQueryDraft] = useState({ keyword: "", status: "", contract_id: undefined as number | undefined });
  const [appliedQuery, setAppliedQuery] = useState(queryDraft);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 15, total: 0 });
  const [contractOptions, setContractOptions] = useState<{ value: number; label: string; customer?: string }[]>([]);
  const [editing, setEditing] = useState<JarFee | null>(null);
  const [editorReadonly, setEditorReadonly] = useState(false);
  const [editorOpen, setEditorOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [fileTarget, setFileTarget] = useState<JarFee | null>(null);
  const [files, setFiles] = useState<JarAttachment[]>([]);
  const [filesLoading, setFilesLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [statusTarget, setStatusTarget] = useState<JarFee | null>(null);
  const [statusValue, setStatusValue] = useState("待确认");
  const [statusComment, setStatusComment] = useState("");
  const fileTargetIdRef = useRef<number | null>(null);
  const canManageStatus = (row: JarFee) =>
    row.capabilities?.can_manage_status === true && Boolean(row.capabilities.allowed_statuses?.length);
  const canUpdate = (row: JarFee) => row.capabilities?.can_update === true;
  const canDelete = (row: JarFee) => row.capabilities?.can_delete === true;
  const canManageFiles = (row: JarFee) => row.capabilities?.can_manage_files === true;

  const loadRows = useCallback(async (
    next: { current: number; pageSize: number; total?: number },
    filters = appliedQuery,
  ) => {
    setLoading(true);
    try {
      const { data } = await api.get("/finance/jar-fees", {
        params: {
          keyword: filters.keyword || undefined,
          status: filters.status || undefined,
          contract_id: Number.isInteger(filters.contract_id) ? filters.contract_id : undefined,
          page: next.current,
          page_size: next.pageSize,
        },
      });
      setRows(data.items || []);
      setPagination({ current: data.page || next.current, pageSize: data.page_size || next.pageSize, total: data.total || 0 });
    } catch (error: any) {
      message.error(errorText(error, "JAR交案费列表加载失败"));
    } finally {
      setLoading(false);
    }
  }, [appliedQuery]);

  useEffect(() => { void loadRows({ current: 1, pageSize: 15, total: 0 }, appliedQuery); }, [appliedQuery, loadRows]);

  const searchContracts = async (keyword: string) => {
    const { data } = await api.get("/records", { params: { module: "contract", keyword, page_size: 20 } });
    setContractOptions((data.items || []).map((item: any) => ({
      value: item.id,
      label: item.serial_no || item.title || `合同 #${item.id}`,
      customer: item.customer || "",
    })));
  };

  const openEditor = (row?: JarFee, readonly = false) => {
    setEditing(row || null);
    setEditorReadonly(readonly);
    const data = row?.data || {};
    form.setFieldsValue({
      contract_id: data.contract_id,
      title: row?.title || "",
      customer: row?.customer || "",
      payer_name: data.payer_name || "",
      bank_voucher_no: data.bank_voucher_no || "",
      received_date: data.received_date ? dayjs(data.received_date) : undefined,
      amount: data.amount,
      official_fee_amount: data.official_fee_amount || 0,
      agency_fee_amount: data.agency_fee_amount || 0,
      other_fee_amount: data.other_fee_amount || 0,
      payment_method: data.payment_method || "",
      handler: data.handler || "",
      remark: data.remark || "",
    });
    if (data.contract_id) setContractOptions([{ value: Number(data.contract_id), label: data.contract_no || `合同 #${data.contract_id}`, customer: row?.customer }]);
    setEditorOpen(true);
  };

  const save = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const payload = { ...values, received_date: values.received_date?.format("YYYY-MM-DD") };
      if (editing) await api.put(`/finance/jar-fees/${editing.id}`, payload);
      else await api.post("/finance/jar-fees", payload);
      message.success(editing ? "JAR交案费已更新" : "JAR交案费已新增");
      setEditorOpen(false);
      await loadRows(pagination);
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(errorText(error, "JAR交案费保存失败"));
    } finally { setSaving(false); }
  };

  const remove = (row: JarFee) => {
    Modal.confirm({
      title: "删除JAR交案费",
      content: `确定删除“${row.title || row.serial_no || row.id}”吗？此操作不可恢复。`,
      okButtonProps: { danger: true },
      onOk: async () => {
        try { await api.delete(`/finance/jar-fees/${row.id}`); message.success("JAR交案费已删除"); await loadRows(pagination); }
        catch (error: any) { message.error(errorText(error, "JAR交案费删除失败")); }
      },
    });
  };

  const loadFiles = async (row: JarFee) => {
    fileTargetIdRef.current = row.id;
    setFileTarget(row); setFiles([]); setFilesLoading(true);
    try {
      const { data } = await api.get(`/finance/jar-fees/${row.id}/files`);
      if (fileTargetIdRef.current === row.id) setFiles(data.items || []);
    }
    catch (error: any) { message.error(errorText(error, "交案费附件加载失败")); }
    finally { if (fileTargetIdRef.current === row.id) setFilesLoading(false); }
  };

  const uploadFile = async (file: File) => {
    if (!fileTarget) return false;
    const body = new FormData(); body.append("file", file); body.append("category", "JAR交案费附件");
    setUploading(true);
    try { await api.post(`/finance/jar-fees/${fileTarget.id}/files`, body); message.success("附件已上传"); await loadFiles(fileTarget); }
    catch (error: any) { message.error(errorText(error, "附件上传失败")); }
    finally { setUploading(false); }
    return false;
  };

  const downloadFile = async (file: JarAttachment) => {
    if (!fileTarget) return;
    try {
      const result = await api.get(`/finance/jar-fees/${fileTarget.id}/files/${file.id}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(result.data); const link = document.createElement("a");
      link.href = url; link.download = file.original_name; link.click(); URL.revokeObjectURL(url);
    } catch (error: any) { message.error(errorText(error, "附件下载失败")); }
  };

  const deleteFile = async (file: JarAttachment) => {
    if (!fileTarget) return;
    try { await api.delete(`/finance/jar-fees/${fileTarget.id}/files/${file.id}`); message.success("附件已删除"); await loadFiles(fileTarget); }
    catch (error: any) { message.error(errorText(error, "附件删除失败")); }
  };

  const changeStatus = async () => {
    if (!statusTarget) return;
    try {
      await api.post(`/finance/jar-fees/${statusTarget.id}/status`, { status: statusValue, comment: statusComment });
      message.success("交案费状态已更新"); setStatusTarget(null); await loadRows(pagination);
    } catch (error: any) { message.error(errorText(error, "状态更新失败")); }
  };

  const exportRows = async () => {
    try {
      const result = await api.get("/finance/jar-fees/export", { params: appliedQuery, responseType: "blob" });
      const url = URL.createObjectURL(result.data); const link = document.createElement("a");
      link.href = url; link.download = `JAR交案费-${dayjs().format("YYYY-MM-DD")}.csv`; link.click(); URL.revokeObjectURL(url);
    } catch (error: any) { message.error(errorText(error, "JAR交案费导出失败")); }
  };

  const openContract = async (row: JarFee) => {
    const contractId = Number(row.data?.contract_id || 0);
    if (!contractId) {
      message.warning("未找到关联合同或当前账号无权查看");
      return;
    }
    try {
      const { data } = await api.get(`/records/${contractId}`);
      if (!data?.id) throw new Error("contract missing");
      rememberContractDetailTarget({ id: data.id, serial_no: data.serial_no || row.data?.contract_no });
      onNavigate?.("contract-company");
    } catch (error: any) {
      message.warning(error?.response?.data?.detail || "未找到关联合同或当前账号无权查看");
    }
  };

  const columns: TableColumnsType<JarFee> = useMemo(() => [
    { title: "交案费编号", dataIndex: "serial_no", width: 150, render: (v) => v || "—" },
    { title: "标题", dataIndex: "title", width: 180, ellipsis: true },
    { title: "合同编号", width: 140, render: (_, row) => row.data?.contract_no ? <Button type="link" size="small" onClick={() => void openContract(row)}>{row.data.contract_no}</Button> : "—" },
    { title: "客户", dataIndex: "customer", width: 140, ellipsis: true },
    { title: "交款单位", width: 150, render: (_, row) => row.data?.payer_name || "—", ellipsis: true },
    { title: "到账日期", width: 110, render: (_, row) => row.data?.received_date || "—" },
    { title: "交案费金额", width: 130, align: "right", render: (_, row) => row.data?.amount == null ? "—" : `¥ ${amount(row.data.amount)}` },
    { title: "经办人", width: 100, render: (_, row) => row.data?.handler || row.owner || "—" },
    { title: "状态", width: 105, render: (_, row) => <Tag color={statusColors[row.status] || "default"}>{row.status || "待确认"}</Tag> },
    { title: "操作", key: "actions", fixed: "right", width: 250, render: (_, row) => (
      <Space size={0} wrap>
        <Button type="link" size="small" onClick={() => openEditor(row, true)}>查看</Button>
        {canUpdate(row) && <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEditor(row)}>编辑</Button>}
        {canManageStatus(row) && <Button type="link" size="small" onClick={() => { setStatusTarget(row); setStatusValue(row.capabilities?.allowed_statuses?.[0] || row.status || "待确认"); setStatusComment(""); }}>状态</Button>}
        <Button type="link" size="small" icon={<FileOutlined />} onClick={() => void loadFiles(row)}>文件</Button>
        {canDelete(row) && <Button danger type="link" size="small" icon={<DeleteOutlined />} onClick={() => remove(row)}>删除</Button>}
      </Space>
    ) },
  ], [onNavigate]);

  return <div className="finance-center">
    <Card className="panel" title="JAR交案费管理" extra={<Space><Button icon={<ReloadOutlined />} onClick={() => void loadRows(pagination)} loading={loading}>刷新</Button><Button icon={<ExportOutlined />} onClick={() => void exportRows()}>导出 CSV</Button><Button type="primary" icon={<PlusOutlined />} onClick={() => openEditor()}>新增交案费</Button></Space>}>
      <Form layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item label="关键词"><Input allowClear value={queryDraft.keyword} placeholder="编号、标题、客户、交款单位" onChange={(e) => setQueryDraft((v) => ({ ...v, keyword: e.target.value }))} /></Form.Item>
        <Form.Item label="合同"><Select allowClear showSearch filterOption={false} style={{ width: 190 }} value={queryDraft.contract_id} placeholder="输入合同编号查询" onSearch={(value) => void searchContracts(value)} options={contractOptions} onChange={(value) => setQueryDraft((v) => ({ ...v, contract_id: Number.isInteger(value) ? value : undefined }))} /></Form.Item>
        <Form.Item label="状态"><Select allowClear style={{ width: 120 }} value={queryDraft.status || undefined} options={statusOptions.map((value) => ({ value, label: value }))} onChange={(value) => setQueryDraft((v) => ({ ...v, status: value || "" }))} /></Form.Item>
        <Form.Item><Button type="primary" onClick={() => setAppliedQuery(queryDraft)}>查询</Button></Form.Item>
        <Form.Item><Button onClick={() => { const blank = { keyword: "", status: "", contract_id: undefined }; setQueryDraft(blank); setAppliedQuery(blank); }}>清空</Button></Form.Item>
      </Form>
      <Table rowKey="id" loading={loading} columns={columns} dataSource={rows} scroll={{ x: 1460 }} pagination={{ current: pagination.current, pageSize: pagination.pageSize, total: pagination.total, showSizeChanger: true, onChange: (current, pageSize) => void loadRows({ current, pageSize, total: pagination.total }) }} />
    </Card>
    <Drawer open={editorOpen} width="min(760px, 95vw)" title={editorReadonly ? "查看JAR交案费" : editing ? "编辑JAR交案费" : "新增JAR交案费"} onClose={() => setEditorOpen(false)} extra={!editorReadonly && <Button type="primary" loading={saving} onClick={() => void save()}>保存</Button>} destroyOnHidden>
      <Form form={form} layout="vertical" disabled={editorReadonly} initialValues={{ official_fee_amount: 0, agency_fee_amount: 0, other_fee_amount: 0 }}>
        <Space style={{ display: "flex" }} size={16} align="start"><Form.Item label="关联合同" name="contract_id" rules={[{ required: true, message: "请选择关联合同" }]} style={{ width: 260 }}><Select showSearch filterOption={false} placeholder="输入合同编号查询" onSearch={(value) => void searchContracts(value)} options={contractOptions} onSelect={(_value, option: any) => form.setFieldValue("customer", option.customer || "")} /></Form.Item><Form.Item label="标题" name="title" rules={[{ required: true, message: "请输入交案费标题" }]} style={{ flex: 1 }}><Input maxLength={200} /></Form.Item></Space>
        <Space style={{ display: "flex" }} size={16} align="start"><Form.Item label="客户" name="customer" style={{ flex: 1 }}><Input /></Form.Item><Form.Item label="交款单位" name="payer_name" style={{ flex: 1 }}><Input /></Form.Item></Space>
        <Space style={{ display: "flex" }} size={16} align="start"><Form.Item label="银行单据号" name="bank_voucher_no" style={{ flex: 1 }}><Input /></Form.Item><Form.Item label="到账日期" name="received_date" style={{ flex: 1 }}><DatePicker style={{ width: "100%" }} /></Form.Item></Space>
        <Space style={{ display: "flex" }} size={16} align="start"><Form.Item label="交案费金额" name="amount" rules={[{ required: true, message: "请输入交案费金额" }]} style={{ flex: 1 }}><InputNumber min={0.01} precision={2} style={{ width: "100%" }} /></Form.Item><Form.Item label="回款方式" name="payment_method" style={{ flex: 1 }}><Input placeholder="例如：银行转账" /></Form.Item><Form.Item label="经办人" name="handler" style={{ flex: 1 }}><Input /></Form.Item></Space>
        <Space style={{ display: "flex" }} size={16} align="start"><Form.Item label="官费" name="official_fee_amount" style={{ flex: 1 }}><InputNumber min={0} precision={2} style={{ width: "100%" }} /></Form.Item><Form.Item label="代理费" name="agency_fee_amount" style={{ flex: 1 }}><InputNumber min={0} precision={2} style={{ width: "100%" }} /></Form.Item><Form.Item label="其他费用" name="other_fee_amount" style={{ flex: 1 }}><InputNumber min={0} precision={2} style={{ width: "100%" }} /></Form.Item></Space>
        <Form.Item label="备注" name="remark"><Input.TextArea rows={3} maxLength={1000} /></Form.Item>
      </Form>
    </Drawer>
    <Drawer open={Boolean(fileTarget)} width="min(720px, 95vw)" title={`交案费文件${fileTarget?.serial_no ? `：${fileTarget.serial_no}` : ""}`} onClose={() => { fileTargetIdRef.current = null; setFileTarget(null); setFiles([]); }} destroyOnHidden extra={fileTarget && canManageFiles(fileTarget) ? <Upload showUploadList={false} beforeUpload={uploadFile} disabled={uploading}><Button icon={<UploadOutlined />} loading={uploading}>上传文件</Button></Upload> : undefined}>
      <Table rowKey="id" loading={filesLoading} dataSource={files} pagination={false} locale={{ emptyText: "尚未上传交案费附件" }} columns={[{ title: "文件名", dataIndex: "original_name" }, { title: "分类", dataIndex: "category", width: 140 }, { title: "上传人", dataIndex: "uploader_display_name", width: 110 }, { title: "操作", width: 150, render: (_, file: JarAttachment) => <Space><Button type="link" size="small" icon={<DownloadOutlined />} onClick={() => void downloadFile(file)}>下载</Button>{fileTarget && canManageFiles(fileTarget) && <Button type="link" danger size="small" onClick={() => void deleteFile(file)}>删除</Button>}</Space> }]} />
    </Drawer>
    <Modal open={Boolean(statusTarget)} title="变更JAR交案费状态" onCancel={() => setStatusTarget(null)} onOk={() => void changeStatus()} okText="确认变更">
      <Form layout="vertical"><Form.Item label="状态"><Select value={statusValue} options={(statusTarget?.capabilities?.allowed_statuses || []).map((value) => ({ value, label: value }))} onChange={setStatusValue} /></Form.Item><Form.Item label="操作说明"><Input.TextArea value={statusComment} rows={3} maxLength={500} onChange={(event) => setStatusComment(event.target.value)} /></Form.Item></Form>
    </Modal>
  </div>;
}
