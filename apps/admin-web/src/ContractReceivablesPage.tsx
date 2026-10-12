import { useEffect, useMemo, useState } from "react";
import { Button, Card, DatePicker, Form, Input, InputNumber, message, Modal, Select, Space } from "antd";
import Table from "./components/ResizableTable";
import dayjs from "dayjs";
import { api } from "./api";
import { rememberCaseDetailTarget } from "./caseDetailNavigation";
import { rememberContractDetailTarget } from "./contractDetailNavigation";
import { rememberCustomerDetailTarget } from "./customerDetailNavigation";
import { resolveDetailRelation } from "./detailRelationResolver";
import { formatRequiredDate } from "./formSafety";
import "./contract-center.css";

type Receivable = {
  id: number | string;
  contract_record_id: number;
  contract_no: string;
  contract_title: string;
  customer: string;
  phase: string;
  due_date: string;
  amount: number;
  paid_amount: number;
  received_amount: number;
  remaining_amount: number;
  status: string;
  owner: string;
  source_person: string;
  contract_body: string;
  contract_date: string;
  case_record_id?: number;
  case_no: string;
  case_stage: string;
  case_type: string;
  fee_type: string;
  fee_category: "official" | "agency";
  contract_totals: Record<string, number>;
};
type Contract = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  owner: string;
  owner_display_name?: string;
  department: string;
  data: Record<string, any>;
};
export type ReceivableDetailAmountFilter = "official-unreceived" | "official-loss" | "agency-due";
type ReceivableDetailContext = { contract_no: string; return_view: string; amount_filter?: ReceivableDetailAmountFilter; owner?: string };

const money = (value: unknown) => Number(value || 0).toFixed(2);
const personDisplayName = (value: unknown) => String(value || "").trim() || "姓名待维护";
const peopleDisplayNames = (value: unknown) => {
  const names = (Array.isArray(value) ? value : [value]).map((item) => String(item || "").trim()).filter(Boolean);
  return names.length ? names.join("、") : "姓名待维护";
};
export const shouldUseMyReceivablesPagination = (initialView: string) => ["contract-receivable-mine", "contract-receivable-dept"].includes(initialView);
export const shouldShowMyReceivablesSinglePageJumper = (initialView: string, rowCount: number, pageSize: number) => ["contract-receivable-mine", "contract-receivable-dept"].includes(initialView) && rowCount > 0 && rowCount <= pageSize;
export const receivablesDetailPageSizes = [10, 15, 20, 50, 100, 200];
export const shouldShowReceivablesDetailSinglePageJumper = (rowCount: number, pageSize: number) => rowCount > 0 && rowCount <= pageSize;
export const shouldShowReceivableCreateAction = (detailView: boolean) => !detailView;
export const shouldShowReceivableResetAction = (detailView: boolean) => !detailView;
export const shouldRenderReceivablesDetailSummary = (rowCount: number) => rowCount > 0;
export const receivableDetailAmountFilters: Record<string, ReceivableDetailAmountFilter> = {
  unCashedCaseOfficeFeeAmount: "official-unreceived",
  deficitCaseOfficeFeeAmount: "official-loss",
  unCashedCaseNonOfficeFeeAmount: "agency-due",
};
export const receivablesDetailSummaryKeys = ["official_paid", "official_received", "official_unreceived", "official_loss", "agency_total", "agency_received", "agency_due"];
const receivableDetailAmounts = (detail: Receivable) => ({
  official_paid: detail.fee_category === "official" ? Number(detail.paid_amount || 0) : 0,
  official_received: detail.fee_category === "official" ? Number(detail.received_amount || 0) : 0,
  official_unreceived: detail.fee_category === "official" ? Number(detail.remaining_amount || 0) : 0,
  official_loss: detail.fee_category === "official" && String(detail.phase || "").includes("亏损") ? Number(detail.remaining_amount || 0) : 0,
  agency_total: detail.fee_category === "agency" ? Number(detail.amount || 0) : 0,
  agency_received: detail.fee_category === "agency" ? Number(detail.received_amount || 0) : 0,
  agency_due: detail.fee_category === "agency" ? Number(detail.remaining_amount || 0) : 0,
});
export const calculateReceivablesDetailTotals = (rows: Array<{ contract_record_id: number }>, _contractById: Map<number, Contract>) => {
  const totals = Object.fromEntries(receivablesDetailSummaryKeys.map((key) => [key, 0])) as Record<string, number>;
  rows.forEach((row) => {
    const amounts = receivableDetailAmounts(row as Receivable);
    receivablesDetailSummaryKeys.forEach((key) => { totals[key] += amounts[key as keyof typeof amounts]; });
  });
  return totals;
};
export const buildReceivableCaseDetailRoute = (record: { id: number; serial_no: string }) => `case-detail-${record.id}-${encodeURIComponent(record.serial_no)}`;
export const receivableDetailReturnView = (initialView: string) => ["contract-receivable-mine", "contract-receivable-dept", "contract-receivable-company"].includes(initialView) ? initialView : "contract-receivable-mine";
export const matchesReceivableDetailContract = (detailContractNo: unknown, contractNo: unknown) => !String(detailContractNo || "").trim() || String(detailContractNo).trim() === String(contractNo || "").trim();
export const buildReceivableDetailContext = (contractNo: unknown, initialView: string, amountFilter?: ReceivableDetailAmountFilter): ReceivableDetailContext => ({
  contract_no: String(contractNo || "").trim(),
  return_view: receivableDetailReturnView(initialView),
  ...(amountFilter ? { amount_filter: amountFilter } : {}),
});
export const matchesReceivableDetailAmountFilter = (row: Pick<Receivable, "phase" | "fee_category" | "remaining_amount">, _contract: Contract | undefined, amountFilter?: ReceivableDetailAmountFilter) => {
  if (!amountFilter) return true;
  const official = row.fee_category === "official";
  const remainsDue = Number(row.remaining_amount || 0) > 0;
  if (amountFilter === "agency-due") return !official && remainsDue;
  if (amountFilter === "official-loss") return official && remainsDue && String(row.phase || "").includes("亏损");
  return official && remainsDue;
};
export const calculateReceivablesListTotals = (rows: Contract[]) => {
  const totals = Object.fromEntries(receivablesDetailSummaryKeys.map((key) => [key, 0])) as Record<string, number>;
  rows.forEach((row) => receivablesDetailSummaryKeys.forEach((key) => { totals[key] += Number(row.data[key] || 0); }));
  return totals;
};

