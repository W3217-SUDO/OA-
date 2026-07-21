import { useEffect, useMemo, useState } from "react";
import { Button, Card, DatePicker, Form, Input, message, Select, Table } from "antd";
import dayjs from "dayjs";
import { api } from "./api";
import "./contract-center.css";

type Receivable = {
  id: number;
  contract_record_id: number;
  contract_no: string;
  contract_title: string;
  customer: string;
  phase: string;
  due_date: string;
  amount: number;
  received_amount: number;
  remaining_amount: number;
  status: string;
  owner: string;
};
type Contract = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  owner: string;
  department: string;
  data: Record<string, any>;
};
type Profile = { username: string; display_name: string; department: string };

const money = (value: unknown) => Number(value || 0).toFixed(2);

export default function ContractReceivablesPage({ initialView }: { initialView: string }) {
  const [receivables, setReceivables] = useState<Receivable[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [profile, setProfile] = useState<Profile>({ username: "", display_name: "", department: "" });
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState<Record<string, any>>({});
  const [form] = Form.useForm();
  const detailView = initialView === "contract-receivable-detail";

  const load = async () => {
    setLoading(true);
    try {
      const [receivableRes, contractRes, profileRes] = await Promise.all([
        api.get("/receivables"),
        api.get("/records", { params: { module: "contract", page_size: 100 } }),
        api.get("/auth/me"),
      ]);
      setReceivables(receivableRes.data.items || []);
      setContracts(contractRes.data.items || []);
      setProfile(profileRes.data);
    } catch {
      message.error("合同应收加载失败");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { void load(); }, [initialView]);

  const visibleContracts = useMemo(() => {
    const names = [profile.username, profile.display_name].filter(Boolean);
    let rows = contracts;
    if (initialView === "contract-receivable-mine") rows = rows.filter((row) => names.includes(row.owner));
    if (initialView === "contract-receivable-dept") rows = rows.filter((row) => row.department === profile.department);
    const text = (value: unknown) => String(value || "").toLowerCase();
    if (query.contract_body) rows = rows.filter((row) => (row.data.contract_body || "律所") === query.contract_body);
    if (query.contract_no) rows = rows.filter((row) => text(row.serial_no).includes(text(query.contract_no)));
    if (query.customer) rows = rows.filter((row) => text(row.customer).includes(text(query.customer)));
    if (query.case_no) rows = rows.filter((row) => text(row.data.case_no).includes(text(query.case_no)));
    if (query.source_person) rows = rows.filter((row) => text(row.data.source_person || row.owner).includes(text(query.source_person)));
    if (query.contract_date?.length === 2) rows = rows.filter((row) => row.data.signed_at && dayjs(row.data.signed_at).isAfter(query.contract_date[0].subtract(1, "day")) && dayjs(row.data.signed_at).isBefore(query.contract_date[1].add(1, "day")));
    return rows;
  }, [contracts, initialView, profile, query]);

  const contractById = useMemo(() => new Map(contracts.map((row) => [row.id, row])), [contracts]);
  const detailRows = useMemo(() => receivables.filter((item) => {
    const contract = contractById.get(item.contract_record_id);
    if (!contract) return false;
    if (query.contract_body && (contract.data.contract_body || "律所") !== query.contract_body) return false;
    if (query.contract_no && !contract.serial_no.toLowerCase().includes(String(query.contract_no).toLowerCase())) return false;
    if (query.customer && !contract.customer.toLowerCase().includes(String(query.customer).toLowerCase())) return false;
    if (query.case_no && !String(contract.data.case_no || "").toLowerCase().includes(String(query.case_no).toLowerCase())) return false;
    if (query.source_person && !String(contract.data.source_person || contract.owner).toLowerCase().includes(String(query.source_person).toLowerCase())) return false;
    return true;
  }), [receivables, contractById, query]);

  const listColumns = [
    { title: "合同号", dataIndex: "serial_no", width: 130 },
    { title: "合同名称", dataIndex: "title", width: 210, ellipsis: true },
    { title: "合同状态", dataIndex: "status", width: 90 },
    { title: "官费支付金额", key: "official_paid", width: 110, align: "right" as const, render: (_: unknown, row: Contract) => money(row.data.official_paid) },
    { title: "官费到账金额", key: "official_received", width: 110, align: "right" as const, render: (_: unknown, row: Contract) => money(row.data.official_received) },
    { title: "官费未到金额", key: "official_unreceived", width: 110, align: "right" as const, render: (_: unknown, row: Contract) => money(row.data.official_unreceived) },
    { title: "官费亏损金额", key: "official_loss", width: 110, align: "right" as const, render: (_: unknown, row: Contract) => money(row.data.official_loss) },
    { title: "代理费总金额", key: "agency_total", width: 110, align: "right" as const, render: (_: unknown, row: Contract) => money(row.data.agency_total) },
    { title: "代理费到账金额", key: "agency_received", width: 110, align: "right" as const, render: (_: unknown, row: Contract) => money(row.data.agency_received) },
    { title: "代理费待收金额", key: "agency_due", width: 110, align: "right" as const, render: (_: unknown, row: Contract) => money(row.data.agency_due) },
    { title: "案源人", key: "source", width: 90, render: (_: unknown, row: Contract) => row.data.source_person || row.owner },
    { title: "客户管理人", key: "manager", width: 100, render: (_: unknown, row: Contract) => row.data.customer_manager || "—" },
    { title: "签订日期", key: "signed_at", width: 105, render: (_: unknown, row: Contract) => row.data.signed_at || "—" },
    { title: "客户名称", dataIndex: "customer", width: 190, ellipsis: true },
  ];
  const detailColumns = [
    { title: "合同号", dataIndex: "contract_no", width: 130 },
    { title: "合同名称", dataIndex: "contract_title", width: 200, ellipsis: true },
    { title: "官费支付金额", key: "official_paid", width: 110, render: (_: unknown, row: Receivable) => money(contractById.get(row.contract_record_id)?.data.official_paid) },
    { title: "官费到账金额", key: "official_received", width: 110, render: (_: unknown, row: Receivable) => money(contractById.get(row.contract_record_id)?.data.official_received) },
    { title: "官费未到金额", key: "official_unreceived", width: 110, render: (_: unknown, row: Receivable) => money(contractById.get(row.contract_record_id)?.data.official_unreceived) },
    { title: "官费亏损金额", key: "official_loss", width: 110, render: (_: unknown, row: Receivable) => money(contractById.get(row.contract_record_id)?.data.official_loss) },
    { title: "代理费总金额", key: "agency_total", width: 110, render: (_: unknown, row: Receivable) => money(contractById.get(row.contract_record_id)?.data.agency_total) },
    { title: "代理费到账金额", key: "agency_received", width: 110, render: (_: unknown, row: Receivable) => money(contractById.get(row.contract_record_id)?.data.agency_received) },
    { title: "代理费待收金额", key: "agency_due", width: 110, render: (_: unknown, row: Receivable) => money(contractById.get(row.contract_record_id)?.data.agency_due) },
    { title: "案号", key: "case_no", width: 130, render: (_: unknown, row: Receivable) => contractById.get(row.contract_record_id)?.data.case_no || "—" },
    { title: "案件阶段", dataIndex: "phase", width: 110 },
    { title: "案件类型", key: "case_type", width: 110, render: (_: unknown, row: Receivable) => contractById.get(row.contract_record_id)?.data.case_type || "—" },
    { title: "费用类型", key: "fee_type", width: 110, render: (_: unknown, row: Receivable) => contractById.get(row.contract_record_id)?.data.fee_type || "代理费" },
    { title: "费用金额", dataIndex: "amount", width: 105, align: "right" as const, render: money },
    { title: "已收", dataIndex: "received_amount", width: 105, align: "right" as const, render: money },
    { title: "应收", dataIndex: "remaining_amount", width: 105, align: "right" as const, render: money },
  ];

  const exportExcel = () => {
    const header = detailView
      ? ["合同号", "合同名称", "官费支付金额", "官费到账金额", "官费未到金额", "官费亏损金额", "代理费总金额", "代理费到账金额", "代理费待收金额", "案号", "案件阶段", "案件类型", "费用类型", "费用金额", "已收", "应收"]
      : ["合同号", "合同名称", "合同状态", "官费支付金额", "官费到账金额", "官费未到金额", "官费亏损金额", "代理费总金额", "代理费到账金额", "代理费待收金额", "案源人", "客户管理人", "签订日期", "客户名称"];
    const body = detailView
      ? detailRows.map((row) => {
          const contract = contractById.get(row.contract_record_id);
          return [row.contract_no, row.contract_title, contract?.data.official_paid, contract?.data.official_received, contract?.data.official_unreceived, contract?.data.official_loss, contract?.data.agency_total, contract?.data.agency_received, contract?.data.agency_due, contract?.data.case_no, row.phase, contract?.data.case_type, contract?.data.fee_type || "代理费", row.amount, row.received_amount, row.remaining_amount];
        })
      : visibleContracts.map((row) => [row.serial_no, row.title, row.status, row.data.official_paid, row.data.official_received, row.data.official_unreceived, row.data.official_loss, row.data.agency_total, row.data.agency_received, row.data.agency_due, row.data.source_person || row.owner, row.data.customer_manager || "", row.data.signed_at || "", row.customer]);
    const quote = (value: unknown) => `"${String(value ?? "").replace(/"/g, '""')}"`;
    const csv = `\ufeff${[header, ...body].map((row) => row.map(quote).join(",")).join("\r\n")}`;
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `${detailView ? "应收款明细" : "应收账款统计"}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return <Card className="panel contract-original-panel" title={detailView ? "应收账款明细" : "应收账款统计"}>
    <Form form={form} className="contract-query" onFinish={setQuery}>
      <Form.Item label="合同主体" name="contract_body"><Select allowClear placeholder="请选择" options={["律所", "平台"].map((value) => ({ value, label: value }))} /></Form.Item>
      <Form.Item label="合同编号" name="contract_no"><Input placeholder="合同编号" /></Form.Item>
      <Form.Item label="合同日期" name="contract_date"><DatePicker.RangePicker /></Form.Item>
      <Form.Item label="客户名称" name="customer"><Input placeholder="客户名称" /></Form.Item>
      <Form.Item label="案件编号" name="case_no"><Input placeholder="案号" /></Form.Item>
      <Form.Item label="案源人" name="source_person"><Input /></Form.Item>
      <Form.Item className="contract-query-submit"><Button type="primary" htmlType="submit">查询</Button></Form.Item>
    </Form>
    {detailView ? (
      <Table<Receivable> className="contract-original-table" rowKey="id" loading={loading} size="small" rowSelection={{}} columns={detailColumns} dataSource={detailRows} locale={{ emptyText: "没有查询到符合条件的记录" }} scroll={{ x: 1900 }} pagination={{ pageSize: 15, showTotal: (total) => `共 ${total} 条` }} />
    ) : (
      <Table<Contract> className="contract-original-table" rowKey="id" loading={loading} size="small" rowSelection={{}} columns={listColumns} dataSource={visibleContracts} locale={{ emptyText: "没有查询到符合条件的记录" }} scroll={{ x: 1750 }} pagination={{ pageSize: 15, showTotal: (total) => `共 ${total} 条` }} />
    )}
    <div className="contract-bottom-actions"><Button onClick={exportExcel}>导出Excel</Button></div>
  </Card>;
}
