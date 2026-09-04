import { useEffect, useState } from "react";
import { DownloadOutlined } from "@ant-design/icons";
import { Alert, Button, DatePicker, Empty, Form, Input, Select, Spin, Table, message } from "antd";import {
  Bar,
  BarChart,
  Cell,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "./api";
import { rememberCustomerDetailTarget, resolveCustomerDetailTarget } from "./customerDetailNavigation";
import "./report-center.css";

type ChartResult = { title: string; unit: ChartSpec["unit"]; items: { name: string; value: number }[] };
type Analytics = { charts: ChartResult[]; filter_options: { customers: string[]; lawyers: string[] }; source: "realtime" };
type ReportFilterValues = {
  customer?: string[];
  courtLawyer?: string[];
  handlingLawyer?: string;
  assistant?: string;
  investigator?: string;
  court?: string;
  groupMode?: string;
  sourceDate?: any;
  hearingDate?: any;
};

type ChartSpec = {
  title: string;
  unit: "天/案" | "元" | "百分比" | "个/案";
  metricKeys?: string[];
  limit?: number;
};

type PageSpec = {
  title: string;
  tab?: string;
  filter: "brand" | "lawyer" | "none" | "customer-roi";
  charts: ChartSpec[];
};

type CustomerRoiRow = {
  customer: string;
  customer_id?: number;
  customer_no?: string;
  department: string;
  employee: string;
  income: number;
  cost: number;
  profit: number;
  roi: number | null;
};

type CustomerRoiData = {
  view: "customer-roi";
  rows: CustomerRoiRow[];
  totals: Omit<CustomerRoiRow, "customer" | "department" | "employee">;
  filter_options: { departments: string[]; employees: string[] };
  source: "realtime";
  date_basis?: string;
  formula?: string;
};

type CustomerRoiFilterValues = {
  dateRange?: any;
  department?: string;
  employee?: string;
};

type StaffRoiFilterValues = {
  dateRange?: any;
  departmentId?: string | number;
};

type StaffRoiRow = {
  employee: string;
  employee_username?: string;
  department: string;
  performance: number;
  cost: number;
  roi: number | null;
};

type StaffRoiResponse = {
  items: StaffRoiRow[];
  filter_options?: { departments?: { id: string | number; name: string }[] };
};

const PAGE_SPECS: Record<string, PageSpec> = {
  "reports-brand": {
    title: "资金运营情况统计",
    tab: "按品牌统计",
    filter: "brand",
    charts: [
      { title: "资金回款周期统计", unit: "天/案", metricKeys: ["资金回款周期", "资金回款周期统计"] },
      { title: "资金亏损金额统计", unit: "元", metricKeys: ["资金亏损金额", "资金亏损金额统计"] },
      { title: "资金回报率统计", unit: "百分比", metricKeys: ["资金回报率", "资金回报率统计"] },
      { title: "资金亏损率统计", unit: "百分比", metricKeys: ["资金亏损率", "资金亏损率统计"] },
    ],
  },
  "reports-lawyer": {
    title: "资金运营情况统计",
    tab: "按开庭律师统计",
    filter: "lawyer",
    charts: [
      { title: "资金回款周期统计", unit: "天/案", metricKeys: ["资金回款周期", "资金回款周期统计"] },
      { title: "资金亏损金额统计", unit: "元", metricKeys: ["资金亏损金额", "资金亏损金额统计"] },
      { title: "资金回报率统计", unit: "百分比", metricKeys: ["资金回报率", "资金回报率统计"] },
      { title: "资金亏损率统计", unit: "百分比", metricKeys: ["资金亏损率", "资金亏损率统计"] },
    ],
  },
  "reports-refund": {
    title: "退费进度案件统计",
    filter: "none",
    charts: [
      { title: "准备资料进度案件数量", unit: "个/案" },
      { title: "客户盖章进度案件数量", unit: "个/案" },
      { title: "提交法院进度案件数量", unit: "个/案" },
      { title: "等待客户回款进度案件数量", unit: "个/案" },
    ],
  },
  "reports-execution-1": {
    title: "执行进度案件统计",
    filter: "none",
    charts: [
      { title: "一审待执行案件数量", unit: "个/案", limit: 20 },
      { title: "二审待执行案件数量", unit: "个/案", limit: 20 },
      { title: "准备材料案件数量", unit: "个/案", limit: 20 },
      { title: "提交法院案件数量", unit: "个/案", limit: 20 },
    ],
  },
};

PAGE_SPECS["reports-execution-2"] = {
  title: "执行进度案件统计",
  filter: "none",
  charts: [
    { title: "执行受理案件数量", unit: "个/案", limit: 20 },
    { title: "执行中止案件数量", unit: "个/案", limit: 20 },
    { title: "执行结案案件数量", unit: "个/案", limit: 20 },
    { title: "执行终本案件数量", unit: "个/案", limit: 20 },
  ],
};
PAGE_SPECS["reports-execution-3"] = {
  title: "执行进度案件统计",
  filter: "none",
  charts: [
    { title: "执行终结案件数量", unit: "个/案", limit: 20 },
    { title: "执行中止案件数量", unit: "个/案", limit: 20 },
  ],
};
PAGE_SPECS["reports-staff-roi"] = {
  title: "员工业绩ROI统计",
  filter: "none",
  charts: [],
};

PAGE_SPECS["reports-customer-roi"] = {
  title: "客户ROI统计",
  filter: "customer-roi",
  charts: [],
};

function Filters({ kind, options, onQuery }: { kind: "brand" | "lawyer"; options: Analytics["filter_options"]; onQuery: (values: ReportFilterValues) => void }) {
  const [form] = Form.useForm();

  return (
    <Form
      form={form}
      className="report-filter"
      initialValues={{ customer: [], courtLawyer: [], groupMode: "按律师分组统计" }}
      onFinish={onQuery}
    >
      <Form.Item className="report-filter-wide" label="客户名称" name="customer">
        <Select mode="multiple" showSearch optionFilterProp="label" maxTagCount="responsive" placeholder="请选择客户" options={options.customers.map(value => ({ value, label: value }))} />
      </Form.Item>
      <Form.Item className="report-filter-wide" label="开庭律师" name="courtLawyer">
        <Select mode="multiple" showSearch optionFilterProp="label" maxTagCount="responsive" placeholder="请选择" options={options.lawyers.map(value => ({ value, label: value }))} />
      </Form.Item>
      {kind === "brand" ? (
        <Form.Item label="经办律师" name="handlingLawyer">
          <Input placeholder="开庭律师" />
        </Form.Item>
      ) : (
        <Form.Item label="分组模式" name="groupMode">
          <Select
            options={[
              { value: "按律师分组统计", label: "按律师分组统计" },
              { value: "按文书分组统计", label: "按文书分组统计" },
            ]}
          />
        </Form.Item>
      )}
      <Form.Item label="律师助理" name="assistant">
        <Input />
      </Form.Item>
      <Form.Item label="案源时间" name="sourceDate">
        <DatePicker.RangePicker />
      </Form.Item>
      <Form.Item label="调查员" name="investigator">
        <Input />
      </Form.Item>
      <Form.Item label="法院名称" name="court">
        <Input />
      </Form.Item>
      <Form.Item label="开庭时间" name="hearingDate">
        <DatePicker.RangePicker />
      </Form.Item>
      <div className="report-filter-action">
        <Button type="primary" htmlType="submit">查询</Button>
        <Button onClick={()=>{form.resetFields(); onQuery({})}}>重置</Button>
      </div>
    </Form>
  );
}

function MetricChart({ spec, items }: { spec: ChartSpec; items: { name: string; value: number }[] }) {
  const chartItems = spec.limit ? items.slice(0, spec.limit) : items;
  return (
    <section className="report-chart-panel">
      <div className="report-chart-title">
        <span>{spec.title}</span>
        <span className="report-chart-unit">单位： {spec.unit}</span>
      </div>
      <div className="report-chart-body">
        {chartItems.length ? <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartItems} margin={{ top: 20, right: 24, bottom: 16, left: 4 }}>
            <CartesianGrid stroke="#ececec" vertical={false} />
            <XAxis dataKey="name" axisLine={{ stroke: "#d8d8d8" }} tickLine={false} tick={{ fill: "#777", fontSize: 11 }} />
            <YAxis
              allowDecimals={spec.unit !== "个/案"}
              domain={[0, "auto"]}
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#777", fontSize: 11 }}
            />
            <Tooltip formatter={(item) => [`${Number(item).toLocaleString()} ${spec.unit}`, spec.title]} />
            <Bar dataKey="value" fill="#36b978" maxBarSize={72} />
          </BarChart>
        </ResponsiveContainer> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前条件下暂无真实业务数据" />}
      </div>
    </section>
  );
}

const currency = (value: number) => Number(value || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const percentage = (value: number) => `${Number(value || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
const roiDisplay = (roi: number | null, cost: number) => Number(cost || 0) === 0 || roi === null ? "—" : percentage(roi);

function CustomerRoiReport({ onNavigate }: { onNavigate?: (route: string) => void }) {
  const [form] = Form.useForm<CustomerRoiFilterValues>();
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [data, setData] = useState<CustomerRoiData>({
    view: "customer-roi",
    rows: [],
    totals: { income: 0, cost: 0, profit: 0, roi: 0 },
    filter_options: { departments: [], employees: [] },
    source: "realtime",
  });

  const paramsFor = (values: CustomerRoiFilterValues) => ({
    date_from: values.dateRange?.[0]?.format("YYYY-MM-DD"),
    date_to: values.dateRange?.[1]?.format("YYYY-MM-DD"),
    department: values.department || undefined,
    employee: values.employee || undefined,
  });
  const load = async (values: CustomerRoiFilterValues = form.getFieldsValue()) => {
    setLoading(true);
    try {
      const { data: result } = await api.get<CustomerRoiData>("/reports/customer-roi", { params: paramsFor(values) });
      setData(result);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "客户ROI统计加载失败");
    } finally {
      setLoading(false);
    }
  };
  const exportReport = async () => {
    setExporting(true);
    try {
      const response = await api.get("/reports/customer-roi/export", { params: paramsFor(form.getFieldsValue()), responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "客户ROI统计.csv";
      link.click();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "客户ROI统计导出失败");
    } finally {
      setExporting(false);
    }
  };
  const openCustomer = async (row: CustomerRoiRow) => {
    const target = await resolveCustomerDetailTarget({ id: row.customer_id, serial_no: row.customer_no, title: row.customer });
    if (!target || !rememberCustomerDetailTarget(target)) {
      message.warning("未找到关联客户或当前账号无权查看");
      return;
    }
    onNavigate?.("customer-company");
  };

  useEffect(() => { void load({}); }, []);
  return (
    <div className="report-page report-customer-roi-page">
      <div className="report-page-heading">客户ROI统计</div>
      <Form form={form} className="report-filter report-customer-roi-filter" onFinish={values => void load(values)}>
        <Form.Item label="收付款日期" name="dateRange"><DatePicker.RangePicker /></Form.Item>
        <Form.Item label="归属部门" name="department"><Select allowClear showSearch optionFilterProp="label" placeholder="全部收付款归属部门" options={data.filter_options.departments.map(value => ({ value, label: value }))} /></Form.Item>
        <Form.Item label="负责人" name="employee"><Select allowClear showSearch optionFilterProp="label" placeholder="全部收付款负责人" options={data.filter_options.employees.map(value => ({ value, label: value }))} /></Form.Item>
        <div className="report-filter-action">
          <Button type="primary" htmlType="submit">查询</Button>
          <Button onClick={() => { form.resetFields(); void load({}); }}>重置</Button>
          <Button icon={<DownloadOutlined />} loading={exporting} onClick={() => void exportReport()}>导出CSV</Button>
        </div>
      </Form>
      <div className="report-roi-description">{data.date_basis || "收付款流水日期"}；{data.formula || "ROI＝（收入－成本）÷ 成本 × 100%"}，成本为 0 时显示“—”。部门和负责人按收付款归属筛选。</div>
      <div className="report-roi-table-panel">
        <Table<CustomerRoiRow>
          rowKey={(row) => `${row.customer}-${row.department}-${row.employee}`}
          loading={loading}
          dataSource={data.rows}
          locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前条件下暂无真实业务数据" /> }}
          pagination={{ pageSize: 20, showSizeChanger: true, showTotal: total => `共 ${total} 条` }}
          scroll={{ x: 1050 }}
          summary={() => (
            <Table.Summary.Row>
              <Table.Summary.Cell index={0} colSpan={3}>合计</Table.Summary.Cell>
              <Table.Summary.Cell index={3}>{currency(data.totals.income)}</Table.Summary.Cell>
              <Table.Summary.Cell index={4}>{currency(data.totals.cost)}</Table.Summary.Cell>
              <Table.Summary.Cell index={5}>{currency(data.totals.profit)}</Table.Summary.Cell>
              <Table.Summary.Cell index={6}>{roiDisplay(data.totals.roi, data.totals.cost)}</Table.Summary.Cell>
            </Table.Summary.Row>
          )}
          columns={[
            { title: "客户", dataIndex: "customer", width: 240, ellipsis: true, render: (value, row) => <Button type="link" className="report-roi-customer-link" onClick={() => void openCustomer(row)}>{value || "—"}</Button> },
            { title: "部门", dataIndex: "department", width: 170, ellipsis: true, render: value => value || "—" },
            { title: "员工", dataIndex: "employee", width: 160, ellipsis: true, render: value => value || "—" },
            { title: "收入（元）", dataIndex: "income", width: 150, align: "right", render: currency },
            { title: "成本（元）", dataIndex: "cost", width: 150, align: "right", render: currency },
            { title: "利润（元）", dataIndex: "profit", width: 150, align: "right", render: currency },
            { title: "ROI", dataIndex: "roi", width: 130, align: "right", render: (value, row) => roiDisplay(value, row.cost) },
          ]}
        />
      </div>
    </div>
  );
}


function StaffRoiReport() {
  const [form] = Form.useForm<StaffRoiFilterValues>();
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState<StaffRoiRow[]>([]);
  const [departments, setDepartments] = useState<{ id: string | number; name: string }[]>([]);

  const paramsFor = (values: StaffRoiFilterValues) => ({
    start_date: values.dateRange?.[0]?.format("YYYY-MM-DD"),
    end_date: values.dateRange?.[1]?.format("YYYY-MM-DD"),
    department_id: values.departmentId || undefined,
  });
  const load = async (values: StaffRoiFilterValues = form.getFieldsValue()) => {
    setLoading(true);
    try {
      const { data } = await api.get<StaffRoiResponse>("/reports/staff-roi", { params: paramsFor(values) });
      setRows(data.items || []);
      setDepartments(data.filter_options?.departments || []);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "员工业绩ROI统计加载失败");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { void load({}); }, []);

  const reset = () => {
    form.resetFields();
    void load({});
  };
  const exportCsv = async () => {
    try {
      const response = await api.get("/reports/staff-roi/export", {
        params: paramsFor(form.getFieldsValue()),
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "员工业绩ROI统计.csv";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "员工业绩ROI统计导出失败");
    }
  };

  return (
    <div className="report-page">
      <div className="report-page-heading">员工业绩ROI统计</div>
      <div style={{ marginBottom: 16, color: "#666" }}>业绩按到账回款依员工提成比例分摊；成本为提成实际付款；ROI=业绩÷成本×100%，成本为0时不计算。</div>
      <Form form={form} className="report-filter" onFinish={load}>
        <Form.Item label="统计时间" name="dateRange">
          <DatePicker.RangePicker />
        </Form.Item>
        <Form.Item label="部门" name="departmentId">
          <Select allowClear showSearch optionFilterProp="label" placeholder="全部部门" options={(departments || []).map((item) => ({ value: item.id, label: item.name }))} />
        </Form.Item>
        <div className="report-filter-action">
          <Button type="primary" htmlType="submit">查询</Button>
          <Button onClick={reset}>重置</Button>
          <Button onClick={exportCsv}>导出CSV</Button>
        </div>
      </Form>
      <Spin spinning={loading}>
        <Table
          rowKey={(row) => `${row.department}-${row.employee_username || row.employee}`}
          dataSource={rows}
          pagination={{ showSizeChanger: true, showTotal: (total) => `共 ${total} 名员工` }}
          locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前条件下暂无真实业务数据" /> }}
          scroll={{ x: 760 }}
          columns={[
            { title: "员工", dataIndex: "employee", width: 180 },
            { title: "部门", dataIndex: "department", width: 160 },
            { title: "业绩（元）", dataIndex: "performance", align: "right", render: (value: number) => currency(value) },
            { title: "成本（元）", dataIndex: "cost", align: "right", render: (value: number) => currency(value) },
            { title: "ROI", dataIndex: "roi", align: "right", render: (value: number | null, row: StaffRoiRow) => roiDisplay(value, row.cost) },
          ]}
        />
      </Spin>
    </div>
  );
}

const largeScreenViews = ["reports-refund", "reports-execution-1", "reports-execution-2", "reports-execution-3"];
const LARGE_SCREEN_COLORS = ["#18c7bb", "#4e8cff", "#ffb95c", "#8a74e8", "#ef6d85", "#2cc47c"];

type LargeScreenData = {
  case_summary: { total: number; in_progress: number; closed: number };
  finance: { amount_visible: boolean; income: number | null; expense: number | null; income_label?: string; expense_label?: string };
  customer_summary: { total: number };
  employee_ranking: { username?: string; name: string; value: number }[];
  case_type_distribution: { name: string; value: number }[];
  monthly_trend: { month: string; cases: number; income: number | null; expense: number | null }[];
  definitions?: Record<string, string>;
  generated_at?: string;
};

const emptyLargeScreenData: LargeScreenData = {
  case_summary: { total: 0, in_progress: 0, closed: 0 },
  finance: { amount_visible: false, income: null, expense: null },
  customer_summary: { total: 0 },
  employee_ranking: [],
  case_type_distribution: [],
  monthly_trend: [],
};

const formatNumber = (value: number) => Number(value || 0).toLocaleString("zh-CN");
const formatCurrency = (value: number | null) => value == null ? "—" : `¥${Number(value).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function LargeScreenEmpty({ description = "暂无可展示的真实业务数据" }: { description?: string }) {
  return <Empty className="large-screen-empty" image={Empty.PRESENTED_IMAGE_SIMPLE} description={description} />;
}

export function ReportLargeScreenPage({ onExit }: { onExit?: () => void }) {
  const [screenMode, setScreenMode] = useState<"overview" | "legacy">("overview");
  const [legacyIndex, setLegacyIndex] = useState(0);
  const [fullscreen, setFullscreen] = useState(Boolean(document.fullscreenElement));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [data, setData] = useState<LargeScreenData>(emptyLargeScreenData);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get<LargeScreenData>("/reports/large-screen");
      setData({ ...emptyLargeScreenData, ...response.data, case_summary: { ...emptyLargeScreenData.case_summary, ...response.data.case_summary }, finance: { ...emptyLargeScreenData.finance, ...response.data.finance }, customer_summary: { ...emptyLargeScreenData.customer_summary, ...response.data.customer_summary } });
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || "大屏实时数据加载失败，请稍后重试。");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    const refreshTimer = window.setInterval(() => void load(), 60_000);
    const syncFullscreen = () => setFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", syncFullscreen);
    return () => {
      window.clearInterval(refreshTimer);
      document.removeEventListener("fullscreenchange", syncFullscreen);
    };
  }, []);

  useEffect(() => {
    if (screenMode !== "legacy") return;
    const timer = window.setInterval(() => setLegacyIndex(current => (current + 1) % largeScreenViews.length), 30_000);
    return () => window.clearInterval(timer);
  }, [screenMode]);

  const toggleFullscreen = () => {
    if (document.fullscreenElement) {
      void document.exitFullscreen?.();
      return;
    }
    void document.documentElement.requestFullscreen?.().catch(() => message.warning("当前浏览器不支持进入全屏模式"));
  };

  const rankingData = data.employee_ranking.slice(0, 8);
  const typeData = data.case_type_distribution;
  const trendData = data.monthly_trend;
  return (
    <div className="report-large-screen">
      <header className="large-screen-header">
        <div>
          <p>REPORTING CENTER · REALTIME</p>
          <h1>经营数据大屏</h1>
        </div>
        <div className="large-screen-actions">
          <Button type={screenMode === "overview" ? "primary" : "default"} onClick={() => setScreenMode("overview")}>综合概览</Button>
          <Button type={screenMode === "legacy" ? "primary" : "default"} onClick={() => setScreenMode("legacy")}>旧报表轮播</Button>
          <Button onClick={() => void load()} loading={loading}>刷新数据</Button>
          <Button onClick={toggleFullscreen}>{fullscreen ? "退出全屏" : "全屏展示"}</Button>
          {onExit && <Button onClick={onExit}>返回报表中心</Button>}
        </div>
      </header>
      {screenMode === "legacy" ? (
        <section className="large-screen-legacy">
          <div className="large-screen-legacy-note">旧版专题报表每 30 秒自动切换，可保留用于会议轮播展示。</div>
          <ReportCenterPage key={largeScreenViews[legacyIndex]} initialView={largeScreenViews[legacyIndex]} />
        </section>
      ) : (
        <Spin spinning={loading} tip="正在汇总实时数据">
          {error ? <Alert className="large-screen-alert" type="error" showIcon message="大屏数据未加载" description={error} action={<Button size="small" onClick={() => void load()}>重试</Button>} /> : (
            <main className="large-screen-content">
              <section className="large-screen-kpis" aria-label="业务概览">
                <article><span>案件总数</span><strong>{formatNumber(data.case_summary.total)}</strong><em>{data.definitions?.case_total || "符合统计条件的可见案件"}</em></article>
                <article><span>在办案件</span><strong>{formatNumber(data.case_summary.in_progress)}</strong><em>{data.definitions?.case_in_progress || "当前办理中"}</em></article>
                <article><span>已结案件</span><strong>{formatNumber(data.case_summary.closed)}</strong><em>{data.definitions?.case_closed || "已完成或归档"}</em></article>
                <article><span>财务收入</span><strong>{formatCurrency(data.finance.income)}</strong><em>{data.finance.amount_visible ? (data.definitions?.income || data.finance.income_label || "当前数据范围") : "无财务数据查看权限"}</em></article>
                <article><span>财务支出</span><strong>{formatCurrency(data.finance.expense)}</strong><em>{data.finance.amount_visible ? (data.definitions?.expense || data.finance.expense_label || "当前数据范围") : "无财务数据查看权限"}</em></article>
                <article><span>客户总数</span><strong>{formatNumber(data.customer_summary.total)}</strong><em>全部可见客户</em></article>
              </section>
              <section className="large-screen-grid">
                <article className="large-screen-card ranking-card">
                  <h2>员工业绩排行 <small>{data.definitions?.employee_ranking || "统计口径以系统数据为准"}</small></h2>
                  <div className="large-screen-chart">{rankingData.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={rankingData} layout="vertical" margin={{ top: 8, right: 24, bottom: 0, left: 14 }}><CartesianGrid stroke="#e8f0f2" horizontal={false} /><XAxis type="number" allowDecimals={false} /><YAxis type="category" dataKey="name" width={72} tick={{ fontSize: 12 }} /><Tooltip formatter={(value) => [formatNumber(Number(value)), "办案量"]} /><Bar dataKey="value" fill="#00a65a" radius={[0, 5, 5, 0]} maxBarSize={20} /></BarChart></ResponsiveContainer> : <LargeScreenEmpty />}</div>
                </article>
                <article className="large-screen-card distribution-card">
                  <h2>案件类型分布 <small>按案件数量</small></h2>
                  <div className="large-screen-chart">{typeData.length ? <ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={typeData} dataKey="value" nameKey="name" innerRadius="48%" outerRadius="72%" paddingAngle={3}>{typeData.map((entry, index) => <Cell key={`${entry.name}-${index}`} fill={LARGE_SCREEN_COLORS[index % LARGE_SCREEN_COLORS.length]} />)}</Pie><Tooltip formatter={(value) => [formatNumber(Number(value)), "案件"]} /><Legend /></PieChart></ResponsiveContainer> : <LargeScreenEmpty />}</div>
                </article>
                <article className="large-screen-card trend-card">
                  <h2>月度业务趋势 <small>{data.definitions?.monthly_trend || "最近12个月案件量与收支概览"}</small></h2>
                  <div className="large-screen-chart">{trendData.length ? <ResponsiveContainer width="100%" height="100%"><LineChart data={trendData} margin={{ top: 12, right: 28, bottom: 0, left: 0 }}><CartesianGrid stroke="#e8f0f2" vertical={false} /><XAxis dataKey="month" tick={{ fontSize: 12 }} /><YAxis yAxisId="count" allowDecimals={false} />{data.finance.amount_visible && <YAxis yAxisId="amount" orientation="right" tickFormatter={(value) => `${Math.round(Number(value) / 10000)}万`} />}<Tooltip formatter={(value, name) => [name === "案件量" ? formatNumber(Number(value)) : formatCurrency(value == null ? null : Number(value)), name]} /><Legend /><Line yAxisId="count" type="monotone" dataKey="cases" name="案件量" stroke="#00a65a" strokeWidth={3} dot={false} />{data.finance.amount_visible && <><Line yAxisId="amount" type="monotone" dataKey="income" name="收入" stroke="#3e8ef7" strokeWidth={2} dot={false} /><Line yAxisId="amount" type="monotone" dataKey="expense" name="支出" stroke="#ef7e56" strokeWidth={2} dot={false} /></>}</LineChart></ResponsiveContainer> : <LargeScreenEmpty />}</div>
                </article>
              </section>
              {data.generated_at && <p className="large-screen-updated">数据更新时间：{data.generated_at}</p>}
            </main>
          )}
        </Spin>
      )}
    </div>
  );
}