const readReceivableDetailContext = (): ReceivableDetailContext | null => {
  try {
    const parsed = JSON.parse(sessionStorage.getItem("sunhold:receivable-detail-context") || "") as ReceivableDetailContext;
    if ((parsed?.contract_no || parsed?.amount_filter) && receivableDetailReturnView(parsed.return_view) === parsed.return_view) return parsed;
  } catch {
    // A direct menu entry remains available when no short-lived navigation context exists.
  }
  return null;
};

export default function ContractReceivablesPage({ initialView, dashboardQueue = "", onNavigate }: { initialView: string; dashboardQueue?: string; onNavigate?: (route: string) => void }) {
  const [receivables, setReceivables] = useState<Receivable[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState<Record<string, any>>({});
  const [creating, setCreating] = useState(false);
  const [listPage, setListPage] = useState(1);
  const [listPageSize, setListPageSize] = useState(10);
  const [detailPage, setDetailPage] = useState(1);
  const [detailPageSize, setDetailPageSize] = useState(10);
  const [detailContext, setDetailContext] = useState<ReceivableDetailContext | null>(null);
  const [form] = Form.useForm();
  const [receivableForm] = Form.useForm();
  const detailView = initialView === "contract-receivable-detail";

  useEffect(() => {
    if (!detailView) return setDetailContext(null);
    if (dashboardQueue) {
      setDetailContext({ contract_no: "", return_view: "contract-receivable-mine", amount_filter: "official-unreceived" });
      return;
    }
    const context = readReceivableDetailContext();
    if (context) setDetailContext(context);
  }, [detailView]);

  const load = async () => {
    setLoading(true);
    try {
      const [receivableRes, contractRes] = await Promise.all([
        api.get("/receivables/detail", { params: { dashboard_queue: dashboardQueue || undefined } }),
        dashboardQueue ? Promise.resolve(null) : api.get("/contracts/receivables/contracts", { params: {
          scope: detailView ? "all" : initialView === "contract-receivable-mine" ? "mine" : initialView === "contract-receivable-dept" ? "department" : "company",
          contract_no: query.contract_no, customer: query.customer, case_no: detailView ? undefined : query.case_no,
          contract_body: query.contract_body, source_person: query.source_person,
          signed_at_start: query.contract_date?.[0]?.format("YYYY-MM-DD"),
          signed_at_end: query.contract_date?.[1]?.format("YYYY-MM-DD"),
        } }),
      ]);
      setReceivables(receivableRes.data.items || []);
      setContracts(contractRes?.data.items || []);
    } catch {
      message.error("合同应收加载失败");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { void load(); }, [initialView, query]);

  const visibleContracts = contracts;

  const contractById = useMemo(() => new Map(contracts.map((row) => [row.id, row])), [contracts]);
  const openContract = (contract: { id?: number | string; serial_no?: string; contract_no?: string; contract_record_id?: number }) => {
    rememberContractDetailTarget({ id: contract.contract_record_id || (typeof contract.id === "number" ? contract.id : undefined), serial_no: contract.serial_no || contract.contract_no });
    onNavigate?.("contract-my");
  };
  const openReceivableDetail = (contract: { serial_no?: string; contract_no?: string }, amountFilter?: ReceivableDetailAmountFilter) => {
    const contractNo = String(contract.serial_no || contract.contract_no || "").trim();
    if (!contractNo && !amountFilter) return;
    const context = buildReceivableDetailContext(contractNo, initialView, amountFilter);
    setDetailContext(context);
    try {
      sessionStorage.setItem("sunhold:receivable-detail-context", JSON.stringify(context));
    } catch {
      // The detail page can still open from its menu when session storage is unavailable.
    }
    onNavigate?.("contract-receivable-detail");
  };
  const openCase = async (serialNo: unknown, returnContractNo?: unknown) => {
    const value = String(serialNo || "").trim();
    if (!value) return;
    try {
      const record = await resolveDetailRelation("case", { serial_no: value });
      if (!record) return message.warning("未找到关联案件或当前账号无权查看");
      rememberCaseDetailTarget({ id: record.id, serial_no: record.serial_no });
      const contractNo = String(returnContractNo || detailContext?.contract_no || "").trim();
      if (contractNo && detailContext?.return_view) {
        try {
          sessionStorage.setItem("sunhold:receivable-detail-context", JSON.stringify({ contract_no: contractNo, return_view: detailContext.return_view, amount_filter: detailContext.amount_filter }));
        } catch {
          // Returning to the unfiltered detail list remains available when session storage is unavailable.
        }
      }
      try {
        sessionStorage.setItem("sunhold:case-list-return", JSON.stringify({ route: "contract-receivable-detail", page: 1, pageSize: 10 }));
      } catch {
        // The case detail can still be closed to the current case list.
      }
      onNavigate?.(buildReceivableCaseDetailRoute(record));
    } catch (error: any) { message.error(error?.response?.data?.detail || "关联案件加载失败"); }
  };
  const openCustomer = async (name: unknown) => {
    const title = String(name || "").trim();
    if (!title) return;
    try {
      const record = await resolveDetailRelation("customer", { title });
      if (!record) return message.warning("未找到关联客户或当前账号无权查看");
      rememberCustomerDetailTarget({ id: record.id, title: record.title, serial_no: record.serial_no });
      onNavigate?.("customer-management");
    } catch (error: any) { message.error(error?.response?.data?.detail || "关联客户加载失败"); }
  };
  const detailRows = useMemo(() => receivables.filter((item) => {
    const contract = contractById.get(item.contract_record_id);
    if (!matchesReceivableDetailContract(detailContext?.contract_no, item.contract_no)) return false;
    if (detailContext?.owner && item.owner !== detailContext.owner) return false;
    if (query.contract_body && item.contract_body !== query.contract_body) return false;
    if (query.contract_no && !item.contract_no.toLowerCase().includes(String(query.contract_no).toLowerCase())) return false;
    if (query.customer && !item.customer.toLowerCase().includes(String(query.customer).toLowerCase())) return false;
    if (query.case_no && !item.case_no.toLowerCase().includes(String(query.case_no).toLowerCase())) return false;
    if (query.source_person && !item.source_person.toLowerCase().includes(String(query.source_person).toLowerCase())) return false;
    if (query.contract_date?.length === 2 && (!item.contract_date || !dayjs(item.contract_date).isAfter(query.contract_date[0].subtract(1, "day")) || !dayjs(item.contract_date).isBefore(query.contract_date[1].add(1, "day")))) return false;
    if (!matchesReceivableDetailAmountFilter(item, contract, detailContext?.amount_filter)) return false;
    return true;
  }), [receivables, contractById, detailContext, query]);
  const detailSummary = useMemo(() => calculateReceivablesDetailTotals(detailRows, contractById), [detailRows, contractById]);
  const listSummary = useMemo(() => calculateReceivablesListTotals(visibleContracts), [visibleContracts]);
  const renderDetailSummaryRow = (totals: Record<string, number>, visible = true) => visible ? <tr className="contract-detail-summary-row"><td /><td /><td />{receivablesDetailSummaryKeys.map((key) => <td key={key} style={{ textAlign: "right" }}><strong>{money(totals[key])}</strong></td>)}{Array.from({ length: 7 }, (_, index) => <td key={index} />)}</tr> : null;
  const renderReceivablesListSummaryRow = (totals: Record<string, number>, visible = true) => visible ? <tr className="contract-list-summary-row"><td /><td /><td />
    <td>{money(totals.official_paid)}</td><td>{money(totals.official_received)}</td>
    <td><Button type="link" onClick={() => openReceivableDetail({}, "official-unreceived")}>{money(totals.official_unreceived)}</Button></td>
    <td><Button type="link" onClick={() => openReceivableDetail({}, "official-loss")}>{money(totals.official_loss)}</Button></td>
    <td>{money(totals.agency_total)}</td><td>{money(totals.agency_received)}</td>
    <td><Button type="link" onClick={() => openReceivableDetail({}, "agency-due")}>{money(totals.agency_due)}</Button></td>
    {Array.from({ length: 4 }, (_, index) => <td key={index} />)}</tr> : null;

  const openCreateReceivable = () => {
    receivableForm.resetFields();
    receivableForm.setFieldsValue({ due_date: dayjs() });
    setCreating(true);
  };
  const createReceivable = async () => {
    const values = await receivableForm.validateFields();
    try {
      await api.post("/receivables", {
        ...values,
        due_date: formatRequiredDate(values.due_date, "到期日"),
      });
      message.success("应收计划已创建");
      setCreating(false);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "应收计划创建失败");
    }
  };

  const listColumns = [
    { title: "合同号", dataIndex: "serial_no", width: 130, render: (_: unknown, row: Contract) => <Button type="link" onClick={() => openReceivableDetail(row)}>{row.serial_no}</Button> },
    { title: "合同名称", dataIndex: "title", width: 210, ellipsis: true },
    { title: "合同状态", dataIndex: "status", width: 90 },
    { title: "官费支付金额", key: "official_paid", width: 110, align: "right" as const, render: (_: unknown, row: Contract) => money(row.data.official_paid) },
    { title: "官费到账金额", key: "official_received", width: 110, align: "right" as const, render: (_: unknown, row: Contract) => money(row.data.official_received) },
    { title: "官费未到金额", key: "official_unreceived", width: 110, align: "right" as const, render: (_: unknown, row: Contract) => <Button type="link" onClick={() => openReceivableDetail(row, "official-unreceived")}>{money(row.data.official_unreceived)}</Button> },
    { title: "官费亏损金额", key: "official_loss", width: 110, align: "right" as const, render: (_: unknown, row: Contract) => <Button type="link" onClick={() => openReceivableDetail(row, "official-loss")}>{money(row.data.official_loss)}</Button> },
    { title: "代理费总金额", key: "agency_total", width: 110, align: "right" as const, render: (_: unknown, row: Contract) => money(row.data.agency_total) },
    { title: "代理费到账金额", key: "agency_received", width: 110, align: "right" as const, render: (_: unknown, row: Contract) => money(row.data.agency_received) },
    { title: "代理费待收金额", key: "agency_due", width: 110, align: "right" as const, render: (_: unknown, row: Contract) => <Button type="link" onClick={() => openReceivableDetail(row, "agency-due")}>{money(row.data.agency_due)}</Button> },
    { title: "案源人", key: "source", width: 90, render: (_: unknown, row: Contract) => personDisplayName(row.data.source_person_display_name || row.owner_display_name) },
    { title: "客户管理人", key: "manager", width: 100, render: (_: unknown, row: Contract) => peopleDisplayNames(row.data.customer_manager_display_names || row.data.customer_manager_display_name) },
    { title: "签订日期", key: "signed_at", width: 105, render: (_: unknown, row: Contract) => row.data.signed_at || "—" },
    { title: "客户名称", dataIndex: "customer", width: 190, ellipsis: true, render: (value: string) => <Button type="link" onClick={() => openCustomer(value)}>{value}</Button> },
  ];
  const detailColumns = [
    { title: "合同号", dataIndex: "contract_no", width: 130, render: (_: unknown, row: Receivable) => <Button type="link" onClick={() => openContract(row)}>{row.contract_no}</Button> },
    { title: "合同名称", dataIndex: "contract_title", width: 200, ellipsis: true, render: (value: string, row: Receivable) => value || contractById.get(row.contract_record_id)?.title },
    ...receivablesDetailSummaryKeys.map((key, index) => ({
      title: ["官费支付金额", "官费到账金额", "官费未到金额", "官费亏损金额", "代理费总金额", "代理费到账金额", "代理费待收金额"][index],
      key, width: 110, align: "right" as const,
      render: (_: unknown, row: Receivable) => money(receivableDetailAmounts(row)[key as keyof ReturnType<typeof receivableDetailAmounts>]),
    })),
    { title: "案号", key: "case_no", width: 130, render: (_: unknown, row: Receivable) => {
      const caseNo = row.case_no;
              return caseNo ? <Button type="link" className="receivable-case-link" style={{ maxWidth: "100%", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", textAlign: "left" }} onClick={() => void openCase(caseNo, row.contract_no)}>{caseNo}</Button> : "—";
    } },
    { title: "案件阶段", dataIndex: "case_stage", width: 110 },
    { title: "案件类型", dataIndex: "case_type", width: 110, align: "right" as const, render: (value: string) => value || "—" },
    { title: "费用类型", dataIndex: "fee_type", width: 110 },
    { title: "费用金额", dataIndex: "amount", width: 105, align: "right" as const, render: money },
    { title: "已收", dataIndex: "received_amount", width: 105, align: "right" as const, render: money },
    { title: "应收", dataIndex: "remaining_amount", width: 105, align: "right" as const, render: money },
  ];

  const exportExcel = async () => {
    try {
      const response = await api.get("/contracts/receivables/export-excel", {
        responseType: "blob",
        params: {
          detail: detailView,
          scope: initialView === "contract-receivable-mine" ? "mine" : initialView === "contract-receivable-dept" ? "department" : "company",
          contract_no: query.contract_no, customer: query.customer, case_no: query.case_no,
          contract_body: query.contract_body, source_person: query.source_person,
          signed_at_start: query.contract_date?.[0]?.format("YYYY-MM-DD"),
          signed_at_end: query.contract_date?.[1]?.format("YYYY-MM-DD"),
          detail_contract_no: detailContext?.contract_no, amount_filter: detailContext?.amount_filter,
          owner: detailContext?.owner, dashboard_queue: dashboardQueue || undefined,
        },
      });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${detailView ? "应收款明细" : "应收账款统计"}.xls`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      let detail = "合同应收导出失败";
      if (error?.response?.data instanceof Blob) {
        try { detail = JSON.parse(await error.response.data.text()).detail || detail; } catch { /* 非 JSON 响应保留导出失败提示。 */ }
      }
      message.error(detail);
    }
  };

  return <Card className="panel contract-original-panel" title={dashboardQueue ? "未到官费" : detailView ? "应收账款明细" : "应收账款统计"}>
    <Form form={form} className="contract-query" onFinish={setQuery}>
      <Form.Item label="合同主体" name="contract_body"><Select allowClear placeholder="请选择" options={["律所", "平台"].map((value) => ({ value, label: value }))} /></Form.Item>
      <Form.Item label="合同编号" name="contract_no"><Input placeholder="合同编号" /></Form.Item>
      <Form.Item label="合同日期" name="contract_date"><DatePicker.RangePicker /></Form.Item>
      <Form.Item label="客户名称" name="customer"><Input placeholder="客户名称" /></Form.Item>
      <Form.Item label="案件编号" name="case_no"><Input placeholder="案号" /></Form.Item>
      <Form.Item label="案源人" name="source_person"><Input /></Form.Item>
      <Form.Item className="contract-query-submit">
        <Button type="primary" htmlType="submit">查询</Button>
        {shouldShowReceivableResetAction(detailView) && <Button onClick={() => { form.resetFields(); setQuery({}); }}>重置</Button>}
      </Form.Item>
    </Form>
    {detailView ? (
      <><Table<Receivable> className="contract-original-table" rowKey="id" loading={loading} size="small" rowSelection={{}} columns={detailColumns} components={{ header: { wrapper: ({ children, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) => <thead {...props}>{children}{renderDetailSummaryRow(detailSummary, shouldRenderReceivablesDetailSummary(detailRows.length))}</thead> } }} dataSource={detailRows} locale={{ emptyText: "没有查询到符合条件的记录" }} scroll={{ x: 1900 }} pagination={{ current: detailPage, pageSize: detailPageSize, showSizeChanger: true, pageSizeOptions: receivablesDetailPageSizes, showQuickJumper: { goButton: <Button size="small">GO</Button> }, onChange: (page, pageSize) => { setDetailPage(page); setDetailPageSize(pageSize); }, showTotal: (total) => `共 ${total} 条` }} summary={() => <Table.Summary>{renderDetailSummaryRow(detailSummary, shouldRenderReceivablesDetailSummary(detailRows.length))}</Table.Summary>} />
      {shouldShowReceivablesDetailSinglePageJumper(detailRows.length, detailPageSize) && <Space style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}><InputNumber size="small" min={1} max={1} value={1} controls={false} readOnly aria-label="页码"/><Button size="small" onClick={() => setDetailPage(1)}>GO</Button></Space>}</>
    ) : (
      <>{visibleContracts.length > 0 && <table className="contract-list-summary-top"><tbody>{renderReceivablesListSummaryRow(listSummary, true)}</tbody></table>}<Table<Contract> className="contract-original-table" rowKey="id" loading={loading} size="small" rowSelection={{}} columns={shouldUseMyReceivablesPagination(initialView) ? [...listColumns, { title: "", key: "legacy-empty-operation", width: 80 }] : listColumns} dataSource={visibleContracts} locale={{ emptyText: "没有查询到符合条件的记录" }} scroll={{ x: 1750 }} pagination={{ ...(shouldUseMyReceivablesPagination(initialView) ? { current: listPage, pageSize: listPageSize, showSizeChanger: true, pageSizeOptions: [10, 15, 20, 50, 100, 200], showQuickJumper: { goButton: <Button size="small">GO</Button> }, onChange: (page, pageSize) => { setListPage(page); setListPageSize(pageSize); } } : { pageSize: 15 }), showTotal: (total) => `共 ${total} 条` }} summary={() => <Table.Summary>{renderReceivablesListSummaryRow(listSummary, visibleContracts.length > 0)}</Table.Summary>} />
      {shouldShowMyReceivablesSinglePageJumper(initialView, visibleContracts.length, listPageSize) && <Space style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}><InputNumber size="small" min={1} max={1} value={1} controls={false} readOnly aria-label="页码"/><Button size="small" onClick={() => setListPage(1)}>GO</Button></Space>}</>
    )}
    <div className="contract-bottom-actions">{shouldShowReceivableCreateAction(detailView) && <Button type="primary" onClick={openCreateReceivable}>新增应收计划</Button>}<Button onClick={exportExcel}>导出Excel</Button></div>
    <Modal
      open={creating}
      title="新增应收计划"
      okText="创建计划"
      cancelText="取消"
      onOk={() => void createReceivable()}
      onCancel={() => setCreating(false)}
    >
      <Form form={receivableForm} layout="vertical">
        <Form.Item label="合同" name="contract_record_id" rules={[{ required: true, message: "请选择合同" }]}>
          <Select
            showSearch
            optionFilterProp="label"
            placeholder="选择可见合同"
            options={visibleContracts.filter((contract) => contract.status === "审批通过").map((contract) => ({ value: contract.id, label: `${contract.serial_no}｜${contract.title}` }))}
          />
        </Form.Item>
        <Form.Item label="应收阶段" name="phase" rules={[{ required: true, message: "请填写应收阶段" }]}><Input placeholder="例如：首期代理费" /></Form.Item>
        <Form.Item label="到期日" name="due_date" rules={[{ required: true, message: "请选择到期日" }]}><DatePicker style={{ width: "100%" }} /></Form.Item>
        <Form.Item label="应收金额" name="amount" rules={[{ required: true, message: "请填写应收金额" }]}><InputNumber min={0.01} precision={2} style={{ width: "100%" }} /></Form.Item>
        <Form.Item label="付款方" name="payer"><Input placeholder="默认使用合同客户" /></Form.Item>
        <Form.Item label="备注" name="remark"><Input.TextArea rows={3} /></Form.Item>
      </Form>
    </Modal>
  </Card>;
}
