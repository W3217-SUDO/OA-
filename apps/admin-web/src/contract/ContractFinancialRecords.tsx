import { Button, Table } from "antd";
import { normalizeIncomingPaymentForContract, normalizeInvoiceObject, normalizePaidObject } from "../contractObjectPresentation.mjs";
import { amount } from "./constants";
import type { Contract } from "./types";

interface Props {
  viewing: Contract;
  detailReceipts: any[];
  detailInvoices: Contract[];
  detailPayments: Contract[];
  personName: (value: unknown) => string;
  onOpenRelatedPayment: (row: Contract) => void;
}

export function ContractFinancialRecords({ viewing, detailReceipts, detailInvoices, detailPayments, personName, onOpenRelatedPayment }: Props) {
  const presentedReceipts = detailReceipts
    .map((row) => {
      const item = normalizeIncomingPaymentForContract(row, viewing || {});
      if (!item) return null;
      return {
        ...row,
        receipt_no: item.sequenceNo,
        received_date: item.receivedDate,
        bank_reference: item.bankReference,
        amount: item.amount,
        official_amount: item.officialAmount,
        agency_amount: item.agencyAmount,
        other_amount: item.otherAmount,
        payment_method: item.paymentMethod,
        claimant: item.claimant,
      };
    })
    .filter(Boolean);

  const presentedInvoices = detailInvoices.map((row) => {
    const item = normalizeInvoiceObject(row);
    return {
      ...row,
      serial_no: item.applicationNo,
      status: item.status,
      description: item.remark,
      data: {
        ...row.data,
        invoice_no: item.invoiceNo,
        invoice_date: item.invoiceDate,
        amount: item.amount,
        official_amount: item.officialAmount,
        agency_amount: item.agencyAmount,
        other_amount: item.otherAmount,
        __lineThrough: item.lineThrough,
      },
    };
  });

  const presentedPayments = detailPayments.map((row) => {
    const item = normalizePaidObject(row);
    return {
      ...row,
      serial_no: item.applicationNo,
      data: {
        ...row.data,
        applicant: item.applicant,
        pending_amount: item.pendingAmount,
        payment_date: item.paymentDate,
        payment_reference: item.packageNo,
        amount: item.paidAmount,
        payment_type: item.paymentType,
        official_amount: item.officialAmount,
        other_amount: item.otherAmount,
        __lineThrough: item.lineThrough,
      },
    };
  });

  return <>
          <section className="contract-record-section">
            <h3>回款记录</h3>
            <Table
              size="small"
              rowKey="id"
              pagination={false}
              scroll={{ x: 1180 }}
              dataSource={presentedReceipts as any[]}
              locale={{ emptyText: "暂无回款记录" }}
              columns={[
                { title: "序号", width: 64, render: (_: unknown, __: any, index: number) => index + 1 },
                { title: "回款单号", dataIndex: "receipt_no", width: 150 },
                { title: "回款日期", dataIndex: "received_date", width: 120 },
                { title: "银行单据号", dataIndex: "bank_reference", width: 150 },
                { title: "回款金额", dataIndex: "amount", width: 110, render: (value: number) => amount(value) },
                { title: "官费", width: 100, render: (_: unknown, row: any) => amount(row.official_amount || 0) },
                { title: "代理费", width: 100, render: (_: unknown, row: any) => amount(row.agency_amount || 0) },
                { title: "其他费用", width: 100, render: (_: unknown, row: any) => amount(row.other_amount || 0) },
                { title: "回款方式", dataIndex: "payment_method", width: 120 },
                { title: "回款分配人", dataIndex: "claimant", width: 120 },
              ]}
            />
          </section>
          <section className="contract-record-section">
            <h3>开票记录</h3>
            <Table
              size="small"
              rowKey="id"
              pagination={false}
              scroll={{ x: 1120 }}
              dataSource={presentedInvoices}
              rowClassName={(row: any) => (row.data?.__lineThrough ? "contract-line-through" : "")}
              locale={{ emptyText: "暂无开票记录" }}
              columns={[
                { title: "序号", width: 64, render: (_: unknown, __: Contract, index: number) => index + 1 },
                { title: "请票单号", dataIndex: "serial_no", width: 150 },
                {
                  title: "发票号码",
                  width: 150,
                  render: (_: unknown, row: Contract) => (row.data as any).invoice_no || "—",
                },
                {
                  title: "开票日期",
                  width: 120,
                  render: (_: unknown, row: Contract) => (row.data as any).invoice_date || "—",
                },
                {
                  title: "开票金额",
                  width: 110,
                  render: (_: unknown, row: Contract) => amount((row.data as any).amount || 0),
                },
                {
                  title: "官费",
                  width: 100,
                  render: (_: unknown, row: Contract) => amount((row.data as any).official_amount || 0),
                },
                {
                  title: "代理费",
                  width: 100,
                  render: (_: unknown, row: Contract) => amount((row.data as any).agency_amount || 0),
                },
                {
                  title: "其他费用",
                  width: 100,
                  render: (_: unknown, row: Contract) => amount((row.data as any).other_amount || 0),
                },
                { title: "状态", dataIndex: "status", width: 110 },
                { title: "备注", dataIndex: "description", width: 180 },
              ]}
            />
          </section>
          <section className="contract-record-section">
            <h3>付款记录</h3>
            <Table
              size="small"
              rowKey="id"
              pagination={false}
              scroll={{ x: 1120 }}
              dataSource={presentedPayments}
              rowClassName={(row: any) => (row.data?.__lineThrough ? "contract-line-through" : "")}
              locale={{ emptyText: "暂无付款记录" }}
              columns={[
                { title: "序号", width: 64, render: (_: unknown, __: Contract, index: number) => index + 1 },
                {
                  title: "申请单号",
                  dataIndex: "serial_no",
                  width: 150,
                  render: (value: string, row: Contract) =>
                    value ? (
                      <Button type="link" className="contract-cell-link" onClick={() => onOpenRelatedPayment(row)}>
                        {value}
                      </Button>
                    ) : (
                      "—"
                    ),
                },
                {
                  title: "申请人",
                  width: 120,
                  render: (_: unknown, row: Contract) =>
                    personName(
                      (row.data as any).applicant_display_name ||
                        (row.data as any).applicant ||
                        (row as any).owner_display_name ||
                        row.owner,
                    ),
                },
                {
                  title: "待付金额",
                  width: 110,
                  render: (_: unknown, row: Contract) => amount((row.data as any).pending_amount || 0),
                },
                {
                  title: "付款日期",
                  width: 120,
                  render: (_: unknown, row: Contract) => (row.data as any).payment_date || "—",
                },
                {
                  title: "付款单据",
                  width: 140,
                  render: (_: unknown, row: Contract) => (row.data as any).payment_reference || "—",
                },
                {
                  title: "付款金额",
                  width: 110,
                  render: (_: unknown, row: Contract) => amount((row.data as any).amount || 0),
                },
                {
                  title: "付款类型",
                  width: 120,
                  render: (_: unknown, row: Contract) => (row.data as any).payment_type || "—",
                },
                {
                  title: "付款标的",
                  width: 260,
                  dataIndex: "line_summary",
                  render: (value: string) => value || "—",
                },
                {
                  title: "官费",
                  width: 100,
                  render: (_: unknown, row: Contract) => amount((row.data as any).official_amount || 0),
                },
                {
                  title: "其他费用",
                  width: 100,
                  render: (_: unknown, row: Contract) => amount((row.data as any).other_amount || 0),
                },
              ]}
            />
          </section>
  </>;
}
