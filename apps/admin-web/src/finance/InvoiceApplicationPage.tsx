import { Alert, Button, Descriptions, Form, Input, InputNumber, Select, Space, Table, Tabs, message } from "antd";
import type { FormInstance } from "antd";
import { useEffect, useRef, useState } from "react";
import { InvoiceServiceItemsTable } from "../contract/InvoiceServiceItemsTable";
import { invoiceFeeAvailableAmount, invoiceFeeIssuedAmount } from "./constants";
import type { Fee } from "./types";
import { api } from "../api";

export function InvoiceApplicationPage({ form, target, fees, selectedIds, onSelect, onSave, onClose, openCase, openContract, loadReference }: {
  form: FormInstance; target: Fee | null; fees: Fee[]; selectedIds: number[];
  onSelect: (ids: number[]) => void; onSave: (submit?: boolean) => Promise<void>; onClose: () => void;
  openCase: (value: string) => void; openContract: (value: string) => void;
  loadReference: (options?: Record<string, any>) => Promise<any>;
}) {
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState("");
  const [feeTab, setFeeTab] = useState(target || selectedIds.length ? "selected" : "available");
  const [sourceRows, setSourceRows] = useState<Fee[]>([]);
  const [sourceMeta, setSourceMeta] = useState({ total: 0, page: 1, pageSize: 50 });
  const [sourceLoading, setSourceLoading] = useState(false);
  const [sourceError, setSourceError] = useState("");
  const [customerOptions, setCustomerOptions] = useState<Fee[]>([]);
  const requestId = useRef(0);
  const customerRequestId = useRef(0);
  const customerId = Form.useWatch("customer_record_id", form);
  const autoServiceAmount = useRef<number | null>(null);
  const totalAmount = Form.useWatch("amount", form);
  const allocations = Form.useWatch("case_fee_allocations", form) || [];
  const searchCustomers = async (keyword: string) => {
    const token = ++customerRequestId.current;
    try {
      const { data } = await api.get("/records", { params: { module: "customer", keyword, page: 1, page_size: 50 } });
      if (token === customerRequestId.current) setCustomerOptions(data.items || []);
    } catch (failure: any) { if (token === customerRequestId.current) message.error(failure?.response?.data?.detail || "客户查询失败"); }
  };
  const loadSources = async (page = 1, pageSize = sourceMeta.pageSize, options: Record<string, any> = {}) => {
    const token = ++requestId.current;
    setSourceLoading(true); setSourceError("");
    try {
      const result = await loadReference({ invoice_id: target?.id, customer_id: form.getFieldValue("customer_record_id") || undefined,
        customer: form.getFieldValue("customer"), keyword: query, page, page_size: pageSize, ...options, isCurrent: () => token === requestId.current });
      if (token !== requestId.current) return;
      setSourceRows(result.candidateRows); setSourceMeta({ total: result.total, page: result.page, pageSize: result.pageSize });
      if (result.customerRecord && !target) {
        setCustomerOptions((previous) => Array.from(new Map([...previous, result.customerRecord].map((row) => [row.id, row])).values()));
        form.setFieldValue("customer_record_id", result.customerRecord.id);
      }
      if (options.applyDefaults) {
        form.setFieldsValue({ ...result.customerDefaults, customer_record_id: result.customerRecord?.id });
      }
      if (result.customerMissing) setSourceError("客户档案不存在或无权访问，请核对开票资料");
    } catch (failure: any) {
      if (token === requestId.current) { setSourceRows([]); setSourceError(failure?.response?.data?.detail || failure.message || "开票费用加载失败"); }
    } finally { if (token === requestId.current) setSourceLoading(false); }
  };
  useEffect(() => {
    void loadSources();
    return () => { requestId.current += 1; customerRequestId.current += 1; };
  }, [target?.id]);
  useEffect(() => {
    if (!target && !(form.getFieldValue("service_items") || []).length) {
      const value = Number(form.getFieldValue("amount") || 0);
      form.setFieldValue("service_items", [{ service_name: form.getFieldValue("invoice_content") || "法律服务费", quantity: 1, unit_price: value, amount: value, tax_rate: 0, tax_amount: 0 }]);
      autoServiceAmount.current = value;
    }
  }, [form, target]);
  useEffect(() => {
    const previous = autoServiceAmount.current;
    if (target || previous == null) return;
    const services = form.getFieldValue("service_items") || [];
    const row = services[0];
    if (services.length !== 1 || row?.service_name !== (form.getFieldValue("invoice_content") || "法律服务费") || Number(row.quantity) !== 1 || Number(row.unit_price) !== previous || Number(row.amount) !== previous || Number(row.tax_rate || 0) !== 0 || Number(row.tax_amount || 0) !== 0) {
      autoServiceAmount.current = null;
      return;
    }
    const next = Number(totalAmount || 0);
    if (Number.isFinite(next) && next !== previous) {
      form.setFieldValue("service_items", [{ ...row, unit_price: next, amount: next }]);
      autoServiceAmount.current = next;
    }
  }, [form, target, totalAmount]);
  const setAllocation = (id: number, value: number | null) => {
    const next = selectedIds.map((feeId) => ({ fee_id: feeId, amount: feeId === id ? value : allocations.find((row: any) => Number(row.fee_id) === feeId)?.amount ?? null }));
    form.setFieldsValue({ case_fee_allocations: next, amount: Number(next.reduce((sum, row) => sum + Number(row.amount || 0), 0).toFixed(2)) });
  };
  const save = async (submit: boolean) => {
    if (busy) return;
    setBusy(true);
    try { await onSave(submit); } catch (error: any) {
      if (!error?.errorFields) throw error;
    } finally { setBusy(false); }
  };
  const visibleFees = feeTab === "selected" ? fees.filter((row) => selectedIds.includes(row.id)) : sourceRows;
  return <section className="finance-original-panel finance-invoice-request-page" aria-label={target ? "编辑发票申请" : "新增发票申请"}>
    <header className="finance-original-title"><h2>{target ? "编辑发票申请" : "新增发票申请"}</h2><Button disabled={busy} onClick={onClose}>返回</Button></header>
    <Descriptions size="small" column={{ xs: 1, sm: 2, lg: 3 }}>
      <Descriptions.Item label="开票申请号">{target?.serial_no || "保存后生成"}</Descriptions.Item>
      <Descriptions.Item label="申请日期">{target?.data?.application_date || target?.created_at?.slice(0, 10) || "保存后生成"}</Descriptions.Item>
      <Descriptions.Item label="状态">{target?.status || "草稿"}</Descriptions.Item>
    </Descriptions>
    <Form form={form} layout="vertical" disabled={busy} className="finance-invoice-request-form">
      {["case_record_id", "contract_record_id", "case_fee_ids", "case_fee_allocations"].map((name) => <Form.Item key={name} name={name} hidden><Input /></Form.Item>)}
      <div className="finance-invoice-detail-section-title">申请信息</div>
      <div className="finance-invoice-request-grid">
        {target ? <Form.Item label="客户名称" name="customer" rules={[{ required: true }]}><Input readOnly /></Form.Item> : <>
          <Form.Item name="customer" hidden rules={[{ required: true, message: "请选择客户" }]}><Input /></Form.Item>
          <Form.Item label="客户名称"><Select showSearch filterOption={false} value={customerId} disabled={busy} onSearch={(value) => void searchCustomers(value)} onOpenChange={(open) => { if (open) void searchCustomers(""); }}
            options={customerOptions.map((row) => ({ value: row.id, label: `${row.title || row.customer} (${row.serial_no})` }))}
            onChange={(id) => {
              const row = customerOptions.find((item) => item.id === id);
              if (!row) return;
              onSelect([]); setFeeTab("available"); setQuery("");
              form.setFieldsValue({ customer_record_id: row.id, customer: row.title || row.customer });
              void loadSources(1, 50, { customer_id: row.id, customer: row.title || row.customer, keyword: "", applyDefaults: true });
            }} /></Form.Item>
          <Form.Item name="customer_record_id" hidden><InputNumber /></Form.Item>
        </>}
        <Form.Item label="来源案件" name="case_no"><Input readOnly /></Form.Item>
        <Form.Item label="合同编号" name="contract_no"><Input readOnly /></Form.Item>
        <Form.Item label="外部合同号" name="external_contract_no"><Input readOnly /></Form.Item>
        <Form.Item label="申请开票金额" name="amount" rules={[{ required: true }]}><InputNumber min={0.01} precision={2} readOnly style={{ width: "100%" }} /></Form.Item>
        <Form.Item label="高开发票金额" name="extra_amount"><InputNumber min={0} precision={2} style={{ width: "100%" }} /></Form.Item>
      </div>
      <div className="finance-invoice-detail-section-title">发票内容</div>
      <div className="finance-invoice-request-grid">
        <Form.Item label="发票类型" name="invoice_type" rules={[{ required: true }]}><Select options={["增值税普通发票", "增值税专用发票", "电子普通发票", "电子专用发票"].map((value) => ({ value, label: value }))} /></Form.Item>
        <Form.Item label="发票抬头" name="invoice_title" rules={[{ required: true }]}><Input /></Form.Item>
        <Form.Item label="纳税人识别号" name="taxpayer_id" rules={[{ required: true }]}><Input /></Form.Item>
        <Form.Item label="公司电话" name="invoice_phone"><Input /></Form.Item>
        <Form.Item label="银行账号" name="bank_account"><Input /></Form.Item>
        <Form.Item label="开户银行" name="bank_name"><Input /></Form.Item>
        <Form.Item label="开票地址" name="invoice_address"><Input /></Form.Item>
        <Form.Item label="开票内容" name="invoice_content"><Input /></Form.Item>
      </div>
      <div className="finance-invoice-detail-section-title">服务项</div>
      <InvoiceServiceItemsTable form={form} disabled={busy} />
      <div className="finance-invoice-detail-section-title">费用明细</div>
      {sourceError && <Alert type="warning" message={sourceError} action={<Button onClick={() => void loadSources()}>重新加载</Button>} />}
      <Tabs activeKey={feeTab} onChange={setFeeTab} items={[{ key: "selected", label: `已选费用 (${selectedIds.length})` }, { key: "available", label: "可选费用" }]} />
      {feeTab === "available" && <Input.Search aria-label="查询费用" placeholder="合同号、案号、费用类型" allowClear value={query} onChange={(event) => setQuery(event.target.value)} onSearch={() => void loadSources(1)} style={{ width: "min(420px, 100%)", marginBottom: 12 }} />}
      <Table<Fee> rowKey="id" size="small" loading={sourceLoading} dataSource={visibleFees} scroll={{ x: 1550 }} pagination={feeTab === "selected" ? false : { current: sourceMeta.page, pageSize: sourceMeta.pageSize, total: sourceMeta.total, showSizeChanger: true, pageSizeOptions: [15, 30, 50, 100], onChange: (page, size) => void loadSources(size !== sourceMeta.pageSize ? 1 : page, size) }}
        rowSelection={{ selectedRowKeys: selectedIds, preserveSelectedRowKeys: true, onChange: (keys) => onSelect(keys.map(Number)), getCheckboxProps: () => ({ disabled: busy }) }}
        columns={[
          { title: "合同编号", width: 170, render: (_, fee) => fee.data?.contract_no ? <Button type="link" onClick={() => openContract(fee.data.contract_no)}>{fee.data.contract_no}</Button> : "未关联" },
          { title: "外部合同号", width: 150, render: (_, fee) => fee.data?.external_contract_no },
          { title: "案件名称", width: 200, render: (_, fee) => fee.data?.case_name || fee.data?.case_title || fee.title },
          { title: "案件类型", width: 100, render: (_, fee) => fee.data?.case_type },
          { title: "案件阶段", width: 100, render: (_, fee) => fee.data?.case_stage || fee.data?.stage },
          { title: "案号", width: 170, render: (_, fee) => fee.data?.case_no ? <Button type="link" onClick={() => openCase(fee.data.case_no)}>{fee.data.case_no}</Button> : "未关联" },
          { title: "费用类型", width: 110, render: (_, fee) => fee.data?.fee_type },
          { title: "费用金额", width: 110, render: (_, fee) => fee.data?.amount == null ? "未提供" : Number(fee.data.amount).toFixed(2) },
          { title: "到账金额", width: 110, render: (_, fee) => fee.data?.received_amount == null && fee.data?.cashed_amount == null ? "未提供" : Number(fee.data.received_amount ?? fee.data.cashed_amount).toFixed(2) },
          { title: "已开票金额", width: 110, render: (_, fee) => invoiceFeeIssuedAmount(fee).toFixed(2) },
          { title: "可开票金额", width: 110, render: (_, fee) => invoiceFeeAvailableAmount(fee).toFixed(2) },
          { title: "本次开票", width: 140, render: (_, fee) => <InputNumber aria-label={`本次开票 ${fee.id}`} min={0.01} precision={2} disabled={busy || !selectedIds.includes(fee.id)} value={allocations.find((row: any) => Number(row.fee_id) === fee.id)?.amount ?? null} onChange={(value) => setAllocation(fee.id, value)} style={{ width: "100%" }} /> },
        ]} />
      <div className="finance-invoice-detail-section-title">交付信息</div>
      <div className="finance-invoice-request-grid">
        <Form.Item label="交付方式" name="delivery_method"><Select options={["电子发票", "邮寄纸质发票", "现场领取"].map((value) => ({ value, label: value }))} /></Form.Item>
        <Form.Item label="接收邮箱" name="email"><Input /></Form.Item>
        <Form.Item label="收件人" name="recipient"><Input /></Form.Item>
        <Form.Item label="联系电话" name="recipient_phone"><Input /></Form.Item>
        <Form.Item label="邮寄地址" name="delivery_address"><Input /></Form.Item>
        <Form.Item label="备注" name="remark"><Input.TextArea rows={2} /></Form.Item>
      </div>
    </Form>
    <Space wrap style={{ marginTop: 16 }}>
      <Button disabled={busy} onClick={onClose}>取消</Button>
      <Button loading={busy} disabled={sourceLoading} onClick={() => void save(false)}>{target ? "保存修改" : "保存草稿"}</Button>
      <Button type="primary" loading={busy} disabled={sourceLoading} onClick={() => void save(true)}>{target?.status === "已驳回" ? "保存并重新提交" : "保存并提交"}</Button>
    </Space>
  </section>;
}
