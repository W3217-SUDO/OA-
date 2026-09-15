import { useEffect, useState } from "react";
import { Button, DatePicker, Form, Input, InputNumber, message, Modal, Select, Space, Upload } from "antd";
import dayjs from "dayjs";
import { api } from "../api";
import "./payment-application.css";
import { PaymentDocument } from "./PaymentDocument";

export function PaymentApplicationPage({ record, canPay, onClose, onChange, onCase, onContract }: { record: any; canPay: boolean; onClose: () => void; onChange: () => Promise<void>; onCase?: (no: string) => void; onContract?: (no: string) => void }) {
  const [row, setRow] = useState(record);
  const [printing, setPrinting] = useState(Boolean(record.data?._open_print));
  const [writing, setWriting] = useState(Boolean(record.data?._open_writeoff));
  const [busy, setBusy] = useState(false);
  const [files, setFiles] = useState<any[]>([]);
  const [form] = Form.useForm();
  const data = row.data || {};
  const internal = Boolean(data.application_items);
  const status = data.payment_status || row.status;
  const waiting = !internal && ["已审批", "待付款"].includes(status);
  const pending = !internal && status === "待核销";
  useEffect(() => {
    form.setFieldsValue({amount:data.amount, paid_date:dayjs(), payment_method:"自动扣款"});
  }, [row.id, data.amount, form]);
  const submit = async (printAfter: boolean) => {
    if (busy) return;
    setBusy(true);
    try {
      const response = data._batch_ids ? await api.post("/finance/payment-workflow/submit-batch", {record_ids:data._batch_ids}) : await api.post(`/finance/payment-workflow/${row.id}/submit`);
      setRow((await api.get(`/finance/payment-workflow/${response.data.id}/document`)).data);
      await onChange();
      message.success("已提交至待核销列表");
      if (printAfter) window.setTimeout(() => window.print(), 100);
    } catch (error: any) { message.error(error?.response?.data?.detail || "提交失败"); }
    finally { setBusy(false); }
  };
  const writeoff = async () => {
    const values = await form.validateFields();
    if (!files.length) return message.warning("请上传付款凭证");
    if (busy) return;
    setBusy(true);
    try {
      const body = new FormData();
      body.append("paid_date", values.paid_date.format("YYYY-MM-DD"));
      for (const key of ["amount", "payment_method", "invoice_no", "remark"]) body.append(key, String(values[key] ?? ""));
      for (const file of files) body.append("files", file.originFileObj || file);
      const response = await api.post(`/finance/payment-workflow/${row.id}/writeoff`, body);
      setRow((await api.get(`/finance/payment-workflow/${response.data.id}/document`)).data); setWriting(false); setFiles([]);
      await onChange();
      message.success("已付款，凭证已关联案件费用发票号");
    } catch (error: any) { message.error(error?.response?.data?.detail || "核销失败"); }
    finally { setBusy(false); }
  };
  return <section className="payment-application-page">
    <div className="payment-screen-actions"><Space>
      <Button onClick={onClose}>返回列表</Button>
      {!internal && <Button onClick={() => setPrinting(!printing)}>{printing ? "查看请款单" : "付款单打印"}</Button>}
      {printing && waiting && canPay && <><Button loading={busy} onClick={() => void submit(false)}>提交</Button><Button loading={busy} onClick={() => void submit(true)}>提交并打印</Button></>}
      {printing && !waiting && <Button onClick={() => window.print()}>打印</Button>}
      {pending && canPay && <Button type="primary" onClick={() => { form.setFieldsValue({ amount: data.amount, paid_date: dayjs(), payment_method: "自动扣款" }); setWriting(true); }}>核销</Button>}
    </Space></div>
    <PaymentDocument row={row} printing={printing} onCase={onCase} onContract={onContract} />
    <Modal open={writing} title="付款核销" onCancel={() => setWriting(false)} onOk={() => void writeoff()} confirmLoading={busy} okText="确定" cancelText="取消">
      <Form form={form} layout="horizontal" labelCol={{span:7}} wrapperCol={{span:17}}>
        <Form.Item label="付款打包号"><Input readOnly value={data.payment_package_no} /></Form.Item>
        <Form.Item name="amount" label="确认付款金额" rules={[{required:true}]}><InputNumber readOnly /></Form.Item>
        <Form.Item name="paid_date" label="付款日期" rules={[{required:true}]}><DatePicker /></Form.Item>
        <Form.Item name="payment_method" label="付款方式" rules={[{required:true}]}><Select options={["自动扣款", "银行卡", "现金"].map(value => ({value,label:value}))} /></Form.Item>
        <Form.Item name="invoice_no" label="付款单据号" rules={[{required:true, whitespace:true}]}><Input /></Form.Item>
        <Form.Item name="remark" label="付款备注"><Input.TextArea /></Form.Item>
        <Form.Item label="付款凭证" required><Upload beforeUpload={() => false} multiple maxCount={10} fileList={files} onChange={({fileList}) => setFiles(fileList)}><Button>选择文件</Button></Upload></Form.Item>
      </Form>
    </Modal>
  </section>;
}
