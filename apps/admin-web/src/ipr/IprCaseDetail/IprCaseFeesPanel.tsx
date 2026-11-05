import { useCallback,useEffect,useState } from "react";
import dayjs from "dayjs";
import { Alert,Button,DatePicker,Form,Input,InputNumber,Modal,Select,Space,Typography,message } from "antd";
import Table from "../../components/ResizableTable";
import { api } from "../../api";
import { iprCaseIgnoresStatus, personDisplayName } from "../constants";
import type { Attachment,IprRecord } from "../types";
import { iprDateText,iprFlagChecked } from "./iprCaseInfo";
import { IprRowContextMenu } from "./IprRowContextMenu";
import { roleActionAllowed } from "../../roleActions";
import { feeTypes } from "../../finance/constants";

/** 原系统 IPR_Case_FeeItem 一行（后端 legacy-fee-items 原样转出）。 */
type LegacyFeeItem = {
  id: number;
  fee_type?: string | null;
  yearly?: string | number | null;
  fee_mitigation?: string | null;
  amount?: number | null;
  actual_amount?: number | null;
  inform_date?: string | null;
  gained_date?: string | null;
  payment_bank?: string | null;
  bill_no?: string | null;
  bill_date?: string | null;
  bill_amount?: number | null;
  bill_file_name?: string | null;
};

type CaseFeeRow = { id: number; status?: string; title?: string; created_at?: string; data?: Record<string, any> };

/** 费用明细一行：新系统费用和原系统费用明细合在一张表里。 */
type FeeLine = {
  key: string;
  source: "新系统" | "原系统";
  fee?: CaseFeeRow;
  feeType: string;
  yearly: string;
  amount: number | null;
  paidAmount: number | null;
  mitigation: boolean;
  informDate: string;
  gainedDate: string;
  status: string;
};

const money = (value: number | null | undefined) => (value === null || value === undefined ? "—" : Number(value).toFixed(2));

