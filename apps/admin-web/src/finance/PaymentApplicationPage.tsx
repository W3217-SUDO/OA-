import { useEffect, useState } from "react";
import { Button, DatePicker, Form, Input, InputNumber, message, Modal, Select, Space, Upload } from "antd";
import dayjs from "dayjs";
import { api } from "../api";
import "./payment-application.css";
import { PaymentDocument } from "./PaymentDocument";
import { paymentMethodOptions } from "./constants";

// 付款申请单 Word 单独下载后再打开打印，不在系统页面上弹浏览器打印窗口、不遮挡侧栏和顶栏。
async function downloadPaymentWord(recordId: number) {
  const response = await api.get(`/finance/payment-workflow/${recordId}/print-word`, { responseType: "blob" });
  const disposition = String(response.headers?.["content-disposition"] || "");
  const match = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
  let filename = "付款申请单.docx";
  if (match?.[1]) { try { filename = decodeURIComponent(match[1]); } catch { filename = match[1]; } }
  const url = URL.createObjectURL(response.data);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function blobErrorDetail(error: any) {
  const data = error?.response?.data;
  if (data instanceof Blob) { try { return JSON.parse(await data.text())?.detail; } catch { return ""; } }
  return data?.detail;
}

export function PaymentApplicationPage({ record, onClose, onChange, onCase, onContract, reviewable = false }: { record: any; onClose: () => void; onChange: () => Promise<void>; onCase?: (no: string) => void; onContract?: (no: string) => void; reviewable?: boolean }) {
  const [row, setRow] = useState(record);
  const [printing, setPrinting] = useState(Boolean(record.data?._open_print));
  const [writing, setWriting] = useState(Boolean(record.data?._open_writeoff && record.data?.can_writeoff_payment));
  const [busy, setBusy] = useState(false);
  const [files, setFiles] = useState<any[]>([]);
  const [reviewComment, setReviewComment] = useState("");
  const [form] = Form.useForm();
  const data = row.data || {};
  const internal = Boolean(data.application_items);
  const status = row.status || data.payment_status;
  const canSubmitPayment = data.can_submit_payment === true;
  const canWriteoffPayment = data.can_writeoff_payment === true;
  const waiting = !internal && ["已审批", "待付款"].includes(status);
  const pending = !internal && status === "待核销";
  const reviewing = reviewable && !internal && status === "待审批";
  const printWord = async (recordId: number) => {
    try { await downloadPaymentWord(recordId); message.success("付款申请单已导出，请打开文件后打印"); }
    catch (error: any) { message.error(await blobErrorDetail(error) || "付款申请单导出失败"); }
  };
  const confirmPrint = () => Modal.confirm({
    title: "打印付款申请单",
    content: "将导出付款申请单 Word 文件，打开文件后再确认打印。",
    okText: "导出打印", cancelText: "取消",
    onOk: () => printWord(row.id),
  });
  const review = async (approved: boolean) => {
    if (busy) return;
    if (!approved && !reviewComment.trim()) return message.warning("拒绝时请填写审批意见");
    setBusy(true);
    try {
      const contractPayment = row.module === "contract_payment" || data._source_module === "contract_payment";
      await api.post(contractPayment ? `/contract-payment-applications/${row.id}/review` : `/finance/fees/${row.id}/review`, { approved, comment: reviewComment.trim() });
      message.success(approved ? "审批已通过" : "申请已拒绝");
      await onChange();
      onClose();
    } catch (error: any) { message.error(error?.response?.data?.detail || "审批失败"); }
    finally { setBusy(false); }
  };
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
      if (printAfter) await printWord(response.data.id);
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
      message.success("已付款，缴费凭证已关联案件费用");
    } catch (error: any) { message.error(error?.response?.data?.detail || "核销失败"); }
    finally { setBusy(false); }
  };
  return <section className="payment-application-page">
    <div className="payment-screen-actions"><Space>
      <Button onClick={onClose}>返回列表</Button>
      {!internal && <Button onClick={() => setPrinting(!printing)}>{printing ? "查看请款单" : "付款单打印"}</Button>}
      {waiting && canSubmitPayment && <><Button type="primary" loading={busy} onClick={() => void submit(false)}>提交</Button><Button type="primary" loading={busy} onClick={() => void submit(true)}>提交并打印</Button></>}
      {printing && !waiting && <Button onClick={confirmPrint}>打印</Button>}
      {pending && canWriteoffPayment && <Button type="primary" onClick={() => { form.setFieldsValue({ amount: data.amount, paid_date: dayjs(), payment_method: "自动扣款" }); setWriting(true); }}>核销</Button>}
    </Space></div>
    {reviewing && <div className="payment-review-panel">
      <div className="payment-review-title">付款审批</div>
      <Input.TextArea aria-label="审批意见" placeholder="审批意见" rows={3} maxLength={500} value={reviewComment} onChange={(event) => setReviewComment(event.target.value)} />
      <Space><Button type="primary" loading={busy} onClick={() => void review(true)}>同意</Button><Button danger loading={busy} onClick={() => void review(false)}>拒绝</Button></Space>
    </div>}
    <PaymentDocument row={row} printing={printing} onCase={onCase} onContract={onContract} />
    <Modal open={writing} title="付款核销" onCancel={() => setWriting(false)} onOk={() => void writeoff()} confirmLoading={busy} okText="确定" cancelText="取消">
      <Form form={form} layout="horizontal" labelCol={{span:7}} wrapperCol={{span:17}}>
        <Form.Item label="付款打包号"><Input readOnly value={data.payment_package_no} /></Form.Item>
        <Form.Item name="amount" label="确认付款金额" rules={[{required:true}]}><InputNumber readOnly /></Form.Item>
        <Form.Item name="paid_date" label="付款日期" rules={[{required:true}]}><DatePicker /></Form.Item>
        <Form.Item name="payment_method" label="付款方式" rules={[{required:true}]}><Select options={paymentMethodOptions.map(value => ({value,label:value}))} /></Form.Item>
        <Form.Item name="invoice_no" label="付款单据号" rules={[{required:true, whitespace:true}]}><Input /></Form.Item>
        <Form.Item name="remark" label="付款备注"><Input.TextArea /></Form.Item>
        <Form.Item label="付款凭证" required><Upload beforeUpload={() => false} multiple maxCount={10} fileList={files} onChange={({fileList}) => setFiles(fileList)}><Button>选择文件</Button></Upload></Form.Item>
      </Form>
    </Modal>
  </section>;
}