function StandardReportCenterPage({ initialView = "reports-brand", onNavigate }: { initialView?: string; onNavigate?: (route: string) => void }) {  const page = PAGE_SPECS[initialView] ?? PAGE_SPECS["reports-brand"];
  const [loading, setLoading] = useState(false);
  const [analytics, setAnalytics] = useState<Analytics>({ charts: [], filter_options: { customers: [], lawyers: [] }, source: "realtime" });
  const [query, setQuery] = useState<ReportFilterValues>({});
  const view = initialView.replace("reports-", "");

  const paramsFor = (values: ReportFilterValues) => ({
    view,
    customer: values.customer?.join(",") || "",
    court_lawyer: values.courtLawyer?.join(",") || "",
    handling_lawyer: values.handlingLawyer || "",
    assistant: values.assistant || "",
    investigator: values.investigator || "",
    court: values.court || "",
    group_mode: values.groupMode || "",
    source_from: values.sourceDate?.[0]?.format("YYYY-MM-DD"),
    source_to: values.sourceDate?.[1]?.format("YYYY-MM-DD"),
    hearing_from: values.hearingDate?.[0]?.format("YYYY-MM-DD"),
    hearing_to: values.hearingDate?.[1]?.format("YYYY-MM-DD"),
  });
  const load = async (values: ReportFilterValues = query) => {
    setLoading(true);
    try {
      const { data } = await api.get("/reports/analytics", { params: paramsFor(values) });
      setAnalytics(data);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "报表实时数据加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setQuery({});
    if (initialView !== "reports-customer-roi") void load({});
  }, [initialView]);
  const queryReport = (values: ReportFilterValues) => { setQuery(values); void load(values); };
  const chartItems = (title: string) => analytics.charts.find(item => item.title === title)?.items ?? [];
  if (initialView === "reports-customer-roi") return <CustomerRoiReport onNavigate={onNavigate} />;
  if (initialView === "reports-staff-roi") return <StaffRoiReport />;
  return (
    <div className={`report-page ${page.filter === "none" ? "report-page-no-filter" : ""}`}>
      <div className="report-page-heading">
        <span>{page.title}</span>
        {onNavigate && <Button size="small" type="primary" onClick={() => onNavigate("reports-large-screen")}>大屏展示</Button>}
      </div>
      {page.filter !== "none" && <Filters key={initialView} kind={page.filter} options={analytics.filter_options} onQuery={queryReport} />}      {page.tab && (
        <div className="report-tabs">
          <span className="report-tab-active">{page.tab}</span>
        </div>
      )}
      <Spin spinning={loading}>
        <div className={`report-chart-grid ${page.charts.length === 2 ? "report-chart-grid-two" : ""}`}>
          {page.charts.map((chart, index) => (
            <MetricChart key={`${chart.title}-${index}`} spec={chart} items={chartItems(chart.title)} />
          ))}
        </div>
      </Spin>
    </div>
  );
}

export default function ReportCenterPage({ initialView = "reports-brand", onNavigate }: { initialView?: string; onNavigate?: (route: string) => void }) {
  return initialView === "reports-large-screen"
    ? <ReportLargeScreenPage onExit={() => onNavigate?.("reports-brand")} />
    : <StandardReportCenterPage initialView={initialView} onNavigate={onNavigate} />;
}
