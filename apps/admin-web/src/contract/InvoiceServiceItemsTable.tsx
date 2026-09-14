import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import { Button, Form, Input, InputNumber, Table, Tooltip } from "antd";
import type { FormInstance } from "antd";
import { invoiceMoney, invoiceTotal } from "./contractInvoiceApplication";

export interface InvoiceServiceItemsTableProps {
  form: FormInstance;
  fieldName?: string;
  disabled?: boolean;
}

export function InvoiceServiceItemsTable({ form, fieldName = "service_items", disabled = false }: InvoiceServiceItemsTableProps) {
  const values = Form.useWatch(fieldName, form) || [];
  const updateProduct = (index: number, key: string, value: number | null) => {
    const row = { ...form.getFieldValue([fieldName, index]), [key]: value };
    form.setFieldValue([fieldName, index, "amount"], invoiceMoney(Number(row.quantity || 0) * Number(row.unit_price || 0)));
  };
  return <Form.List name={fieldName}>
    {(fields, { add, remove }) => <>
      <Table size="small" rowKey="key" pagination={false} scroll={{ x: 1040 }} dataSource={fields}
        columns={[
          { title: "序号", width: 60, render: (_, field) => field.name + 1 },
          { title: "服务名称", width: 260, render: (_, field) => <Form.Item name={[field.name, "service_name"]} rules={[{ required: true, whitespace: true, message: "请输入服务名称" }]} style={{ marginBottom: 0 }}><Input disabled={disabled} aria-label={`服务名称 ${field.name + 1}`} /></Form.Item> },
          ...([ ["quantity", "数量", 0.01], ["unit_price", "单价", 0], ["amount", "金额", 0], ["tax_rate", "税率(%)", 0], ["tax_amount", "税额", 0] ] as const).map(([key, title, min]) => ({
            title, width: 132, render: (_: unknown, field: { name: number }) => <Form.Item name={[field.name, key]} rules={[{ required: true, message: `请输入${title}` }, { type: "number", min, max: key === "tax_rate" ? 100 : undefined, message: `${title}超出允许范围` }]} style={{ marginBottom: 0 }}>
              <InputNumber aria-label={`${title} ${field.name + 1}`} disabled={disabled} readOnly={key === "amount"} min={min} max={key === "tax_rate" ? 100 : undefined} precision={2} style={{ width: "100%" }} onChange={key === "quantity" || key === "unit_price" ? value => updateProduct(field.name, key, value) : undefined} />
            </Form.Item>,
          })),
          { title: "操作", width: 60, render: (_, field) => <Tooltip title="删除服务项"><Button aria-label={`删除服务项 ${field.name + 1}`} icon={<DeleteOutlined />} disabled={disabled || fields.length <= 1} danger onClick={() => remove(field.name)} /></Tooltip> },
        ]}
        summary={() => <Table.Summary.Row><Table.Summary.Cell index={0} colSpan={4}>合计</Table.Summary.Cell><Table.Summary.Cell index={4}>{invoiceTotal(values).toFixed(2)}</Table.Summary.Cell><Table.Summary.Cell index={5} /><Table.Summary.Cell index={6}>{invoiceTotal(values.map((row: any) => ({ amount: row?.tax_amount }))).toFixed(2)}</Table.Summary.Cell><Table.Summary.Cell index={7} /></Table.Summary.Row>}
      />
      <Button style={{ marginTop: 8 }} disabled={disabled || fields.length >= 100} icon={<PlusOutlined />} onClick={() => add({ service_name: "", quantity: 1, unit_price: 0, amount: 0, tax_rate: 0, tax_amount: 0 })}>新增服务项</Button>
    </>}
  </Form.List>;
}
