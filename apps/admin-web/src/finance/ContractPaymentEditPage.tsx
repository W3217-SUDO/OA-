import { Alert, Button, DatePicker, Descriptions, Form, Input, InputNumber, Space, Spin, Table, message } from "antd";
import dayjs from "dayjs";
import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { ContractPaymentUnitPicker } from "../contract/ContractPaymentUnitPicker";
import { PaymentTypeCreateModal } from "../contract/ContractModals";
import { formatRequiredDate } from "../formSafety";
import { canEditContractPayment, contractPaymentEditPayload, paymentLineKey } from "./paymentLifecycle.mjs";

export function ContractPaymentEditPage({ paymentId, onClose, onSaved }: {
  paymentId: number; onClose: () => void; onSaved: () => Promise<void>;
}) {
  const [form] = Form.useForm();
  const [unitForm] = Form.useForm();
  const [context, setContext] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const saving = useRef(false);
  const [retry, setRetry] = useState(0);
  const [selected, setSelected] = useState<string[]>([]);
  const [amounts, setAmounts] = useState<Record<string, number | null>>({});
  const [remarks, setRemarks] = useState<Record<string, string>>({});
  const [picker, setPicker] = useState(false);
  const [unitCreate, setUnitCreate] = useState(false);
  const [unitBusy, setUnitBusy] = useState(false);
  const unitId = Form.useWatch("payment_type_id", form);
  useEffect(() => {
    let active = true;
    setLoading(true); setError(""); setContext(null);
    void api.get(`/contract-payment-applications/${paymentId}/edit-context`).then(({ data }) => {
      if (!active) return;
      if (!data?.payment || Number(data.payment.id) !== paymentId || !canEditContractPayment(data.payment)) throw new Error("当前请款单状态不可编辑");
      setContext(data);
      const payment = data.payment;
      const lines = payment.data?.lines || payment.lines || [];
      setSelected(lines.map(paymentLineKey));
      setAmounts(Object.fromEntries(lines.map((row: any) => [paymentLineKey(row), row.amount ?? row.requested_amount])));
      setRemarks(Object.fromEntries(lines.map((row: any) => [paymentLineKey(row), row.remark || ""])));
      form.resetFields();
      form.setFieldsValue({ ...payment.data, payer_name: payment.data?.payer_name || "", remark: payment.data?.remark ?? payment.description ?? "", application_date: dayjs(payment.data?.application_date || payment.created_at) });
    }).catch((failure) => {
      if (active) setError(failure?.response?.data?.detail || failure.message || "请款编辑数据加载失败");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [paymentId, form, retry]);
  const unit = context?.payment_types?.find((row: any) => Number(row.value) === Number(unitId));
  const save = async (submit: boolean) => {
    if (saving.current || !context || !canEditContractPayment(context.payment)) return;
    saving.current = true; setBusy(true);
    try {
      const values = await form.validateFields();
      if (!unit || !String(unit.account_bank || "").trim() || !String(unit.account || "").trim()) throw new Error("收款单位的开户行与账号必须完整");
      const payload = contractPaymentEditPayload({ ...values, application_date: formatRequiredDate(values.application_date, "申请日期") }, selected, context.items || [], amounts, remarks);
      const { data } = await api.put(`/contract-payment-applications/${paymentId}`, payload);
      setContext((previous: any) => ({ ...previous, payment: { ...previous.payment, ...data, data: { ...previous.payment.data, ...data?.data } } }));
      if (submit) {
        try { await api.post(`/contract-payment-applications/${paymentId}/submit`, { comment: "修改原请款单并重新提交" }); }
        catch (failure: any) { message.error(failure?.response?.data?.detail || "原单已保存，提交失败，可重试"); return; }
      }
      message.success(submit ? "原请款单已保存并重新提交" : "原请款单已保存");
      await onSaved(); onClose();
    } catch (failure: any) {
      if (!failure?.errorFields) message.error(failure?.response?.data?.detail || failure.message || "请款保存失败");
    } finally { saving.current = false; setBusy(false); }
  };
  const createUnit = async () => {
    if (unitBusy || !context?.contract?.id) return;
    setUnitBusy(true);
    try {
      const values = await unitForm.validateFields();
      const { data } = await api.post(`/contracts/${context.contract.id}/payment-types`, values);
      setContext((previous: any) => ({ ...previous, payment_types: [...previous.payment_types.filter((row: any) => row.value !== data.value), data] }));
      setUnitCreate(false); unitForm.resetFields(); message.success("收款单位已新增");
    } catch (failure: any) { if (!failure?.errorFields) message.error(failure?.response?.data?.detail || "收款单位新增失败"); }
    finally { setUnitBusy(false); }
  };
  return <section className="finance-original-panel" aria-label="编辑合同请款">
    <header className="finance-original-title"><h2>编辑合同请款</h2><Button disabled={busy} onClick={onClose}>返回我的请款</Button></header>
    {loading ? <Spin /> : error ? <Alert type="error" message={error} action={<Button onClick={() => setRetry((value) => value + 1)}>重新加载</Button>} /> : context && <>
      <Descriptions size="small" column={{ xs: 1, sm: 2, lg: 3 }}>
        <Descriptions.Item label="申请编号">{context.payment.serial_no}</Descriptions.Item>
        <Descriptions.Item label="合同编号">{context.contract?.serial_no}</Descriptions.Item>
        <Descriptions.Item label="合同名称">{context.contract?.title}</Descriptions.Item>
        <Descriptions.Item label="客户名称">{context.payment.customer}</Descriptions.Item>
        <Descriptions.Item label="状态">{context.payment.status}</Descriptions.Item>
      </Descriptions>
      <Form form={form} layout="vertical" disabled={busy}>
        <div className="finance-invoice-request-grid">
          <Form.Item label="交款人" name="payer_name"><Input maxLength={200} /></Form.Item>
          <Form.Item label="申请日期" name="application_date" rules={[{ required: true }]}><DatePicker disabled /></Form.Item>
          <Form.Item name="payment_type_id" hidden rules={[{ required: true }]}><InputNumber /></Form.Item>
          <Form.Item label="收款单位"><Input readOnly value={unit?.payee || ""} onClick={() => setPicker(true)} addonAfter={<Button type="link" disabled={busy} onClick={() => setPicker(true)}>选择</Button>} /></Form.Item>
          <Form.Item label="开户行"><Input readOnly value={unit?.account_bank || ""} /></Form.Item>
          <Form.Item label="账号信息"><Input readOnly value={unit?.account || ""} /></Form.Item>
          <Form.Item label="备注" name="remark"><Input maxLength={2000} /></Form.Item>
        </div>
      </Form>
      <div className="finance-invoice-detail-section-title">付款信息</div>
      <Table<any> rowKey={paymentLineKey} size="small" pagination={false} scroll={{ x: 1200 }} dataSource={context.items || []}
        rowSelection={{ selectedRowKeys: selected, getCheckboxProps: () => ({ disabled: busy }), onChange: (keys) => {
          const next = keys.map(String); setSelected(next);
          setAmounts((previous) => ({ ...previous, ...Object.fromEntries(next.map((key) => [key, previous[key] ?? context.items.find((row: any) => paymentLineKey(row) === key)?.remaining_amount ?? null])) }));
        } }} columns={[
          { title: "序号", width: 65, render: (_, _row, index) => index + 1 },
          { title: "案件类型", dataIndex: "case_type", width: 100 },
          { title: "案件名称", dataIndex: "case_title", width: 200 },
          { title: "案号", dataIndex: "case_no", width: 170 },
          { title: "费用类型", dataIndex: "fee_type", width: 110 },
          { title: "通知时间", dataIndex: "inform_date", width: 110 },
          { title: "待付金额", dataIndex: "remaining_amount", width: 110, render: (value) => value == null ? "未提供" : Number(value).toFixed(2) },
          { title: "本次支付", width: 140, render: (_, row) => <InputNumber min={0.01} max={row.remaining_amount} precision={2} disabled={busy || !selected.includes(paymentLineKey(row))} value={amounts[paymentLineKey(row)]} onChange={(value) => setAmounts((previous) => ({ ...previous, [paymentLineKey(row)]: value }))} style={{ width: "100%" }} /> },
          { title: "备注", width: 180, render: (_, row) => <Input disabled={busy} maxLength={1000} value={remarks[paymentLineKey(row)] || ""} onChange={(event) => setRemarks((previous) => ({ ...previous, [paymentLineKey(row)]: event.target.value }))} /> },
        ]} />
      <Space wrap style={{ marginTop: 16 }}><Button disabled={busy} onClick={onClose}>取消</Button><Button loading={busy} onClick={() => void save(false)}>保存修改</Button><Button type="primary" loading={busy} onClick={() => void save(true)}>保存并重新提交</Button></Space>
      <ContractPaymentUnitPicker open={picker} options={context.payment_types || []} selectedId={unit?.value} onCancel={() => setPicker(false)} onSelect={(row) => { form.setFieldValue("payment_type_id", row.value); setPicker(false); }} onCreate={() => { unitForm.resetFields(); unitForm.setFieldValue("nature", "官费"); setUnitCreate(true); }} />
      <PaymentTypeCreateModal open={unitCreate} paymentTypeCreateForm={unitForm} creating={unitBusy} onCancel={() => setUnitCreate(false)} onOk={() => void createUnit()} />
    </>}
  </section>;
}
