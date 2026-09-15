import { useState } from "react";
import { Alert, Button, DatePicker, Descriptions, Form, Input, InputNumber, message, Modal, Select, Space, Steps, Table, Upload } from "antd";
import dayjs from "dayjs";
import { api } from "../api";
import "./payment-application.css";

export function PaymentApplicationPage({ record, canPay, onClose, onChange }: { record: any; canPay: boolean; onClose: () => void; onChange: () => Promise<void> }) {
  const [row, setRow] = useState(record);
  const [printing, setPrinting] = useState(Boolean(record.data?._open_print));
  const [writing, setWriting] = useState(false);
  const [busy, setBusy] = useState(false);
  const [files, setFiles] = useState<any[]>([]);
  const [form] = Form.useForm();
  const data = row.data || {};
  const internal = Boolean(data.application_items);
  const status = data.payment_status || row.status;
  const waiting = !internal && ["已审批", "待付款"].includes(status);
  const pending = !internal && status === "待核销";
  const details = data.application_items?.map((item: any) => ({...item.data, id: item.id})) || data.items || data.lines || [{ ...data, id: row.id }];
  const columns = [
    { title: "案号", dataIndex: "case_no" }, { title: "合同编号", dataIndex: "contract_no" },
    { title: "费用类型", render: (_: any, item: any) => item.commission_type || item.expense_subtype || item.fee_type },
    { title: "支付对象", render: (_: any, item: any) => item.payee_display_name || item.payee || "—" },
    { title: "金额", render: (_: any, item: any) => item.amount ?? item.requested_amount ?? "—" },
    { title: "备注", dataIndex: "remark" }, { title: "截止日期", dataIndex: "deadline" },
  ];
  const submit = async (printAfter: boolean) => {
    if (busy) return;
    setBusy(true);
    try {
      const response = data._batch_ids ? await api.post("/finance/payment-workflow/submit-batch", {record_ids:data._batch_ids}) : await api.post(`/finance/payment-workflow/${row.id}/submit`);
      setRow(response.data);
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
      setRow(response.data); setWriting(false); setFiles([]);
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
    <div className="payment-print-document">
      <h2>{printing ? `${data.company_name || "上海申浩律师事务所"} 付款申请单` : "查看请款单"}</h2>
      {!printing && <Steps size="small" current={["待审批"].includes(status) ? 2 : 3} items={["付款信息填写", "提交申请", "财务审批", "财务付款"].map(title => ({title}))} />}
      <Descriptions bordered size="small" column={3} style={{marginTop: 16}} items={[
        { key: "no", label: "请款单号", children: row.serial_no },
        { key: "package", label: "付款打包号", children: data.payment_package_no || "提交时生成" },
        { key: "status", label: "状态", children: status },
        { key: "contract", label: "合同编号", children: data.contract_no || "—" },
        { key: "contractName", label: "合同名称", children: data.contract_name || "—" },
        { key: "customer", label: "客户名称", children: row.customer || "—" },
        { key: "payee", label: "收款单位", children: data.payee_display_name || data.payee || "—" },
        { key: "bank", label: "开户行", children: data.account_bank || data.bank_name || data.payee_bank || data.bank || "—" },
        { key: "account", label: "银行账号", children: data.account || data.bank_account || data.payee_account || "—" },
        { key: "amount", label: "申请金额", children: data.amount ?? "—" },
        { key: "applicant", label: "申请人", children: data.applicant_display_name || data.applicant || row.owner },
        { key: "date", label: "申请日期", children: String(data.application_date || row.created_at || "").slice(0,10) },
      ]} />
      <Table rowKey={(item: any) => String(item.id || item.case_fee_id || item.contract_object_id)} size="small" bordered pagination={false} dataSource={details} columns={columns} style={{marginTop: 16}} />
      <div className="payment-print-total">备注：{row.description || data.remark || "—"}<span>小计：{data.amount ?? "—"} 元</span></div>
      {printing && <div className="payment-print-signatures"><span>客户管理人签字：</span><span>审批人签字：</span><span>出纳签字：</span></div>}
    </div>
    <Modal open={writing} title="付款核销" onCancel={() => setWriting(false)} onOk={() => void writeoff()} confirmLoading={busy} okText="确定" cancelText="取消">
      <Form form={form} layout="vertical">
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
