import { Button, Table } from "antd";
import { invoiceObjectRows, invoiceServiceRows } from "./invoiceDetails.mjs";
import type { InvoiceObjectRow, InvoiceServiceRow } from "./invoiceDetails.mjs";

const amount = (value: unknown) => value == null || value === "" || !Number.isFinite(Number(value)) ? "未提供" : Number(value).toFixed(2);
const total = (rows: InvoiceServiceRow[], field: "amount" | "tax_amount") => !rows.length || rows.some((row) => row[field] == null) ? null : rows.reduce((sum, row) => sum + Number(row[field]), 0);

export function InvoiceDetailTables({ record, openCase, openContract }: {
  record: any; openCase: (value: string) => void; openContract: (value: string) => void;
}) {
  const services = invoiceServiceRows(record);
  const objects = invoiceObjectRows(record);
  return <>
    <div className="finance-invoice-detail-section-title">服务项</div>
    <Table<InvoiceServiceRow> rowKey="key" size="small" pagination={false} dataSource={services} scroll={{ x: 800 }}
      locale={{ emptyText: "未提供服务明细" }} columns={[
        { title: "序号", width: 65, render: (_, _row, index) => index + 1 },
        { title: "服务名称", dataIndex: "service_name", width: 230 },
        { title: "数量", dataIndex: "quantity" },
        { title: "单价", dataIndex: "unit_price", render: amount },
        { title: "金额", dataIndex: "amount", render: amount },
        { title: "税率", dataIndex: "tax_rate", render: (value) => value == null ? "未提供" : `${value}%` },
        { title: "税额", dataIndex: "tax_amount", render: amount },
      ]} summary={() => <Table.Summary.Row><Table.Summary.Cell index={0} colSpan={4}>合计</Table.Summary.Cell>
        <Table.Summary.Cell index={4}>{amount(total(services, "amount"))}</Table.Summary.Cell>
        <Table.Summary.Cell index={5} />
        <Table.Summary.Cell index={6}>{amount(total(services, "tax_amount"))}</Table.Summary.Cell>
      </Table.Summary.Row>} />
    <div className="finance-invoice-detail-section-title">合同信息 / 费用明细</div>
    <Table<InvoiceObjectRow> rowKey="key" size="small" pagination={false} dataSource={objects} scroll={{ x: 1400 }}
      locale={{ emptyText: "未提供费用明细" }} columns={[
        { title: "序号", width: 65, render: (_, _row, index) => index + 1 },
        { title: "合同编号", dataIndex: "contract_no", width: 170, render: (value) => value ? <Button type="link" onClick={() => openContract(value)}>{value}</Button> : "未关联" },
        { title: "外部合同号", dataIndex: "external_contract_no", width: 150 },
        { title: "案件类型", dataIndex: "case_type", width: 100 },
        { title: "案件名称", width: 200, render: (_, row) => row.case_name || row.case_title },
        { title: "案号", dataIndex: "case_no", width: 170, render: (value) => value ? <Button type="link" onClick={() => openCase(value)}>{value}</Button> : "未关联" },
        { title: "费用类型", dataIndex: "fee_type", width: 110 },
        { title: "费用金额", dataIndex: "fee_amount", width: 110, render: amount },
        { title: "到账金额", dataIndex: "received_amount", width: 110, render: amount },
        { title: "已开票金额", dataIndex: "issued_amount", width: 110, render: amount },
        { title: "本次开票", dataIndex: "allocation_amount", width: 110, render: amount },
      ]} />
  </>;
}
