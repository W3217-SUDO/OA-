import { Button, DatePicker, Divider, Form, Input, InputNumber, Select, Space, Table, Tag } from "antd";
import type { FormInstance } from "antd";
import type { Key } from "react";
import { useState } from "react";
import { InvoiceServiceItemsTable } from "./InvoiceServiceItemsTable";
import { filterInvoiceSubjects, invoiceMoney, invoiceSubjectQueryFields, invoiceTotal, selectedInvoiceAllocations } from "./contractInvoiceApplication";
import type { InvoiceAllocation, InvoiceApplicationSubject } from "./contractInvoiceApplication";
import "./invoice-application.css";

export type { InvoiceApplicationSubject } from "./contractInvoiceApplication";
export interface InvoiceApplicationFormProps {
  form: FormInstance;
  subjects: InvoiceApplicationSubject[];
  selectedFeeIds: Key[];
  onSelectionChange: (keys: Key[]) => void;
  disabled?: boolean;
}

export function InvoiceApplicationForm({ form, subjects, selectedFeeIds, onSelectionChange, disabled = false }: InvoiceApplicationFormProps) {
  const [queryForm] = Form.useForm();
  const [query, setQuery] = useState<Record<string, any>>({});
  const [page, setPage] = useState(1);
  const allocations: InvoiceAllocation[] = Form.useWatch("case_fee_allocations", form) || [];
  const amount = Form.useWatch("amount", form) || 0;
  const available = invoiceTotal(subjects.filter(row => selectedFeeIds.map(Number).includes(row.fee_id)).map(row => ({ amount: row.invoiceable_amount })));
  const overAmount = invoiceTotal(allocations.map(row => ({ amount: Math.max(0, invoiceMoney(row.amount) - Number(subjects.find(item => item.fee_id === row.fee_id)?.invoiceable_amount || 0)) })));
  const setAllocations = (next: InvoiceAllocation[]) => {
    form.setFieldValue("case_fee_allocations", next);
    const total = invoiceTotal(next);
    form.setFieldValue("amount", total);
    const services = form.getFieldValue("service_items") || [];
    // As in the original page, a single service follows the selected fee total.
    // Multiple manually split services are never silently redistributed.
    if (services.length <= 1 && Number(services[0]?.quantity || 1) === 1) {
      const service = services[0] || {};
      const quantity = Number(service.quantity || 1);
      form.setFieldValue("service_items", [{ service_name: "法律服务费", tax_rate: 0, tax_amount: 0, ...service, quantity, unit_price: invoiceMoney(total / quantity), amount: total }]);
    }
  };
  const choose = (keys: Key[]) => {
    setAllocations(selectedInvoiceAllocations(keys, form.getFieldValue("case_fee_allocations") || [], subjects));
    onSelectionChange(keys);
  };
  const moneyCell = (value: unknown) => value == null ? "-" : invoiceMoney(value).toFixed(2);
  const required = (label: string) => [{ required: true, whitespace: true, message: `请填写${label}` }];
  const special = (label: string) => [({ getFieldValue }: any) => ({ required: String(getFieldValue("invoice_type") || "").includes("专用"), whitespace: true, message: `专用发票必须填写${label}` })];
  return <div className="invoice-application-form">
    <Form form={form} layout="horizontal" disabled={disabled} labelCol={{ flex: "110px" }} wrapperCol={{ flex: "auto" }}>
      <Divider titlePlacement="start" plain>申请信息</Divider>
      <div className="invoice-fields">
        <Form.Item label="申请人" name="applicant"><Input readOnly /></Form.Item>
        <Form.Item label="申请单号" name="application_no"><Input readOnly placeholder="提交后生成" /></Form.Item>
        <Form.Item label="申请日期" name="application_date"><Input readOnly /></Form.Item>
        <Form.Item label="开票金额" name="amount" rules={[{ required: true, type: "number", min: 0.01, message: "请选择费用并填写本次开票金额" }]}><InputNumber readOnly precision={2} style={{ width: "100%" }} /></Form.Item>
      </div>
      <Divider titlePlacement="start" plain>发票内容</Divider>
      <div className="invoice-fields">
        <Form.Item label="发票类别" name="invoice_type" rules={required("发票类别")}><Select options={["增值税普通发票", "增值税专用发票", "电子普通发票", "电子专用发票"].map(value => ({ value, label: value }))} /></Form.Item>
        <Form.Item label="发票抬头" name="invoice_title" rules={required("发票抬头")}><Input /></Form.Item>
        <Form.Item label="纳税人识别号" name="taxpayer_id" rules={required("纳税人识别号")}><Input /></Form.Item>
        <Form.Item label="银行账号" name="bank_account" dependencies={["invoice_type"]} rules={special("银行账号")}><Input /></Form.Item>
        <Form.Item label="公司电话" name="invoice_phone" dependencies={["invoice_type"]} rules={special("公司电话")}><Input /></Form.Item>
        <Form.Item label="开户银行" name="bank_name" dependencies={["invoice_type"]} rules={special("开户银行")}><Input /></Form.Item>
        <Form.Item label="开票地址" name="invoice_address" dependencies={["invoice_type"]} rules={special("开票地址")}><Input /></Form.Item>
        <Form.Item label="开票内容" name="invoice_content" rules={required("开票内容")}><Input /></Form.Item>
      </div>
      <Form.Item label="备注" name="remark"><Input.TextArea rows={2} /></Form.Item>
      <Divider titlePlacement="start" plain>服务项</Divider>
      <InvoiceServiceItemsTable form={form} disabled={disabled} />
      <Divider titlePlacement="start" plain>交付信息</Divider>
      <div className="invoice-fields">
        <Form.Item label="交付方式" name="delivery_method" rules={required("交付方式")}><Select options={["电子发票", "邮寄纸质发票", "现场领取"].map(value => ({ value, label: value }))} /></Form.Item>
        <Form.Item label="接收邮箱" name="email" dependencies={["delivery_method"]} rules={[{ type: "email", message: "邮箱格式无效" }, ({ getFieldValue }) => ({ required: getFieldValue("delivery_method") === "电子发票", message: "电子发票必须填写接收邮箱" })]}><Input /></Form.Item>
        <Form.Item label="收件人" name="recipient"><Input /></Form.Item>
        <Form.Item label="联系电话" name="recipient_phone"><Input /></Form.Item>
        <Form.Item label="交付地址" name="delivery_address" dependencies={["delivery_method"]} rules={[({ getFieldValue }) => ({ required: getFieldValue("delivery_method") !== "电子发票", message: "纸质发票或现场领取必须填写交付地址" })]}><Input /></Form.Item>
      </div>
      <Form.Item name="case_fee_allocations" hidden><Input /></Form.Item>
    </Form>
    <Divider titlePlacement="start" plain>发票明细</Divider>
    <Form form={queryForm} layout="horizontal" labelCol={{ flex: "100px" }} wrapperCol={{ flex: "auto" }} onFinish={values => {
      const dates = values.received_range || [];
      setQuery({ ...values, received_from: dates[0]?.format("YYYY-MM-DD"), received_to: dates[1]?.format("YYYY-MM-DD") }); setPage(1);
    }}>
      <div className="invoice-query-fields">
        {invoiceSubjectQueryFields.map(([key, label]) => <Form.Item key={key} name={key} label={label}><Input allowClear /></Form.Item>)}
        <Form.Item label="回款时间" name="received_range"><DatePicker.RangePicker style={{ width: "100%" }} /></Form.Item>
      </div>
      <Space><Button htmlType="submit" type="primary">查询</Button><Button onClick={() => { queryForm.resetFields(); setQuery({}); setPage(1); }}>重置</Button></Space>
    </Form>
    <div className="invoice-allocation-totals"><Tag>已选 {selectedFeeIds.length} 笔</Tag><span>可开合计：{moneyCell(available)}</span><span>本次开票：{moneyCell(amount)}</span><span>高开金额：{moneyCell(overAmount)}</span></div>
    <Table<InvoiceApplicationSubject> rowKey="fee_id" size="small" dataSource={filterInvoiceSubjects(subjects, query)} scroll={{ x: 1720 }}
      pagination={{ current: page, onChange: setPage, defaultPageSize: 10, showSizeChanger: true, showTotal: total => `共 ${total} 笔` }}
      rowSelection={{ preserveSelectedRowKeys: true, selectedRowKeys: selectedFeeIds, onChange: choose, getCheckboxProps: row => ({ disabled: disabled || row.amount == null || row.invoiceable_amount == null, title: row.amount == null || row.invoiceable_amount == null ? "费用金额或可开票余额缺失，请先核对财务资料" : undefined }) }}
      columns={[
        { title: "合同编号", dataIndex: "contract_no", width: 150 },
        { title: "合同外部编号", dataIndex: "external_contract_no", width: 150 },
        { title: "案件名称", dataIndex: "case_title", width: 220 },
        { title: "案件阶段", dataIndex: "case_stage", width: 100 },
        { title: "案号", dataIndex: "case_no", width: 150 },
        { title: "费用编号", dataIndex: "fee_no", width: 150 },
        { title: "费用类型", dataIndex: "fee_type", width: 140 },
        { title: "费用归属", dataIndex: "expense_scope", width: 100 },
        ...([["amount", "费用金额"], ["received_amount", "已到账金额"], ["invoiced_amount", "已开票金额"], ["invoiceable_amount", "可开票金额"]] as const).map(([dataIndex, title]) => ({ title, dataIndex, width: 115, render: moneyCell })),
        { title: "本次开票", width: 150, render: (_, row) => <InputNumber aria-label={`本次开票 ${row.fee_no || row.fee_id}`} min={0.01} precision={2} style={{ width: "100%" }} disabled={disabled || !selectedFeeIds.map(Number).includes(row.fee_id)} value={allocations.find(item => item.fee_id === row.fee_id)?.amount} onChange={value => setAllocations(allocations.map(item => item.fee_id === row.fee_id ? { ...item, amount: value == null ? 0 : Number(value) } : item))} /> },
      ]}
    />
  </div>;
}