function useLegacyFeeItems(caseId: number, reloadKey = 0) {
  const [items, setItems] = useState<LegacyFeeItem[]>([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let active = true;
    setLoading(true);
    api.get<{ items: LegacyFeeItem[] }>(`/ipr/cases/${caseId}/legacy-fee-items`)
      .then(({ data }) => { if (active) setItems(data.items || []); })
      .catch(() => { if (active) setItems([]); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [caseId, reloadKey]);
  return { items, loading };
}

type PaymentType = { id: number; name: string; payee: string; account_bank: string; account: string };

const errorText = (error: any, fallback: string) => error?.response?.data?.detail || fallback;

/** 费用明细页签（原系统“费用明细”）。右键菜单按原系统：新增、修改、开票申请、付款申请、合同文件、刷新（BUG20261028020）。
 * 原系统迁移来的费用只读，只能刷新；新系统费用按状态和权限决定哪些项可用。 */
export function IprCaseFeesPanel({ detail, onOpenContract }: { detail: IprRecord; onOpenContract: (contractNo: string) => void }) {
  const [reloadKey, setReloadKey] = useState(0);
  const legacy = useLegacyFeeItems(detail.id, reloadKey);
  const [fees, setFees] = useState<CaseFeeRow[]>([]);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<CaseFeeRow | "new" | null>(null);
  const [invoiceFee, setInvoiceFee] = useState<CaseFeeRow | null>(null);
  const [paymentFee, setPaymentFee] = useState<CaseFeeRow | null>(null);
  const [paymentTypes, setPaymentTypes] = useState<PaymentType[]>([]);
  const [saving, setSaving] = useState(false);
  const [feeForm] = Form.useForm();
  const [invoiceForm] = Form.useForm();
  const [paymentForm] = Form.useForm();
  useEffect(() => {
    let active = true;
    setError("");
    api.get<{ items: CaseFeeRow[] }>(`/ipr/cases/${detail.id}/fees`, { params: { page: 1, page_size: 200 } })
      .then(({ data }) => { if (active) setFees(data.items || []); })
      .catch(() => { if (active) { setFees([]); setError("新系统费用加载失败"); } });
    return () => { active = false; };
  }, [detail.id, reloadKey]);
  const refresh = useCallback(() => setReloadKey((value) => value + 1), []);
  const lines: FeeLine[] = [
    ...fees.map((row) => ({
      key: `fee-${row.id}`,
      source: "新系统" as const,
      fee: row,
      feeType: row.data?.fee_subtype || row.data?.fee_type || row.title || "—",
      yearly: "",
      amount: row.data?.amount ?? null,
      paidAmount: row.data?.paid_amount ?? null,
      mitigation: false,
      informDate: iprDateText(row.created_at),
      gainedDate: iprDateText(row.data?.paid_at || row.data?.arrived_at),
      status: row.status || "",
    })),
    ...legacy.items.map((row) => ({
      key: `legacy-${row.id}`,
      source: "原系统" as const,
      feeType: row.fee_type || "—",
      yearly: row.yearly ? String(row.yearly) : "",
      amount: row.amount ?? null,
      paidAmount: row.actual_amount ?? null,
      mitigation: iprFlagChecked(row.fee_mitigation),
      informDate: iprDateText(row.inform_date),
      gainedDate: iprDateText(row.gained_date),
      status: row.gained_date ? "已缴" : "未缴",
    })),
  ];

  const active = detail.status === "在办";
  // 501190：新增、修改不看状态（非诉）；开票、付款申请仍要在办（canManage）。
  const canCreate = (active || iprCaseIgnoresStatus(detail)) && roleActionAllowed("ipr.case.fee.create");
  const canManage = active && roleActionAllowed("ipr.case.fee.manage");
  const isDraft = (fee: CaseFeeRow) => fee.status === "草稿" && !fee.data?.locked && !fee.data?.is_locked && !fee.data?.payment_application_id;
  const openEdit = (fee: CaseFeeRow | "new") => {
    feeForm.resetFields();
    feeForm.setFieldsValue(fee === "new"
      ? { fee_type: "官方费用", fee_date: dayjs() }
      : { fee_type: fee.data?.base_fee_type || fee.data?.fee_type, amount: fee.data?.amount, fee_date: fee.data?.fee_date ? dayjs(fee.data.fee_date) : dayjs(), description: (fee as any).description || "" });
    setEditing(fee);
  };
  const openInvoice = (fee: CaseFeeRow) => {
    invoiceForm.resetFields();
    invoiceForm.setFieldsValue({
      customer: detail.customer || "", invoice_title: detail.customer || "",
      amount: Number(fee.data?.amount || 0) > 0 ? Number(fee.data?.amount) : undefined,
      invoice_type: "增值税普通发票", invoice_content: "法律服务费", delivery_method: "电子发票",
    });
    setInvoiceFee(fee);
  };
  const openPayment = (fee: CaseFeeRow) => {
    paymentForm.resetFields();
    paymentForm.setFieldsValue({ application_date: dayjs() });
    setPaymentFee(fee);
    api.get<{ items: PaymentType[] }>(`/ipr/cases/${detail.id}/fees/${fee.id}/payment-types`)
      .then(({ data }) => setPaymentTypes(data.items || []))
      .catch((err) => { setPaymentTypes([]); message.error(errorText(err, "付款类型加载失败")); });
  };
  const submit = async (run: () => Promise<unknown>, done: string, close: () => void) => {
    setSaving(true);
    try {
      await run();
      message.success(done);
      close();
      refresh();
    } catch (err: any) {
      if (!err?.errorFields) message.error(errorText(err, "保存失败"));
    } finally {
      setSaving(false);
    }
  };
  const saveFee = () => submit(async () => {
    const values = await feeForm.validateFields();
    const body = { ...values, fee_date: values.fee_date ? values.fee_date.format("YYYY-MM-DD") : null, description: values.description || "" };
    if (editing === "new") {
      await api.post(`/ipr/cases/${detail.id}/fees`, { ...body, contract_record_id: Number(detail.data?.contract_record_id) || null });
    } else if (editing) {
      await api.patch(`/ipr/cases/${detail.id}/fees/${editing.id}`, body);
    }
  }, editing === "new" ? "费用已新增" : "费用已修改", () => setEditing(null));
  const saveInvoice = () => submit(async () => {
    const values = await invoiceForm.validateFields();
    await api.post(`/ipr/cases/${detail.id}/fees/${invoiceFee!.id}/invoice`, values);
  }, "开票申请已提交", () => setInvoiceFee(null));
  const savePayment = () => submit(async () => {
    const values = await paymentForm.validateFields();
    await api.post(`/ipr/cases/${detail.id}/fees/${paymentFee!.id}/payment-application`, {
      ...values, application_date: values.application_date.format("YYYY-MM-DD"), remark: values.remark || "",
    });
  }, "付款申请已提交", () => setPaymentFee(null));

  const menuItems = (line: FeeLine | null) => {
    const fee = line?.fee;
    const contractNo = String(fee?.data?.contract_no || "").trim();
    return [
      { key: "create", label: "新增", disabled: !canCreate, onClick: () => openEdit("new") },
      { key: "edit", label: "修改", disabled: !fee || !canCreate || !isDraft(fee), onClick: () => fee && openEdit(fee) },
      { key: "invoice", label: "开票申请", disabled: !fee || !canManage || fee.status === "已作废", onClick: () => fee && openInvoice(fee) },
      {
        key: "payment", label: "付款申请",
        disabled: !fee || !canManage || fee.status === "已作废" || !!fee.data?.payment_application_id,
        onClick: () => fee && openPayment(fee),
      },
      { key: "contract", label: "合同文件", disabled: !contractNo, onClick: () => onOpenContract(contractNo) },
      { key: "refresh", label: "刷新", onClick: refresh },
    ];
  };

  return (
    <>
      {error ? <Alert type="warning" showIcon message={error} style={{ marginBottom: 12 }} /> : null}
      <IprRowContextMenu rows={lines} rowKey={(line) => line.key} items={menuItems}>
        <Table
          rowKey="key"
          size="small"
          loading={legacy.loading}
          pagination={lines.length > 15 ? { pageSize: 15, showSizeChanger: false } : false}
          locale={{ emptyText: "暂无费用" }}
          dataSource={lines}
          columns={[
            { title: "费用类型", dataIndex: "feeType", ellipsis: true },
            { title: "年度", dataIndex: "yearly", width: 70, render: (value) => value || "—" },
            { title: "应缴金额", dataIndex: "amount", width: 110, align: "right", render: money },
            { title: "实缴金额", dataIndex: "paidAmount", width: 110, align: "right", render: money },
            { title: "费减", dataIndex: "mitigation", width: 60, render: (value) => (value ? "是" : "否") },
            { title: "通知日期", dataIndex: "informDate", width: 110, render: (value) => value || "—" },
            { title: "缴费日期", dataIndex: "gainedDate", width: 110, render: (value) => value || "—" },
            { title: "状态", dataIndex: "status", width: 90, render: (value) => value || "—" },
            { title: "来源", dataIndex: "source", width: 80 },
          ]}
        />
      </IprRowContextMenu>

      <Modal open={!!editing} title={editing === "new" ? "新增案件费用" : "修改案件费用"} onCancel={() => setEditing(null)} onOk={() => void saveFee()} confirmLoading={saving} okText="保存">
        <Form form={feeForm} layout="vertical">
          <Form.Item name="fee_type" label="费用类型" rules={[{ required: true, message: "请选择费用类型" }]}>
            <Select options={feeTypes.map((value) => ({ value, label: value }))} />
          </Form.Item>
          <Form.Item name="amount" label="金额" rules={[{ required: true, message: "请填写金额" }]}>
            <InputNumber style={{ width: "100%" }} precision={2} />
          </Form.Item>
          <Form.Item name="fee_date" label="费用日期">
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="description" label="说明">
            <Input.TextArea rows={2} maxLength={2000} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal open={!!invoiceFee} title="开票申请" onCancel={() => setInvoiceFee(null)} onOk={() => void saveInvoice()} confirmLoading={saving} okText="提交">
        <Form form={invoiceForm} layout="vertical">
          <Form.Item name="customer" label="客户" rules={[{ required: true, message: "请填写客户" }]}><Input maxLength={255} /></Form.Item>
          <Form.Item name="amount" label="开票金额" rules={[{ required: true, message: "请填写开票金额" }]}>
            <InputNumber style={{ width: "100%" }} min={0.01} precision={2} />
          </Form.Item>
          <Form.Item name="invoice_title" label="发票抬头" rules={[{ required: true, message: "请填写发票抬头" }]}><Input maxLength={255} /></Form.Item>
          <Form.Item name="taxpayer_id" label="纳税人识别号" rules={[{ required: true, message: "请填写纳税人识别号" }]}><Input maxLength={128} /></Form.Item>
          <Form.Item name="invoice_type" label="发票类型">
            <Select options={["增值税普通发票", "增值税专用发票"].map((value) => ({ value, label: value }))} />
          </Form.Item>
          <Form.Item name="invoice_content" label="开票内容"><Input maxLength={128} /></Form.Item>
          <Form.Item name="delivery_method" label="交付方式">
            <Select options={["电子发票", "纸质发票"].map((value) => ({ value, label: value }))} />
          </Form.Item>
          <Form.Item name="email" label="接收邮箱"><Input maxLength={255} /></Form.Item>
          <Form.Item name="remark" label="备注"><Input.TextArea rows={2} maxLength={1000} /></Form.Item>
        </Form>
      </Modal>

      <Modal open={!!paymentFee} title="付款申请" onCancel={() => setPaymentFee(null)} onOk={() => void savePayment()} confirmLoading={saving} okText="提交">
        <Form form={paymentForm} layout="vertical">
          <Form.Item name="payment_type_id" label="付款类型（收款方）" rules={[{ required: true, message: "请选择付款类型" }]}>
            <Select
              showSearch
              optionFilterProp="label"
              options={paymentTypes.map((item) => ({ value: item.id, label: `${item.name}｜${item.payee}` }))}
            />
          </Form.Item>
          <Form.Item name="application_date" label="申请日期" rules={[{ required: true, message: "请选择申请日期" }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="remark" label="备注"><Input.TextArea rows={2} maxLength={1000} /></Form.Item>
        </Form>
      </Modal>
    </>
  );
}

/** 发票文件页签：案件文档里的发票/收据类文件，加上原系统费用明细里登记的票据。 */
export function IprInvoiceFilesPanel({ detail, onPreviewAttachment, onDownloadAttachment }: {
  detail: IprRecord;
  onPreviewAttachment: (item: Attachment) => void;
  onDownloadAttachment: (item: Attachment) => void;
}) {
  const legacy = useLegacyFeeItems(detail.id);
  const [files, setFiles] = useState<Attachment[]>([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let active = true;
    setLoading(true);
    api.get<{ items: Attachment[] }>(`/ipr/cases/${detail.id}/files`, { params: { page: 1, page_size: 200, category_keywords: "发票,收据" } })
      .then(({ data }) => { if (active) setFiles(data.items || []); })
      .catch(() => { if (active) setFiles([]); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [detail.id]);
  const bills = legacy.items.filter((row) => row.bill_no || row.bill_file_name);
  return (
    <>
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        pagination={files.length > 15 ? { pageSize: 15, showSizeChanger: false } : false}
        locale={{ emptyText: "暂无发票文件" }}
        dataSource={files}
        columns={[
          { title: "文档类型", dataIndex: "category", ellipsis: true, render: (value) => value || "—" },
          {
            title: "文件名称",
            dataIndex: "original_name",
            ellipsis: true,
            render: (value: string, row: Attachment) => <Button type="link" size="small" onClick={() => onPreviewAttachment(row)}>{value}</Button>,
          },
          { title: "文档日期", dataIndex: "document_date", width: 110, render: (value) => iprDateText(value) || "—" },
          { title: "上传人", dataIndex: "uploader_display_name", width: 100, render: personDisplayName },
          { title: "操作", width: 70, render: (_, row: Attachment) => <Button type="link" size="small" onClick={() => onDownloadAttachment(row)}>下载</Button> },
        ]}
      />
      {bills.length ? (
        <Space direction="vertical" size={8} style={{ width: "100%", marginTop: 16 }}>
          <Typography.Text strong>原系统登记的票据</Typography.Text>
          <Table
            rowKey="id"
            size="small"
            pagination={bills.length > 15 ? { pageSize: 15, showSizeChanger: false } : false}
            dataSource={bills}
            columns={[
              { title: "费用类型", dataIndex: "fee_type", ellipsis: true, render: (value) => value || "—" },
              { title: "票据号", dataIndex: "bill_no", width: 140, render: (value) => value || "—" },
              { title: "票据金额", dataIndex: "bill_amount", width: 110, align: "right", render: money },
              { title: "票据日期", dataIndex: "bill_date", width: 110, render: (value) => iprDateText(value) || "—" },
              { title: "票据文件", dataIndex: "bill_file_name", ellipsis: true, render: (value) => value || "—" },
            ]}
          />
        </Space>
      ) : null}
    </>
  );
}
