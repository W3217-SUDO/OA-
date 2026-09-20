import { useEffect, useState } from "react";
import { Alert, Button, Card, Descriptions, Input, InputNumber, message, Select, Space, Table } from "antd";
import { api } from "../api";
import { money } from "./constants";

type Allocation = { index: number; case_no: string; contract_no: string; case_title: string; case_type: string; court_keywords: string; fee_type: string; case_stage: string; plaintiff: string; defendant: string; fee_amount: number | null; fee_received: number | null; fee_remaining: number | null; amount: number; allocated_at: string };
type Result = { payment: { receipt_no: string; payer_name: string; received_date: string; amount: number; allocated_amount: number; remaining_amount: number; bank_reference: string; claimed_customer: string; claimant_display_name: string; contract_no: string; payment_method: string; remark: string }; items: Allocation[]; revision: string; can_cancel: boolean };

export function IncomingAllocationRecordsPage({ paymentId, onClose, onChange, onCase, onContract }: {
  paymentId: number; onClose: () => void; onChange: () => Promise<unknown>; onCase: (value: string) => unknown; onContract: (value: string) => unknown;
}) {
  const [result, setResult] = useState<Result>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<React.Key[]>([]);
  const [keyword, setKeyword] = useState("");
  const [stage, setStage] = useState<string>();
  const [feeType, setFeeType] = useState<string>();
  const [minimum, setMinimum] = useState<number | null>(null);
  const [maximum, setMaximum] = useState<number | null>(null);
  const [filters, setFilters] = useState({ keyword: "", stage: "", feeType: "", minimum: null as number | null, maximum: null as number | null });
  useEffect(() => {
    let active = true;
    setBusy(true);
    api.get<Result>(`/finance/incoming-payments/${paymentId}/allocation-records`).then(({ data }) => { if (active) setResult(data); }).catch((err) => { if (active) setError(err.response?.data?.detail || "分配记录加载失败"); }).finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [paymentId]);
  const cancel = async () => {
    if (!result || !selected.length || busy) return;
    setBusy(true); setError("");
    try {
      const { data } = await api.post<Result>(`/finance/incoming-payments/${paymentId}/allocation-records/cancel`, { revision: result.revision, indexes: selected });
      setResult(data); setSelected([]); await onChange(); message.success("已取消所选分配");
    } catch (err: any) { setError(err.response?.data?.detail || "取消分配失败"); }
    finally { setBusy(false); }
  };
  const rows = (result?.items || []).filter(row =>
    (!filters.keyword || [row.case_no, row.contract_no, row.plaintiff, row.defendant, row.case_title, row.court_keywords].some(value => String(value || "").includes(filters.keyword))) &&
    (!filters.stage || row.case_stage === filters.stage) && (!filters.feeType || row.fee_type === filters.feeType) &&
    (filters.minimum == null || row.amount >= filters.minimum) && (filters.maximum == null || row.amount <= filters.maximum));
  const options = (key: "case_stage" | "fee_type") => [...new Set((result?.items || []).map(row => row[key]).filter(Boolean))].map(value => ({ value, label: value }));
  const payment = result?.payment;
  return <Card title={`已分配回款记录：${payment?.receipt_no || ""}`} extra={<Button onClick={onClose}>返回列表</Button>}>
    {error && <Alert type="error" showIcon title={error} style={{ marginBottom: 12 }} />}
    <Descriptions bordered size="small" column={3} items={[
      { key: "payer", label: "回款单位", children: payment?.payer_name }, { key: "date", label: "到账日期", children: payment?.received_date },
      { key: "bank", label: "银行单号", children: payment?.bank_reference }, { key: "amount", label: "到账金额", children: payment ? money(payment.amount) : "—" },
      { key: "allocated", label: "已分配", children: payment ? money(payment.allocated_amount) : "—" },
      { key: "remaining", label: "未分配", children: payment ? money(payment.remaining_amount) : "—" },
      { key: "customer", label: "客户名称", children: payment?.claimed_customer },
      { key: "method", label: "回款方式", children: payment?.payment_method },
      { key: "claimant", label: "领取人", children: payment?.claimant_display_name },
      { key: "contract", label: "合同号", children: payment?.contract_no },
      { key: "remark", label: "备注", children: payment?.remark, span: 2 },
    ]} />
    <Space wrap style={{ margin: "16px 0" }}>
      <Input placeholder="案号、法院、原告、被告、案件名称" value={keyword} onChange={e => setKeyword(e.target.value)} style={{ width: 270 }} />
      <Select placeholder="案件阶段" allowClear value={stage} onChange={setStage} options={options("case_stage")} style={{ width: 155 }} />
      <Select placeholder="费用类型" allowClear value={feeType} onChange={setFeeType} options={options("fee_type")} style={{ width: 170 }} />
      <InputNumber placeholder="最小金额" value={minimum} onChange={setMinimum} min={0} /><InputNumber placeholder="最大金额" value={maximum} onChange={setMaximum} min={0} />
      <Button type="primary" onClick={() => { setFilters({ keyword: keyword.trim(), stage: stage || "", feeType: feeType || "", minimum, maximum }); setSelected([]); }}>查询</Button>
      <Button onClick={() => { setKeyword(""); setStage(undefined); setFeeType(undefined); setMinimum(null); setMaximum(null); setFilters({ keyword: "", stage: "", feeType: "", minimum: null, maximum: null }); setSelected([]); }}>清空</Button>
    </Space>
    <Table<Allocation> rowKey="index" loading={busy} dataSource={rows} size="small" scroll={{ x: 1200 }} rowSelection={{ selectedRowKeys: selected, onChange: setSelected }} columns={[
      { title: "案号", dataIndex: "case_no", width: 150, render: value => <Button type="link" onClick={() => onCase(value)}>{value}</Button> },
      { title: "合同号", dataIndex: "contract_no", width: 150, render: value => <Button type="link" onClick={() => onContract(value)}>{value}</Button> },
      { title: "案件类型", dataIndex: "case_type", width: 100 }, { title: "案件名称", dataIndex: "case_title", width: 180, ellipsis: true },
      { title: "原告", dataIndex: "plaintiff", ellipsis: true }, { title: "被告", dataIndex: "defendant", ellipsis: true },
      { title: "案件阶段", dataIndex: "case_stage" }, { title: "费用类型", dataIndex: "fee_type" },
      { title: "费用总额", dataIndex: "fee_amount", align: "right", render: value => value == null ? "—" : money(value) },
      { title: "已收", dataIndex: "fee_received", align: "right", render: value => value == null ? "—" : money(value) },
      { title: "待收", dataIndex: "fee_remaining", align: "right", render: value => value == null ? "—" : money(value) },
      { title: "分配金额", dataIndex: "amount", align: "right", render: money }, { title: "分配时间", dataIndex: "allocated_at", width: 180 },
    ]} />
    <Button danger disabled={!result?.can_cancel || !selected.length} loading={busy} onClick={() => void cancel()}>取消分配（{selected.length}）</Button>
  </Card>;
}
